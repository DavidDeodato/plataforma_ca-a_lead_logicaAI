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


def _ensure_schema_columns() -> None:
    inspector = inspect(engine)
    dialect = engine.dialect.name

    bool_false = "BOOLEAN DEFAULT FALSE NOT NULL" if dialect == "postgresql" else "BOOLEAN DEFAULT 0 NOT NULL"
    bool_true = "BOOLEAN DEFAULT TRUE NOT NULL" if dialect == "postgresql" else "BOOLEAN DEFAULT 1 NOT NULL"

    schema_patches = {
        "leads": {
            "campaign_id": "INTEGER",
        },
        "conversations": {
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
        },
        "agent_tasks": {
            "conversation_id": "INTEGER",
            "scheduled_reason": "VARCHAR(120)",
            "review_required": bool_false,
        },
        "prospecting_candidates": {
            "lead_id": "INTEGER",
            "conversation_id": "INTEGER",
            "outreach_external_message_id": "VARCHAR(255)",
            "delivery_status": "VARCHAR(40)",
            "delivery_note": "TEXT",
            "existing_lead_id": "INTEGER",
            "existing_lead_status": "VARCHAR(40)",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in schema_patches.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
