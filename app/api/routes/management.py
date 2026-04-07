from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.db.models import (
    AgentStrategy,
    AgentTask,
    Campaign,
    Conversation,
    KnowledgeItem,
    Lead,
    LeadResearch,
    Message,
    OfferProduct,
    Playbook,
    PromptTemplate,
    ProspectingBatch,
    ProspectingCandidate,
    ProspectingPrompt,
    ProspectingPromptCategory,
    ProspectingRecipe,
    QualifiedLead,
    WhatsappSession,
)
from app.db.schemas import (
    AgentStrategyCreate,
    AgentStrategyRead,
    AgentStrategyUpdate,
    AgentPreviewRequest,
    AgentPreviewResponse,
    AgentTaskRead,
    BulkConversationActionRequest,
    BulkLeadActionRequest,
    CampaignCreate,
    CampaignRead,
    CampaignUpdate,
    ConversationListItemRead,
    ConversationListResponse,
    ConversationRead,
    ConversationWorkspaceRead,
    ConversationSettingsUpdate,
    ConversationTakeoverRequest,
    KnowledgeItemCreate,
    KnowledgeItemRead,
    KnowledgeItemUpdate,
    LeadDetailRead,
    LeadListResponse,
    LeadRead,
    LeadUpdate,
    ManualQualificationRequest,
    ManualMessageRequest,
    OfferProductCreate,
    OfferProductRead,
    OfferProductUpdate,
    PlaybookCreate,
    PlaybookRead,
    PlaybookUpdate,
    PromptTemplateCreate,
    PromptTemplateRead,
    PromptTemplateUpdate,
    ProspectingAdvisorRequest,
    ProspectingAdvisorResponse,
    ProspectingBatchActionRequest,
    ProspectingBatchCreate,
    ProspectingBatchRead,
    ProspectingPromptCategoryCreate,
    ProspectingPromptCategoryRead,
    ProspectingPromptCategoryUpdate,
    ProspectingPromptCreate,
    ProspectingPromptRead,
    ProspectingPromptUpdate,
    ProspectingRecipeCreate,
    ProspectingRecipeRead,
    ProspectingRecipeUpdate,
    TaskListResponse,
    WhatsappSessionCreate,
    WhatsappSessionQrRead,
    WhatsappSessionRead,
    WhatsappSessionWorkspaceRead,
)
from app.api.routes import leads as lead_routes
from app.services.conversation_agent import ConversationAgentService
from app.services.conversion_kpis import (
    apply_fit_score_to_record,
    mark_disqualified,
    mark_manual_qualified,
    priority_snapshot,
    recommended_action_snapshot,
    select_suggested_playbook,
)
from app.services.conversation_ops import ConversationOpsService
from app.services.enrichment import EnrichmentService
from app.services.prospecting import ProspectLead, ProspectingService
from app.services.prospecting_advisor import ProspectingAdvisorService, ProspectingDraft
from app.services.runtime_config import RuntimeConfigService
from app.services.whatsapp_sessions import DEFAULT_WEBHOOK_EVENTS, WhatsappSessionService


router = APIRouter(prefix="/api", tags=["management"])


@router.get("/leads/search", response_model=LeadListResponse)
def search_leads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    niche: str | None = None,
    city: str | None = None,
    sort_by: str = Query(default="priority"),
    sort_direction: str = Query(default="desc"),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Lead).options(selectinload(Lead.conversations))
    playbooks = list(db.scalars(select(Playbook).where(Playbook.active.is_(True)).order_by(Playbook.updated_at.desc())))

    filters = []
    if q:
        term = f"%{q}%"
        filters.append(
            or_(
                Lead.business_name.ilike(term),
                Lead.phone_number.ilike(term),
                Lead.instagram_url.ilike(term),
                Lead.website.ilike(term),
            )
        )
    if status:
        filters.append(Lead.status == status)
    if niche:
        filters.append(Lead.niche == niche)
    if city:
        filters.append(Lead.city == city)

    for condition in filters:
        stmt = stmt.where(condition)
    rows = list(db.scalars(stmt))
    for lead in rows:
        setattr(lead, "_candidate_playbooks", playbooks)
    items = [_attach_priority(lead) for lead in rows]
    items = _sort_leads(items, sort_by=sort_by, sort_direction=sort_direction)
    total = len(items)
    sliced = items[(page - 1) * page_size : page * page_size]
    return {"items": sliced, "total": total, "page": page, "page_size": page_size}


@router.get("/leads/{lead_id}", response_model=LeadDetailRead)
def get_lead_detail(lead_id: int, db: Session = Depends(get_db)) -> Lead:
    stmt = (
        select(Lead)
        .options(
            selectinload(Lead.research_entries),
            selectinload(Lead.tasks),
            selectinload(Lead.qualified_lead),
            selectinload(Lead.conversations).selectinload(Conversation.messages),
            selectinload(Lead.conversations).selectinload(Conversation.whatsapp_session),
        )
        .where(Lead.id == lead_id)
    )
    lead = db.scalars(stmt).one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    playbooks = list(db.scalars(select(Playbook).where(Playbook.active.is_(True)).order_by(Playbook.updated_at.desc())))
    setattr(lead, "_candidate_playbooks", playbooks)
    return _attach_priority(lead)


@router.patch("/leads/{lead_id}", response_model=LeadRead)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, key, value)
    latest_research = sorted(lead.research_entries, key=lambda item: item.created_at)[-1].structured_data if lead.research_entries else None
    apply_fit_score_to_record(lead, latest_research)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/leads/{lead_id}/qualify", response_model=LeadDetailRead)
