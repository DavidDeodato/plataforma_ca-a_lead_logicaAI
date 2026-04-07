from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecommendedActionRead(BaseModel):
    key: str
    label: str
    description: str
    tone: str = "default"


class SuggestedPlaybookRead(BaseModel):
    id: int
    name: str
    niche: str | None = None
    stage: str | None = None
    instructions: str
    objection_handling: str | None = None
    qualification_rules: str | None = None
    applicability_reason: str


class LeadBase(BaseModel):
    business_name: str
    niche: str
    city: str
    phone_number: str | None = None
    whatsapp_number: str | None = None
    website: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    source_url: str | None = None
    source_query: str | None = None
    source_platform: str | None = None
    status: str = "new"
    notes: str | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    business_name: str | None = None
    niche: str | None = None
    city: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    website: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    source_url: str | None = None
    source_query: str | None = None
    source_platform: str | None = None
    status: str | None = None
    notes: str | None = None


class LeadRead(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int | None = None
    offer_product_id: int | None = None
    agent_strategy_id: int | None = None
    prospecting_recipe_id: int | None = None
    prospecting_prompt_category_id: int | None = None
    prospecting_prompt_id: int | None = None
    funnel_stage: str = "captured"
    fit_score: float | None = None
    fit_label: str | None = None
    fit_reasons_json: dict | None = None
    fit_scored_at: datetime | None = None
    first_contacted_at: datetime | None = None
    first_replied_at: datetime | None = None
    positive_reply_detected: bool = False
    positive_reply_at: datetime | None = None
    pain_status: str = "unknown"
    pain_confirmed_at: datetime | None = None
    intent_status: str = "unknown"
    fit_confirmed_at: datetime | None = None
    authority_status: str = "unknown"
    urgency_status: str = "unknown"
    objection_status: str = "none"
    meeting_status: str = "not_offered"
    meeting_offered_at: datetime | None = None
    meeting_booked_at: datetime | None = None
    qualified_opportunity_at: datetime | None = None
    closed_won_at: datetime | None = None
    closed_lost_at: datetime | None = None
    last_signal_at: datetime | None = None
    priority_score: float | None = None
    priority_label: str | None = None
    priority_reasons: list[str] = []
    recommended_action: RecommendedActionRead | None = None
    suggested_playbook: SuggestedPlaybookRead | None = None
    source_origin: str = "manual"
    inbound_unverified: bool = False
    created_at: datetime
    updated_at: datetime


class LeadResearchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    summary: str | None = None
    pain_points: list[str] | None = None
    opportunities: list[str] | None = None
    evidence: list[str] | None = None
    structured_data: dict | None = None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_message_id: str | None = None
    direction: str
    sender: str | None = None
    content: str
    status: str | None = None
    author_role: str | None = None
    prompt_phase: str | None = None
    instruction_snapshot_json: dict | None = None
    metadata_json: dict | None = None
    sent_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    channel: str
    whatsapp_session_id: int | None = None
    whatsapp_session_name: str | None = None
    whatsapp_session_phone_number: str | None = None
    external_chat_id: str | None = None
    temperature: str
    stage: str
    summary: str | None = None
    last_message_at: datetime | None = None
    last_inbound_at: datetime | None = None
    last_outbound_at: datetime | None = None
    unread_count: int
    assignee: str | None = None
    manual_mode: bool
    automation_paused: bool
    auto_reply_enabled: bool
    reply_delay_seconds: int
    taken_over_at: datetime | None = None
    taken_over_by: str | None = None
    pending_human_review: bool
    pending_review_reason: str | None = None
    pending_draft: str | None = None
    messages: list[MessageRead] = []


class AgentTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    conversation_id: int | None = None
    task_type: str
    status: str
    next_run_at: datetime | None = None
    current_attempt: int
    scheduled_reason: str | None = None
    review_required: bool
    payload: dict | None = None
    last_result: str | None = None
    created_at: datetime
    updated_at: datetime


class QualifiedLeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    score: float
    qualification_reason: str
    handoff_summary: str | None = None
    created_at: datetime


class LeadDetailRead(LeadRead):
    research_entries: list[LeadResearchRead] = []
    conversations: list[ConversationRead] = []
    tasks: list[AgentTaskRead] = []
    qualified_lead: QualifiedLeadRead | None = None


class LeadWorkspaceRead(LeadRead):
    tasks: list[AgentTaskRead] = []
    qualified_lead: QualifiedLeadRead | None = None


class LeadListResponse(BaseModel):
    items: list[LeadRead]
    total: int
    page: int
    page_size: int


class ConversationListItemRead(BaseModel):
    id: int
    lead_id: int
    lead_name: str
    phone_number: str | None = None
    source_origin: str | None = None
    inbound_unverified: bool = False
    whatsapp_session_id: int | None = None
    whatsapp_session_name: str | None = None
    whatsapp_session_phone_number: str | None = None
    temperature: str
    stage: str
    lead_fit_score: float | None = None
    lead_fit_label: str | None = None
    lead_funnel_stage: str | None = None
    lead_intent_status: str | None = None
    lead_pain_status: str | None = None
    lead_meeting_status: str | None = None
    priority_score: float | None = None
    priority_label: str | None = None
    priority_reasons: list[str] = []
    recommended_action: RecommendedActionRead | None = None
    suggested_playbook: SuggestedPlaybookRead | None = None
    unread_count: int = 0
    assignee: str | None = None
    manual_mode: bool = False
    automation_paused: bool = False
    auto_reply_enabled: bool = True
    reply_delay_seconds: int = 30
    pending_human_review: bool = False
    summary: str | None = None
    last_message_at: datetime | None = None
    latest_message_preview: str | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationListItemRead]
    total: int
    page: int
    page_size: int


