from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    niche: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    offer_product_id: Mapped[int | None] = mapped_column(ForeignKey("offer_products.id", ondelete="SET NULL"), index=True)
    agent_strategy_id: Mapped[int | None] = mapped_column(ForeignKey("agent_strategies.id", ondelete="SET NULL"), index=True)
    prospecting_recipe_id: Mapped[int | None] = mapped_column(ForeignKey("prospecting_recipes.id", ondelete="SET NULL"), index=True)
    prospecting_prompt_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("prospecting_prompt_categories.id", ondelete="SET NULL"),
        index=True,
    )
    prospecting_prompt_id: Mapped[int | None] = mapped_column(
        ForeignKey("prospecting_prompts.id", ondelete="SET NULL"),
        index=True,
    )
    phone_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(500))
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    facebook_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_query: Mapped[str | None] = mapped_column(String(255))
    source_platform: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    funnel_stage: Mapped[str] = mapped_column(String(40), default="captured", index=True)
    fit_score: Mapped[float | None] = mapped_column(Float, index=True)
    fit_label: Mapped[str | None] = mapped_column(String(20), index=True)
    fit_reasons_json: Mapped[dict | None] = mapped_column("fit_reasons", JSON)
    fit_scored_at: Mapped[datetime | None] = mapped_column(DateTime)
    first_contacted_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    first_replied_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    positive_reply_detected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    positive_reply_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    pain_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    pain_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    intent_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    fit_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    authority_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    urgency_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    objection_status: Mapped[str] = mapped_column(String(40), default="none", index=True)
    meeting_status: Mapped[str] = mapped_column(String(30), default="not_offered", index=True)
    meeting_offered_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    meeting_booked_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    qualified_opportunity_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    closed_won_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    closed_lost_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    source_origin: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    inbound_unverified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    research_entries: Mapped[list[LeadResearch]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    qualified_lead: Mapped[QualifiedLead | None] = relationship(back_populates="lead", cascade="all, delete-orphan")
    tasks: Mapped[list[AgentTask]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    campaign: Mapped[Campaign | None] = relationship(back_populates="leads")
    offer_product: Mapped[OfferProduct | None] = relationship(back_populates="leads")
    agent_strategy: Mapped[AgentStrategy | None] = relationship(back_populates="leads")
    prospecting_recipe: Mapped[ProspectingRecipe | None] = relationship(back_populates="leads")
    prospecting_prompt_category: Mapped[ProspectingPromptCategory | None] = relationship(back_populates="leads")
    prospecting_prompt: Mapped[ProspectingPrompt | None] = relationship(back_populates="leads")


class WhatsappSession(Base):
    __tablename__ = "whatsapp_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    wasender_session_id: Mapped[int | None] = mapped_column(Integer, unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="disconnected", index=True)
    api_key: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255))
    webhook_url: Mapped[str | None] = mapped_column(String(500))
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    webhook_events: Mapped[list[str] | None] = mapped_column(JSON)
    account_protection: Mapped[bool] = mapped_column(Boolean, default=True)
    log_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    read_incoming_messages: Mapped[bool] = mapped_column(Boolean, default=False)
    outbound_cooldown_seconds: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(40), default="manual", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="whatsapp_session")

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @property
    def has_webhook_secret(self) -> bool:
        return bool(self.webhook_secret)


