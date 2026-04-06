from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import AgentTask, Conversation, Lead, LeadResearch, Message, QualifiedLead
from app.db.schemas import ConversationRead, LeadCreate, LeadRead, ProspectingRequest, QualificationRead
from app.services.conversation_agent import ConversationAgentService
from app.services.conversation_ops import ConversationOpsService
from app.services.enrichment import EnrichmentService
from app.services.prospecting import ProspectLead, ProspectingService
from app.services.runtime_config import RuntimeConfigService
from app.services.whatsapp_sessions import WhatsappSessionService


router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads", response_model=list[LeadRead])
def list_leads(db: Session = Depends(get_db)) -> list[Lead]:
    stmt = select(Lead).order_by(Lead.created_at.desc())
    return list(db.scalars(stmt))


@router.post("/leads", response_model=LeadRead)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/prospecting/run", response_model=list[LeadRead])
def run_prospecting(payload: ProspectingRequest, db: Session = Depends(get_db)) -> list[Lead]:
    prospecting_service = ProspectingService(validate_phone_format=payload.validate_phone_format)
    enrichment_service = EnrichmentService()

    leads = prospecting_service.find_leads(niche=payload.niche, city=payload.city, limit=payload.limit)
    saved: list[Lead] = []

    for prospect in leads:
        lead = _upsert_lead(db=db, prospect=prospect)
        if payload.enrich:
            try:
                research_payload = enrichment_service.enrich_lead(lead)
                if research_payload:
                    _save_research(db=db, lead=lead, research_payload=research_payload)
                    _hydrate_lead_from_research(lead=lead, research_payload=research_payload)
            except Exception as exc:
                lead.notes = f"{lead.notes or ''}\nEnriquecimento falhou: {exc}".strip()
        saved.append(lead)

    db.commit()
    for lead in saved:
        db.refresh(lead)
    return saved


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@router.post("/outreach/{lead_id}/start", response_model=ConversationRead)
def start_outreach(lead_id: int, db: Session = Depends(get_db)) -> Conversation:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    if not lead.phone_number and not lead.whatsapp_number:
        raise HTTPException(status_code=400, detail="Lead sem telefone/WhatsApp para contato.")
    conversation, _ = _start_outreach_internal(db=db, lead=lead, queue_context={"queue_origin": "outreach_start"})
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/leads/{lead_id}/conversation", response_model=ConversationRead)
def get_lead_conversation(lead_id: int, db: Session = Depends(get_db)) -> Conversation:
    active_session = WhatsappSessionService().get_active_session(db)
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.whatsapp_session))
        .where(Conversation.lead_id == lead_id, Conversation.channel == "whatsapp")
        .order_by(
            desc(Conversation.whatsapp_session_id == (active_session.id if active_session else -1)),
            Conversation.last_message_at.desc().nullslast(),
            Conversation.id.desc(),
        )
    )
    conversation = db.scalars(stmt).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return conversation


@router.get("/qualified-leads", response_model=list[QualificationRead])
def list_qualified_leads(db: Session = Depends(get_db)) -> list[QualifiedLead]:
    stmt = select(QualifiedLead).order_by(QualifiedLead.created_at.desc())
    return list(db.scalars(stmt))


def _upsert_lead(db: Session, prospect: ProspectLead) -> Lead:
    lead = None
    if prospect.phone_number:
        lead = db.scalar(select(Lead).where(Lead.phone_number == prospect.phone_number))
    if not lead:
        lead = db.scalar(
            select(Lead).where(
                Lead.business_name == prospect.business_name,
                Lead.city == prospect.city,
            )
        )

    if not lead:
        lead = Lead(
            business_name=prospect.business_name,
            niche=prospect.niche,
            city=prospect.city,
        )
        db.add(lead)

    lead.phone_number = lead.phone_number or prospect.phone_number
    lead.whatsapp_number = lead.whatsapp_number or prospect.phone_number
    lead.website = lead.website or prospect.website
    lead.instagram_url = lead.instagram_url or prospect.instagram_url
    lead.facebook_url = lead.facebook_url or prospect.facebook_url
    lead.source_url = lead.source_url or prospect.source_url
    lead.source_query = prospect.source_query
    lead.source_platform = prospect.source_platform
    lead.notes = prospect.notes or lead.notes
    return lead


