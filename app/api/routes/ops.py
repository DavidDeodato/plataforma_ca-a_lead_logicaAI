from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import AgentTask, Conversation, Lead, QualifiedLead
from app.db.schemas import DashboardSummaryRead, RuntimeSettingsRead, RuntimeSettingsUpdate
from app.services.runtime_config import RuntimeConfigService


router = APIRouter(prefix="/api", tags=["ops"])


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    runtime_service = RuntimeConfigService()
    runtime = runtime_service.get_runtime_config(db)
    missing = []
    if not settings.firecrawl_api_key:
        missing.append("firecrawl_api")
    if not settings.openai_api_key:
        missing.append("openai_api_key")
    if not settings.database_url:
        missing.append("database_url")
    if not settings.wasender_api_key:
        missing.append("wasender_api_key")

    return {
        "ready_for_local_tests": len(missing) == 0,
        "ready_for_live_outreach": len(missing) == 0 and bool(runtime["outbound_enabled"]),
        "missing": missing,
        "safe_mode": {
            "outbound_enabled": bool(runtime["outbound_enabled"]),
            "auto_reply_enabled": bool(runtime["auto_reply_enabled"]),
        },
        "notes": [
            "Webhook publico e segredo ainda sao necessarios para resposta automatica em producao."
        ],
    }


@router.get("/settings/runtime", response_model=RuntimeSettingsRead)
def get_runtime_settings(db: Session = Depends(get_db)) -> dict:
    return RuntimeConfigService().get_runtime_config(db)


@router.patch("/settings/runtime", response_model=RuntimeSettingsRead)
def update_runtime_settings(payload: RuntimeSettingsUpdate, db: Session = Depends(get_db)) -> dict:
    updates = payload.model_dump(exclude_none=True)
    return RuntimeConfigService().update_runtime_config(db, updates)


@router.get("/dashboard/summary", response_model=DashboardSummaryRead)
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    runtime_service = RuntimeConfigService()
    runtime = runtime_service.get_runtime_config(db)

    totals = {
        "leads": db.scalar(select(func.count()).select_from(Lead)) or 0,
        "qualified": db.scalar(select(func.count()).select_from(QualifiedLead)) or 0,
        "conversations": db.scalar(select(func.count()).select_from(Conversation)) or 0,
        "tasks_pending": (
            db.scalar(select(func.count()).select_from(AgentTask).where(AgentTask.status == "pending")) or 0
        ),
    }
    recent_activity = {
        "new_leads": db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "new")) or 0,
        "contacted": db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "contacted")) or 0,
        "replied": db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "replied")) or 0,
        "qualified": totals["qualified"],
    }
    return {
        "totals": totals,
        "safe_mode": runtime_service.get_flags(db),
        "recent_activity": recent_activity,
        "runtime": runtime,
    }
