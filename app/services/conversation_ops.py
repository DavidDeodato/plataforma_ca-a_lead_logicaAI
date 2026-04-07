from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AgentTask, Conversation, Lead, Message, WhatsappSession
from app.services.runtime_config import RuntimeConfigService
from app.services.wasender_client import WasenderClient
from app.services.whatsapp_sessions import WhatsappSessionService


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


PROVIDER_RATE_LIMIT_SECONDS = 60


class ConversationOpsService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.runtime_service = RuntimeConfigService()
        self.session_service = WhatsappSessionService()

    def apply_defaults(self, db: Session, conversation: Conversation) -> Conversation:
        runtime = self.runtime_service.get_runtime_config(db)
        if conversation.reply_delay_seconds is None:
            conversation.reply_delay_seconds = int(runtime["default_auto_reply_delay_seconds"])
        return conversation

    def can_auto_reply(self, db: Session, conversation: Conversation, *, lead: Lead | None = None) -> bool:
        runtime = self.runtime_service.get_runtime_config(db)
        inbound_scope = str(runtime.get("inbound_auto_reply_scope") or "known_only")
        if inbound_scope == "known_only" and lead is not None and getattr(lead, "inbound_unverified", False):
            return False
        return (
            bool(runtime["auto_reply_enabled"])
            and conversation.auto_reply_enabled
            and not conversation.manual_mode
            and not conversation.automation_paused
        )

    def take_over(self, conversation: Conversation, operator_name: str) -> Conversation:
        conversation.assignee = operator_name
        conversation.manual_mode = True
        conversation.automation_paused = True
        conversation.taken_over_by = operator_name
        conversation.taken_over_at = utcnow()
        conversation.pending_human_review = False
        conversation.pending_review_reason = None
        return conversation

    def release(self, conversation: Conversation) -> Conversation:
        conversation.manual_mode = False
        conversation.automation_paused = False
        conversation.taken_over_by = None
        conversation.taken_over_at = None
        conversation.pending_human_review = False
        conversation.pending_review_reason = None
        return conversation

    def mark_read(self, conversation: Conversation) -> Conversation:
        conversation.unread_count = 0
        return conversation

    def schedule_delayed_auto_reply(
        self,
        db: Session,
        *,
        lead: Lead,
        conversation: Conversation,
        review_required: bool = False,
        scheduled_reason: str = "inbound_reply",
    ) -> AgentTask:
        self.cancel_open_auto_reply_tasks(db, conversation.id)
        task = AgentTask(
            lead_id=lead.id,
            conversation_id=conversation.id,
            task_type="delayed_auto_reply",
            status="pending",
            next_run_at=utcnow() + timedelta(seconds=max(0, conversation.reply_delay_seconds)),
            scheduled_reason=scheduled_reason,
            review_required=review_required,
            payload={"conversation_id": conversation.id, "lead_id": lead.id},
        )
        db.add(task)
        return task

    def cancel_open_auto_reply_tasks(self, db: Session, conversation_id: int) -> None:
        tasks = list(
            db.scalars(
                select(AgentTask).where(
                    AgentTask.conversation_id == conversation_id,
                    AgentTask.task_type == "delayed_auto_reply",
                    AgentTask.status == "pending",
                )
            )
        )
        for task in tasks:
            task.status = "cancelled"
            task.last_result = "Cancelada por nova mensagem ou acao manual."

    def session_outbound_cooldown_seconds(self, session: WhatsappSession | None) -> int:
        if session is None or session.outbound_cooldown_seconds is None:
            return 0
        return max(0, int(session.outbound_cooldown_seconds))

    def next_outbound_slot(
        self,
        db: Session,
        *,
        outbound_session_id: int | None,
        delay_seconds: int = PROVIDER_RATE_LIMIT_SECONDS,
        exclude_task_id: int | None = None,
        base_time: datetime | None = None,
    ) -> datetime:
        slot = base_time or utcnow()
        if delay_seconds <= 0:
            return slot
        latest_outbound_stmt = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Message.direction == "outbound")
        )
        if outbound_session_id is None:
            latest_outbound_stmt = latest_outbound_stmt.where(Conversation.whatsapp_session_id.is_(None))
        else:
            latest_outbound_stmt = latest_outbound_stmt.where(Conversation.whatsapp_session_id == outbound_session_id)
        latest_outbound = db.scalar(latest_outbound_stmt.order_by(Message.sent_at.desc()))
        if latest_outbound:
            slot = max(slot, latest_outbound.sent_at + timedelta(seconds=delay_seconds))

        queued_tasks = list(
            db.scalars(
                select(AgentTask)
                .join(Conversation, Conversation.id == AgentTask.conversation_id)
                .where(
                    AgentTask.task_type == "queued_outbound",
                    AgentTask.status == "pending",
                    Conversation.whatsapp_session_id == outbound_session_id,
                )
            )
        )
        if exclude_task_id is not None:
            queued_tasks = [task for task in queued_tasks if task.id != exclude_task_id]
        if queued_tasks:
            latest_reserved = max(task.next_run_at or slot for task in queued_tasks)
            slot = max(slot, latest_reserved + timedelta(seconds=delay_seconds))
        return slot

    def extract_retry_after_seconds(self, send_result: dict[str, Any]) -> int | None:
        raw_error = send_result.get("error")
        error = raw_error if isinstance(raw_error, dict) else {}
        if isinstance(error.get("body"), str):
            try:
                body = json.loads(error["body"])
                retry_after = body.get("retry_after")
                if retry_after is not None:
                    return max(1, int(retry_after))
            except (ValueError, TypeError):
                return None
        return None

    def is_rate_limited(self, send_result: dict[str, Any]) -> bool:
        raw_error = send_result.get("error")
        error = raw_error if isinstance(raw_error, dict) else {}
        return int(error.get("status_code") or 0) == 429

    def queue_existing_message(
        self,
        db: Session,
        *,
        lead: Lead,
        conversation: Conversation,
        message: Message,
        scheduled_for: datetime,
        queue_reason: str,
        queue_context: dict[str, Any] | None = None,
        status: str = "queued_waiting",
        existing_task: AgentTask | None = None,
    ) -> AgentTask:
        metadata = dict(message.metadata_json or {})
        metadata["queue"] = {
            "scheduled_for": scheduled_for.isoformat(),
            "reason": queue_reason,
            **(queue_context or {}),
        }
        message.status = status
        message.metadata_json = metadata

        payload = {
            "conversation_id": conversation.id,
            "lead_id": lead.id,
            "message_id": message.id,
            **(queue_context or {}),
        }
        if existing_task:
            existing_task.status = "pending"
            existing_task.next_run_at = scheduled_for
            existing_task.scheduled_reason = queue_reason
            existing_task.payload = payload
            existing_task.last_result = f"Mensagem reenfileirada para {scheduled_for.isoformat()}."
            return existing_task

        task = AgentTask(
            lead_id=lead.id,
            conversation_id=conversation.id,
            task_type="queued_outbound",
            status="pending",
            next_run_at=scheduled_for,
            scheduled_reason=queue_reason,
            review_required=False,
            payload=payload,
            last_result=f"Mensagem enfileirada para {scheduled_for.isoformat()}.",
        )
        db.add(task)
        return task

    def send_outbound_message(
        self,
        db: Session,
        *,
        lead: Lead,
        conversation: Conversation,
        text: str,
        sender: str,
        author_role: str,
        metadata: dict[str, Any] | None = None,
        queue_context: dict[str, Any] | None = None,
        respect_rate_limit: bool = True,
        prompt_phase: str | None = None,
        instruction_snapshot: dict[str, Any] | None = None,
    ) -> Message:
        runtime = self.runtime_service.get_runtime_config(db)
        outbound_session = self._resolve_outbound_session(db, conversation)
        session_cooldown_seconds = self.session_outbound_cooldown_seconds(outbound_session)
        can_send_real = bool(runtime["outbound_enabled"]) and (
            bool(self._session_api_key(outbound_session)) or bool(getattr(self.settings, "has_wasender_credentials", False))
        )
        now = utcnow()

        if can_send_real and respect_rate_limit and session_cooldown_seconds > 0:
            next_slot = self.next_outbound_slot(
                db,
                outbound_session_id=outbound_session.id if outbound_session else None,
                delay_seconds=session_cooldown_seconds,
                base_time=now,
            )
            if next_slot > now:
                message = Message(
                    conversation_id=conversation.id,
                    external_message_id=None,
                    direction="outbound",
                    sender=sender,
                    author_role=author_role,
                    content=text,
                    status="queued_waiting",
                    prompt_phase=prompt_phase,
                    instruction_snapshot_json=instruction_snapshot,
                    metadata_json={},
                    sent_at=now,
                )
                db.add(message)
                db.flush()
                self.queue_existing_message(
                    db,
                    lead=lead,
                    conversation=conversation,
                    message=message,
                    scheduled_for=next_slot,
                    queue_reason="provider_rate_limit_window",
                    queue_context=queue_context,
                    status="queued_waiting",
                )
                conversation.last_message_at = message.sent_at
                conversation.last_outbound_at = message.sent_at
                return message

        send_result: dict[str, Any] = metadata or {"data": {"status": "draft_only", "msgId": None}}
        if can_send_real:
            send_result = WasenderClient(api_key=self._session_api_key(outbound_session)).send_text_message(
                to=lead.whatsapp_number or lead.phone_number,
                text=text,
            )

        message = Message(
            conversation_id=conversation.id,
            external_message_id=(
                str(send_result.get("data", {}).get("msgId"))
                if send_result.get("data", {}).get("msgId") is not None
                else None
            ),
            direction="outbound",
            sender=sender,
            author_role=author_role,
            content=text,
            status=send_result.get("data", {}).get("status", "queued"),
            prompt_phase=prompt_phase,
            instruction_snapshot_json=instruction_snapshot,
            metadata_json=send_result,
            sent_at=utcnow(),
        )
        db.add(message)
        conversation.last_message_at = message.sent_at
        conversation.last_outbound_at = message.sent_at

        if can_send_real and self.is_rate_limited(send_result):
            retry_after = self.extract_retry_after_seconds(send_result)
            retry_delay_seconds = (
                max(1, retry_after) if retry_after is not None else max(session_cooldown_seconds, PROVIDER_RATE_LIMIT_SECONDS)
            )
            scheduled_for = max(
                utcnow() + timedelta(seconds=retry_delay_seconds),
                self.next_outbound_slot(
                    db,
                    outbound_session_id=outbound_session.id if outbound_session else None,
                    delay_seconds=retry_delay_seconds,
                    base_time=now,
                ),
            )
            db.flush()
            self.queue_existing_message(
                db,
                lead=lead,
                conversation=conversation,
                message=message,
                scheduled_for=scheduled_for,
                queue_reason="provider_retry_after",
                queue_context=queue_context,
                status="queued_retry",
            )
        return message

    def retry_queued_message(
        self,
        db: Session,
        *,
        lead: Lead,
        conversation: Conversation,
        message: Message,
        task: AgentTask,
    ) -> Message:
        outbound_session = self._resolve_outbound_session(db, conversation)
        session_cooldown_seconds = self.session_outbound_cooldown_seconds(outbound_session)
        send_result = WasenderClient(api_key=self._session_api_key(outbound_session)).send_text_message(
            to=lead.whatsapp_number or lead.phone_number,
            text=message.content,
        )
        if self.is_rate_limited(send_result):
            retry_after = self.extract_retry_after_seconds(send_result)
            queue_context = dict(task.payload or {})
            queue_context.pop("message_id", None)
            retry_delay_seconds = (
                max(1, retry_after) if retry_after is not None else max(session_cooldown_seconds, PROVIDER_RATE_LIMIT_SECONDS)
            )
            scheduled_for = max(
                utcnow() + timedelta(seconds=retry_delay_seconds),
                self.next_outbound_slot(
                    db,
                    outbound_session_id=outbound_session.id if outbound_session else None,
                    delay_seconds=retry_delay_seconds,
                    exclude_task_id=task.id,
                    base_time=utcnow(),
                ),
            )
            self.queue_existing_message(
                db,
                lead=lead,
                conversation=conversation,
                message=message,
                scheduled_for=scheduled_for,
                queue_reason="provider_retry_after",
                queue_context=queue_context,
                status="queued_retry",
                existing_task=task,
            )
            return message

        message.external_message_id = (
            str(send_result.get("data", {}).get("msgId"))
            if send_result.get("data", {}).get("msgId") is not None
            else None
        )
        message.status = str(send_result.get("data", {}).get("status", "queued"))
        message.metadata_json = send_result
        message.sent_at = utcnow()
        conversation.last_message_at = message.sent_at
        conversation.last_outbound_at = message.sent_at
        task.status = "completed" if not str(message.status).startswith("send_") else "failed"
        task.last_result = f"Mensagem processada com status {message.status}."
        return message

    def _resolve_outbound_session(self, db: Session, conversation: Conversation) -> WhatsappSession | None:
        if conversation.whatsapp_session_id:
            return db.get(WhatsappSession, conversation.whatsapp_session_id)
        return self.session_service.get_active_session(db)

    def _session_api_key(self, session: WhatsappSession | None) -> str | None:
        if session and session.api_key:
            return session.api_key
        return getattr(self.settings, "wasender_api_key", None) or None