def _save_research(db: Session, lead: Lead, research_payload: dict) -> None:
    db.add(
        LeadResearch(
            lead=lead,
            source="firecrawl",
            summary=research_payload.get("summary"),
            pain_points=research_payload.get("pain_points"),
            opportunities=research_payload.get("opportunities"),
            evidence=research_payload.get("evidence"),
            structured_data=research_payload,
        )
    )


def _hydrate_lead_from_research(lead: Lead, research_payload: dict) -> None:
    lead.website = lead.website or research_payload.get("website")
    lead.instagram_url = lead.instagram_url or research_payload.get("instagram_url")
    lead.phone_number = lead.phone_number or research_payload.get("phone_number")
    lead.whatsapp_number = lead.whatsapp_number or research_payload.get("phone_number")


def _latest_research_payload(lead: Lead) -> dict:
    if not lead.research_entries:
        return {}
    ordered = sorted(lead.research_entries, key=lambda item: item.created_at)
    return ordered[-1].structured_data or {}


def _get_or_create_conversation(db: Session, lead: Lead) -> Conversation:
    active_session = WhatsappSessionService().get_active_session(db)
    stmt = select(Conversation).where(Conversation.lead_id == lead.id, Conversation.channel == "whatsapp")
    if active_session:
        stmt = stmt.where(Conversation.whatsapp_session_id == active_session.id)
    else:
        stmt = stmt.where(Conversation.whatsapp_session_id.is_(None))
    conversation = db.scalar(stmt)
    if conversation:
        return conversation
    conversation = Conversation(
        lead=lead,
        channel="whatsapp",
        stage="new",
        temperature="cold",
        whatsapp_session_id=active_session.id if active_session else None,
    )
    db.add(conversation)
    db.flush()
    return conversation


def _ensure_followup_task(db: Session, lead: Lead, research: dict) -> None:
    task = db.scalar(select(AgentTask).where(AgentTask.lead_id == lead.id, AgentTask.task_type == "follow_up"))
    runtime = RuntimeConfigService().get_runtime_config(db)
    active_session = WhatsappSessionService().get_active_session(db)
    conversation_stmt = select(Conversation).where(Conversation.lead_id == lead.id, Conversation.channel == "whatsapp")
    if active_session:
        conversation_stmt = conversation_stmt.where(Conversation.whatsapp_session_id == active_session.id)
    else:
        conversation_stmt = conversation_stmt.where(Conversation.whatsapp_session_id.is_(None))
    conversation = db.scalar(conversation_stmt)
    if task:
        task.next_run_at = utcnow() + timedelta(days=1)
        task.payload = research
        task.status = "pending"
        task.conversation_id = conversation.id if conversation else None
        return
    db.add(
        AgentTask(
            lead_id=lead.id,
            conversation_id=conversation.id if conversation else None,
            task_type="follow_up",
            status="pending",
            next_run_at=utcnow() + timedelta(seconds=int(runtime["outreach_delay_seconds"])),
            payload=research,
        )
    )


def _start_outreach_internal(
    *,
    db: Session,
    lead: Lead,
    queue_context: dict | None = None,
) -> tuple[Conversation, Message]:
    runtime_service = RuntimeConfigService()
    ops = ConversationOpsService()
    research_payload = _latest_research_payload(lead)
    conversation = _get_or_create_conversation(db=db, lead=lead)
    ops.apply_defaults(db, conversation)
    agent = ConversationAgentService()
    text = agent.draft_first_message(
        lead=lead,
        research=research_payload,
        custom_instruction=runtime_service.build_sales_instruction(db),
    )

    conversation.stage = "contacted"
    conversation.temperature = conversation.temperature or "cold"
    lead.status = "contacted"
    sent = ops.send_outbound_message(
        db=db,
        lead=lead,
        conversation=conversation,
        text=text,
        sender="agent",
        author_role="agent",
        queue_context=queue_context,
    )
    _ensure_followup_task(db=db, lead=lead, research=research_payload)
    return conversation, sent
