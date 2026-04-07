from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.db.models import AgentTask, Conversation, Lead, Message, ProspectingCandidate
from app.services.conversation_agent import ConversationAgentService
from app.services.conversation_ops import ConversationOpsService
from app.services.runtime_config import RuntimeConfigService
from app.services.whatsapp_sessions import WhatsappSessionService


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _mark_candidate_status(db, task: AgentTask, status: str) -> None:
    payload = task.payload or {}
    candidate_id = payload.get("candidate_id")
    if not candidate_id:
        return
    candidate = db.get(ProspectingCandidate, int(candidate_id))
    if candidate:
        candidate.status = status


def _sync_candidate_delivery(db, task: AgentTask, message: Message, status: str) -> None:
    payload = task.payload or {}
    candidate_id = payload.get("candidate_id")
    if not candidate_id:
        return
    candidate = db.get(ProspectingCandidate, int(candidate_id))
    if candidate:
        candidate.status = status
        candidate.conversation_id = message.conversation_id
        candidate.outreach_external_message_id = message.external_message_id
        candidate.delivery_status = message.status


def process_pending_tasks() -> None:
    with SessionLocal() as db:
        runtime_service = RuntimeConfigService()
        runtime = runtime_service.get_runtime_config(db)
        ops = ConversationOpsService()
        session_service = WhatsappSessionService()
        tasks = list(
            db.scalars(
                select(AgentTask).where(
                    AgentTask.task_type.in_(("follow_up", "delayed_auto_reply", "queued_outbound")),
                    AgentTask.status == "pending",
                    AgentTask.next_run_at <= utcnow(),
                )
            )
        )
        for task in tasks:
            lead = db.get(Lead, task.lead_id)
            if not lead or lead.status in {"qualified", "do_not_contact"}:
                task.status = "cancelled"
                task.last_result = "Lead indisponível para processamento."
                _mark_candidate_status(db, task, "contact_failed")
                continue

            conversation = None
            if task.conversation_id:
                conversation = db.get(Conversation, task.conversation_id)
            if not conversation:
                active_session = session_service.get_active_session(db)
                stmt = select(Conversation).where(Conversation.lead_id == lead.id, Conversation.channel == "whatsapp")
                if active_session:
                    stmt = stmt.where(Conversation.whatsapp_session_id == active_session.id)
                conversation = db.scalar(stmt.order_by(Conversation.last_message_at.desc()))
            if not conversation:
                task.status = "cancelled"
                task.last_result = "Sem conversa para processamento."
                _mark_candidate_status(db, task, "contact_failed")
                continue

            ops.apply_defaults(db, conversation)
            agent = ConversationAgentService()

            if task.task_type == "queued_outbound":
                payload = task.payload or {}
                message_id = payload.get("message_id")
                message = db.get(Message, int(message_id)) if message_id else None
                if not message:
                    task.status = "cancelled"
                    task.last_result = "Mensagem da fila não encontrada."
                    _mark_candidate_status(db, task, "contact_failed")
                    continue

                queue_origin = str(payload.get("queue_origin") or "")
                if message.author_role == "agent" and (conversation.manual_mode or conversation.automation_paused):
                    task.status = "cancelled"
                    task.last_result = "Mensagem agent cancelada porque a conversa entrou em controle manual."
                    message.status = "cancelled"
                    _mark_candidate_status(db, task, "contact_failed")
                    continue
                if queue_origin in {"auto_reply", "follow_up"} and (conversation.manual_mode or conversation.automation_paused):
                    task.status = "cancelled"
                    task.last_result = "Envio automático cancelado porque a conversa entrou em controle manual."
                    message.status = "cancelled"
                    continue

                retried = ops.retry_queued_message(
                    db=db,
                    lead=lead,
                    conversation=conversation,
                    message=message,
                    task=task,
                )
                if retried.status in {"queued_waiting", "queued_retry"}:
                    _sync_candidate_delivery(db, task, retried, "queued_contact")
                elif retried.status in {"send_failed", "send_timeout"}:
                    _sync_candidate_delivery(db, task, retried, "contact_failed")
                else:
                    _sync_candidate_delivery(db, task, retried, "contacted")
                continue

            if task.task_type == "delayed_auto_reply":
                if not ops.can_auto_reply(db, conversation, lead=lead):
                    task.status = "cancelled"
                    task.last_result = "Auto-reply cancelado por configuracao/manual takeover."
                    continue

                latest_inbound = db.scalar(
                    select(Message)
                    .where(Message.conversation_id == conversation.id, Message.direction == "inbound")
                    .order_by(Message.sent_at.desc())
                )
                inbound_text = latest_inbound.content if latest_inbound else ""
                result = agent.handle_incoming_message(
                    db=db,
                    lead=lead,
                    conversation=conversation,
                    inbound_text=inbound_text,
                    research=task.payload or {},
                    operating_instruction=runtime_service.build_sales_instruction(
                        db,
                        lead=lead,
                        conversation=conversation,
                        phase="reply",
                    ),
                    instruction_snapshot=runtime_service.build_instruction_snapshot(
                        db,
                        phase="reply",
                        lead=lead,
                        conversation=conversation,
                    ),
                )
                conversation.temperature = result.get("temperature", conversation.temperature)
                conversation.stage = result.get("stage", conversation.stage or "engaged")
                conversation.summary = result.get("handoff_summary") or conversation.summary
                reply_text = result.get("reply")
                if not reply_text:
                    task.status = "completed"
                    task.last_result = "Sem resposta gerada pelo agente."
                    continue

                if task.review_required or conversation.pending_human_review:
                    conversation.pending_human_review = True
                    conversation.pending_review_reason = "Resposta aguardando revisão humana."
                    conversation.pending_draft = reply_text
                    task.status = "completed"
                    task.last_result = "Rascunho gerado para revisão humana."
                    continue

                sent = ops.send_outbound_message(
                    db=db,
                    lead=lead,
                    conversation=conversation,
                    text=reply_text,
                    sender="agent",
                    author_role="agent",
                    queue_context={"queue_origin": "auto_reply"},
                    prompt_phase=str(result.get("_prompt_phase") or "reply"),
                    instruction_snapshot=result.get("_instruction_snapshot"),
                )
                task.status = "completed"
                task.last_result = f"Resposta processada com status {sent.status}."
                continue

            if conversation.manual_mode or conversation.automation_paused:
                task.status = "cancelled"
                task.last_result = "Follow-up cancelado porque a conversa esta em controle manual/pausada."
                continue

            followup_payload = agent.schedule_followup_message_payload(
                db=db,
                lead=lead,
                conversation=conversation,
                research=task.payload or {},
                operating_instruction=runtime_service.build_sales_instruction(
                    db,
                    lead=lead,
                    conversation=conversation,
                    phase="followup",
                ),
            )
            text = str(followup_payload.get("message") or "")

            sent = ops.send_outbound_message(
                db=db,
                lead=lead,
                conversation=conversation,
                text=text,
                sender="agent",
                author_role="agent",
                queue_context={"queue_origin": "follow_up"},
                prompt_phase=str(followup_payload.get("_prompt_phase") or "followup"),
                instruction_snapshot=followup_payload.get("_instruction_snapshot"),
            )
            task.current_attempt += 1
            task.last_result = f"Follow-up processado em {utcnow().isoformat()} com status {sent.status}"
            task.next_run_at = utcnow() + timedelta(days=2)

            if task.current_attempt >= 3:
                task.status = "completed"
                lead.status = "nurturing"

        db.commit()


def run() -> None:
    get_settings()
    init_db()
    process_pending_tasks()


if __name__ == "__main__":
    run()
