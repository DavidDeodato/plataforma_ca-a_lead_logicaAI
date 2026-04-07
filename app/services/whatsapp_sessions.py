from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Conversation, WhatsappSession
from app.services.wasender_management_client import WasenderManagementClient

DEFAULT_WEBHOOK_EVENTS = [
    "messages.received",
    "messages.upsert",
    "messages.update",
    "message.sent",
    "session.status",
]


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WhatsappSessionService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def list_sessions(self, db: Session) -> list[WhatsappSession]:
        self.ensure_env_backed_session(db)
        stmt = select(WhatsappSession).order_by(WhatsappSession.is_active.desc(), WhatsappSession.updated_at.desc())
        return list(db.scalars(stmt))

    def get_active_session(self, db: Session) -> WhatsappSession | None:
        self.ensure_env_backed_session(db)
        return db.scalar(select(WhatsappSession).where(WhatsappSession.is_active.is_(True)))

    def ensure_env_backed_session(self, db: Session) -> WhatsappSession | None:
        if not self.settings.wasender_api_key and not self.settings.wasender_webhook_secret:
            return None

        stmt = None
        if self.settings.wasender_api_key:
            stmt = select(WhatsappSession).where(WhatsappSession.api_key == self.settings.wasender_api_key)
        elif self.settings.wasender_webhook_secret:
            stmt = select(WhatsappSession).where(WhatsappSession.webhook_secret == self.settings.wasender_webhook_secret)
        session = db.scalar(stmt) if stmt is not None else None
        if not session:
            session = WhatsappSession(
                name="Sessão importada do .env",
                api_key=self.settings.wasender_api_key or None,
                webhook_secret=self.settings.wasender_webhook_secret or None,
                webhook_url=self.default_webhook_url(),
                webhook_enabled=bool(self.settings.wasender_webhook_secret),
                webhook_events=list(DEFAULT_WEBHOOK_EVENTS),
                source="env",
                status="unknown",
            )
            db.add(session)
            db.flush()

        session.api_key = self.settings.wasender_api_key or session.api_key
        session.webhook_secret = self.settings.wasender_webhook_secret or session.webhook_secret
        session.webhook_url = session.webhook_url or self.default_webhook_url()
        session.webhook_events = session.webhook_events or list(DEFAULT_WEBHOOK_EVENTS)
        if not db.scalar(select(WhatsappSession).where(WhatsappSession.is_active.is_(True), WhatsappSession.id != session.id)):
            session.is_active = True
        return session

    def activate(self, db: Session, target: WhatsappSession) -> WhatsappSession:
        sessions = list(db.scalars(select(WhatsappSession)))
        for session in sessions:
            session.is_active = session.id == target.id
        return target

    def resolve_by_webhook_signature(self, db: Session, signature: str | None) -> WhatsappSession | None:
        self.ensure_env_backed_session(db)
        if not signature:
            return self.get_active_session(db)
        return db.scalar(select(WhatsappSession).where(WhatsappSession.webhook_secret == signature))

    def upsert_provider_session(
        self,
        db: Session,
        payload: dict[str, Any],
        *,
        source: str = "wasender",
        activate: bool = False,
    ) -> WhatsappSession:
        wasender_session_id = payload.get("id")
        api_key = payload.get("api_key")
        stmt = None
        if wasender_session_id is not None:
            stmt = select(WhatsappSession).where(WhatsappSession.wasender_session_id == int(wasender_session_id))
        elif api_key:
            stmt = select(WhatsappSession).where(WhatsappSession.api_key == str(api_key))
        session = db.scalar(stmt) if stmt is not None else None
        if not session:
            session = WhatsappSession(name=str(payload.get("name") or payload.get("phone_number") or "Sessão WhatsApp"))
            db.add(session)
            db.flush()

        session.name = str(payload.get("name") or session.name)
        session.wasender_session_id = int(wasender_session_id) if wasender_session_id is not None else session.wasender_session_id
        session.phone_number = str(payload.get("phone_number")) if payload.get("phone_number") else session.phone_number
        session.status = str(payload.get("status") or session.status or "unknown")
        session.api_key = str(api_key) if api_key else session.api_key
        session.webhook_secret = (
            str(payload.get("webhook_secret")) if payload.get("webhook_secret") else session.webhook_secret
        )
        session.webhook_url = str(payload.get("webhook_url")) if payload.get("webhook_url") else session.webhook_url
        session.webhook_enabled = bool(payload.get("webhook_enabled", session.webhook_enabled))
        events = payload.get("webhook_events")
        if isinstance(events, list):
            session.webhook_events = [str(item) for item in events]
        session.account_protection = bool(payload.get("account_protection", session.account_protection))
        session.log_messages = bool(payload.get("log_messages", session.log_messages))
        session.read_incoming_messages = bool(payload.get("read_incoming_messages", session.read_incoming_messages))
        if payload.get("outbound_cooldown_seconds") is not None:
            session.outbound_cooldown_seconds = max(0, int(payload["outbound_cooldown_seconds"]))
        session.source = source
        session.last_synced_at = utcnow()
        if activate:
            self.activate(db, session)
        return session

    def sync_all_from_provider(self, db: Session) -> list[WhatsappSession]:
        client = WasenderManagementClient()
        provider_sessions = client.list_sessions()
        synced: list[WhatsappSession] = []
        for item in provider_sessions:
            details = client.get_session_details(int(item["id"]))
            synced.append(self.upsert_provider_session(db, details, source="wasender"))
        if synced and not any(item.is_active for item in synced):
            self.activate(db, synced[0])
        return self.list_sessions(db)

    def create_session(
        self,
        db: Session,
        *,
        name: str,
        phone_number: str | None,
        account_protection: bool,
        log_messages: bool,
        read_incoming_messages: bool,
        outbound_cooldown_seconds: int | None,
        webhook_enabled: bool,
        webhook_url: str | None,
        webhook_events: list[str] | None,
        api_key: str | None = None,
        webhook_secret: str | None = None,
        create_on_provider: bool = False,
        set_active: bool = True,
    ) -> WhatsappSession:
        payload = {
            "name": name,
            "phone_number": phone_number,
            "account_protection": account_protection,
            "log_messages": log_messages,
            "read_incoming_messages": read_incoming_messages,
            "webhook_enabled": webhook_enabled,
            "webhook_url": webhook_url,
            "webhook_events": webhook_events or list(DEFAULT_WEBHOOK_EVENTS),
        }
        if create_on_provider:
            provider_payload = WasenderManagementClient().create_session(payload)
            session = self.upsert_provider_session(db, provider_payload, source="wasender", activate=set_active)
            session.outbound_cooldown_seconds = outbound_cooldown_seconds
            return session

        session = WhatsappSession(
            name=name,
            phone_number=phone_number,
            status="manual",
            api_key=api_key,
            webhook_secret=webhook_secret,
            webhook_url=webhook_url,
            webhook_enabled=webhook_enabled,
            webhook_events=webhook_events or list(DEFAULT_WEBHOOK_EVENTS),
            account_protection=account_protection,
            log_messages=log_messages,
            read_incoming_messages=read_incoming_messages,
            outbound_cooldown_seconds=outbound_cooldown_seconds,
            source="manual",
            last_synced_at=utcnow(),
        )
        db.add(session)
        db.flush()
        if set_active:
            self.activate(db, session)
        return session

    def connect_session(self, db: Session, session: WhatsappSession) -> dict[str, Any]:
        if session.wasender_session_id is None:
            raise RuntimeError("Essa sessão ainda não tem ID do WASender para iniciar o QR code.")
        result = WasenderManagementClient().connect_session(int(session.wasender_session_id))
        session.status = str(result.get("status") or session.status)
        session.last_synced_at = utcnow()
        return result

    def get_qrcode(self, db: Session, session: WhatsappSession) -> str | None:
        if session.wasender_session_id is None:
            raise RuntimeError("Essa sessão ainda não tem ID do WASender para buscar QR code.")
        qr_code = WasenderManagementClient().get_session_qrcode(int(session.wasender_session_id))
        session.last_synced_at = utcnow()
        return qr_code

    def default_webhook_url(self) -> str | None:
        if not self.settings.app_url:
            return None
        return f"{self.settings.app_url.rstrip('/')}/webhooks/wasender"

    def attach_status_by_api_key(self, db: Session, api_key: str | None, status: str | None) -> None:
        if not api_key or not status:
            return
        session = db.scalar(select(WhatsappSession).where(WhatsappSession.api_key == api_key))
        if not session:
            return
        session.status = str(status)
        session.last_synced_at = utcnow()

    def legacy_scope_label(self) -> str:
        return "Histórico legado"

    def update_legacy_conversation_label(self, conversation: Conversation) -> None:
        if conversation.whatsapp_session_id is None and not conversation.external_chat_id:
            conversation.external_chat_id = "legacy"