class ConversationWorkspaceRead(BaseModel):
    conversation: ConversationRead
    lead: LeadWorkspaceRead


class TaskListResponse(BaseModel):
    items: list[AgentTaskRead]
    total: int
    page: int
    page_size: int


class ProspectingRequest(BaseModel):
    niche: str
    city: str
    limit: int = Field(default=10, ge=1, le=50)
    enrich: bool = True
    validate_phone_format: bool = False


class OutreachRequest(BaseModel):
    lead_id: int
    custom_instruction: str | None = None


class ManualQualificationRequest(BaseModel):
    score: float = Field(default=0.8, ge=0, le=1)
    qualification_reason: str
    handoff_summary: str | None = None


class ConversationTakeoverRequest(BaseModel):
    operator_name: str = Field(min_length=1, max_length=120)


class ConversationSettingsUpdate(BaseModel):
    assignee: str | None = None
    manual_mode: bool | None = None
    automation_paused: bool | None = None
    auto_reply_enabled: bool | None = None
    reply_delay_seconds: int | None = Field(default=None, ge=0, le=86400)
    pending_human_review: bool | None = None
    pending_review_reason: str | None = None
    pending_draft: str | None = None


class ManualMessageRequest(BaseModel):
    operator_name: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1)
    mark_as_read: bool = True


class BulkLeadActionRequest(BaseModel):
    lead_ids: list[int] = Field(min_length=1)
    action: str
    status: str | None = None


class BulkConversationActionRequest(BaseModel):
    conversation_ids: list[int] = Field(min_length=1)
    action: str
    operator_name: str | None = None
    auto_reply_enabled: bool | None = None
    reply_delay_seconds: int | None = Field(default=None, ge=0, le=86400)


class RuntimeSettingsRead(BaseModel):
    outbound_enabled: bool
    auto_reply_enabled: bool
    inbound_auto_reply_scope: str
    persist_unknown_inbound: bool
    default_niche: str
    default_city: str
    outreach_daily_limit: int
    outreach_delay_seconds: int
    default_auto_reply_delay_seconds: int
    offer_name: str
    offer_summary: str
    offer_goal: str
    sales_tone: str
    cta_style: str
    active_offer_product_id: int | None = None
    active_agent_strategy_id: int | None = None
    active_prospecting_recipe_id: int | None = None


class RuntimeSettingsUpdate(BaseModel):
    outbound_enabled: bool | None = None
    auto_reply_enabled: bool | None = None
    inbound_auto_reply_scope: str | None = None
    persist_unknown_inbound: bool | None = None
    default_niche: str | None = None
    default_city: str | None = None
    outreach_daily_limit: int | None = Field(default=None, ge=1, le=500)
    outreach_delay_seconds: int | None = Field(default=None, ge=5, le=86400)
    default_auto_reply_delay_seconds: int | None = Field(default=None, ge=0, le=86400)
    offer_name: str | None = None
    offer_summary: str | None = None
    offer_goal: str | None = None
    sales_tone: str | None = None
    cta_style: str | None = None
    active_offer_product_id: int | None = None
    active_agent_strategy_id: int | None = None
    active_prospecting_recipe_id: int | None = None


