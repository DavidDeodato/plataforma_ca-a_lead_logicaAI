import type {
  AgentPreview,
  Campaign,
  ConversationListResponse,
  Conversation,
  DashboardSummary,
  KnowledgeItem,
  Lead,
  LeadDetail,
  LeadListResponse,
  Playbook,
  ProspectingAdvisorResponse,
  ProspectingBatch,
  QualifiedLead,
  Readiness,
  RuntimeSettings,
  Task,
  TaskListResponse,
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
