from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import Conversation, Lead, Message, ProspectingCandidate, WhatsappSession
from app.services.conversation_ops import ConversationOpsService, utcnow
from app.services.runtime_config import RuntimeConfigService
from app.services.whatsapp_sessions import WhatsappSessionService


router = APIRouter(prefix="/webhooks/wasender", tags=["wasender"])


@router.post("")
async def receive_wasender_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_signature: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    session_service = WhatsappSessionService()
    provider_session = session_service.resolve_by_webhook_signature(db, x_webhook_signature)
    valid_signature = bool(provider_session)
    session_secret_exists = db.scalar(select(WhatsappSession.id).where(WhatsappSession.webhook_secret.is_not(None)).limit(1))
    if settings.wasender_webhook_secret and x_webhook_signature == settings.wasender_webhook_secret:
        valid_signature = True
    if (settings.wasender_webhook_secret or session_secret_exists) and not valid_signature:
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    payload = await request.json()
    event = payload.get("event")

    if event == "session.status":
        session_service.attach_status_by_api_key(
            db,
            api_key=str(payload.get("data", {}).get("session_id") or "") or None,
            status=str(payload.get("data", {}).get("status") or "") or None,
        )
        db.commit()
        return {"received": True}

    if event == "messages.update":
        _handle_message_status_update(db=db, payload=payload)
        db.commit()
        return {"received": True}

    if event not in {"messages.upsert", "messages.received"}:
        return {"received": True}

    messages = _extract_messages(payload)
    for item in messages:
        _handle_message_upsert(db=db, item=item, provider_session=provider_session)
    db.commit()
    return {"received": True}


def _extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_messages = payload.get("data", {}).get("messages", [])
    if isinstance(raw_messages, list):
        return [item for item in raw_messages if isinstance(item, dict)]
    if isinstance(raw_messages, dict):
        return [raw_messages]
    return []


def _handle_message_upsert(db: Session, item: dict[str, Any], provider_session: WhatsappSession | None) -> None:
    ops = ConversationOpsService()
    key = item.get("key", {})
    from_me = bool(key.get("fromMe"))
    external_message_id = key.get("id")
    remote_jid = key.get("remoteJid")
    sender_phone = key.get("cleanedSenderPn") or key.get("senderPn") or remote_jid
    text = item.get("messageBody") or item.get("message", {}).get("conversation") or ""

    existing = None
    if external_message_id:
        existing = db.scalar(select(Message).where(Message.external_message_id == external_message_id))
    if existing:
        return

    lead = _get_or_create_lead(db=db, sender_phone=sender_phone)
    conversation = _get_or_create_conversation(
        db=db,
        lead=lead,
        external_chat_id=remote_jid,
        provider_session=provider_session,
    )
    ops.apply_defaults(db, conversation)
    if from_me:
        reconciled = _reconcile_existing_outbound_message(
            db=db,
            conversation=conversation,
            item=item,
            text=text,
        )
        if reconciled:
            conversation.last_message_at = reconciled.sent_at
            conversation.last_outbound_at = reconciled.sent_at
            return

    db.add(
        Message(
            conversation_id=conversation.id,
            external_message_id=external_message_id,
            direction="outbound" if from_me else "inbound",
            sender="lead" if not from_me else "agent",
            author_role="lead" if not from_me else "provider_outbound",
            content=text,
            status="received" if not from_me else "sent",
            metadata_json=item,
            sent_at=utcnow(),
        )
    )
    conversation.last_message_at = utcnow()
    if from_me:
        conversation.last_outbound_at = conversation.last_message_at
        return

    conversation.last_inbound_at = conversation.last_message_at
    conversation.unread_count += 1
    lead.status = "replied"
    research_payload = {}
    if lead.research_entries:
        research_payload = sorted(lead.research_entries, key=lambda row: row.created_at)[-1].structured_data or {}

    if not ops.can_auto_reply(db, conversation):
        return

    ops.schedule_delayed_auto_reply(
        db,
        lead=lead,
        conversation=conversation,
        review_required=conversation.pending_human_review,
        scheduled_reason="inbound_reply",
    )


