export type RuntimeSettings = {
  outbound_enabled: boolean
  auto_reply_enabled: boolean
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

export type DashboardSummary = {
  totals: Record<string, number>
  safe_mode: {
    outbound_enabled: boolean
    auto_reply_enabled: boolean
  }
  recent_activity: Record<string, number>
  runtime: RuntimeSettings
}

export type Lead = {
  id: number
  campaign_id?: number | null
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
  content: string
  status?: string | null
  metadata_json?: Record<string, unknown> | null
  sent_at: string
}

export type Conversation = {
  id: number
  lead_id: number
  channel: string
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
}

export type ProspectingAdvisorResponse = {
  assistant_message: string
  state: ProspectingAdvisorState
  missing_fields: string[]
  ready_to_search: boolean
  supported_niches: string[]
  supported_cities_hint: string[]
}

export type ConversationListItem = {
  id: number
  lead_id: number
  lead_name: string
  phone_number?: string | null
  temperature: string
  stage: string
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
  lead_id?: number | null
  conversation_id?: number | null
  outreach_external_message_id?: string | null
  delivery_status?: string | null
  delivery_note?: string | null
  existing_lead_id?: number | null
  existing_lead_status?: string | null
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
  niche: string
  city: string
  limit: number
  enrich: boolean
  validate_phone_format?: boolean
  status: string
  created_at: string
  updated_at: string
  candidates: ProspectingCandidate[]
}
