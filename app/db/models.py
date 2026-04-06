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
    phone_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    whatsapp_number: Mapped[str | None] = mapped_column(String(40))
    website: Mapped[str | None] = mapped_column(String(500))
    instagram_url: Mapped[str | None] = mapped_column(String(500))
    facebook_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_query: Mapped[str | None] = mapped_column(String(255))
    source_platform: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    research_entries: Mapped[list[LeadResearch]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    qualified_lead: Mapped[QualifiedLead | None] = relationship(back_populates="lead", cascade="all, delete-orphan")
    tasks: Mapped[list[AgentTask]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    campaign: Mapped[Campaign | None] = relationship(back_populates="leads")


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
    __table_args__ = (UniqueConstraint("lead_id", "channel", name="uq_lead_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(40), default="whatsapp")
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
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    tasks: Mapped[list[AgentTask]] = relationship(back_populates="conversation")


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


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    niche: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
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
    niche: Mapped[str] = mapped_column(String(120), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True)
    limit: Mapped[int] = mapped_column(Integer, default=10)
    enrich: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    campaign: Mapped[Campaign | None] = relationship(back_populates="prospecting_batches")
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
    lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    conversation_id: Mapped[int | None] = mapped_column(Integer, index=True)
    outreach_external_message_id: Mapped[str | None] = mapped_column(String(255), index=True)
    delivery_status: Mapped[str | None] = mapped_column(String(40), index=True)
    delivery_note: Mapped[str | None] = mapped_column(Text)
    existing_lead_id: Mapped[int | None] = mapped_column(Integer, index=True)
    existing_lead_status: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    research_summary: Mapped[str | None] = mapped_column(Text)
    research_payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="pending_review", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    batch: Mapped[ProspectingBatch] = relationship(back_populates="candidates")