def qualify_lead(lead_id: int, payload: ManualQualificationRequest, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")

    existing = db.scalar(select(QualifiedLead).where(QualifiedLead.lead_id == lead_id))
    if not existing:
        existing = QualifiedLead(lead_id=lead_id, score=payload.score, qualification_reason=payload.qualification_reason)
        db.add(existing)

    existing.score = payload.score
    existing.qualification_reason = payload.qualification_reason
    existing.handoff_summary = payload.handoff_summary
    mark_manual_qualified(lead)
    db.commit()
    return get_lead_detail(lead_id, db)


@router.post("/leads/{lead_id}/disqualify", response_model=LeadRead)
def disqualify_lead(lead_id: int, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    mark_disqualified(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/leads/{lead_id}/reprocess", response_model=LeadDetailRead)
def reprocess_lead(lead_id: int, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    research_payload = EnrichmentService().enrich_lead(lead)
    db.add(
        LeadResearch(
            lead_id=lead.id,
            source="firecrawl",
            summary=research_payload.get("summary"),
            pain_points=research_payload.get("pain_points"),
            opportunities=research_payload.get("opportunities"),
            evidence=research_payload.get("evidence"),
            structured_data=research_payload,
        )
    )
    lead.website = lead.website or research_payload.get("website")
    lead.instagram_url = lead.instagram_url or research_payload.get("instagram_url")
    lead.phone_number = lead.phone_number or research_payload.get("phone_number")
    lead.whatsapp_number = lead.whatsapp_number or research_payload.get("phone_number")
    apply_fit_score_to_record(lead, research_payload)
    db.commit()
    return get_lead_detail(lead_id, db)


@router.post("/leads/{lead_id}/agent-preview", response_model=AgentPreviewResponse)
def agent_preview(lead_id: int, payload: AgentPreviewRequest, db: Session = Depends(get_db)) -> dict:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    research_payload = {}
    if lead.research_entries:
        research_payload = sorted(lead.research_entries, key=lambda item: item.created_at)[-1].structured_data or {}
    runtime_instruction = RuntimeConfigService().build_sales_instruction(db, lead=lead)
    preview_payload = ConversationAgentService().draft_first_message_payload(
        db=db,
        lead=lead,
        research=research_payload,
        custom_instruction=" ".join(filter(None, [runtime_instruction, payload.custom_instruction])),
    )
    return {
        "lead_id": lead.id,
        "preview_message": preview_payload.get("message"),
        "runtime_instruction": runtime_instruction,
        "instruction_snapshot": preview_payload.get("_instruction_snapshot"),
    }


@router.get("/whatsapp-sessions", response_model=WhatsappSessionWorkspaceRead)
def list_whatsapp_sessions(db: Session = Depends(get_db)) -> dict:
    service = WhatsappSessionService()
    items = service.list_sessions(db)
    active = next((item for item in items if item.is_active), None)
    return {
        "items": items,
        "active_session_id": active.id if active else None,
        "provider_management_available": service.settings.has_wasender_management_credentials,
        "legacy_label": service.legacy_scope_label(),
    }


@router.post("/whatsapp-sessions", response_model=WhatsappSessionRead)
def create_whatsapp_session(payload: WhatsappSessionCreate, db: Session = Depends(get_db)) -> WhatsappSession:
    service = WhatsappSessionService()
    try:
        session = service.create_session(
            db,
            name=payload.name,
            phone_number=payload.phone_number,
            account_protection=payload.account_protection,
            log_messages=payload.log_messages,
            read_incoming_messages=payload.read_incoming_messages,
            outbound_cooldown_seconds=payload.outbound_cooldown_seconds,
            webhook_enabled=payload.webhook_enabled,
            webhook_url=payload.webhook_url or service.default_webhook_url(),
            webhook_events=payload.webhook_events or list(DEFAULT_WEBHOOK_EVENTS),
            api_key=payload.api_key,
            webhook_secret=payload.webhook_secret,
            create_on_provider=payload.create_on_provider,
            set_active=payload.set_active,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)
    return session


@router.post("/whatsapp-sessions/sync", response_model=WhatsappSessionWorkspaceRead)
def sync_whatsapp_sessions(db: Session = Depends(get_db)) -> dict:
    service = WhatsappSessionService()
    try:
        items = service.sync_all_from_provider(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    active = next((item for item in items if item.is_active), None)
    return {
        "items": items,
        "active_session_id": active.id if active else None,
        "provider_management_available": service.settings.has_wasender_management_credentials,
        "legacy_label": service.legacy_scope_label(),
    }


@router.post("/whatsapp-sessions/{session_id}/activate", response_model=WhatsappSessionRead)
def activate_whatsapp_session(session_id: int, db: Session = Depends(get_db)) -> WhatsappSession:
    session = _get_whatsapp_session_or_404(db, session_id)
    WhatsappSessionService().activate(db, session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/whatsapp-sessions/{session_id}/connect", response_model=WhatsappSessionQrRead)
def connect_whatsapp_session(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = _get_whatsapp_session_or_404(db, session_id)
    try:
        result = WhatsappSessionService().connect_session(db, session)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {
        "session_id": session.id,
        "status": str(result.get("status")) if result.get("status") else session.status,
        "qr_code": str(result.get("qrCode")) if result.get("qrCode") else None,
    }


@router.get("/whatsapp-sessions/{session_id}/qrcode", response_model=WhatsappSessionQrRead)
def get_whatsapp_session_qrcode(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = _get_whatsapp_session_or_404(db, session_id)
    try:
        qr_code = WhatsappSessionService().get_qrcode(db, session)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return {
        "session_id": session.id,
        "status": session.status,
        "qr_code": qr_code,
    }


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    stage: str | None = None,
    temperature: str | None = None,
    assignee: str | None = None,
    manual_mode: bool | None = None,
    unread_only: bool = False,
    pending_review_only: bool = False,
    whatsapp_session_id: int | None = None,
    active_session_only: bool = False,
    legacy_only: bool = False,
    sort_by: str = Query(default="priority"),
    sort_direction: str = Query(default="desc"),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Conversation).options(
        selectinload(Conversation.lead),
        selectinload(Conversation.whatsapp_session),
    )
    playbooks = list(db.scalars(select(Playbook).where(Playbook.active.is_(True)).order_by(Playbook.updated_at.desc())))
    session_service = WhatsappSessionService()

    if stage:
        stmt = stmt.where(Conversation.stage == stage)
    if temperature:
        stmt = stmt.where(Conversation.temperature == temperature)
    if assignee:
        stmt = stmt.where(Conversation.assignee == assignee)
    if manual_mode is not None:
        stmt = stmt.where(Conversation.manual_mode == manual_mode)
    if unread_only:
        stmt = stmt.where(Conversation.unread_count > 0)
    if pending_review_only:
        stmt = stmt.where(Conversation.pending_human_review.is_(True))
    if active_session_only:
        active_session = session_service.get_active_session(db)
        if active_session:
            stmt = stmt.where(Conversation.whatsapp_session_id == active_session.id)
        else:
            stmt = stmt.where(Conversation.id == -1)
    elif legacy_only:
        stmt = stmt.where(Conversation.whatsapp_session_id.is_(None))
    elif whatsapp_session_id is not None:
        stmt = stmt.where(Conversation.whatsapp_session_id == whatsapp_session_id)

    rows = list(db.scalars(stmt))
    latest_preview_map = _latest_message_preview_map(db, [row.id for row in rows])

    items = []
    for row in rows:
        latest_message = latest_preview_map.get(row.id)
        if row.lead:
            setattr(row.lead, "_candidate_playbooks", playbooks)
        priority = priority_snapshot(
            row.lead,
            unread_count=row.unread_count,
            pending_human_review=row.pending_human_review,
        ) if row.lead else {"score": 0.0, "label": "baixa", "reasons": []}
        recommended_action = (
            recommended_action_snapshot(
                row.lead,
                unread_count=row.unread_count,
                pending_human_review=row.pending_human_review,
                has_open_conversation=True,
            )
            if row.lead
            else {
                "key": "none",
                "label": "Sem ação",
                "description": "Sem lead carregado para esta conversa.",
                "tone": "default",
            }
        )
        items.append(
            ConversationListItemRead(
                id=row.id,
                lead_id=row.lead_id,
                lead_name=row.lead.business_name if row.lead else "Lead",
                phone_number=row.lead.phone_number if row.lead else None,
                source_origin=row.lead.source_origin if row.lead else None,
                inbound_unverified=bool(row.lead.inbound_unverified) if row.lead else False,
                whatsapp_session_id=row.whatsapp_session_id,
                whatsapp_session_name=row.whatsapp_session_name,
                whatsapp_session_phone_number=row.whatsapp_session_phone_number,
                temperature=row.temperature,
                stage=row.stage,
                lead_fit_score=row.lead.fit_score if row.lead else None,
                lead_fit_label=row.lead.fit_label if row.lead else None,
                lead_funnel_stage=row.lead.funnel_stage if row.lead else None,
                lead_intent_status=row.lead.intent_status if row.lead else None,
                lead_pain_status=row.lead.pain_status if row.lead else None,
                lead_meeting_status=row.lead.meeting_status if row.lead else None,
                priority_score=priority["score"],
                priority_label=priority["label"],
                priority_reasons=priority["reasons"],
                recommended_action=recommended_action,
                suggested_playbook=select_suggested_playbook(row.lead, playbooks) if row.lead else None,
                unread_count=row.unread_count,
                assignee=row.assignee,
                manual_mode=row.manual_mode,
                automation_paused=row.automation_paused,
                auto_reply_enabled=row.auto_reply_enabled,
                reply_delay_seconds=row.reply_delay_seconds,
                pending_human_review=row.pending_human_review,
                summary=row.summary,
                last_message_at=row.last_message_at,
                latest_message_preview=latest_message,
            )
        )
    items = _sort_conversations(items, sort_by=sort_by, sort_direction=sort_direction)
    total = len(items)
    sliced = items[(page - 1) * page_size : page * page_size]
    return {"items": sliced, "total": total, "page": page, "page_size": page_size}


@router.get("/conversations/{conversation_id}/workspace", response_model=ConversationWorkspaceRead)
def get_conversation_workspace(conversation_id: int, db: Session = Depends(get_db)) -> dict:
    stmt = (
        select(Conversation)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.whatsapp_session),
            selectinload(Conversation.lead).selectinload(Lead.tasks),
            selectinload(Conversation.lead).selectinload(Lead.qualified_lead),
            selectinload(Conversation.lead).selectinload(Lead.conversations),
        )
        .where(Conversation.id == conversation_id)
    )
    conversation = db.scalars(stmt).one_or_none()
    if not conversation or not conversation.lead:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    playbooks = list(db.scalars(select(Playbook).where(Playbook.active.is_(True)).order_by(Playbook.updated_at.desc())))
    setattr(conversation.lead, "_candidate_playbooks", playbooks)
    return {"conversation": conversation, "lead": _attach_priority(conversation.lead)}


@router.get("/conversations/{conversation_id}", response_model=ConversationRead)
def get_conversation_detail(conversation_id: int, db: Session = Depends(get_db)) -> Conversation:
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.whatsapp_session))
        .where(Conversation.id == conversation_id)
    )
    conversation = db.scalars(stmt).one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return conversation


@router.post("/conversations/{conversation_id}/takeover", response_model=ConversationRead)
def take_over_conversation(
    conversation_id: int,
    payload: ConversationTakeoverRequest,
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = _get_conversation_or_404(db, conversation_id)
    ops = ConversationOpsService()
    ops.take_over(conversation, payload.operator_name)
    ops.cancel_open_auto_reply_tasks(db, conversation.id)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/conversations/{conversation_id}/release", response_model=ConversationRead)
def release_conversation(conversation_id: int, db: Session = Depends(get_db)) -> Conversation:
    conversation = _get_conversation_or_404(db, conversation_id)
    ConversationOpsService().release(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.patch("/conversations/{conversation_id}/settings", response_model=ConversationRead)
def update_conversation_settings(
    conversation_id: int,
    payload: ConversationSettingsUpdate,
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = _get_conversation_or_404(db, conversation_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(conversation, key, value)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/conversations/{conversation_id}/mark-read", response_model=ConversationRead)
def mark_conversation_read(conversation_id: int, db: Session = Depends(get_db)) -> Conversation:
    conversation = _get_conversation_or_404(db, conversation_id)
    ConversationOpsService().mark_read(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/conversations/{conversation_id}/messages/manual-send", response_model=ConversationRead)
def send_manual_message(
    conversation_id: int,
    payload: ManualMessageRequest,
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = _get_conversation_or_404(db, conversation_id)
    lead = db.get(Lead, conversation.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    ops = ConversationOpsService()
    ops.take_over(conversation, payload.operator_name)
    ops.cancel_open_auto_reply_tasks(db, conversation.id)
    ops.send_outbound_message(
        db=db,
        lead=lead,
        conversation=conversation,
        text=payload.content,
        sender=payload.operator_name,
        author_role="human",
    )
    conversation.pending_draft = None
    conversation.pending_human_review = False
    conversation.pending_review_reason = None
    if payload.mark_as_read:
        ops.mark_read(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/leads/bulk")
def bulk_lead_action(payload: BulkLeadActionRequest, db: Session = Depends(get_db)) -> dict:
    leads = list(db.scalars(select(Lead).where(Lead.id.in_(payload.lead_ids))))
    affected = 0
    for lead in leads:
        if payload.action == "set_status" and payload.status:
            lead.status = payload.status
            affected += 1
        elif payload.action == "do_not_contact":
            mark_disqualified(lead)
            affected += 1
        elif payload.action == "start_outreach":
            lead_routes.start_outreach(lead.id, db)
            affected += 1
    db.commit()
    return {"affected": affected}


@router.post("/conversations/bulk")
def bulk_conversation_action(payload: BulkConversationActionRequest, db: Session = Depends(get_db)) -> dict:
    conversations = list(db.scalars(select(Conversation).where(Conversation.id.in_(payload.conversation_ids))))
    ops = ConversationOpsService()
    affected = 0
    for conversation in conversations:
        if payload.action == "takeover" and payload.operator_name:
            ops.take_over(conversation, payload.operator_name)
            affected += 1
        elif payload.action == "release":
            ops.release(conversation)
            affected += 1
        elif payload.action == "pause":
            conversation.automation_paused = True
            affected += 1
        elif payload.action == "resume":
            conversation.automation_paused = False
            conversation.manual_mode = False
            affected += 1
        elif payload.action == "set_auto_reply" and payload.auto_reply_enabled is not None:
            conversation.auto_reply_enabled = payload.auto_reply_enabled
            if payload.reply_delay_seconds is not None:
                conversation.reply_delay_seconds = payload.reply_delay_seconds
            affected += 1
    db.commit()
    return {"affected": affected}


@router.post("/prospecting/advisor", response_model=ProspectingAdvisorResponse)
def advise_prospecting(payload: ProspectingAdvisorRequest) -> dict:
    draft = None
    if payload.current_state:
        draft = ProspectingDraft(
            niche=payload.current_state.niche,
            city=payload.current_state.city,
            limit=payload.current_state.limit,
            enrich=payload.current_state.enrich,
            recipe_id=payload.current_state.recipe_id,
            search_goal=payload.current_state.search_goal,
            system_prompt=payload.current_state.system_prompt,
            source_channels=payload.current_state.source_channels,
            discovery_mode=payload.current_state.discovery_mode,
            minimum_valid_contacts=payload.current_state.minimum_valid_contacts,
            require_phone=payload.current_state.require_phone,
            fallback_enabled=payload.current_state.fallback_enabled,
            search_depth=payload.current_state.search_depth,
            agent_max_credits=payload.current_state.agent_max_credits,
        )
    return ProspectingAdvisorService().advise(message=payload.message, draft=draft)


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(AgentTask)
    count_stmt = select(func.count()).select_from(AgentTask)
    if status:
        stmt = stmt.where(AgentTask.status == status)
        count_stmt = count_stmt.where(AgentTask.status == status)
    total = db.scalar(count_stmt) or 0
    items = list(
        db.scalars(
            stmt.order_by(AgentTask.next_run_at.asc().nullslast()).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/tasks/{task_id}/run-now", response_model=AgentTaskRead)
def run_task_now(task_id: int, db: Session = Depends(get_db)) -> AgentTask:
    task = db.get(AgentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task não encontrada.")
    from app.workers.followup_worker import utcnow

    task.next_run_at = utcnow()
    task.status = "pending"
    db.commit()
    db.refresh(task)
    return task


@router.post("/tasks/{task_id}/cancel", response_model=AgentTaskRead)
def cancel_task(task_id: int, db: Session = Depends(get_db)) -> AgentTask:
    task = db.get(AgentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task não encontrada.")
    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    return task


@router.post("/prospecting/batches/preview", response_model=ProspectingBatchRead)
def create_prospecting_batch(payload: ProspectingBatchCreate, db: Session = Depends(get_db)) -> ProspectingBatch:
    advisor = ProspectingAdvisorService()
    normalized_city = advisor.normalize_city(payload.city) or payload.city
    prompt_snapshot = _resolve_prompt_snapshot(db, payload)
    recipe_snapshot = _resolve_recipe_snapshot(db, payload, prompt_snapshot=prompt_snapshot)
    batch = ProspectingBatch(
        campaign_id=payload.campaign_id,
        recipe_id=payload.recipe_id or recipe_snapshot.get("id"),
        prompt_category_id=prompt_snapshot.get("category_id"),
        prompt_id=prompt_snapshot.get("id"),
        niche=payload.niche,
        city=normalized_city,
        limit=payload.limit,
        enrich=payload.enrich,
        recipe_snapshot_json=recipe_snapshot,
        prompt_snapshot_json=prompt_snapshot,
        status="pending_review",
    )
    db.add(batch)
    db.flush()

    prospecting_service = ProspectingService(validate_phone_format=payload.validate_phone_format)
    enrichment_service = EnrichmentService()
    try:
        candidates = prospecting_service.find_leads(
            niche=payload.niche,
            city=normalized_city,
            limit=payload.limit,
            recipe=recipe_snapshot,
        )
    except TypeError:
        candidates = prospecting_service.find_leads(
            niche=payload.niche,
            city=normalized_city,
            limit=payload.limit,
        )
    batch.search_metrics_json = {
        "requested_limit": payload.limit,
        "returned_candidates": len(candidates),
        "discovery_mode": recipe_snapshot.get("discovery_mode"),
        "minimum_valid_contacts": recipe_snapshot.get("minimum_valid_contacts"),
        "source_channels": recipe_snapshot.get("source_channels"),
        "prompt_id": prompt_snapshot.get("id"),
        "prompt_name": prompt_snapshot.get("name"),
        "prompt_category_id": prompt_snapshot.get("category_id"),
        "prompt_category_name": prompt_snapshot.get("category_name"),
        "coverage_gap": max(int(recipe_snapshot.get("minimum_valid_contacts") or payload.limit) - len(candidates), 0),
    }
    for candidate in candidates:
        candidate_phone = candidate.phone_number
        research_payload = None
        research_summary = None
        if payload.enrich:
            try:
                tmp_lead = Lead(
                    business_name=candidate.business_name,
                    niche=candidate.niche,
                    city=candidate.city,
                    phone_number=candidate.phone_number,
                    whatsapp_number=candidate.phone_number,
                    website=candidate.website,
                    instagram_url=candidate.instagram_url,
                    facebook_url=candidate.facebook_url,
                    source_url=candidate.source_url,
                    source_query=candidate.source_query,
                    source_platform=candidate.source_platform,
                )
                research_payload = enrichment_service.enrich_lead(tmp_lead)
                research_summary = research_payload.get("summary") if research_payload else None
                enriched_phone = prospecting_service.sanitize_phone(
                    str(research_payload.get("phone_number")) if research_payload and research_payload.get("phone_number") else None
                )
                candidate_phone = candidate_phone or enriched_phone
            except Exception:
                research_payload = None
                research_summary = None

        if not candidate_phone:
            continue

        existing_lead = _find_existing_lead(
            db,
            business_name=candidate.business_name,
            city=candidate.city,
            phone_number=candidate_phone,
            website=candidate.website,
            instagram_url=candidate.instagram_url,
        )

        batch_candidate = ProspectingCandidate(
            batch_id=batch.id,
            business_name=candidate.business_name,
            niche=candidate.niche,
            city=candidate.city,
            source_url=candidate.source_url,
            source_query=candidate.source_query,
            source_platform=candidate.source_platform,
            website=candidate.website,
            instagram_url=candidate.instagram_url,
            facebook_url=candidate.facebook_url,
            phone_number=candidate_phone,
            prospecting_prompt_category_id=prompt_snapshot.get("category_id"),
            prospecting_prompt_id=prompt_snapshot.get("id"),
            existing_lead_id=existing_lead.id if existing_lead else None,
            existing_lead_status=existing_lead.status if existing_lead else None,
            notes=candidate.notes,
            research_summary=research_summary,
            research_payload=research_payload,
            status="duplicate" if existing_lead else "pending_review",
            search_reason=candidate.search_reason,
        )
        apply_fit_score_to_record(batch_candidate, research_payload)
        db.add(batch_candidate)
    db.commit()
    return _get_batch_or_404(db, batch.id)


@router.get("/prospecting/batches", response_model=list[ProspectingBatchRead])
def list_prospecting_batches(db: Session = Depends(get_db)) -> list[ProspectingBatch]:
    stmt = select(ProspectingBatch).options(selectinload(ProspectingBatch.candidates)).order_by(ProspectingBatch.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/prospecting/batches/{batch_id}", response_model=ProspectingBatchRead)
def get_prospecting_batch(batch_id: int, db: Session = Depends(get_db)) -> ProspectingBatch:
    return _get_batch_or_404(db, batch_id)


@router.post("/prospecting/batches/{batch_id}/apply", response_model=ProspectingBatchRead)
def apply_prospecting_batch_action(
    batch_id: int,
    payload: ProspectingBatchActionRequest,
    db: Session = Depends(get_db),
) -> ProspectingBatch:
    batch = _get_batch_or_404(db, batch_id)
    candidates = list(
        db.scalars(
            select(ProspectingCandidate).where(
                ProspectingCandidate.batch_id == batch_id,
                ProspectingCandidate.id.in_(payload.candidate_ids),
            )
        )
    )
    for candidate in candidates:
        if payload.action == "reject":
            candidate.status = "rejected"
            continue

        if payload.action in {"save_only", "save_and_start_outreach"}:
            prospect = ProspectLead(
                business_name=candidate.business_name,
                niche=candidate.niche,
                city=candidate.city,
                source_url=candidate.source_url,
                source_query=candidate.source_query,
                source_platform=candidate.source_platform,
                website=candidate.website,
                instagram_url=candidate.instagram_url,
                facebook_url=candidate.facebook_url,
                phone_number=candidate.phone_number,
                search_reason=candidate.search_reason,
                notes=candidate.notes,
            )
            lead = lead_routes._upsert_lead(db, prospect)
            lead.campaign_id = batch.campaign_id
            lead.prospecting_recipe_id = batch.recipe_id or lead.prospecting_recipe_id
            lead.prospecting_prompt_category_id = batch.prompt_category_id or lead.prospecting_prompt_category_id
            lead.prospecting_prompt_id = batch.prompt_id or lead.prospecting_prompt_id
            lead.source_origin = "prospecting"
            lead.inbound_unverified = False
            if batch.campaign_id:
                campaign = db.get(Campaign, batch.campaign_id)
                if campaign:
                    lead.offer_product_id = campaign.offer_product_id or lead.offer_product_id
                    lead.agent_strategy_id = campaign.agent_strategy_id or lead.agent_strategy_id
                    lead.prospecting_recipe_id = campaign.prospecting_recipe_id or lead.prospecting_recipe_id
            db.flush()
            candidate.lead_id = lead.id
            candidate.prospecting_prompt_category_id = lead.prospecting_prompt_category_id
            candidate.prospecting_prompt_id = lead.prospecting_prompt_id
            if candidate.research_payload:
                lead_routes._save_research(db, lead, candidate.research_payload)
                lead_routes._hydrate_lead_from_research(lead, candidate.research_payload)
            candidate.status = "saved"
            if payload.action == "save_and_start_outreach":
                if not lead.phone_number and not lead.whatsapp_number:
                    candidate.status = "saved_missing_contact"
                    candidate.delivery_status = None
                    candidate.delivery_note = "Lead salvo sem telefone/WhatsApp para iniciar contato."
                    continue
                try:
                    conversation, sent_message = lead_routes._start_outreach_internal(
                        db=db,
                        lead=lead,
                        queue_context={
                            "queue_origin": "outreach_start",
                            "candidate_id": candidate.id,
                            "batch_id": batch.id,
                        },
                    )
                    db.flush()
                    candidate.conversation_id = conversation.id
                    candidate.outreach_external_message_id = sent_message.external_message_id
                    candidate.delivery_status = sent_message.status
                    candidate.delivery_note = _candidate_delivery_note(sent_message)
                    candidate.status = _candidate_status_from_message(sent_message)
                except HTTPException:
                    candidate.status = "contact_failed"
                    candidate.delivery_status = "send_failed"
                    candidate.delivery_note = "Falha ao iniciar outreach para este lead."
    batch.status = "processed"
    db.commit()
    return _get_batch_or_404(db, batch_id)


@router.get("/campaigns", response_model=list[CampaignRead])
def list_campaigns(db: Session = Depends(get_db)) -> list[Campaign]:
    stmt = select(Campaign).order_by(Campaign.updated_at.desc())
    return list(db.scalars(stmt))


@router.get("/offer-products", response_model=list[OfferProductRead])
def list_offer_products(db: Session = Depends(get_db)) -> list[OfferProduct]:
    stmt = select(OfferProduct).order_by(OfferProduct.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/offer-products", response_model=OfferProductRead)
def create_offer_product(payload: OfferProductCreate, db: Session = Depends(get_db)) -> OfferProduct:
    item = OfferProduct(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/offer-products/{offer_product_id}", response_model=OfferProductRead)
def update_offer_product(offer_product_id: int, payload: OfferProductUpdate, db: Session = Depends(get_db)) -> OfferProduct:
    item = db.get(OfferProduct, offer_product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Oferta não encontrada.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/agent-strategies", response_model=list[AgentStrategyRead])
def list_agent_strategies(db: Session = Depends(get_db)) -> list[AgentStrategy]:
    stmt = select(AgentStrategy).order_by(AgentStrategy.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/agent-strategies", response_model=AgentStrategyRead)
def create_agent_strategy(payload: AgentStrategyCreate, db: Session = Depends(get_db)) -> AgentStrategy:
    item = AgentStrategy(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/agent-strategies/{strategy_id}", response_model=AgentStrategyRead)
def update_agent_strategy(strategy_id: int, payload: AgentStrategyUpdate, db: Session = Depends(get_db)) -> AgentStrategy:
    item = db.get(AgentStrategy, strategy_id)
    if not item:
        raise HTTPException(status_code=404, detail="Estratégia não encontrada.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/prompt-templates", response_model=list[PromptTemplateRead])
def list_prompt_templates(db: Session = Depends(get_db)) -> list[PromptTemplate]:
    stmt = select(PromptTemplate).order_by(PromptTemplate.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/prompt-templates", response_model=PromptTemplateRead)
def create_prompt_template(payload: PromptTemplateCreate, db: Session = Depends(get_db)) -> PromptTemplate:
    item = PromptTemplate(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/prompt-templates/{template_id}", response_model=PromptTemplateRead)
def update_prompt_template(template_id: int, payload: PromptTemplateUpdate, db: Session = Depends(get_db)) -> PromptTemplate:
    item = db.get(PromptTemplate, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="Template não encontrado.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/prospecting-prompt-categories", response_model=list[ProspectingPromptCategoryRead])
def list_prospecting_prompt_categories(db: Session = Depends(get_db)) -> list[ProspectingPromptCategory]:
    stmt = select(ProspectingPromptCategory).order_by(ProspectingPromptCategory.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/prospecting-prompt-categories", response_model=ProspectingPromptCategoryRead)
def create_prospecting_prompt_category(
    payload: ProspectingPromptCategoryCreate,
    db: Session = Depends(get_db),
) -> ProspectingPromptCategory:
    item = ProspectingPromptCategory(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/prospecting-prompt-categories/{category_id}", response_model=ProspectingPromptCategoryRead)
def update_prospecting_prompt_category(
    category_id: int,
    payload: ProspectingPromptCategoryUpdate,
    db: Session = Depends(get_db),
) -> ProspectingPromptCategory:
    item = db.get(ProspectingPromptCategory, category_id)
    if not item:
        raise HTTPException(status_code=404, detail="Categoria de prompt não encontrada.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/prospecting-prompts", response_model=list[ProspectingPromptRead])
def list_prospecting_prompts(
    category_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[ProspectingPrompt]:
    stmt = select(ProspectingPrompt)
    if category_id is not None:
        stmt = stmt.where(ProspectingPrompt.category_id == category_id)
    stmt = stmt.order_by(ProspectingPrompt.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/prospecting-prompts", response_model=ProspectingPromptRead)
def create_prospecting_prompt(payload: ProspectingPromptCreate, db: Session = Depends(get_db)) -> ProspectingPrompt:
    if payload.category_id and not db.get(ProspectingPromptCategory, payload.category_id):
        raise HTTPException(status_code=404, detail="Categoria de prompt não encontrada.")
    item = ProspectingPrompt(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/prospecting-prompts/{prompt_id}", response_model=ProspectingPromptRead)
def update_prospecting_prompt(prompt_id: int, payload: ProspectingPromptUpdate, db: Session = Depends(get_db)) -> ProspectingPrompt:
    item = db.get(ProspectingPrompt, prompt_id)
    if not item:
        raise HTTPException(status_code=404, detail="Prompt de prospecção não encontrado.")
    updates = payload.model_dump(exclude_unset=True)
    category_id = updates.get("category_id")
    if category_id and not db.get(ProspectingPromptCategory, category_id):
        raise HTTPException(status_code=404, detail="Categoria de prompt não encontrada.")
    for key, value in updates.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/prospecting-recipes", response_model=list[ProspectingRecipeRead])
def list_prospecting_recipes(db: Session = Depends(get_db)) -> list[ProspectingRecipe]:
    stmt = select(ProspectingRecipe).order_by(ProspectingRecipe.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/prospecting-recipes", response_model=ProspectingRecipeRead)
def create_prospecting_recipe(payload: ProspectingRecipeCreate, db: Session = Depends(get_db)) -> ProspectingRecipe:
    item = ProspectingRecipe(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/prospecting-recipes/{recipe_id}", response_model=ProspectingRecipeRead)
def update_prospecting_recipe(recipe_id: int, payload: ProspectingRecipeUpdate, db: Session = Depends(get_db)) -> ProspectingRecipe:
    item = db.get(ProspectingRecipe, recipe_id)
    if not item:
        raise HTTPException(status_code=404, detail="Recipe não encontrada.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.post("/campaigns", response_model=CampaignRead)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)) -> Campaign:
    campaign = Campaign(**payload.model_dump())
    if campaign.is_active:
        _deactivate_other_campaigns(db, exclude_id=None)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.patch("/campaigns/{campaign_id}", response_model=CampaignRead)
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, key, value)
    if campaign.is_active:
        _deactivate_other_campaigns(db, exclude_id=campaign.id)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/playbooks", response_model=list[PlaybookRead])
def list_playbooks(db: Session = Depends(get_db)) -> list[Playbook]:
    stmt = select(Playbook).order_by(Playbook.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/playbooks", response_model=PlaybookRead)
def create_playbook(payload: PlaybookCreate, db: Session = Depends(get_db)) -> Playbook:
    playbook = Playbook(**payload.model_dump())
    db.add(playbook)
    db.commit()
    db.refresh(playbook)
    return playbook


@router.patch("/playbooks/{playbook_id}", response_model=PlaybookRead)
def update_playbook(playbook_id: int, payload: PlaybookUpdate, db: Session = Depends(get_db)) -> Playbook:
    playbook = db.get(Playbook, playbook_id)
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook não encontrado.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(playbook, key, value)
    db.commit()
    db.refresh(playbook)
    return playbook


@router.get("/knowledge-items", response_model=list[KnowledgeItemRead])
def list_knowledge_items(db: Session = Depends(get_db)) -> list[KnowledgeItem]:
    stmt = select(KnowledgeItem).order_by(KnowledgeItem.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/knowledge-items", response_model=KnowledgeItemRead)
def create_knowledge_item(payload: KnowledgeItemCreate, db: Session = Depends(get_db)) -> KnowledgeItem:
    item = KnowledgeItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/knowledge-items/{item_id}", response_model=KnowledgeItemRead)
def update_knowledge_item(item_id: int, payload: KnowledgeItemUpdate, db: Session = Depends(get_db)) -> KnowledgeItem:
    item = db.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item de conhecimento não encontrado.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def _get_conversation_or_404(db: Session, conversation_id: int) -> Conversation:
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages), selectinload(Conversation.whatsapp_session))
        .where(Conversation.id == conversation_id)
    )
    conversation = db.scalars(stmt).one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return conversation


def _get_whatsapp_session_or_404(db: Session, session_id: int) -> WhatsappSession:
    session = db.get(WhatsappSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão WhatsApp não encontrada.")
    return session


def _attach_priority(lead: Lead) -> Lead:
    unread_count = sum(conversation.unread_count for conversation in lead.conversations)
    pending_review = any(conversation.pending_human_review for conversation in lead.conversations)
    priority = priority_snapshot(lead, unread_count=unread_count, pending_human_review=pending_review)
    recommended_action = recommended_action_snapshot(
        lead,
        unread_count=unread_count,
        pending_human_review=pending_review,
        has_open_conversation=bool(lead.conversations),
    )
    setattr(lead, "priority_score", priority["score"])
    setattr(lead, "priority_label", priority["label"])
    setattr(lead, "priority_reasons", priority["reasons"])
    setattr(lead, "recommended_action", recommended_action)
    setattr(lead, "suggested_playbook", select_suggested_playbook(lead, getattr(lead, "_candidate_playbooks", None)))
    return lead


def _sort_leads(items: list[Lead], *, sort_by: str, sort_direction: str) -> list[Lead]:
    reverse = sort_direction != "asc"

    def key_priority(lead: Lead) -> tuple[float, float]:
        return (float(getattr(lead, "priority_score", 0) or 0), float(lead.fit_score or 0))

    def key_fit(lead: Lead) -> tuple[float, float]:
        return (float(lead.fit_score or 0), float(getattr(lead, "priority_score", 0) or 0))

    def key_updated(lead: Lead):
        return lead.updated_at

    def key_created(lead: Lead):
        return lead.created_at

    key_map = {
        "priority": key_priority,
        "fit_score": key_fit,
        "updated_at": key_updated,
        "created_at": key_created,
    }
    return sorted(items, key=key_map.get(sort_by, key_priority), reverse=reverse)


def _sort_conversations(
    items: list[ConversationListItemRead],
    *,
    sort_by: str,
    sort_direction: str,
) -> list[ConversationListItemRead]:
    reverse = sort_direction != "asc"

    def key_priority(item: ConversationListItemRead) -> tuple[float, int, float]:
        return (float(item.priority_score or 0), int(item.unread_count or 0), float(item.lead_fit_score or 0))

    def key_recent(item: ConversationListItemRead) -> tuple[bool, object]:
        return (item.last_message_at is not None, item.last_message_at)

    def key_unread(item: ConversationListItemRead) -> tuple[int, float]:
        return (int(item.unread_count or 0), float(item.priority_score or 0))

    def key_fit(item: ConversationListItemRead) -> tuple[float, float]:
        return (float(item.lead_fit_score or 0), float(item.priority_score or 0))

    key_map = {
        "priority": key_priority,
        "recent": key_recent,
        "unread": key_unread,
        "fit_score": key_fit,
    }
    return sorted(items, key=key_map.get(sort_by, key_priority), reverse=reverse)


def _latest_message_preview_map(db: Session, conversation_ids: list[int]) -> dict[int, str]:
    if not conversation_ids:
        return {}
    latest_sent_at_subquery = (
        select(
            Message.conversation_id.label("conversation_id"),
            func.max(Message.sent_at).label("latest_sent_at"),
        )
        .where(Message.conversation_id.in_(conversation_ids))
        .group_by(Message.conversation_id)
        .subquery()
    )
    rows = db.execute(
        select(Message.conversation_id, Message.content)
        .join(
            latest_sent_at_subquery,
            (Message.conversation_id == latest_sent_at_subquery.c.conversation_id)
            & (Message.sent_at == latest_sent_at_subquery.c.latest_sent_at),
        )
    ).all()
    preview_map: dict[int, str] = {}
    for conversation_id, content in rows:
        preview_map[int(conversation_id)] = content
    return preview_map


def _get_batch_or_404(db: Session, batch_id: int) -> ProspectingBatch:
    stmt = (
        select(ProspectingBatch)
        .options(selectinload(ProspectingBatch.candidates))
        .where(ProspectingBatch.id == batch_id)
    )
    batch = db.scalars(stmt).one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Lote de prospecção não encontrado.")
    return batch


def _resolve_prompt_snapshot(db: Session, payload: ProspectingBatchCreate) -> dict:
    prompt = db.get(ProspectingPrompt, payload.prompt_id) if payload.prompt_id else None
    if payload.prompt_id and not prompt:
        raise HTTPException(status_code=404, detail="Prompt de prospecção não encontrado.")
    category = None
    if prompt and prompt.category_id:
        category = db.get(ProspectingPromptCategory, prompt.category_id)
    elif payload.prompt_category_id:
        category = db.get(ProspectingPromptCategory, payload.prompt_category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Categoria de prompt não encontrada.")

    prompt_text = payload.system_prompt
    if not prompt_text and prompt:
        prompt_text = prompt.prompt_text

    objective = payload.search_goal
    if not objective and prompt and prompt.objective:
        objective = prompt.objective

    return {
        "id": prompt.id if prompt else None,
        "name": prompt.name if prompt else ("Prompt ad-hoc" if prompt_text else None),
        "category_id": category.id if category else None,
        "category_name": category.name if category else None,
        "category_description": category.description if category else None,
        "offer_context": category.offer_context if category else None,
        "target_niche": category.target_niche if category else None,
        "objective": objective,
        "prompt_text": prompt_text or "",
        "source_channels": payload.source_channels or (prompt.source_channels if prompt and prompt.source_channels else None),
        "discovery_mode": payload.discovery_mode or (prompt.discovery_mode if prompt else None),
        "minimum_valid_contacts": payload.minimum_valid_contacts
        or (prompt.minimum_valid_contacts if prompt and prompt.minimum_valid_contacts else None),
        "require_phone": payload.require_phone if payload.require_phone is not None else (prompt.require_phone if prompt else None),
        "fallback_enabled": payload.fallback_enabled
        if payload.fallback_enabled is not None
        else (prompt.fallback_enabled if prompt else None),
        "search_depth": payload.search_depth or (prompt.search_depth if prompt and prompt.search_depth else None),
        "agent_max_credits": payload.agent_max_credits or (prompt.agent_max_credits if prompt else None),
        "notes": prompt.notes if prompt else None,
        "active": prompt.active if prompt else True,
    }


def _resolve_recipe_snapshot(db: Session, payload: ProspectingBatchCreate, *, prompt_snapshot: dict | None = None) -> dict:
    campaign = db.get(Campaign, payload.campaign_id) if payload.campaign_id else None
    recipe_id = payload.recipe_id or (campaign.prospecting_recipe_id if campaign else None)
    recipe = db.get(ProspectingRecipe, recipe_id) if recipe_id else None
    prompt_snapshot = prompt_snapshot or {}
    return {
        "id": recipe.id if recipe else None,
        "name": recipe.name if recipe else "Recipe ad-hoc",
        "objective": prompt_snapshot.get("objective")
        or payload.search_goal
        or (recipe.objective if recipe else f"achar {payload.niche} em {payload.city}"),
        "system_prompt": prompt_snapshot.get("prompt_text") or payload.system_prompt or (recipe.system_prompt if recipe else ""),
        "source_channels": prompt_snapshot.get("source_channels")
        or payload.source_channels
        or (recipe.source_channels if recipe else ["google", "linkedin", "instagram"]),
        "inclusion_rules": recipe.inclusion_rules if recipe else "",
        "exclusion_rules": recipe.exclusion_rules if recipe else "",
        "minimum_valid_contacts": prompt_snapshot.get("minimum_valid_contacts")
        or payload.minimum_valid_contacts
        or (recipe.minimum_valid_contacts if recipe else payload.limit),
        "max_total_results": recipe.max_total_results if recipe else max(payload.limit, 10),
        "search_depth": prompt_snapshot.get("search_depth") or payload.search_depth or (recipe.search_depth if recipe else 2),
        "require_phone": prompt_snapshot.get("require_phone")
        if prompt_snapshot.get("require_phone") is not None
        else payload.require_phone
        if payload.require_phone is not None
        else (recipe.require_phone if recipe else True),
        "validate_phone_format": payload.validate_phone_format if payload.validate_phone_format is not None else (recipe.validate_phone_format if recipe else False),
        "discovery_mode": prompt_snapshot.get("discovery_mode") or payload.discovery_mode or (recipe.discovery_mode if recipe else "hybrid"),
        "fallback_enabled": prompt_snapshot.get("fallback_enabled")
        if prompt_snapshot.get("fallback_enabled") is not None
        else payload.fallback_enabled
        if payload.fallback_enabled is not None
        else (recipe.fallback_enabled if recipe else True),
        "scoring_guidance": recipe.scoring_guidance if recipe else "",
        "assistant_notes": recipe.assistant_notes if recipe else "",
        "schema_fields": recipe.schema_fields if recipe else None,
        "agent_max_credits": prompt_snapshot.get("agent_max_credits")
        or payload.agent_max_credits
        or (recipe.agent_max_credits if recipe else None),
        "prompt_category_id": prompt_snapshot.get("category_id"),
        "prompt_category_name": prompt_snapshot.get("category_name"),
        "prompt_id": prompt_snapshot.get("id"),
        "prompt_name": prompt_snapshot.get("name"),
        "active": True,
    }


def _deactivate_other_campaigns(db: Session, exclude_id: int | None) -> None:
    campaigns = list(db.scalars(select(Campaign).where(Campaign.is_active.is_(True))))
    for campaign in campaigns:
        if exclude_id is not None and campaign.id == exclude_id:
            continue
        campaign.is_active = False


def _candidate_status_from_message(message) -> str:
    status = str(message.status or "")
    if status in {"queued_waiting", "queued_retry"}:
        return "queued_contact"
    if status in {"send_failed", "send_timeout", "draft_only", "cancelled"}:
        return "contact_failed"
    return "contacted"


def _candidate_delivery_note(message) -> str | None:
    metadata = message.metadata_json if isinstance(message.metadata_json, dict) else {}
    error = metadata.get("error") if isinstance(metadata.get("error"), dict) else {}
    queue = metadata.get("queue") if isinstance(metadata.get("queue"), dict) else {}
    status = str(message.status or "")
    if status in {"queued_waiting", "queued_retry"}:
        scheduled_for = queue.get("scheduled_for")
        return (
            f"Mensagem aguardando fila do provedor ate {scheduled_for}."
            if scheduled_for
            else "Mensagem aguardando fila do provedor."
        )
    if status in {"send_failed", "send_timeout"}:
        body = error.get("body")
        if isinstance(body, str) and body:
            return body
        message_text = error.get("message")
        if isinstance(message_text, str) and message_text:
            return message_text
        return "O provedor rejeitou ou nao concluiu o envio."
    if status == "draft_only":
        return "Outbound real desligado no momento do envio."
    return "Contato iniciado e aceito pelo provedor."


def _find_existing_lead(
    db: Session,
    *,
    business_name: str,
    city: str,
    phone_number: str | None,
    website: str | None,
    instagram_url: str | None,
) -> Lead | None:
    if phone_number:
        lead = db.scalar(select(Lead).where(Lead.phone_number == phone_number))
        if lead:
            return lead
    if website:
        lead = db.scalar(select(Lead).where(Lead.website == website))
        if lead:
            return lead
    if instagram_url:
        lead = db.scalar(select(Lead).where(Lead.instagram_url == instagram_url))
        if lead:
            return lead
    return db.scalar(select(Lead).where(Lead.business_name == business_name, Lead.city == city))
