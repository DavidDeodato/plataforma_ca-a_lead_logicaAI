export type RuntimeSettings = {
  outbound_enabled: boolean
  auto_reply_enabled: boolean
  inbound_auto_reply_scope: string
  persist_unknown_inbound: boolean
  default_niche: string
  default_city: string
  outreach_daily_limit: number
  outreach_delay_seconds: number
  default_auto_reply_delay_seconds: number
  offer_name: string
  offer_summary: string
  offer_goal: string
  sales_tone: string
  cta_style: string
  active_offer_product_id?: number | null
  active_agent_strategy_id?: number | null
  active_prospecting_recipe_id?: number | null
}

export type Readiness = {
  ready_for_local_tests: boolean
  ready_for_live_outreach: boolean
  missing: string[]
  safe_mode: {
    outbound_enabled: boolean
    auto_reply_enabled: boolean
  }
  notes: string[]
}

export type RecommendedAction = {
  key: string
  label: string
  description: string
  tone: string
}

export type SuggestedPlaybook = {
  id: number
  name: string
  niche?: string | null
  stage?: string | null
  instructions: string
  objection_handling?: string | null
  qualification_rules?: string | null
  applicability_reason: string
}

export type DashboardSummary = {
  totals: Record<string, number>
  safe_mode: {
    outbound_enabled: boolean
    auto_reply_enabled: boolean
  }
  recent_activity: Record<string, number>
  funnel: Record<string, number>
  conversion: Record<string, number>
  operations: Record<string, number>
  campaigns: Array<{
    id: number
    name: string
    status: string
    is_active: boolean
    leads: number
    contacted: number
    reply_rate: number
    positive_reply_rate: number
    meetings_booked: number
    qualified_opportunities: number
    fit_score_avg: number
  }>
  offers: Array<Record<string, number | string>>
  strategies: Array<Record<string, number | string>>
  recipes: Array<Record<string, number | string>>
  prompt_categories: PromptCategoryPerformance[]
  prospecting_prompts: ProspectingPromptPerformance[]
  runtime: RuntimeSettings
}

export type PromptCategoryPerformance = {
  id: number
  name: string
  leads: number
  contacted: number
  reply_rate: number
  positive_reply_rate: number
  meetings_booked: number
  closed_won: number
  fit_score_avg: number
}

export type ProspectingPromptPerformance = {
  id: number
  name: string
  category_id?: number | null
  category_name?: string | null
  leads: number
  contacted: number
  reply_rate: number
  positive_reply_rate: number
  meetings_booked: number
  closed_won: number
  fit_score_avg: number
}

export type Lead = {
  id: number
  campaign_id?: number | null
  offer_product_id?: number | null
  agent_strategy_id?: number | null
  prospecting_recipe_id?: number | null
  prospecting_prompt_category_id?: number | null
  prospecting_prompt_id?: number | null
  business_name: string
  niche: string
  city: string
  phone_number?: string | null
  whatsapp_number?: string | null
  website?: string | null
  instagram_url?: string | null
  facebook_url?: string | null
  source_url?: string | null
  source_query?: string | null
  source_platform?: string | null
  status: string
  funnel_stage: string
  fit_score?: number | null
  fit_label?: string | null
  fit_reasons_json?: {
    components?: Array<{ key: string; label: string; score: number; max_score: number; reason: string }>
    reasons?: string[]
  } | null
  fit_scored_at?: string | null
  first_contacted_at?: string | null
  first_replied_at?: string | null
  positive_reply_detected: boolean
  positive_reply_at?: string | null
  pain_status: string
  pain_confirmed_at?: string | null
  intent_status: string
  fit_confirmed_at?: string | null
  authority_status: string
  urgency_status: string
  objection_status: string
  meeting_status: string
  meeting_offered_at?: string | null
  meeting_booked_at?: string | null
  qualified_opportunity_at?: string | null
  closed_won_at?: string | null
  closed_lost_at?: string | null
  last_signal_at?: string | null
  priority_score?: number | null
  priority_label?: string | null
  priority_reasons?: string[]
  recommended_action?: RecommendedAction | null
  suggested_playbook?: SuggestedPlaybook | null
  source_origin: string
  inbound_unverified: boolean
  notes?: string | null
  created_at: string
  updated_at: string
}

export type LeadResearch = {
  id: number
  source: string
  summary?: string | null
  pain_points?: string[] | null
  opportunities?: string[] | null
  evidence?: string[] | null
  structured_data?: Record<string, unknown> | null
  created_at: string
}

