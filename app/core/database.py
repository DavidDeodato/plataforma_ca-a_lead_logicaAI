from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


engine_kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()
    _ensure_schema_constraints()


def _ensure_schema_columns() -> None:
    inspector = inspect(engine)
    dialect = engine.dialect.name

    bool_false = "BOOLEAN DEFAULT FALSE NOT NULL" if dialect == "postgresql" else "BOOLEAN DEFAULT 0 NOT NULL"
    bool_true = "BOOLEAN DEFAULT TRUE NOT NULL" if dialect == "postgresql" else "BOOLEAN DEFAULT 1 NOT NULL"

    schema_patches = {
        "leads": {
            "campaign_id": "INTEGER",
            "offer_product_id": "INTEGER",
            "agent_strategy_id": "INTEGER",
            "prospecting_recipe_id": "INTEGER",
            "prospecting_prompt_category_id": "INTEGER",
            "prospecting_prompt_id": "INTEGER",
            "funnel_stage": "VARCHAR(40) DEFAULT 'captured' NOT NULL",
            "fit_score": "FLOAT",
            "fit_label": "VARCHAR(20)",
            "fit_reasons": "JSON" if dialect == "postgresql" else "JSON",
            "fit_scored_at": "TIMESTAMP",
            "first_contacted_at": "TIMESTAMP",
            "first_replied_at": "TIMESTAMP",
            "positive_reply_detected": bool_false,
            "positive_reply_at": "TIMESTAMP",
            "pain_status": "VARCHAR(30) DEFAULT 'unknown' NOT NULL",
            "pain_confirmed_at": "TIMESTAMP",
            "intent_status": "VARCHAR(30) DEFAULT 'unknown' NOT NULL",
            "fit_confirmed_at": "TIMESTAMP",
            "authority_status": "VARCHAR(30) DEFAULT 'unknown' NOT NULL",
            "urgency_status": "VARCHAR(30) DEFAULT 'unknown' NOT NULL",
            "objection_status": "VARCHAR(40) DEFAULT 'none' NOT NULL",
            "meeting_status": "VARCHAR(30) DEFAULT 'not_offered' NOT NULL",
            "meeting_offered_at": "TIMESTAMP",
            "meeting_booked_at": "TIMESTAMP",
            "qualified_opportunity_at": "TIMESTAMP",
            "closed_won_at": "TIMESTAMP",
            "closed_lost_at": "TIMESTAMP",
            "last_signal_at": "TIMESTAMP",
            "source_origin": "VARCHAR(40) DEFAULT 'manual' NOT NULL",
            "inbound_unverified": bool_false,
        },
        "conversations": {
            "whatsapp_session_id": "INTEGER",
            "last_inbound_at": "TIMESTAMP",
            "last_outbound_at": "TIMESTAMP",
            "unread_count": "INTEGER DEFAULT 0 NOT NULL",
            "assignee": "VARCHAR(120)",
            "manual_mode": bool_false,
            "automation_paused": bool_false,
            "auto_reply_enabled": bool_true,
            "reply_delay_seconds": "INTEGER DEFAULT 30 NOT NULL",
            "taken_over_at": "TIMESTAMP",
            "taken_over_by": "VARCHAR(120)",
            "pending_human_review": bool_false,
            "pending_review_reason": "TEXT",
            "pending_draft": "TEXT",
        },
        "messages": {
            "author_role": "VARCHAR(40)",
            "prompt_phase": "VARCHAR(40)",
            "instruction_snapshot": "JSON" if dialect == "postgresql" else "JSON",
        },
        "agent_tasks": {
            "conversation_id": "INTEGER",
            "scheduled_reason": "VARCHAR(120)",
            "review_required": bool_false,
        },
        "whatsapp_sessions": {
            "wasender_session_id": "INTEGER",
            "phone_number": "VARCHAR(40)",
            "status": "VARCHAR(40) DEFAULT 'disconnected' NOT NULL",
            "api_key": "VARCHAR(255)",
            "webhook_secret": "VARCHAR(255)",
            "webhook_url": "VARCHAR(500)",
            "webhook_enabled": bool_false,
            "webhook_events": "JSON" if dialect == "postgresql" else "JSON",
            "account_protection": bool_true,
            "log_messages": bool_true,
            "read_incoming_messages": bool_false,
            "outbound_cooldown_seconds": "INTEGER",
            "source": "VARCHAR(40) DEFAULT 'manual' NOT NULL",
            "is_active": bool_false,
            "last_synced_at": "TIMESTAMP",
        },
        "prospecting_candidates": {
            "lead_id": "INTEGER",
            "conversation_id": "INTEGER",
            "outreach_external_message_id": "VARCHAR(255)",
            "delivery_status": "VARCHAR(40)",
            "delivery_note": "TEXT",
            "existing_lead_id": "INTEGER",
            "existing_lead_status": "VARCHAR(40)",
            "prospecting_prompt_category_id": "INTEGER",
            "prospecting_prompt_id": "INTEGER",
            "fit_score": "FLOAT",
            "fit_label": "VARCHAR(20)",
            "fit_reasons": "JSON" if dialect == "postgresql" else "JSON",
            "fit_scored_at": "TIMESTAMP",
            "search_reason": "TEXT",
        },
        "campaigns": {
            "offer_product_id": "INTEGER",
            "agent_strategy_id": "INTEGER",
            "prospecting_recipe_id": "INTEGER",
        },
        "prospecting_batches": {
            "recipe_id": "INTEGER",
            "prompt_category_id": "INTEGER",
            "prompt_id": "INTEGER",
            "recipe_snapshot": "JSON" if dialect == "postgresql" else "JSON",
            "prompt_snapshot": "JSON" if dialect == "postgresql" else "JSON",
            "search_metrics": "JSON" if dialect == "postgresql" else "JSON",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in schema_patches.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


def _ensure_schema_constraints() -> None:
    inspector = inspect(engine)
    dialect = engine.dialect.name

    if dialect == "postgresql":
        existing_constraints = {item["name"] for item in inspector.get_unique_constraints("conversations")}
        with engine.begin() as connection:
            if "uq_lead_channel" in existing_constraints:
                connection.execute(text("ALTER TABLE conversations DROP CONSTRAINT uq_lead_channel"))
            if "uq_lead_channel_session" not in existing_constraints:
                connection.execute(
                    text(
                        "ALTER TABLE conversations "
                        "ADD CONSTRAINT uq_lead_channel_session UNIQUE (lead_id, channel, whatsapp_session_id)"
                    )
                )
        return

    if dialect == "sqlite":
        return
