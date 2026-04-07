import type {
  AgentStrategy,
  AgentPreview,
  Campaign,
  ConversationListResponse,
  Conversation,
  ConversationWorkspace,
  DashboardSummary,
  KnowledgeItem,
  Lead,
  LeadDetail,
  LeadListResponse,
  OfferProduct,
  Playbook,
  PromptTemplate,
  ProspectingAdvisorResponse,
  ProspectingBatch,
  ProspectingPrompt,
  ProspectingPromptCategory,
  ProspectingRecipe,
  QualifiedLead,
  Readiness,
  RuntimeSettings,
  Task,
  TaskListResponse,
  WhatsappSession,
  WhatsappSessionQr,
  WhatsappSessionWorkspace,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const text = await response.text()
    if (text) {
      try {
        const parsed = JSON.parse(text) as { detail?: string }
        throw new Error(parsed.detail || text)
      } catch {
        throw new Error(text)
      }
    }
    throw new Error(`Erro HTTP ${response.status}`)
  }

  return (await response.json()) as T
}

export const api = {
  getReadiness: () => request<Readiness>('/api/readiness'),
  getDashboardSummary: () => request<DashboardSummary>('/api/dashboard/summary'),
  getRuntimeSettings: () => request<RuntimeSettings>('/api/settings/runtime'),
  updateRuntimeSettings: (payload: Partial<RuntimeSettings>) =>
    request<RuntimeSettings>('/api/settings/runtime', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listWhatsappSessions: () => request<WhatsappSessionWorkspace>('/api/whatsapp-sessions'),
  createWhatsappSession: (payload: Record<string, unknown>) =>
    request<WhatsappSession>('/api/whatsapp-sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  syncWhatsappSessions: () =>
    request<WhatsappSessionWorkspace>('/api/whatsapp-sessions/sync', {
      method: 'POST',
    }),
  activateWhatsappSession: (sessionId: number) =>
    request<WhatsappSession>(`/api/whatsapp-sessions/${sessionId}/activate`, {
      method: 'POST',
    }),
  connectWhatsappSession: (sessionId: number) =>
    request<WhatsappSessionQr>(`/api/whatsapp-sessions/${sessionId}/connect`, {
      method: 'POST',
    }),
  getWhatsappSessionQr: (sessionId: number) => request<WhatsappSessionQr>(`/api/whatsapp-sessions/${sessionId}/qrcode`),
  searchLeads: (params: URLSearchParams) => request<LeadListResponse>(`/api/leads/search?${params.toString()}`),
  createLead: (payload: Record<string, unknown>) =>
    request<Lead>('/api/leads', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getLead: (leadId: number) => request<LeadDetail>(`/api/leads/${leadId}`),
  updateLead: (leadId: number, payload: Record<string, unknown>) =>
    request<LeadDetail>(`/api/leads/${leadId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  qualifyLead: (leadId: number, payload: { score: number; qualification_reason: string; handoff_summary?: string }) =>
    request<LeadDetail>(`/api/leads/${leadId}/qualify`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  disqualifyLead: (leadId: number) =>
    request(`/api/leads/${leadId}/disqualify`, {
      method: 'POST',
    }),
  reprocessLead: (leadId: number) =>
    request<LeadDetail>(`/api/leads/${leadId}/reprocess`, {
      method: 'POST',
    }),
  previewAgent: (leadId: number, custom_instruction?: string) =>
    request<AgentPreview>(`/api/leads/${leadId}/agent-preview`, {
      method: 'POST',
      body: JSON.stringify({ custom_instruction }),
    }),
  runProspecting: (payload: { niche: string; city: string; limit: number; enrich: boolean; validate_phone_format?: boolean }) =>
    request('/api/prospecting/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  startOutreach: (leadId: number) =>
    request(`/api/outreach/${leadId}/start`, {
      method: 'POST',
    }),
  listConversations: (params: URLSearchParams) =>
    request<ConversationListResponse>(`/api/conversations?${params.toString()}`),
  getConversation: (conversationId: number) => request<Conversation>(`/api/conversations/${conversationId}`),
  getConversationWorkspace: (conversationId: number) =>
    request<ConversationWorkspace>(`/api/conversations/${conversationId}/workspace`),
  takeOverConversation: (conversationId: number, operatorName: string) =>
    request<Conversation>(`/api/conversations/${conversationId}/takeover`, {
      method: 'POST',
      body: JSON.stringify({ operator_name: operatorName }),
    }),
  releaseConversation: (conversationId: number) =>
    request<Conversation>(`/api/conversations/${conversationId}/release`, {
      method: 'POST',
    }),
  updateConversationSettings: (conversationId: number, payload: Record<string, unknown>) =>
    request<Conversation>(`/api/conversations/${conversationId}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  markConversationRead: (conversationId: number) =>
    request<Conversation>(`/api/conversations/${conversationId}/mark-read`, {
      method: 'POST',
    }),
  sendManualMessage: (conversationId: number, payload: { operator_name: string; content: string; mark_as_read?: boolean }) =>
    request<Conversation>(`/api/conversations/${conversationId}/messages/manual-send`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  bulkLeadAction: (payload: Record<string, unknown>) =>
    request<{ affected: number }>('/api/leads/bulk', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  bulkConversationAction: (payload: Record<string, unknown>) =>
    request<{ affected: number }>('/api/conversations/bulk', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listQualifiedLeads: () => request<QualifiedLead[]>('/api/qualified-leads'),
  listTasks: (params: URLSearchParams) => request<TaskListResponse>(`/api/tasks?${params.toString()}`),
  runTaskNow: (taskId: number) =>
    request<Task>(`/api/tasks/${taskId}/run-now`, {
      method: 'POST',
    }),
  cancelTask: (taskId: number) =>
    request<Task>(`/api/tasks/${taskId}/cancel`, {
      method: 'POST',
    }),
  listCampaigns: () => request<Campaign[]>('/api/campaigns'),
  listOfferProducts: () => request<OfferProduct[]>('/api/offer-products'),
  createOfferProduct: (payload: Record<string, unknown>) =>
    request<OfferProduct>('/api/offer-products', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateOfferProduct: (offerProductId: number, payload: Record<string, unknown>) =>
    request<OfferProduct>(`/api/offer-products/${offerProductId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listAgentStrategies: () => request<AgentStrategy[]>('/api/agent-strategies'),
  createAgentStrategy: (payload: Record<string, unknown>) =>
    request<AgentStrategy>('/api/agent-strategies', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAgentStrategy: (strategyId: number, payload: Record<string, unknown>) =>
    request<AgentStrategy>(`/api/agent-strategies/${strategyId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listPromptTemplates: () => request<PromptTemplate[]>('/api/prompt-templates'),
  createPromptTemplate: (payload: Record<string, unknown>) =>
    request<PromptTemplate>('/api/prompt-templates', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updatePromptTemplate: (templateId: number, payload: Record<string, unknown>) =>
    request<PromptTemplate>(`/api/prompt-templates/${templateId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listProspectingPromptCategories: () => request<ProspectingPromptCategory[]>('/api/prospecting-prompt-categories'),
  createProspectingPromptCategory: (payload: Record<string, unknown>) =>
    request<ProspectingPromptCategory>('/api/prospecting-prompt-categories', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProspectingPromptCategory: (categoryId: number, payload: Record<string, unknown>) =>
    request<ProspectingPromptCategory>(`/api/prospecting-prompt-categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listProspectingPrompts: (categoryId?: number | null) =>
    request<ProspectingPrompt[]>(
      categoryId ? `/api/prospecting-prompts?category_id=${categoryId}` : '/api/prospecting-prompts',
    ),
  createProspectingPrompt: (payload: Record<string, unknown>) =>
    request<ProspectingPrompt>('/api/prospecting-prompts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProspectingPrompt: (promptId: number, payload: Record<string, unknown>) =>
    request<ProspectingPrompt>(`/api/prospecting-prompts/${promptId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listProspectingRecipes: () => request<ProspectingRecipe[]>('/api/prospecting-recipes'),
  createProspectingRecipe: (payload: Record<string, unknown>) =>
    request<ProspectingRecipe>('/api/prospecting-recipes', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateProspectingRecipe: (recipeId: number, payload: Record<string, unknown>) =>
    request<ProspectingRecipe>(`/api/prospecting-recipes/${recipeId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  createCampaign: (payload: Record<string, unknown>) =>
    request<Campaign>('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateCampaign: (campaignId: number, payload: Record<string, unknown>) =>
    request<Campaign>(`/api/campaigns/${campaignId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listPlaybooks: () => request<Playbook[]>('/api/playbooks'),
  createPlaybook: (payload: Record<string, unknown>) =>
    request<Playbook>('/api/playbooks', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updatePlaybook: (playbookId: number, payload: Record<string, unknown>) =>
    request<Playbook>(`/api/playbooks/${playbookId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  listKnowledgeItems: () => request<KnowledgeItem[]>('/api/knowledge-items'),
  createKnowledgeItem: (payload: Record<string, unknown>) =>
    request<KnowledgeItem>('/api/knowledge-items', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateKnowledgeItem: (itemId: number, payload: Record<string, unknown>) =>
    request<KnowledgeItem>(`/api/knowledge-items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  createProspectingBatch: (payload: {
    niche: string
    city: string
    limit: number
    enrich: boolean
    validate_phone_format?: boolean
    campaign_id?: number | null
    recipe_id?: number | null
    prompt_category_id?: number | null
    prompt_id?: number | null
    search_goal?: string | null
    system_prompt?: string | null
    source_channels?: string[]
    discovery_mode?: string
    minimum_valid_contacts?: number | null
    require_phone?: boolean
    fallback_enabled?: boolean
    search_depth?: number | null
    agent_max_credits?: number | null
  }) =>
    request<ProspectingBatch>('/api/prospecting/batches/preview', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  adviseProspecting: (payload: { message: string; current_state?: Record<string, unknown> | null }) =>
    request<ProspectingAdvisorResponse>('/api/prospecting/advisor', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listProspectingBatches: () => request<ProspectingBatch[]>('/api/prospecting/batches'),
  getProspectingBatch: (batchId: number) => request<ProspectingBatch>(`/api/prospecting/batches/${batchId}`),
  applyProspectingBatch: (batchId: number, payload: { candidate_ids: number[]; action: string }) =>
    request<ProspectingBatch>(`/api/prospecting/batches/${batchId}/apply`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