class LeadResearch(Base):
    __tablename__ = "lead_research"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(120), default="firecrawl")
    summary: Mapped[str | None] = mapped_column(Text)
    pain_points: Mapped[list[str] | None] = mapped_column(JSON)
    opportunities: Mapped[list[str] | None] = mapped_column(JSON)
    evidence: Mapped[list[str] | None] = mapped_column(JSON)
    structured_data: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lead: Mapped[Lead] = relationship(back_populates="research_entries")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("lead_id", "channel", "whatsapp_session_id", name="uq_lead_channel_session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(40), default="whatsapp")
    whatsapp_session_id: Mapped[int | None] = mapped_column(ForeignKey("whatsapp_sessions.id", ondelete="SET NULL"), index=True)
    external_chat_id: Mapped[str | None] = mapped_column(String(255))
    temperature: Mapped[str] = mapped_column(String(20), default="cold", index=True)
    stage: Mapped[str] = mapped_column(String(40), default="new", index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    assignee: Mapped[str | None] = mapped_column(String(120))
    manual_mode: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    automation_paused: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    auto_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    reply_delay_seconds: Mapped[int] = mapped_column(Integer, default=30)
    taken_over_at: Mapped[datetime | None] = mapped_column(DateTime)
    taken_over_by: Mapped[str | None] = mapped_column(String(120))
    pending_human_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    pending_review_reason: Mapped[str | None] = mapped_column(Text)
    pending_draft: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    lead: Mapped[Lead] = relationship(back_populates="conversations")
    whatsapp_session: Mapped[WhatsappSession | None] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    tasks: Mapped[list[AgentTask]] = relationship(back_populates="conversation")

    @property
    def whatsapp_session_name(self) -> str | None:
        return self.whatsapp_session.name if self.whatsapp_session else None

    @property
    def whatsapp_session_phone_number(self) -> str | None:
        return self.whatsapp_session.phone_number if self.whatsapp_session else None


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    direction: Mapped[str] = mapped_column(String(20), index=True)
    sender: Mapped[str | None] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str | None] = mapped_column(String(40), index=True)
    author_role: Mapped[str | None] = mapped_column(String(40), index=True)
    prompt_phase: Mapped[str | None] = mapped_column(String(40), index=True)
    instruction_snapshot_json: Mapped[dict | None] = mapped_column("instruction_snapshot", JSON)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class QualifiedLead(Base):
    __tablename__ = "qualified_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), unique=True, index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    qualification_reason: Mapped[str] = mapped_column(Text)
    handoff_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    lead: Mapped[Lead] = relationship(back_populates="qualified_lead")


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(80), default="follow_up", index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    current_attempt: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_reason: Mapped[str | None] = mapped_column(String(120))
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    payload: Mapped[dict | None] = mapped_column(JSON)
    last_result: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    lead: Mapped[Lead] = relationship(back_populates="tasks")
    conversation: Mapped[Conversation | None] = relationship(back_populates="tasks")


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class OfferProduct(Base):
    __tablename__ = "offer_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    target_customer: Mapped[str | None] = mapped_column(Text)
    pains: Mapped[str | None] = mapped_column(Text)
    differentiators: Mapped[str | None] = mapped_column(Text)
    proof_points: Mapped[str | None] = mapped_column(Text)
    cta_primary: Mapped[str | None] = mapped_column(Text)
    allowed_claims: Mapped[str | None] = mapped_column(Text)
    forbidden_claims: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    campaigns: Mapped[list[Campaign]] = relationship(back_populates="offer_product")
    leads: Mapped[list[Lead]] = relationship(back_populates="offer_product")


class AgentStrategy(Base):
    __tablename__ = "agent_strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    persona: Mapped[str | None] = mapped_column(Text)
    primary_goal: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str | None] = mapped_column(String(180))
    opening_strategy: Mapped[str | None] = mapped_column(Text)
    qualification_strategy: Mapped[str | None] = mapped_column(Text)
    objection_strategy: Mapped[str | None] = mapped_column(Text)
    follow_up_strategy: Mapped[str | None] = mapped_column(Text)
    handoff_strategy: Mapped[str | None] = mapped_column(Text)
    guardrails: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    prompt_templates: Mapped[list[PromptTemplate]] = relationship(back_populates="agent_strategy", cascade="all, delete-orphan")
    campaigns: Mapped[list[Campaign]] = relationship(back_populates="agent_strategy")
    leads: Mapped[list[Lead]] = relationship(back_populates="agent_strategy")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agent_strategy_id: Mapped[int | None] = mapped_column(ForeignKey("agent_strategies.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    phase: Mapped[str] = mapped_column(String(40), index=True)
    channel: Mapped[str] = mapped_column(String(40), default="whatsapp", index=True)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str | None] = mapped_column(Text)
    output_contract: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    agent_strategy: Mapped[AgentStrategy | None] = relationship(back_populates="prompt_templates")


class ProspectingRecipe(Base):
    __tablename__ = "prospecting_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    objective: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    source_channels: Mapped[list[str] | None] = mapped_column(JSON)
    inclusion_rules: Mapped[str | None] = mapped_column(Text)
    exclusion_rules: Mapped[str | None] = mapped_column(Text)
    minimum_valid_contacts: Mapped[int] = mapped_column(Integer, default=10)
    max_total_results: Mapped[int] = mapped_column(Integer, default=25)
    search_depth: Mapped[int] = mapped_column(Integer, default=2)
    require_phone: Mapped[bool] = mapped_column(Boolean, default=True)
    validate_phone_format: Mapped[bool] = mapped_column(Boolean, default=True)
    discovery_mode: Mapped[str] = mapped_column(String(40), default="hybrid", index=True)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scoring_guidance: Mapped[str | None] = mapped_column(Text)
    assistant_notes: Mapped[str | None] = mapped_column(Text)
    schema_fields: Mapped[dict | None] = mapped_column(JSON)
    agent_max_credits: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    campaigns: Mapped[list[Campaign]] = relationship(back_populates="prospecting_recipe")
    batches: Mapped[list[ProspectingBatch]] = relationship(back_populates="recipe")
    leads: Mapped[list[Lead]] = relationship(back_populates="prospecting_recipe")


class ProspectingPromptCategory(Base):
    __tablename__ = "prospecting_prompt_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    offer_context: Mapped[str | None] = mapped_column(Text)
    target_niche: Mapped[str | None] = mapped_column(String(120), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    prompts: Mapped[list[ProspectingPrompt]] = relationship(back_populates="category", cascade="all, delete-orphan")
    leads: Mapped[list[Lead]] = relationship(back_populates="prospecting_prompt_category")


class ProspectingPrompt(Base):
    __tablename__ = "prospecting_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("prospecting_prompt_categories.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(180), index=True)
    prompt_text: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str | None] = mapped_column(Text)
    source_channels: Mapped[list[str] | None] = mapped_column(JSON)
    discovery_mode: Mapped[str] = mapped_column(String(40), default="hybrid", index=True)
    minimum_valid_contacts: Mapped[int] = mapped_column(Integer, default=10)
    require_phone: Mapped[bool] = mapped_column(Boolean, default=True)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    search_depth: Mapped[int] = mapped_column(Integer, default=2)
    agent_max_credits: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    category: Mapped[ProspectingPromptCategory | None] = relationship(back_populates="prompts")
    leads: Mapped[list[Lead]] = relationship(back_populates="prospecting_prompt")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    niche: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    offer_product_id: Mapped[int | None] = mapped_column(ForeignKey("offer_products.id", ondelete="SET NULL"), index=True)
    agent_strategy_id: Mapped[int | None] = mapped_column(ForeignKey("agent_strategies.id", ondelete="SET NULL"), index=True)
    prospecting_recipe_id: Mapped[int | None] = mapped_column(ForeignKey("prospecting_recipes.id", ondelete="SET NULL"), index=True)
    offer_name: Mapped[str] = mapped_column(String(160), default="landing page")
    offer_summary: Mapped[str] = mapped_column(Text, default="")
    offer_goal: Mapped[str] = mapped_column(Text, default="")
    sales_tone: Mapped[str] = mapped_column(String(120), default="consultivo")
    cta_style: Mapped[str] = mapped_column(Text, default="")
    auto_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_delay_seconds: Mapped[int] = mapped_column(Integer, default=30)
    start_outreach_on_approve: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    leads: Mapped[list[Lead]] = relationship(back_populates="campaign")
    prospecting_batches: Mapped[list[ProspectingBatch]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    offer_product: Mapped[OfferProduct | None] = relationship(back_populates="campaigns")
    agent_strategy: Mapped[AgentStrategy | None] = relationship(back_populates="campaigns")
    prospecting_recipe: Mapped[ProspectingRecipe | None] = relationship(back_populates="campaigns")


class Playbook(Base):
    __tablename__ = "playbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    niche: Mapped[str | None] = mapped_column(String(120), index=True)
    stage: Mapped[str | None] = mapped_column(String(80), index=True)
    instructions: Mapped[str] = mapped_column(Text)
    objection_handling: Mapped[str | None] = mapped_column(Text)
    qualification_rules: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    niche: Mapped[str | None] = mapped_column(String(120), index=True)
    content: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ProspectingBatch(Base):
    __tablename__ = "prospecting_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), index=True)
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("prospecting_recipes.id", ondelete="SET NULL"), index=True)
    prompt_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("prospecting_prompt_categories.id", ondelete="SET NULL"),
        index=True,
    )
    prompt_id: Mapped[int | None] = mapped_column(ForeignKey("prospecting_prompts.id", ondelete="SET NULL"), index=True)
    niche: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    limit: Mapped[int] = mapped_column(Integer, default=10)
    enrich: Mapped[bool] = mapped_column(Boolean, default=True)
    recipe_snapshot_json: Mapped[dict | None] = mapped_column("recipe_snapshot", JSON)
    prompt_snapshot_json: Mapped[dict | None] = mapped_column("prompt_snapshot", JSON)
    search_metrics_json: Mapped[dict | None] = mapped_column("search_metrics", JSON)
    status: Mapped[str] = mapped_column(String(40), default="pending_review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    campaign: Mapped[Campaign | None] = relationship(back_populates="prospecting_batches")
    recipe: Mapped[ProspectingRecipe | None] = relationship(back_populates="batches")
    candidates: Mapped[list[ProspectingCandidate]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class ProspectingCandidate(Base):
    __tablename__ = "prospecting_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("prospecting_batches.id", ondelete="CASCADE"), index=True)
    business_name: Mapped[str] = mapped_column(String(255))
    niche: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_query: Mapped[str | None] = mapped_column(String(255))
    source_platform: Mapped[str | None] = mapped_column(String(80))
    website: Mapped[str | None] = mapped_column(String(500))
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    facebook_url: Mapped[str | None] = mapped_column(String(500))
    phone_number: Mapped[str | None] = mapped_column(String(40))
    prospecting_prompt_category_id: Mapped[int | None] = mapped_column(Integer, index=True)
    prospecting_prompt_id: Mapped[int | None] = mapped_column(Integer, index=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, index=True)
    outreach_external_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    delivery_status: Mapped[str | None] = mapped_column(String(40), index=True)
    delivery_note: Mapped[str | None] = mapped_column(Text)
    existing_lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    existing_lead_status: Mapped[str | None] = mapped_column(String(40))
    fit_score: Mapped[float | None] = mapped_column(Float, index=True)
    fit_label: Mapped[str | None] = mapped_column(String(20), index=True)
    fit_reasons_json: Mapped[dict | None] = mapped_column("fit_reasons", JSON)
    fit_scored_at: Mapped[datetime | None] = mapped_column(DateTime)
    search_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    research_summary: Mapped[str | None] = mapped_column(Text)
    research_payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="pending_review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    batch: Mapped[ProspectingBatch] = relationship(back_populates="candidates")