def _reconcile_existing_outbound_message(
    db: Session,
    *,
    conversation: Conversation,
    item: dict[str, Any],
    text: str,
) -> Message | None:
    key = item.get("key", {})
    provider_message_id = str(key.get("id")) if key.get("id") is not None else None
    provider_numeric_id = str(key.get("msgId")) if key.get("msgId") is not None else None
    recent_outbound = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id, Message.direction == "outbound")
            .order_by(Message.sent_at.desc())
            .limit(12)
        )
    )

    for message in recent_outbound:
        metadata = message.metadata_json if isinstance(message.metadata_json, dict) else {}
        data = metadata.get("data") if isinstance(metadata.get("data"), dict) else {}
        existing_numeric_id = str(data.get("msgId")) if data.get("msgId") is not None else None
        if provider_message_id and message.external_message_id == provider_message_id:
            _apply_provider_outbound_payload(message, item, provider_message_id)
            return message
        if provider_numeric_id and (str(message.external_message_id or "") == provider_numeric_id or existing_numeric_id == provider_numeric_id):
            _apply_provider_outbound_payload(message, item, provider_message_id)
            return message

    for message in recent_outbound:
        if message.author_role not in {"agent", "human"}:
            continue
        if message.content != text:
            continue
        _apply_provider_outbound_payload(message, item, provider_message_id)
        return message

    return None


def _apply_provider_outbound_payload(message: Message, item: dict[str, Any], provider_message_id: str | None) -> None:
    metadata = dict(message.metadata_json or {})
    metadata["provider_upsert_payload"] = item
    message.metadata_json = metadata
    if provider_message_id:
        message.external_message_id = provider_message_id
    message.status = "sent"


def _handle_message_status_update(db: Session, payload: dict[str, Any]) -> None:
    key = payload.get("data", {}).get("key", {})
    message_id = key.get("id")
    status_code = payload.get("data", {}).get("update", {}).get("status")
    if not message_id:
        return

    message = db.scalar(select(Message).where(Message.external_message_id == str(message_id)))
    if not message:
        return
    message.status = str(status_code)
    current_metadata = message.metadata_json or {}
    current_metadata["status_update_payload"] = payload
    message.metadata_json = current_metadata
    candidate = db.scalar(
        select(ProspectingCandidate).where(ProspectingCandidate.outreach_external_message_id == message.external_message_id)
    )
    if candidate:
        candidate.delivery_status = message.status
        if str(message.status) in {"send_failed", "send_timeout", "cancelled"}:
            candidate.status = "contact_failed"
            candidate.delivery_note = "O provedor marcou a mensagem como falha."
        elif str(message.status) in {"queued_waiting", "queued_retry"}:
            candidate.status = "queued_contact"
            candidate.delivery_note = "Mensagem segue aguardando fila do provedor."
        else:
            candidate.status = "contacted"
            candidate.delivery_note = f"Status atualizado pelo provedor para {message.status}."


def _get_or_create_lead(db: Session, sender_phone: str | None) -> Lead:
    normalized_phone = _normalize_phone(sender_phone)
    lead = None
    if normalized_phone:
        lead = db.scalar(select(Lead).where(Lead.phone_number == normalized_phone))
    if lead:
        return lead

    runtime = RuntimeConfigService().get_runtime_config(db)
    lead = Lead(
        business_name=normalized_phone or "Lead WhatsApp",
        niche=str(runtime["default_niche"]),
        city=str(runtime["default_city"]),
        phone_number=normalized_phone,
        whatsapp_number=normalized_phone,
        status="inbound",
    )
    db.add(lead)
    db.flush()
    return lead


def _get_or_create_conversation(
    db: Session,
    lead: Lead,
    external_chat_id: str | None,
    provider_session: WhatsappSession | None,
) -> Conversation:
    stmt = select(Conversation).where(Conversation.lead_id == lead.id, Conversation.channel == "whatsapp")
    if provider_session:
        stmt = stmt.where(Conversation.whatsapp_session_id == provider_session.id)
    else:
        stmt = stmt.where(Conversation.whatsapp_session_id.is_(None))
    conversation = db.scalar(stmt)
    if conversation:
        if external_chat_id and not conversation.external_chat_id:
            conversation.external_chat_id = external_chat_id
        return conversation

    conversation = Conversation(
        lead_id=lead.id,
        channel="whatsapp",
        whatsapp_session_id=provider_session.id if provider_session else None,
        external_chat_id=external_chat_id,
        stage="engaged",
        temperature="warm",
    )
    db.add(conversation)
    db.flush()
    return conversation


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value)
    if "@" in text:
        text = text.split("@", 1)[0]
    digits = "".join(ch for ch in text if ch.isdigit() or ch == "+")
    return digits or None
