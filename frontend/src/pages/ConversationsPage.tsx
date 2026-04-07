import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent, ReactNode } from 'react'
import { Eye, PanelLeftOpen, SendHorizontal, Settings2, X } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type {
  Conversation,
  ConversationListResponse,
  ConversationWorkspace,
  LeadWorkspace,
  Message,
  Task,
  WhatsappSessionWorkspace,
} from '../lib/types'

function authorLabel(message: Message) {
  if (message.author_role === 'human') return 'Você'
  if (message.author_role === 'agent') return 'Agente'
  if (message.direction === 'inbound') return 'Lead'
  return message.author_role || message.sender || message.direction
}

function secondsUntil(value: string | undefined, nowMs: number) {
  if (!value) return null
  const target = new Date(value).getTime()
  if (Number.isNaN(target)) return null
  return Math.max(0, Math.ceil((target - nowMs) / 1000))
}

function formatCountdown(totalSeconds: number | null) {
  if (totalSeconds === null) return null
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function formatDurationLabel(totalSeconds: number | null | undefined) {
  if (totalSeconds === null || totalSeconds === undefined || totalSeconds <= 0) return 'sem limite'
  if (totalSeconds < 60) return `${totalSeconds}s`
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (seconds === 0) return `${minutes} min`
  return `${minutes}m ${seconds}s`
}

function scheduledAt(task: Task) {
  return typeof task.next_run_at === 'string' ? task.next_run_at : undefined
}

function getMessageDeliveryDetails(message: Message, nowMs = Date.now()): {
  tone: 'default' | 'success' | 'warning' | 'danger' | 'info'
  label: string
  description: string
  providerTarget?: string
  extraHint?: string
} {
  const metadata = message.metadata_json || {}
  const data = (metadata.data as Record<string, unknown> | undefined) || {}
  const error = (metadata.error as Record<string, unknown> | undefined) || {}
  const queue = (metadata.queue as Record<string, unknown> | undefined) || {}
  const providerStatus = typeof data.status === 'string' ? data.status : undefined
  const status = message.status || providerStatus || 'unknown'
  const jid = typeof data.jid === 'string' ? data.jid : undefined
  const rawBody = typeof error.body === 'string' ? error.body : undefined
  const transportMessage = typeof error.message === 'string' ? error.message : undefined
  let providerMessage: string | undefined
  let retryAfter: string | undefined

  if (rawBody) {
    try {
      const parsed = JSON.parse(rawBody) as { message?: string; retry_after?: number | string }
      providerMessage = parsed.message
      retryAfter = parsed.retry_after !== undefined ? String(parsed.retry_after) : undefined
    } catch {
      providerMessage = rawBody
    }
  }

  if (status === 'draft_only') {
    return {
      tone: 'warning',
      label: 'Não enviada',
      description: 'Mensagem antiga criada quando o outbound real ainda estava desligado.',
      providerTarget: jid,
    }
  }

  if (status === 'in_progress') {
    return {
      tone: 'info',
      label: 'Enviando',
      description: 'Mensagem aceita pelo provedor e aguardando confirmação final.',
      providerTarget: jid,
    }
  }

  if (status === 'queued_waiting' || status === 'queued_retry') {
    const remaining = secondsUntil(
      typeof queue.scheduled_for === 'string' ? queue.scheduled_for : undefined,
      nowMs,
    )
    return {
      tone: 'warning',
      label: 'Na fila de envio',
      description:
        remaining !== null
          ? `Aguardando a janela do provedor. Saída prevista em ${formatCountdown(remaining)}.`
          : 'Mensagem entrou na fila e será enviada assim que a janela do provedor liberar.',
      providerTarget: jid,
    }
  }

  if (status === 'sent' || status === 'SERVER_ACK') {
    return {
      tone: 'success',
      label: 'Enviada',
      description: 'Mensagem saiu para o WhatsApp e foi confirmada pelo provedor.',
      providerTarget: jid,
    }
  }

  if (status === 'delivered' || status === 'DELIVERY_ACK') {
    return {
      tone: 'success',
      label: 'Entregue',
      description: 'Mensagem entregue ao destinatário.',
      providerTarget: jid,
    }
  }

  if (status === 'read' || status === 'READ') {
    return {
      tone: 'success',
      label: 'Lida',
      description: 'Destinatário visualizou a mensagem.',
      providerTarget: jid,
    }
  }

  if (status === 'send_timeout') {
    return {
      tone: 'danger',
      label: 'Falhou no envio',
      description: 'O provedor demorou demais para responder.',
      providerTarget: jid,
    }
  }

  if (status === 'send_failed') {
    return {
      tone: 'danger',
      label: 'Falhou no envio',
      description:
        providerMessage ||
        transportMessage ||
        'O provedor rejeitou a mensagem. Pode ser número inválido, limite do plano ou erro externo.',
      extraHint: retryAfter ? `Tente novamente em ${retryAfter}s.` : undefined,
      providerTarget: jid,
    }
  }

  return {
    tone: 'default',
    label: status,
    description: 'Sem detalhe adicional do provedor.',
    providerTarget: jid,
  }
}

function conversationModeLabel(conversation: Conversation) {
  if (conversation.manual_mode) return 'humano'
  if (conversation.automation_paused) return 'pausada'
  return 'agente'
}

function buildConversationHeadline(lead: LeadWorkspace, conversation: Conversation) {
  return `${lead.niche} em ${lead.city} • ${conversation.whatsapp_session_name || 'linha legada'}`
}

function ActionSheet({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string
  subtitle: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="conversation-sheet-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="conversation-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="conversation-sheet__header">
          <div>
            <strong>{title}</strong>
            <p>{subtitle}</p>
          </div>
          <button className="button button--ghost button--icon" type="button" onClick={onClose} aria-label="Fechar painel">
            <X size={16} />
          </button>
        </header>
        <div className="conversation-sheet__body">{children}</div>
      </aside>
    </div>
  )
}

export function ConversationsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const leadIdParam = searchParams.get('leadId')
  const conversationIdParam = searchParams.get('conversationId')
  const selectedConversationIdRef = useRef<number | null>(null)
  const listRequestIdRef = useRef(0)
  const threadRequestIdRef = useRef(0)
  const timelineRef = useRef<HTMLDivElement | null>(null)

  const [data, setData] = useState<ConversationListResponse | null>(null)
  const [sessionWorkspace, setSessionWorkspace] = useState<WhatsappSessionWorkspace | null>(null)
  const [pendingQueueTasks, setPendingQueueTasks] = useState<Task[]>([])
  const [workspace, setWorkspace] = useState<ConversationWorkspace | null>(null)
  const [listLoading, setListLoading] = useState(true)
  const [threadLoading, setThreadLoading] = useState(false)
  const [openingConversationId, setOpeningConversationId] = useState<number | null>(null)
  const [activeSheet, setActiveSheet] = useState<'details' | 'controls' | null>(null)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const [operatorName, setOperatorName] = useState('gestor')
  const [composer, setComposer] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [filters, setFilters] = useState({
    unreadOnly: false,
    pendingReviewOnly: false,
    manualMode: '',
    sessionScope: 'active',
    sortBy: 'priority',
    sortDirection: 'desc',
  })

  const conversation = workspace?.conversation ?? null
  const lead = workspace?.lead ?? null

  const params = useMemo(() => {
    const current = new URLSearchParams({ page: '1', page_size: '50' })
    if (filters.unreadOnly) current.set('unread_only', 'true')
    if (filters.pendingReviewOnly) current.set('pending_review_only', 'true')
    if (filters.manualMode) current.set('manual_mode', filters.manualMode)
    if (filters.sessionScope === 'active') current.set('active_session_only', 'true')
    if (filters.sessionScope === 'legacy') current.set('legacy_only', 'true')
    if (filters.sessionScope.startsWith('session:')) current.set('whatsapp_session_id', filters.sessionScope.replace('session:', ''))
    current.set('sort_by', filters.sortBy)
    current.set('sort_direction', filters.sortDirection)
    return current
  }, [filters])

  const sortedMessages = useMemo(
    () =>
      conversation
        ? [...conversation.messages].sort(
            (left, right) => new Date(left.sent_at).getTime() - new Date(right.sent_at).getTime(),
          )
        : [],
    [conversation],
  )

  const visibleMessages = useMemo(
    () =>
      sortedMessages.filter((message) => {
        if (message.author_role !== 'provider_outbound' || message.direction !== 'outbound') {
          return true
        }
        const messageTime = new Date(message.sent_at).getTime()
        return !sortedMessages.some((candidate) => {
          if (candidate.id === message.id) return false
          if (candidate.direction !== 'outbound') return false
          if (!['agent', 'human'].includes(candidate.author_role || '')) return false
          if (candidate.content !== message.content) return false
          const candidateTime = new Date(candidate.sent_at).getTime()
          return Math.abs(candidateTime - messageTime) <= 10 * 60 * 1000
        })
      }),
    [sortedMessages],
  )

  const conversationTasks = useMemo(
    () => lead?.tasks.filter((task) => task.conversation_id === selectedConversationId) ?? [],
    [lead, selectedConversationId],
  )

  const pendingAutoReplyTask = useMemo(
    () => conversationTasks.find((task) => task.task_type === 'delayed_auto_reply' && task.status === 'pending') ?? null,
    [conversationTasks],
  )

  const pendingQueuedOutboundTasks = useMemo(
    () =>
      conversationTasks
        .filter((task) => task.task_type === 'queued_outbound' && task.status === 'pending')
        .sort((left, right) => new Date(left.next_run_at || 0).getTime() - new Date(right.next_run_at || 0).getTime()),
    [conversationTasks],
  )

  const queuedMessagesInConversation = useMemo(
    () => visibleMessages.filter((message) => ['queued_waiting', 'queued_retry'].includes(message.status || '')),
    [visibleMessages],
  )

  const globalQueuedOutboundTasks = useMemo(
    () =>
      pendingQueueTasks
        .filter((task) => task.task_type === 'queued_outbound' && task.status === 'pending')
        .sort((left, right) => new Date(left.next_run_at || 0).getTime() - new Date(right.next_run_at || 0).getTime()),
    [pendingQueueTasks],
  )

  const queuePositionByTaskId = useMemo(() => {
    const positions = new Map<number, number>()
    globalQueuedOutboundTasks.forEach((task, index) => positions.set(task.id, index + 1))
    return positions
  }, [globalQueuedOutboundTasks])

  const nextQueuedMessageFallback = useMemo(() => {
    const candidates = queuedMessagesInConversation
      .map((message) => {
        const metadata = message.metadata_json || {}
        const queue = (metadata.queue as Record<string, unknown> | undefined) || {}
        const scheduledFor = typeof queue.scheduled_for === 'string' ? queue.scheduled_for : undefined
        return scheduledFor ? { message, scheduledFor } : null
      })
      .filter((item): item is { message: Message; scheduledFor: string } => Boolean(item))
      .sort((left, right) => new Date(left.scheduledFor).getTime() - new Date(right.scheduledFor).getTime())
    return candidates[0] ?? null
  }, [queuedMessagesInConversation])

  const currentSession = useMemo(() => {
    if (!sessionWorkspace) return null
    const sessionId = conversation?.whatsapp_session_id ?? sessionWorkspace.active_session_id ?? null
    if (!sessionId) return null
    return sessionWorkspace.items.find((item) => item.id === sessionId) ?? null
  }, [conversation?.whatsapp_session_id, sessionWorkspace])

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId
  }, [selectedConversationId])

  useEffect(() => {
    const target = timelineRef.current
    if (!target) return
    target.scrollTop = target.scrollHeight
  }, [selectedConversationId, visibleMessages.length])

  useEffect(() => {
    const hasCountdown = Boolean(pendingAutoReplyTask || pendingQueuedOutboundTasks.length)
    if (!hasCountdown) return
    const interval = window.setInterval(() => setNowMs(Date.now()), 1000)
    return () => window.clearInterval(interval)
  }, [pendingAutoReplyTask, pendingQueuedOutboundTasks.length])

  const updateConversationListItem = (updatedConversation: Conversation) => {
    setData((current) => {
      if (!current) return current
      const latestMessage = updatedConversation.messages[updatedConversation.messages.length - 1]
      return {
        ...current,
        items: current.items.map((item) =>
          item.id === updatedConversation.id
            ? {
                ...item,
                manual_mode: updatedConversation.manual_mode,
                automation_paused: updatedConversation.automation_paused,
                auto_reply_enabled: updatedConversation.auto_reply_enabled,
                reply_delay_seconds: updatedConversation.reply_delay_seconds,
                pending_human_review: updatedConversation.pending_human_review,
                assignee: updatedConversation.assignee,
                stage: updatedConversation.stage,
                unread_count: updatedConversation.unread_count,
                last_message_at: updatedConversation.last_message_at,
                latest_message_preview: latestMessage?.content || item.latest_message_preview,
              }
            : item,
        ),
      }
    })
  }

  const updateWorkspaceConversation = (updatedConversation: Conversation) => {
    setWorkspace((current) =>
      current && current.conversation.id === updatedConversation.id
        ? { ...current, conversation: updatedConversation }
        : current,
    )
  }

  const syncConversationSearchParam = useCallback((conversationId: number | null) => {
    const next = new URLSearchParams(searchParams)
    if (conversationId) {
      next.set('conversationId', String(conversationId))
    } else {
      next.delete('conversationId')
    }
    next.delete('leadId')
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const loadList = useCallback(async (options?: { quiet?: boolean }) => {
    const requestId = ++listRequestIdRef.current
    if (!options?.quiet) {
      setListLoading(true)
      setError(null)
    }
    try {
      const payload = await api.listConversations(params)
      if (requestId !== listRequestIdRef.current) return
      setData(payload)
      const currentSelectedConversationId = selectedConversationIdRef.current
      const preferredConversation = conversationIdParam ? payload.items.find((item) => item.id === Number(conversationIdParam)) : null
      const preferred =
        !currentSelectedConversationId && leadIdParam ? payload.items.find((item) => item.lead_id === Number(leadIdParam)) : null
      const selectedStillExists = currentSelectedConversationId
        ? payload.items.some((item) => item.id === currentSelectedConversationId)
        : false

      if (preferredConversation && preferredConversation.id !== currentSelectedConversationId) {
        selectedConversationIdRef.current = preferredConversation.id
        setSelectedConversationId(preferredConversation.id)
      } else if (preferred && preferred.id !== currentSelectedConversationId) {
        selectedConversationIdRef.current = preferred.id
        setSelectedConversationId(preferred.id)
      } else if (!selectedStillExists && payload.items[0]) {
        selectedConversationIdRef.current = payload.items[0].id
        setSelectedConversationId(payload.items[0].id)
      } else if (payload.items.length === 0) {
        selectedConversationIdRef.current = null
        setSelectedConversationId(null)
        setWorkspace(null)
        syncConversationSearchParam(null)
      }
    } catch (err) {
      if (requestId !== listRequestIdRef.current) return
      setError((err as Error).message)
    } finally {
      if (requestId === listRequestIdRef.current && !options?.quiet) {
        setListLoading(false)
      }
    }
  }, [conversationIdParam, leadIdParam, params, syncConversationSearchParam])

  const loadPendingQueueTasks = useCallback(async () => {
    try {
      const taskParams = new URLSearchParams({ page: '1', page_size: '100', status: 'pending' })
      const payload = await api.listTasks(taskParams)
      setPendingQueueTasks(payload.items)
    } catch {
      setPendingQueueTasks([])
    }
  }, [])

  const loadSessionWorkspace = useCallback(async () => {
    try {
      const payload = await api.listWhatsappSessions()
      setSessionWorkspace(payload)
    } catch {
      setSessionWorkspace(null)
    }
  }, [])

  const loadSelected = useCallback(async (conversationId: number, options?: { quiet?: boolean; syncComposer?: boolean }) => {
    const requestId = ++threadRequestIdRef.current
    if (!options?.quiet) {
      setThreadLoading(true)
    }
    try {
      const payload = await api.getConversationWorkspace(conversationId)
      if (requestId !== threadRequestIdRef.current) return
      if (selectedConversationIdRef.current !== conversationId) return
      setWorkspace(payload)
      if (options?.syncComposer) {
        setComposer(payload.conversation.pending_draft || '')
      }
    } catch (err) {
      if (requestId !== threadRequestIdRef.current) return
      if (selectedConversationIdRef.current !== conversationId) return
      const message = (err as Error).message
      setWorkspace(null)
      setComposer('')
      setActionError(
        message.includes('Conversa não encontrada')
          ? 'Essa conversa não existe mais ou ainda não foi criada. Escolha outra thread.'
          : message,
      )
      const fallback = data?.items.find((item) => item.id !== conversationId)
      if (fallback) {
        setSelectedConversationId(fallback.id)
      } else {
        syncConversationSearchParam(null)
      }
    } finally {
      const isCurrentRequest = requestId === threadRequestIdRef.current
      if (isCurrentRequest && selectedConversationIdRef.current === conversationId) {
        setOpeningConversationId(null)
      }
      if (isCurrentRequest && !options?.quiet) {
        setThreadLoading(false)
      }
    }
  }, [data?.items, syncConversationSearchParam])

  useEffect(() => {
    void loadList()
    void loadPendingQueueTasks()
    void loadSessionWorkspace()
  }, [loadList, loadPendingQueueTasks, loadSessionWorkspace])

  useEffect(() => {
    if (!selectedConversationId) return
    syncConversationSearchParam(selectedConversationId)
    void loadSelected(selectedConversationId, { syncComposer: true })
  }, [loadSelected, selectedConversationId, syncConversationSearchParam])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadList({ quiet: true })
      void loadPendingQueueTasks()
      if (selectedConversationId) {
        void loadSelected(selectedConversationId, { quiet: true, syncComposer: false })
      }
    }, 5000)
    return () => window.clearInterval(interval)
  }, [loadList, loadPendingQueueTasks, loadSelected, selectedConversationId])

  const refreshCurrentConversation = async () => {
    await loadList({ quiet: true })
    if (selectedConversationId) {
      await loadSelected(selectedConversationId, { quiet: true, syncComposer: false })
    }
  }

  const handleSelectConversation = (conversationId: number) => {
    if (conversationId === selectedConversationIdRef.current) return
    selectedConversationIdRef.current = conversationId
    setActionError(null)
    setActionNotice(null)
    setOpeningConversationId(conversationId)
    setThreadLoading(true)
    setActiveSheet(null)
    syncConversationSearchParam(conversationId)
    setSelectedConversationId(conversationId)
  }

  const runConversationAction = async (key: string, notice: string, action: () => Promise<void>) => {
    setActionLoading(key)
    setActionError(null)
    setActionNotice(null)
    try {
      await action()
      setActionNotice(notice)
      await refreshCurrentConversation()
    } catch (err) {
      setActionError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const onBulkAction = async (action: string) => {
    if (selectedIds.length === 0) return
    await runConversationAction(`bulk:${action}`, 'Ação em lote aplicada nas conversas selecionadas.', async () => {
      await api.bulkConversationAction({
        conversation_ids: selectedIds,
        action,
        operator_name: operatorName,
        auto_reply_enabled: action === 'set_auto_reply' ? true : undefined,
      })
    })
  }

  const onTakeOver = async () => {
    if (!selectedConversationId) return
    await runConversationAction('takeover', 'Controle humano assumido nesta conversa.', async () => {
      await api.takeOverConversation(selectedConversationId, operatorName)
    })
  }

  const onRelease = async () => {
    if (!selectedConversationId) return
    await runConversationAction('release', 'Controle devolvido para a automação.', async () => {
      await api.releaseConversation(selectedConversationId)
    })
  }

  const onMarkRead = async () => {
    if (!selectedConversationId) return
    await runConversationAction('mark-read', 'Conversa marcada como lida.', async () => {
      await api.markConversationRead(selectedConversationId)
    })
  }

  const onSendManual = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedConversationId || !composer.trim()) return
    const content = composer.trim()
    setActionLoading('manual-send')
    setActionError(null)
    setActionNotice(null)
    try {
      const updatedConversation = await api.sendManualMessage(selectedConversationId, {
        operator_name: operatorName,
        content,
        mark_as_read: true,
      })
      updateWorkspaceConversation(updatedConversation)
      setComposer('')
      updateConversationListItem(updatedConversation)
      const latestMessage = updatedConversation.messages[updatedConversation.messages.length - 1]
      if (latestMessage) {
        const delivery = getMessageDeliveryDetails(latestMessage)
        if (delivery.tone === 'danger') {
          setActionError(delivery.extraHint ? `${delivery.description} ${delivery.extraHint}` : delivery.description)
        } else {
          setActionNotice(
            delivery.extraHint
              ? `${delivery.label}. ${delivery.description} ${delivery.extraHint}`
              : `${delivery.label}. ${delivery.description}`,
          )
        }
      } else {
        setActionNotice('Mensagem enviada com sucesso.')
      }
    } catch (err) {
      setActionError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const onComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return
    event.preventDefault()
    const form = event.currentTarget.form
    if (!form || !composer.trim() || actionLoading === 'manual-send') return
    form.requestSubmit()
  }

  const onSaveSettings = async () => {
    if (!selectedConversationId || !conversation) return
    await runConversationAction('save-settings', 'Controles da conversa atualizados.', async () => {
      const updatedConversation = await api.updateConversationSettings(selectedConversationId, {
        auto_reply_enabled: conversation.auto_reply_enabled,
        automation_paused: conversation.automation_paused,
        reply_delay_seconds: conversation.reply_delay_seconds,
        assignee: conversation.assignee,
        pending_human_review: conversation.pending_human_review,
      })
      updateWorkspaceConversation(updatedConversation)
      updateConversationListItem(updatedConversation)
    })
  }

  const toggleSelection = (conversationId: number) => {
    setSelectedIds((current) =>
      current.includes(conversationId) ? current.filter((id) => id !== conversationId) : [...current, conversationId],
    )
  }

  const leadRequestedWithoutConversation =
    Boolean(leadIdParam) && Boolean(data) && !data?.items.some((item) => item.lead_id === Number(leadIdParam))

  return (
    <div className="page page--conversations">
      <section className="page-heading page-heading--compact">
        <div>
          <span className="eyebrow">Inbox operacional</span>
          <h1>Conversas</h1>
          <p>Thread ampla, leitura clara e controles fora do caminho até você realmente precisar deles.</p>
        </div>
        <div className="page-heading__actions">
          <input
            className="field page-heading__operator"
            value={operatorName}
            onChange={(event) => setOperatorName(event.target.value)}
            placeholder="Operador"
          />
        </div>
      </section>

      <section className="conversation-toolbar">
        <label className="toggle-inline">
          <input
            type="checkbox"
            checked={filters.unreadOnly}
            onChange={(event) => setFilters((current) => ({ ...current, unreadOnly: event.target.checked }))}
          />
          Não lidas
        </label>
        <label className="toggle-inline">
          <input
            type="checkbox"
            checked={filters.pendingReviewOnly}
            onChange={(event) => setFilters((current) => ({ ...current, pendingReviewOnly: event.target.checked }))}
          />
          Review pendente
        </label>
        <select
          className="field conversation-toolbar__field"
          value={filters.manualMode}
          onChange={(event) => setFilters((current) => ({ ...current, manualMode: event.target.value }))}
        >
          <option value="">Todas as threads</option>
          <option value="true">Apenas humano</option>
          <option value="false">Apenas agente</option>
        </select>
        <select
          className="field conversation-toolbar__field"
          value={filters.sessionScope}
          onChange={(event) => setFilters((current) => ({ ...current, sessionScope: event.target.value }))}
        >
          <option value="active">Linha ativa</option>
          <option value="">Todas as linhas</option>
          <option value="legacy">{sessionWorkspace?.legacy_label || 'Histórico legado'}</option>
          {sessionWorkspace?.items.map((item) => (
            <option key={item.id} value={`session:${item.id}`}>
              {item.name}
              {item.phone_number ? ` • ${item.phone_number}` : ''}
            </option>
          ))}
        </select>
        <select
          className="field conversation-toolbar__field"
          value={filters.sortBy}
          onChange={(event) => setFilters((current) => ({ ...current, sortBy: event.target.value }))}
        >
          <option value="priority">Prioridade operacional</option>
          <option value="recent">Mais recentes</option>
          <option value="unread">Mais não lidas</option>
          <option value="fit_score">Maior fit</option>
        </select>
        <select
          className="field conversation-toolbar__field"
          value={filters.sortDirection}
          onChange={(event) => setFilters((current) => ({ ...current, sortDirection: event.target.value }))}
        >
          <option value="desc">Maior primeiro</option>
          <option value="asc">Menor primeiro</option>
        </select>

        {selectedIds.length > 0 ? (
          <div className="conversation-toolbar__bulk-actions">
            <button className="button button--ghost" onClick={() => void onBulkAction('takeover')}>
              {actionLoading === 'bulk:takeover' ? 'Assumindo...' : 'Assumir lote'}
            </button>
            <button className="button button--ghost" onClick={() => void onBulkAction('pause')}>
              {actionLoading === 'bulk:pause' ? 'Pausando...' : 'Pausar lote'}
            </button>
            <button className="button button--ghost" onClick={() => void onBulkAction('resume')}>
              {actionLoading === 'bulk:resume' ? 'Retomando...' : 'Retomar lote'}
            </button>
          </div>
        ) : null}
      </section>

      {actionError ? (
        <article className="note-card note-card--danger">
          <strong>Falha na ação</strong>
          <p>{actionError}</p>
        </article>
      ) : null}
      {actionNotice ? (
        <article className="note-card note-card--success">
          <strong>Status</strong>
          <p>{actionNotice}</p>
        </article>
      ) : null}

      {error ? <EmptyState title="Erro ao carregar conversas" description={error} /> : null}
      {!error && listLoading ? <EmptyState title="Carregando conversas" description="Buscando a fila do banco." /> : null}
      {!error && !listLoading && data && data.items.length === 0 ? (
        <EmptyState title="Sem conversas ainda" description="A thread aparece aqui depois de outreach ou resposta inbound." />
      ) : null}

      {leadRequestedWithoutConversation ? (
        <article className="note-card note-card--warning">
          <strong>Esse lead ainda não abriu thread</strong>
          <p>
            O lead pedido na URL ainda não tem conversa ativa. Isso normalmente acontece quando o start não foi feito ou
            quando falta telefone/WhatsApp para envio.
          </p>
        </article>
      ) : null}

      {data && data.items.length === 0 ? (
        <section className="empty-state empty-state--large">
          <strong>Como criar uma conversa</strong>
          <p>Você pode prospectar um lote novo ou cadastrar um lead manualmente e dar start na abordagem.</p>
          <div className="inline-actions">
            <Link className="button button--primary" to="/prospecting">
              Fazer pesquisa de clientes
            </Link>
            <Link className="button button--ghost" to="/leads">
              Cadastrar lead manualmente
            </Link>
          </div>
        </section>
      ) : null}

      {data && data.items.length > 0 ? (
        <section className="conversation-layout">
          <aside className="conversation-sidebar">
            <header className="conversation-sidebar__header">
              <div>
                <strong>Inbox</strong>
                <p>{data.total} threads no recorte atual</p>
              </div>
            </header>
            <div className="conversation-sidebar__list">
              {data.items.map((item) => (
                <button
                  key={item.id}
                  className={`conversation-card ${
                    selectedConversationId === item.id ? 'thread-card--active' : ''
                  } ${openingConversationId === item.id ? 'thread-card--loading' : ''}`}
                  onClick={() => handleSelectConversation(item.id)}
                >
                  <div className="conversation-card__top">
                    <label className="checkbox-inline" onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelection(item.id)}
                      />
                    </label>
                    <div className="conversation-card__identity">
                      <strong>{item.lead_name}</strong>
                      <span>{formatDateTime(item.last_message_at)}</span>
                    </div>
                    {item.unread_count > 0 ? <span className="thread-card__badge">{item.unread_count}</span> : null}
                  </div>
                  <div className="conversation-card__meta">
                    <StatusPill tone={item.manual_mode ? 'warning' : 'info'}>
                      {item.manual_mode ? 'humano' : 'agente'}
                    </StatusPill>
                    {item.inbound_unverified ? <StatusPill tone="warning">inbound não verificado</StatusPill> : null}
                    <StatusPill tone={item.pending_human_review ? 'warning' : 'default'}>
                      {item.pending_human_review ? 'review' : item.stage}
                    </StatusPill>
                    <StatusPill tone="default">
                      {item.whatsapp_session_name || sessionWorkspace?.legacy_label || 'legado'}
                    </StatusPill>
                  </div>
                  <p className="conversation-card__preview">{item.latest_message_preview || 'Sem preview ainda.'}</p>
                  <small className="conversation-card__summary">
                    {item.lead_funnel_stage || item.stage}
                    {item.lead_fit_score ? ` • fit ${item.lead_fit_score}` : ''}
                    {item.lead_meeting_status ? ` • ${item.lead_meeting_status}` : ''}
                    {item.source_origin ? ` • origem ${item.source_origin}` : ''}
                  </small>
                  <small className="conversation-card__summary">
                    prioridade {item.priority_score ?? '—'}
                    {item.priority_label ? ` • ${item.priority_label}` : ''}
                  </small>
                  <div className="conversation-card__footer">
                    <small>{item.recommended_action?.label || 'Sem próxima ação'}</small>
                    <span className="thread-card__action">{openingConversationId === item.id ? 'Abrindo...' : 'Abrir conversa'}</span>
                  </div>
                </button>
              ))}
            </div>
          </aside>

          <section className="conversation-main">
            {threadLoading ? (
              <EmptyState title="Abrindo conversa" description="Carregando histórico e contexto operacional leve." />
            ) : !conversation || !lead ? (
              <EmptyState title="Selecione uma conversa" description="Ao clicar na thread, o chat completo aparece aqui." />
            ) : (
              <div className="conversation-thread">
                <header className="conversation-thread__header">
                  <div className="conversation-thread__identity">
                    <span className="conversation-thread__avatar">{lead.business_name.slice(0, 1).toUpperCase()}</span>
                    <div>
                      <strong>{lead.business_name}</strong>
                      <p>{buildConversationHeadline(lead, conversation)}</p>
                      <small>
                        Funil {lead.funnel_stage} • Fit {lead.fit_score ?? '—'}
                        {lead.fit_label ? ` (${lead.fit_label})` : ''}
                      </small>
                    </div>
                  </div>
                  <div className="conversation-thread__header-actions">
                    <StatusPill tone={conversation.manual_mode ? 'warning' : 'info'}>
                      {conversationModeLabel(conversation)}
                    </StatusPill>
                    <StatusPill tone={conversation.automation_paused ? 'warning' : 'success'}>
                      {conversation.automation_paused ? 'automação pausada' : 'automação ativa'}
                    </StatusPill>
                    <StatusPill tone={conversation.pending_human_review ? 'warning' : 'default'}>
                      {conversation.pending_human_review ? 'Review pendente' : conversation.stage}
                    </StatusPill>
                    <StatusPill tone={currentSession?.outbound_cooldown_seconds ? 'warning' : 'success'}>
                      Janela da linha: {formatDurationLabel(currentSession?.outbound_cooldown_seconds)}
                    </StatusPill>
                    <button className="button button--ghost button--icon" type="button" onClick={() => setActiveSheet('details')}>
                      <Eye size={16} />
                      Detalhes
                    </button>
                    <button className="button button--ghost button--icon" type="button" onClick={() => setActiveSheet('controls')}>
                      <Settings2 size={16} />
                      Controles
                    </button>
                    <button
                      className="button button--ghost button--icon conversation-mobile-inbox"
                      type="button"
                      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                    >
                      <PanelLeftOpen size={16} />
                      Inbox
                    </button>
                  </div>
                </header>

                <div className="conversation-thread__toolbar">
                  <button className="button button--primary" onClick={() => void onTakeOver()}>
                    {actionLoading === 'takeover' ? 'Assumindo...' : 'Assumir'}
                  </button>
                  <button className="button button--ghost" onClick={() => void onRelease()}>
                    {actionLoading === 'release' ? 'Liberando...' : 'Liberar'}
                  </button>
                  <button className="button button--ghost" onClick={() => void onMarkRead()}>
                    {actionLoading === 'mark-read' ? 'Marcando...' : 'Marcar como lida'}
                  </button>
                </div>

                {pendingAutoReplyTask ? (
                  <article className="chat-queue-card chat-queue-card--soft">
                    <strong>Resposta automática agendada</strong>
                    <p>
                      O agente já viu a mensagem e vai responder em{' '}
                      <strong>{formatCountdown(secondsUntil(pendingAutoReplyTask.next_run_at || undefined, nowMs)) || '00:00'}</strong>.
                    </p>
                  </article>
                ) : null}

                {pendingQueuedOutboundTasks.length > 0 || nextQueuedMessageFallback ? (
                  <article className="chat-queue-card chat-queue-card--warning">
                    <strong>Fila de envio</strong>
                    <p>
                      {pendingQueuedOutboundTasks.length > 0 ? (
                        <>
                          {pendingQueuedOutboundTasks.length} mensagem(ns) desta conversa aguardando. Próxima saída em{' '}
                          <strong>{formatCountdown(secondsUntil(scheduledAt(pendingQueuedOutboundTasks[0]), nowMs)) || '00:00'}</strong> e
                          posição global <strong>#{queuePositionByTaskId.get(pendingQueuedOutboundTasks[0].id) || 1}</strong>.
                        </>
                      ) : (
                        <>
                          Há mensagem em fila nesta conversa. Próxima saída prevista em{' '}
                          <strong>{formatCountdown(secondsUntil(nextQueuedMessageFallback?.scheduledFor, nowMs)) || '00:00'}</strong>.
                        </>
                      )}
                    </p>
                    <p>
                      Janela configurada nesta linha: <strong>{formatDurationLabel(currentSession?.outbound_cooldown_seconds)}</strong>.
                    </p>
                  </article>
                ) : null}

                <div ref={timelineRef} className="conversation-timeline">
                  {visibleMessages.map((message) => {
                    const delivery = getMessageDeliveryDetails(message, nowMs)
                    const matchingQueueTask = pendingQueuedOutboundTasks.find(
                      (task) => Number((task.payload?.message_id as number | string | undefined) || 0) === message.id,
                    )
                    return (
                      <article
                        key={message.id}
                        className={`message message--chat ${message.direction === 'outbound' ? 'message--outbound' : 'message--inbound'}`}
                      >
                        <div className="message__meta">
                          <strong>{authorLabel(message)}</strong>
                          <span>{formatDateTime(message.sent_at)}</span>
                        </div>
                        <p>{message.content}</p>
                        {message.direction === 'outbound' ? (
                          <div className="message-status">
                            <StatusPill tone={delivery.tone}>{delivery.label}</StatusPill>
                            <small>{delivery.description}</small>
                            {matchingQueueTask ? (
                              <small>
                                Posição na fila: #{queuePositionByTaskId.get(matchingQueueTask.id) || 1}. Saída prevista em{' '}
                                {formatCountdown(secondsUntil(scheduledAt(matchingQueueTask), nowMs)) || '00:00'}.
                              </small>
                            ) : null}
                            {delivery.providerTarget ? <small>Destino: {delivery.providerTarget}</small> : null}
                          </div>
                        ) : (
                          <small>Status: {message.status || '—'}</small>
                        )}
                      </article>
                    )
                  })}
                </div>

                <form className="composer composer--chat composer--chat-premium" onSubmit={onSendManual}>
                  <textarea
                    className="field field--textarea"
                    placeholder="Digite uma mensagem e pressione Enter para enviar"
                    value={composer}
                    onChange={(event) => setComposer(event.target.value)}
                    onKeyDown={onComposerKeyDown}
                  />
                  <button
                    className={`composer__send ${actionLoading === 'manual-send' ? 'composer__send--loading' : ''}`}
                    type="submit"
                    disabled={!composer.trim() || actionLoading === 'manual-send'}
                  >
                    <SendHorizontal size={18} />
                    <span>{actionLoading === 'manual-send' ? 'Enviando...' : 'Enviar'}</span>
                  </button>
                </form>
              </div>
            )}
          </section>
        </section>
      ) : null}

      {activeSheet === 'details' && conversation && lead ? (
        <ActionSheet
          title="Detalhes da thread"
          subtitle="Leitura operacional e contexto comercial sem esmagar o chat."
          onClose={() => setActiveSheet(null)}
        >
          <section className="context-section">
            <span className="context-section__title">Resumo rápido</span>
            <div className="kv-list">
              <div><span>Telefone</span><strong>{lead.phone_number || lead.whatsapp_number || '—'}</strong></div>
              <div><span>Responsável</span><strong>{conversation.assignee || 'livre'}</strong></div>
              <div><span>Última saída</span><strong>{formatDateTime(conversation.last_outbound_at)}</strong></div>
              <div><span>Última entrada</span><strong>{formatDateTime(conversation.last_inbound_at)}</strong></div>
              <div><span>Delay atual</span><strong>{conversation.reply_delay_seconds}s</strong></div>
              <div><span>Cooldown da linha</span><strong>{formatDurationLabel(currentSession?.outbound_cooldown_seconds)}</strong></div>
              <div><span>Fit</span><strong>{lead.fit_score ?? '—'} {lead.fit_label ? `(${lead.fit_label})` : ''}</strong></div>
              <div><span>Intent</span><strong>{lead.intent_status}</strong></div>
              <div><span>Dor</span><strong>{lead.pain_status}</strong></div>
              <div><span>Meeting</span><strong>{lead.meeting_status}</strong></div>
              <div><span>Objeção</span><strong>{lead.objection_status}</strong></div>
            </div>
          </section>

          <section className="context-section">
            <span className="context-section__title">Leitura operacional</span>
            <article className="note-card">
              <strong>Resumo</strong>
              <p>{conversation.summary || conversation.pending_review_reason || 'Ainda sem resumo automático desta conversa.'}</p>
            </article>
            <article className="note-card">
              <strong>Próxima ação sugerida</strong>
              <p>
                <strong>{lead.recommended_action?.label || 'Sem recomendação'}</strong>
                {lead.recommended_action?.description ? ` • ${lead.recommended_action.description}` : ''}
              </p>
            </article>
            {lead.suggested_playbook ? (
              <article className="note-card">
                <strong>Playbook sugerido</strong>
                <p>
                  <strong>{lead.suggested_playbook.name}</strong>
                  {lead.suggested_playbook.applicability_reason ? ` • ${lead.suggested_playbook.applicability_reason}` : ''}
                </p>
                <p>{lead.suggested_playbook.instructions}</p>
              </article>
            ) : null}
          </section>

          {lead.notes ? (
            <section className="context-section">
              <span className="context-section__title">Contexto do lead</span>
              <article className="note-card">
                <p>{lead.notes}</p>
              </article>
            </section>
          ) : null}

          {conversation.pending_draft ? (
            <section className="context-section">
              <span className="context-section__title">Rascunho pendente</span>
              <article className="note-card">
                <p>{conversation.pending_draft}</p>
              </article>
            </section>
          ) : null}
        </ActionSheet>
      ) : null}

      {activeSheet === 'controls' && conversation && lead ? (
        <ActionSheet
          title="Controles da thread"
          subtitle="Ajuste automação, revisão e timing sem perder a leitura da conversa."
          onClose={() => setActiveSheet(null)}
        >
          <section className="context-section">
            <span className="context-section__title">Automação</span>
            <label className="toggle-card">
              <input
                type="checkbox"
                checked={conversation.auto_reply_enabled}
                onChange={(event) =>
                  setWorkspace((current) =>
                    current
                      ? { ...current, conversation: { ...current.conversation, auto_reply_enabled: event.target.checked } }
                      : current,
                  )
                }
              />
              <div>
                <strong>Auto reply nesta conversa</strong>
                <p>Liga ou desliga a resposta automática só desta thread.</p>
              </div>
            </label>

            <label className="toggle-card">
              <input
                type="checkbox"
                checked={conversation.automation_paused}
                onChange={(event) =>
                  setWorkspace((current) =>
                    current
                      ? { ...current, conversation: { ...current.conversation, automation_paused: event.target.checked } }
                      : current,
                  )
                }
              />
              <div>
                <strong>Pausar automação</strong>
                <p>Bloqueia respostas do agente e follow-ups desta thread.</p>
              </div>
            </label>

            <label className="toggle-card">
              <input
                type="checkbox"
                checked={conversation.pending_human_review}
                onChange={(event) =>
                  setWorkspace((current) =>
                    current
                      ? { ...current, conversation: { ...current.conversation, pending_human_review: event.target.checked } }
                      : current,
                  )
                }
              />
              <div>
                <strong>Exigir revisão humana</strong>
                <p>Se ligado, a resposta do agente vira rascunho antes do envio.</p>
              </div>
            </label>

            <label className="field-group">
              <span>Delay da resposta automática (segundos)</span>
              <input
                className="field"
                type="number"
                value={conversation.reply_delay_seconds}
                onChange={(event) =>
                  setWorkspace((current) =>
                    current
                      ? { ...current, conversation: { ...current.conversation, reply_delay_seconds: Number(event.target.value) } }
                      : current,
                  )
                }
              />
            </label>

            <button className="button button--primary" onClick={() => void onSaveSettings()}>
              {actionLoading === 'save-settings' ? 'Salvando...' : 'Salvar controles da conversa'}
            </button>
          </section>
        </ActionSheet>
      ) : null}
    </div>
  )
}
