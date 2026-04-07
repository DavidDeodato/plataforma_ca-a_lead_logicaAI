from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.db.models import (
    AgentStrategy,
    AgentTask,
    Campaign,
    Conversation,
    Lead,
    Message,
    OfferProduct,
    ProspectingPrompt,
    ProspectingPromptCategory,
    ProspectingRecipe,
    QualifiedLead,
)
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
    leads = list(db.scalars(select(Lead)))
    campaigns = list(db.scalars(select(Campaign).order_by(Campaign.updated_at.desc())))
    offers = list(db.scalars(select(OfferProduct).order_by(OfferProduct.updated_at.desc())))
    strategies = list(db.scalars(select(AgentStrategy).order_by(AgentStrategy.updated_at.desc())))
    recipes = list(db.scalars(select(ProspectingRecipe).order_by(ProspectingRecipe.updated_at.desc())))
    prompt_categories = list(db.scalars(select(ProspectingPromptCategory).order_by(ProspectingPromptCategory.updated_at.desc())))
    prompt_library = list(db.scalars(select(ProspectingPrompt).order_by(ProspectingPrompt.updated_at.desc())))
    outbound_messages = list(db.scalars(select(Message).where(Message.direction == "outbound")))

    def percentage(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100, 1)

    def average(values: list[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 1)

    contacted = sum(1 for lead in leads if lead.first_contacted_at)
    replied = sum(1 for lead in leads if lead.first_replied_at)
    positive_replies = sum(1 for lead in leads if lead.positive_reply_detected)
    pain_confirmed = sum(1 for lead in leads if lead.pain_status == "confirmed")
    meeting_offered = sum(1 for lead in leads if lead.meeting_status in {"offered", "booked", "won"})
    meetings_booked = sum(1 for lead in leads if lead.meeting_booked_at or lead.meeting_status in {"booked", "won"})
    qualified_opportunities = sum(1 for lead in leads if lead.qualified_opportunity_at)
    valid_contacts = sum(1 for lead in leads if lead.phone_number or lead.whatsapp_number)
    fit_scores = [lead.fit_score for lead in leads if lead.fit_score is not None]
    first_outreach_minutes = [
        round((lead.first_contacted_at - lead.created_at).total_seconds() / 60, 1)
        for lead in leads
        if lead.first_contacted_at and lead.created_at
    ]
    outbound_failures = sum(1 for message in outbound_messages if message.status in {"send_failed", "send_timeout"})
    queued_tasks = db.scalar(
        select(func.count()).select_from(AgentTask).where(
            AgentTask.status == "pending",
            AgentTask.task_type.in_(["queued_outbound", "delayed_auto_reply"]),
        )
    ) or 0

    totals = {
        "leads": len(leads),
        "qualified": db.scalar(select(func.count()).select_from(QualifiedLead)) or 0,
        "conversations": db.scalar(select(func.count()).select_from(Conversation)) or 0,
        "tasks_pending": (
            db.scalar(select(func.count()).select_from(AgentTask).where(AgentTask.status == "pending")) or 0
        ),
        "meetings_booked": meetings_booked,
        "qualified_opportunities": qualified_opportunities,
    }
    recent_activity = {
        "new_leads": db.scalar(select(func.count()).select_from(Lead).where(Lead.status == "new")) or 0,
        "contacted": contacted,
        "replied": replied,
        "qualified": totals["qualified"],
        "meetings_booked": meetings_booked,
    }
    funnel = {stage: 0 for stage in [
        "captured",
        "contacted",
        "replied",
        "positive_reply",
        "pain_confirmed",
        "fit_confirmed",
        "meeting_offered",
        "meeting_booked",
        "qualified_opportunity",
        "closed_won",
        "closed_lost",
        "do_not_contact",
    ]}
    for lead in leads:
        stage = lead.funnel_stage or "captured"
        funnel[stage] = funnel.get(stage, 0) + 1

    conversion = {
        "meetings_qualified_per_100_contacted": percentage(meetings_booked, contacted),
        "qualified_opportunities_per_100_contacted": percentage(qualified_opportunities, contacted),
        "reply_rate": percentage(replied, contacted),
        "positive_reply_rate": percentage(positive_replies, contacted),
        "lead_fit_score_avg": average(fit_scores),
        "valid_contact_rate": percentage(valid_contacts, max(len(leads), 1)),
        "pain_confirmed_rate": percentage(pain_confirmed, max(replied, 1)),
        "meeting_offer_acceptance_rate": percentage(meetings_booked, max(meeting_offered, 1)),
    }
    operations = {
        "send_failure_rate": percentage(outbound_failures, max(len(outbound_messages), 1)),
        "time_to_first_outreach_minutes": average(first_outreach_minutes),
        "queued_tasks": queued_tasks,
        "outbound_messages": len(outbound_messages),
        "outbound_failures": outbound_failures,
    }
    campaign_rows: list[dict] = []
    for campaign in campaigns:
        campaign_leads = [lead for lead in leads if lead.campaign_id == campaign.id]
        if not campaign_leads:
            campaign_rows.append(
                {
                    "id": campaign.id,
                    "name": campaign.name,
                    "status": campaign.status,
                    "is_active": campaign.is_active,
                    "leads": 0,
                    "contacted": 0,
                    "reply_rate": 0.0,
                    "positive_reply_rate": 0.0,
                    "meetings_booked": 0,
                    "qualified_opportunities": 0,
                    "fit_score_avg": 0.0,
                }
            )
            continue
        campaign_contacted = sum(1 for lead in campaign_leads if lead.first_contacted_at)
        campaign_replied = sum(1 for lead in campaign_leads if lead.first_replied_at)
        campaign_positive = sum(1 for lead in campaign_leads if lead.positive_reply_detected)
        campaign_fit_scores = [lead.fit_score for lead in campaign_leads if lead.fit_score is not None]
        campaign_rows.append(
            {
                "id": campaign.id,
                "name": campaign.name,
                "status": campaign.status,
                "is_active": campaign.is_active,
                "leads": len(campaign_leads),
                "contacted": campaign_contacted,
                "reply_rate": percentage(campaign_replied, campaign_contacted),
                "positive_reply_rate": percentage(campaign_positive, campaign_contacted),
                "meetings_booked": sum(1 for lead in campaign_leads if lead.meeting_booked_at),
                "qualified_opportunities": sum(1 for lead in campaign_leads if lead.qualified_opportunity_at),
                "fit_score_avg": average(campaign_fit_scores),
            }
        )

    offer_rows: list[dict] = []
    for offer in offers:
        offer_leads = [lead for lead in leads if lead.offer_product_id == offer.id]
        offer_contacted = sum(1 for lead in offer_leads if lead.first_contacted_at)
        offer_replied = sum(1 for lead in offer_leads if lead.first_replied_at)
        offer_rows.append(
            {
                "id": offer.id,
                "name": offer.name,
                "leads": len(offer_leads),
                "contacted": offer_contacted,
                "reply_rate": percentage(offer_replied, offer_contacted),
                "meetings_booked": sum(1 for lead in offer_leads if lead.meeting_booked_at),
                "fit_score_avg": average([lead.fit_score for lead in offer_leads if lead.fit_score is not None]),
            }
        )

    strategy_rows: list[dict] = []
    for strategy in strategies:
        strategy_leads = [lead for lead in leads if lead.agent_strategy_id == strategy.id]
        strategy_contacted = sum(1 for lead in strategy_leads if lead.first_contacted_at)
        strategy_replied = sum(1 for lead in strategy_leads if lead.first_replied_at)
        strategy_rows.append(
            {
                "id": strategy.id,
                "name": strategy.name,
                "leads": len(strategy_leads),
                "contacted": strategy_contacted,
                "reply_rate": percentage(strategy_replied, strategy_contacted),
                "positive_reply_rate": percentage(
                    sum(1 for lead in strategy_leads if lead.positive_reply_detected),
                    strategy_contacted,
                ),
                "meetings_booked": sum(1 for lead in strategy_leads if lead.meeting_booked_at),
            }
        )

    recipe_rows: list[dict] = []
    for recipe in recipes:
        recipe_leads = [lead for lead in leads if lead.prospecting_recipe_id == recipe.id]
        recipe_contacted = sum(1 for lead in recipe_leads if lead.first_contacted_at)
        recipe_replied = sum(1 for lead in recipe_leads if lead.first_replied_at)
        recipe_rows.append(
            {
                "id": recipe.id,
                "name": recipe.name,
                "leads": len(recipe_leads),
                "contacted": recipe_contacted,
                "reply_rate": percentage(recipe_replied, recipe_contacted),
                "meetings_booked": sum(1 for lead in recipe_leads if lead.meeting_booked_at),
                "fit_score_avg": average([lead.fit_score for lead in recipe_leads if lead.fit_score is not None]),
            }
        )
    prompt_category_rows: list[dict] = []
    for category in prompt_categories:
        category_leads = [lead for lead in leads if lead.prospecting_prompt_category_id == category.id]
        category_contacted = sum(1 for lead in category_leads if lead.first_contacted_at)
        category_replied = sum(1 for lead in category_leads if lead.first_replied_at)
        prompt_category_rows.append(
            {
                "id": category.id,
                "name": category.name,
                "leads": len(category_leads),
                "contacted": category_contacted,
                "reply_rate": percentage(category_replied, category_contacted),
                "positive_reply_rate": percentage(
                    sum(1 for lead in category_leads if lead.positive_reply_detected),
                    category_contacted,
                ),
                "meetings_booked": sum(1 for lead in category_leads if lead.meeting_booked_at),
                "closed_won": sum(1 for lead in category_leads if lead.closed_won_at),
                "fit_score_avg": average([lead.fit_score for lead in category_leads if lead.fit_score is not None]),
            }
        )
    prompt_rows: list[dict] = []
    for prompt in prompt_library:
        prompt_leads = [lead for lead in leads if lead.prospecting_prompt_id == prompt.id]
        prompt_contacted = sum(1 for lead in prompt_leads if lead.first_contacted_at)
        prompt_replied = sum(1 for lead in prompt_leads if lead.first_replied_at)
        prompt_rows.append(
            {
                "id": prompt.id,
                "name": prompt.name,
                "category_id": prompt.category_id,
                "category_name": next((category.name for category in prompt_categories if category.id == prompt.category_id), None),
                "leads": len(prompt_leads),
                "contacted": prompt_contacted,
                "reply_rate": percentage(prompt_replied, prompt_contacted),
                "positive_reply_rate": percentage(
                    sum(1 for lead in prompt_leads if lead.positive_reply_detected),
                    prompt_contacted,
                ),
                "meetings_booked": sum(1 for lead in prompt_leads if lead.meeting_booked_at),
                "closed_won": sum(1 for lead in prompt_leads if lead.closed_won_at),
                "fit_score_avg": average([lead.fit_score for lead in prompt_leads if lead.fit_score is not None]),
            }
        )
    return {
        "totals": totals,
        "safe_mode": runtime_service.get_flags(db),
        "recent_activity": recent_activity,
        "funnel": funnel,
        "conversion": conversion,
        "operations": operations,
        "campaigns": campaign_rows,
        "offers": offer_rows,
        "strategies": strategy_rows,
        "recipes": recipe_rows,
        "prompt_categories": prompt_category_rows,
        "prospecting_prompts": prompt_rows,
        "runtime": runtime,
    }