class AgentPreviewRequest(BaseModel):
    custom_instruction: str | None = None


class AgentPreviewResponse(BaseModel):
    lead_id: int
    preview_message: str
    runtime_instruction: str
    instruction_snapshot: dict | None = None


class OfferProductBase(BaseModel):
    name: str
    category: str | None = None
    summary: str = ""
    objective: str = ""
    target_customer: str | None = None
    pains: str | None = None
    differentiators: str | None = None
    proof_points: str | None = None
    cta_primary: str | None = None
    allowed_claims: str | None = None
    forbidden_claims: str | None = None
    active: bool = True


class OfferProductCreate(OfferProductBase):
    pass


class OfferProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    summary: str | None = None
    objective: str | None = None
    target_customer: str | None = None
    pains: str | None = None
    differentiators: str | None = None
    proof_points: str | None = None
    cta_primary: str | None = None
    allowed_claims: str | None = None
    forbidden_claims: str | None = None
    active: bool | None = None


class OfferProductRead(OfferProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class AgentStrategyBase(BaseModel):
    name: str
    persona: str | None = None
    primary_goal: str = ""
    tone: str | None = None
    opening_strategy: str | None = None
    qualification_strategy: str | None = None
    objection_strategy: str | None = None
    follow_up_strategy: str | None = None
    handoff_strategy: str | None = None
    guardrails: str | None = None
    active: bool = True


class AgentStrategyCreate(AgentStrategyBase):
    pass


class AgentStrategyUpdate(BaseModel):
    name: str | None = None
    persona: str | None = None
    primary_goal: str | None = None
    tone: str | None = None
    opening_strategy: str | None = None
    qualification_strategy: str | None = None
    objection_strategy: str | None = None
    follow_up_strategy: str | None = None
    handoff_strategy: str | None = None
    guardrails: str | None = None
    active: bool | None = None


class AgentStrategyRead(AgentStrategyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PromptTemplateBase(BaseModel):
    agent_strategy_id: int | None = None
    name: str
    phase: str
    channel: str = "whatsapp"
    system_prompt: str = ""
    instructions: str | None = None
    output_contract: str | None = None
    active: bool = True


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateUpdate(BaseModel):
    agent_strategy_id: int | None = None
    name: str | None = None
    phase: str | None = None
    channel: str | None = None
    system_prompt: str | None = None
    instructions: str | None = None
    output_contract: str | None = None
    active: bool | None = None


class PromptTemplateRead(PromptTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProspectingRecipeBase(BaseModel):
    name: str
    objective: str = ""
    system_prompt: str = ""
    source_channels: list[str] = []
    inclusion_rules: str | None = None
    exclusion_rules: str | None = None
    minimum_valid_contacts: int = Field(default=10, ge=1, le=500)
    max_total_results: int = Field(default=25, ge=1, le=500)
    search_depth: int = Field(default=2, ge=1, le=10)
    require_phone: bool = True
    validate_phone_format: bool = True
    discovery_mode: str = "hybrid"
    fallback_enabled: bool = True
    scoring_guidance: str | None = None
    assistant_notes: str | None = None
    schema_fields: dict | None = None
    agent_max_credits: int | None = Field(default=None, ge=1, le=10000)
    active: bool = True


class ProspectingRecipeCreate(ProspectingRecipeBase):
    pass


class ProspectingRecipeUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    system_prompt: str | None = None
    source_channels: list[str] | None = None
    inclusion_rules: str | None = None
    exclusion_rules: str | None = None
    minimum_valid_contacts: int | None = Field(default=None, ge=1, le=500)
    max_total_results: int | None = Field(default=None, ge=1, le=500)
    search_depth: int | None = Field(default=None, ge=1, le=10)
    require_phone: bool | None = None
    validate_phone_format: bool | None = None
    discovery_mode: str | None = None
    fallback_enabled: bool | None = None
    scoring_guidance: str | None = None
    assistant_notes: str | None = None
    schema_fields: dict | None = None
    agent_max_credits: int | None = Field(default=None, ge=1, le=10000)
    active: bool | None = None


class ProspectingRecipeRead(ProspectingRecipeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProspectingPromptCategoryBase(BaseModel):
    name: str
    description: str | None = None
    offer_context: str | None = None
    target_niche: str | None = None
    active: bool = True


class ProspectingPromptCategoryCreate(ProspectingPromptCategoryBase):
    pass


class ProspectingPromptCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    offer_context: str | None = None
    target_niche: str | None = None
    active: bool | None = None


class ProspectingPromptCategoryRead(ProspectingPromptCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProspectingPromptBase(BaseModel):
    category_id: int | None = None
    name: str
    prompt_text: str = ""
    objective: str | None = None
    source_channels: list[str] = []
    discovery_mode: str = "hybrid"
    minimum_valid_contacts: int = Field(default=10, ge=1, le=500)
    require_phone: bool = True
    fallback_enabled: bool = True
    search_depth: int = Field(default=2, ge=1, le=10)
    agent_max_credits: int | None = Field(default=None, ge=1, le=10000)
    notes: str | None = None
    active: bool = True


class ProspectingPromptCreate(ProspectingPromptBase):
    pass


class ProspectingPromptUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    prompt_text: str | None = None
    objective: str | None = None
    source_channels: list[str] | None = None
    discovery_mode: str | None = None
    minimum_valid_contacts: int | None = Field(default=None, ge=1, le=500)
    require_phone: bool | None = None
    fallback_enabled: bool | None = None
    search_depth: int | None = Field(default=None, ge=1, le=10)
    agent_max_credits: int | None = Field(default=None, ge=1, le=10000)
    notes: str | None = None
    active: bool | None = None


class ProspectingPromptRead(ProspectingPromptBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class QualificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    score: float
    qualification_reason: str
    handoff_summary: str | None = None
    created_at: datetime


class DashboardSummaryRead(BaseModel):
    totals: dict[str, int]
    safe_mode: dict[str, bool]
    recent_activity: dict[str, int]
    funnel: dict[str, int | float]
    conversion: dict[str, int | float]
    operations: dict[str, int | float]
    campaigns: list[dict]
    offers: list[dict] = []
    strategies: list[dict] = []
    recipes: list[dict] = []
    prompt_categories: list[dict] = []
    prospecting_prompts: list[dict] = []
    runtime: RuntimeSettingsRead


class CampaignBase(BaseModel):
    name: str
    status: str = "draft"
    niche: str
    city: str
    offer_product_id: int | None = None
    agent_strategy_id: int | None = None
    prospecting_recipe_id: int | None = None
    offer_name: str = "landing page"
    offer_summary: str = ""
    offer_goal: str = ""
    sales_tone: str = "consultivo"
    cta_style: str = ""
    auto_reply_enabled: bool = False
    reply_delay_seconds: int = Field(default=30, ge=0, le=86400)
    start_outreach_on_approve: bool = False
    is_active: bool = False
    notes: str | None = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    niche: str | None = None
    city: str | None = None
    offer_product_id: int | None = None
    agent_strategy_id: int | None = None
    prospecting_recipe_id: int | None = None
    offer_name: str | None = None
    offer_summary: str | None = None
    offer_goal: str | None = None
    sales_tone: str | None = None
    cta_style: str | None = None
    auto_reply_enabled: bool | None = None
    reply_delay_seconds: int | None = Field(default=None, ge=0, le=86400)
    start_outreach_on_approve: bool | None = None
    is_active: bool | None = None
    notes: str | None = None


class CampaignRead(CampaignBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PlaybookBase(BaseModel):
    name: str
    niche: str | None = None
    stage: str | None = None
    instructions: str
    objection_handling: str | None = None
    qualification_rules: str | None = None
    active: bool = True


class PlaybookCreate(PlaybookBase):
    pass


class PlaybookUpdate(BaseModel):
    name: str | None = None
    niche: str | None = None
    stage: str | None = None
    instructions: str | None = None
    objection_handling: str | None = None
    qualification_rules: str | None = None
    active: bool | None = None


class PlaybookRead(PlaybookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class KnowledgeItemBase(BaseModel):
    title: str
    category: str
    niche: str | None = None
    content: str
    active: bool = True


class KnowledgeItemCreate(KnowledgeItemBase):
    pass


class KnowledgeItemUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    niche: str | None = None
    content: str | None = None
    active: bool | None = None


class KnowledgeItemRead(KnowledgeItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ProspectingBatchCreate(BaseModel):
    niche: str
    city: str
    limit: int = Field(default=10, ge=1, le=50)
    enrich: bool = True
    validate_phone_format: bool = False
    campaign_id: int | None = None
    recipe_id: int | None = None
    prompt_category_id: int | None = None
    prompt_id: int | None = None
    search_goal: str | None = None
    system_prompt: str | None = None
    source_channels: list[str] | None = None
    discovery_mode: str | None = None
    minimum_valid_contacts: int | None = Field(default=None, ge=1, le=500)
    require_phone: bool | None = None
    fallback_enabled: bool | None = None
    search_depth: int | None = Field(default=None, ge=1, le=10)
    agent_max_credits: int | None = Field(default=None, ge=1, le=10000)


class ProspectingAdvisorState(BaseModel):
    niche: str | None = None
    city: str | None = None
    limit: int = Field(default=10, ge=1, le=50)
    enrich: bool = True
    recipe_id: int | None = None
    search_goal: str | None = None
    system_prompt: str | None = None
    source_channels: list[str] = []
    discovery_mode: str = "hybrid"
    minimum_valid_contacts: int = Field(default=10, ge=1, le=500)
    require_phone: bool = True
    fallback_enabled: bool = True
    search_depth: int = Field(default=2, ge=1, le=10)
    agent_max_credits: int | None = Field(default=None, ge=1, le=10000)


class ProspectingAdvisorRequest(BaseModel):
    message: str = Field(min_length=1)
    current_state: ProspectingAdvisorState | None = None


class ProspectingAdvisorResponse(BaseModel):
    assistant_message: str
    state: ProspectingAdvisorState
    missing_fields: list[str]
    ready_to_search: bool
    supported_niches: list[str]
    supported_cities_hint: list[str]
    recipe_preview: ProspectingRecipeRead | None = None
    warnings: list[str] = []
    suggested_variables: list[str] = []


class ProspectingCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    business_name: str
    niche: str
    city: str
    source_url: str | None = None
    source_query: str | None = None
    source_platform: str | None = None
    website: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    phone_number: str | None = None
    prospecting_prompt_category_id: int | None = None
    prospecting_prompt_id: int | None = None
    lead_id: int | None = None
    conversation_id: int | None = None
    outreach_external_message_id: str | None = None
    delivery_status: str | None = None
    delivery_note: str | None = None
    existing_lead_id: int | None = None
    existing_lead_status: str | None = None
    fit_score: float | None = None
    fit_label: str | None = None
    fit_reasons_json: dict | None = None
    fit_scored_at: datetime | None = None
    search_reason: str | None = None
    notes: str | None = None
    research_summary: str | None = None
    research_payload: dict | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class ProspectingBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int | None = None
    recipe_id: int | None = None
    prompt_category_id: int | None = None
    prompt_id: int | None = None
    niche: str
    city: str
    limit: int
    enrich: bool
    status: str
    recipe_snapshot_json: dict | None = None
    prompt_snapshot_json: dict | None = None
    search_metrics_json: dict | None = None
    created_at: datetime
    updated_at: datetime
    candidates: list[ProspectingCandidateRead] = []


class ProspectingBatchActionRequest(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)
    action: str


class WhatsappSessionBase(BaseModel):
    name: str
    phone_number: str | None = None
    account_protection: bool = True
    log_messages: bool = True
    read_incoming_messages: bool = False
    outbound_cooldown_seconds: int | None = Field(default=None, ge=0, le=86400)
    webhook_enabled: bool = True
    webhook_url: str | None = None
    webhook_events: list[str] = Field(default_factory=list)


class WhatsappSessionCreate(WhatsappSessionBase):
    api_key: str | None = None
    webhook_secret: str | None = None
    create_on_provider: bool = False
    set_active: bool = True


class WhatsappSessionRead(WhatsappSessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wasender_session_id: int | None = None
    status: str
    source: str
    is_active: bool
    has_api_key: bool = False
    has_webhook_secret: bool = False
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WhatsappSessionWorkspaceRead(BaseModel):
    items: list[WhatsappSessionRead]
    active_session_id: int | None = None
    provider_management_available: bool = False
    legacy_label: str = "Histórico legado"


class WhatsappSessionQrRead(BaseModel):
    session_id: int
    status: str | None = None
    qr_code: str | None = None