export type Message = {
  id: number
  external_message_id?: string | null
  direction: string
  sender?: string | null
  author_role?: string | null
  prompt_phase?: string | null
  content: string
  status?: string | null
  instruction_snapshot_json?: Record<string, unknown> | null
  metadata_json?: Record<string, unknown> | null
  sent_at: string
}

export type Conversation = {
  id: number
  lead_id: number
  channel: string
  whatsapp_session_id?: number | null
  whatsapp_session_name?: string | null
  whatsapp_session_phone_number?: string | null
  external_chat_id?: string | null
  temperature: string
  stage: string
  summary?: string | null
  last_message_at?: string | null
  last_inbound_at?: string | null
  last_outbound_at?: string | null
  unread_count: number
  assignee?: string | null
  manual_mode: boolean
  automation_paused: boolean
  auto_reply_enabled: boolean
  reply_delay_seconds: number
  taken_over_at?: string | null
  taken_over_by?: string | null
  pending_human_review: boolean
  pending_review_reason?: string | null
  pending_draft?: string | null
  messages: Message[]
}

export type Task = {
  id: number
  lead_id: number
  conversation_id?: number | null
  task_type: string
  status: string
  next_run_at?: string | null
  current_attempt: number
  scheduled_reason?: string | null
  review_required: boolean
  payload?: Record<string, unknown> | null
  last_result?: string | null
  created_at: string
  updated_at: string
}

export type QualifiedLead = {
  id: number
  lead_id: number
  score: number
  qualification_reason: string
  handoff_summary?: string | null
  created_at: string
}

export type LeadDetail = Lead & {
  research_entries: LeadResearch[]
  conversations: Conversation[]
  tasks: Task[]
  qualified_lead?: QualifiedLead | null
}

export type LeadWorkspace = Lead & {
  tasks: Task[]
  qualified_lead?: QualifiedLead | null
}

export type LeadListResponse = {
  items: Lead[]
  total: number
  page: number
  page_size: number
}

export type ProspectingAdvisorState = {
  niche?: string | null
  city?: string | null
  limit: number
  enrich: boolean
  recipe_id?: number | null
  search_goal?: string | null
  system_prompt?: string | null
  source_channels?: string[]
  discovery_mode: string
  minimum_valid_contacts: number
  require_phone: boolean
  fallback_enabled: boolean
  search_depth: number
  agent_max_credits?: number | null
}

export type ProspectingAdvisorResponse = {
  assistant_message: string
  state: ProspectingAdvisorState
  missing_fields: string[]
  ready_to_search: boolean
  supported_niches: string[]
  supported_cities_hint: string[]
  recipe_preview?: ProspectingRecipe | null
  warnings: string[]
  suggested_variables: string[]
}

export type ConversationListItem = {
  id: number
  lead_id: number
  lead_name: string
  phone_number?: string | null
  source_origin?: string | null
  inbound_unverified: boolean
  whatsapp_session_id?: number | null
  whatsapp_session_name?: string | null
  whatsapp_session_phone_number?: string | null
  temperature: string
  stage: string
  lead_fit_score?: number | null
  lead_fit_label?: string | null
  lead_funnel_stage?: string | null
  lead_intent_status?: string | null
  lead_pain_status?: string | null
  lead_meeting_status?: string | null
  priority_score?: number | null
  priority_label?: string | null
  priority_reasons?: string[]
  recommended_action?: RecommendedAction | null
  suggested_playbook?: SuggestedPlaybook | null
  unread_count: number
  assignee?: string | null
  manual_mode: boolean
  automation_paused: boolean
  auto_reply_enabled: boolean
  reply_delay_seconds: number
  pending_human_review: boolean
  summary?: string | null
  last_message_at?: string | null
  latest_message_preview?: string | null
}

export type ConversationListResponse = {
  items: ConversationListItem[]
  total: number
  page: number
  page_size: number
}

export type ConversationWorkspace = {
  conversation: Conversation
  lead: LeadWorkspace
}

export type TaskListResponse = {
  items: Task[]
  total: number
  page: number
  page_size: number
}

export type AgentPreview = {
  lead_id: number
  preview_message: string
  runtime_instruction: string
}

export type Campaign = {
  id: number
  name: string
  status: string
  niche: string
  city: string
  offer_product_id?: number | null
  agent_strategy_id?: number | null
  prospecting_recipe_id?: number | null
  offer_name: string
  offer_summary: string
  offer_goal: string
  sales_tone: string
  cta_style: string
  auto_reply_enabled: boolean
  reply_delay_seconds: number
  start_outreach_on_approve: boolean
  is_active: boolean
  notes?: string | null
  created_at: string
  updated_at: string
}

export type OfferProduct = {
  id: number
  name: string
  category?: string | null
  summary: string
  objective: string
  target_customer?: string | null
  pains?: string | null
  differentiators?: string | null
  proof_points?: string | null
  cta_primary?: string | null
  allowed_claims?: string | null
  forbidden_claims?: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type AgentStrategy = {
  id: number
  name: string
  persona?: string | null
  primary_goal: string
  tone?: string | null
  opening_strategy?: string | null
  qualification_strategy?: string | null
  objection_strategy?: string | null
  follow_up_strategy?: string | null
  handoff_strategy?: string | null
  guardrails?: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type PromptTemplate = {
  id: number
  agent_strategy_id?: number | null
  name: string
  phase: string
  channel: string
  system_prompt: string
  instructions?: string | null
  output_contract?: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type Playbook = {
  id: number
  name: string
  niche?: string | null
  stage?: string | null
  instructions: string
  objection_handling?: string | null
  qualification_rules?: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type KnowledgeItem = {
  id: number
  title: string
  category: string
  niche?: string | null
  content: string
  active: boolean
  created_at: string
  updated_at: string
}

export type ProspectingCandidate = {
  id: number
  batch_id: number
  business_name: string
  niche: string
  city: string
  source_url?: string | null
  source_query?: string | null
  source_platform?: string | null
  website?: string | null
  instagram_url?: string | null
  facebook_url?: string | null
  phone_number?: string | null
  prospecting_prompt_category_id?: number | null
  prospecting_prompt_id?: number | null
  lead_id?: number | null
  conversation_id?: number | null
  outreach_external_message_id?: string | null
  delivery_status?: string | null
  delivery_note?: string | null
  existing_lead_id?: number | null
  existing_lead_status?: string | null
  fit_score?: number | null
  fit_label?: string | null
  fit_reasons_json?: {
    components?: Array<{ key: string; label: string; score: number; max_score: number; reason: string }>
    reasons?: string[]
  } | null
  fit_scored_at?: string | null
  search_reason?: string | null
  notes?: string | null
  research_summary?: string | null
  research_payload?: Record<string, unknown> | null
  status: string
  created_at: string
  updated_at: string
}

export type ProspectingBatch = {
  id: number
  campaign_id?: number | null
  recipe_id?: number | null
  prompt_category_id?: number | null
  prompt_id?: number | null
  niche: string
  city: string
  limit: number
  enrich: boolean
  validate_phone_format?: boolean
  status: string
  recipe_snapshot_json?: Record<string, unknown> | null
  prompt_snapshot_json?: Record<string, unknown> | null
  search_metrics_json?: Record<string, unknown> | null
  created_at: string
  updated_at: string
  candidates: ProspectingCandidate[]
}

export type ProspectingPromptCategory = {
  id: number
  name: string
  description?: string | null
  offer_context?: string | null
  target_niche?: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type ProspectingPrompt = {
  id: number
  category_id?: number | null
  name: string
  prompt_text: string
  objective?: string | null
  source_channels: string[]
  discovery_mode: string
  minimum_valid_contacts: number
  require_phone: boolean
  fallback_enabled: boolean
  search_depth: number
  agent_max_credits?: number | null
  notes?: string | null
  active: boolean
  created_at: string
  updated_at: string
}

export type ProspectingRecipe = {
  id: number
  name: string
  objective: string
  system_prompt: string
  source_channels: string[]
  inclusion_rules?: string | null
  exclusion_rules?: string | null
  minimum_valid_contacts: number
  max_total_results: number
  search_depth: number
  require_phone: boolean
  validate_phone_format: boolean
  discovery_mode: string
  fallback_enabled: boolean
  scoring_guidance?: string | null
  assistant_notes?: string | null
  schema_fields?: Record<string, unknown> | null
  agent_max_credits?: number | null
  active: boolean
  created_at: string
  updated_at: string
}

export type WhatsappSession = {
  id: number
  name: string
  phone_number?: string | null
  wasender_session_id?: number | null
  status: string
  source: string
  is_active: boolean
  has_api_key: boolean
  has_webhook_secret: boolean
  account_protection: boolean
  log_messages: boolean
  read_incoming_messages: boolean
  outbound_cooldown_seconds?: number | null
  webhook_enabled: boolean
  webhook_url?: string | null
  webhook_events: string[]
  last_synced_at?: string | null
  created_at: string
  updated_at: string
}

export type WhatsappSessionWorkspace = {
  items: WhatsappSession[]
  active_session_id?: number | null
  provider_management_available: boolean
  legacy_label: string
}

export type WhatsappSessionQr = {
  session_id: number
  status?: string | null
  qr_code?: string | null
}
