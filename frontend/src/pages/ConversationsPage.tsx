import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, SendHorizontal, SlidersHorizontal } from 'lucide-react'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type { Conversation, ConversationListResponse, LeadDetail, Message, Task } from '../lib/types'

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

function scheduledAt(task: Task) {
  return typeof task.next_run_at === 'string' ? task.next_run_at : undefined
}

function getMessageDeliveryDetails(message: Message, nowMs?: number): {
  tone: string
  label: string
  description: string
  providerTarget?: string
  extraHint?: string
}
function getMessageDeliveryDetails(message: Message, nowMs = Date.now()): {
  tone: string
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

export function ConversationsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const leadIdParam = searchParams.get('leadId')
  const conversationIdParam = searchParams.get('conversationId')
  const selectedConversationIdRef = useRef<number | null>(null)
  const listRequestIdRef = useRef(0)
  const threadRequestIdRef = useRef(0)
  const [data, setData] = useState<ConversationListResponse | null>(null)
  const [pendingQueueTasks, setPendingQueueTasks] = useState<Task[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [threadLoading, setThreadLoading] = useState(false)
  const [openingConversationId, setOpeningConversationId] = useState<number | null>(null)
  const [nowMs, setNowMs] = useState(() => Date.now())
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [lead, setLead] = useState<LeadDetail | null>(null)
  const [operatorName, setOperatorName] = useState('gestor')
  const [composer, setComposer] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [showInbox, setShowInbox] = useState(true)
  const [showControls, setShowControls] = useState(true)
  const [filters, setFilters] = useState({
    unreadOnly: false,
    pendingReviewOnly: false,
    manualMode: '',
  })

  const params = useMemo(() => {
    const current = new URLSearchParams({ page: '1', page_size: '50' })
    if (filters.unreadOnly) current.set('unread_only', 'true')
    if (filters.pendingReviewOnly) current.set('pending_review_only', 'true')
    if (filters.manualMode) current.set('manual_mode', filters.manualMode)
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
        .sort((left, right) => {
          const leftTime = new Date(left.next_run_at || 0).getTime()
          const rightTime = new Date(right.next_run_at || 0).getTime()
          return leftTime - rightTime
        }),
    [conversationTasks],
  )

  const queuedMessagesInConversation = useMemo(
    () =>
      visibleMessages.filter((message) => ['queued_waiting', 'queued_retry'].includes(message.status || '')),
    [visibleMessages],
  )

  const globalQueuedOutboundTasks = useMemo(
    () =>
      pendingQueueTasks
        .filter((task) => task.task_type === 'queued_outbound' && task.status === 'pending')
        .sort((left, right) => {
          const leftTime = new Date(left.next_run_at || 0).getTime()
          const rightTime = new Date(right.next_run_at || 0).getTime()
          return leftTime - rightTime
        }),
    [pendingQueueTasks],
  )

  const queuePositionByTaskId = useMemo(() => {
    const positions = new Map<number, number>()
    globalQueuedOutboundTasks.forEach((task, index) => {
      positions.set(task.id, index + 1)
    })
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

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId
  }, [selectedConversationId])

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

  const syncConversationSearchParam = (conversationId: number | null) => {
    const next = new URLSearchParams(searchParams)
    if (conversationId) {
      next.set('conversationId', String(conversationId))
    } else {
      next.delete('conversationId')
    }
    next.delete('leadId')
    setSearchParams(next, { replace: true })
  }

  const loadList = async (options?: { quiet?: boolean }) => {
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
      const preferredConversation = conversationIdParam
        ? payload.items.find((item) => item.id === Number(conversationIdParam))
        : null
      const preferred =
        !currentSelectedConversationId && leadIdParam
          ? payload.items.find((item) => item.lead_id === Number(leadIdParam))
          : null
      const selectedStillExists = currentSelectedConversationId
        ? payload.items.some((item) => item.id === currentSelectedConversationId)
        : false

      if (preferredConversation) {
        if (preferredConversation.id !== currentSelectedConversationId) {
          selectedConversationIdRef.current = preferredConversation.id
          setSelectedConversationId(preferredConversation.id)
        }
      } else if (preferred) {
        if (preferred.id !== currentSelectedConversationId) {
          selectedConversationIdRef.current = preferred.id
          setSelectedConversationId(preferred.id)
        }
      } else if (!selectedStillExists && payload.items[0]) {
        selectedConversationIdRef.current = payload.items[0].id
        setSelectedConversationId(payload.items[0].id)
      } else if (payload.items.length === 0) {
        selectedConversationIdRef.current = null
        setSelectedConversationId(null)
        setConversation(null)
        setLead(null)
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
  }

  const loadPendingQueueTasks = async () => {
    try {
      const params = new URLSearchParams({ page: '1', page_size: '200', status: 'pending' })
      const payload = await api.listTasks(params)
      setPendingQueueTasks(payload.items)
    } catch {
      setPendingQueueTasks([])
    }
  }

  const loadSelected = async (
    conversationId: number,
    options?: { quiet?: boolean; syncComposer?: boolean },
  ) => {
    const requestId = ++threadRequestIdRef.current
    if (!options?.quiet) {
      setThreadLoading(true)
    }
    try {
      const currentConversation = await api.getConversation(conversationId)
      const leadDetail = await api.getLead(currentConversation.lead_id)
      if (requestId !== threadRequestIdRef.current) return
      if (selectedConversationIdRef.current !== conversationId) return
      setConversation(currentConversation)
      if (options?.syncComposer) {
        setComposer(currentConversation.pending_draft || '')
      }
      setLead(leadDetail)
    } catch (err) {
      if (requestId !== threadRequestIdRef.current) return
      if (selectedConversationIdRef.current !== conversationId) return
      const message = (err as Error).message
      setConversation(null)
      setLead(null)
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
      if (requestId !== threadRequestIdRef.current) return
      if (selectedConversationIdRef.current === conversationId) {
        setOpeningConversationId(null)
      }
      if (!options?.quiet) {
        setThreadLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadList()
    void loadPendingQueueTasks()
  }, [params, leadIdParam, conversationIdParam])

  useEffect(() => {
    if (!selectedConversationId) return
    syncConversationSearchParam(selectedConversationId)
    void loadSelected(selectedConversationId, { syncComposer: true })
  }, [selectedConversationId])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadList({ quiet: true })
      void loadPendingQueueTasks()
      if (selectedConversationId) {
        void loadSelected(selectedConversationId, { quiet: true, syncComposer: false })
      }
    }, 2000)

    return () => window.clearInterval(interval)
  }, [params, leadIdParam, conversationIdParam, selectedConversationId])

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
      setConversation(updatedConversation)
      setComposer('')
      updateConversationListItem(updatedConversation)
      const latestMessage = updatedConversation.messages[updatedConversation.messages.length - 1]
      if (latestMessage) {
        const delivery = getMessageDeliveryDetails(latestMessage)
        if (delivery.tone === 'danger') {
          setActionError(
            delivery.extraHint ? `${delivery.description} ${delivery.extraHint}` : delivery.description,
          )
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
      await api.updateConversationSettings(selectedConversationId, {
        auto_reply_enabled: conversation.auto_reply_enabled,
        automation_paused: conversation.automation_paused,
        reply_delay_seconds: conversation.reply_delay_seconds,
        assignee: conversation.assignee,
        pending_human_review: conversation.pending_human_review,
      })
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
      <section className="chat-workspace__topbar">
        <div className="chat-workspace__title">
          <span className="eyebrow">Inbox operacional</span>
          <strong>Conversas</strong>
        </div>
        <div className="chat-workspace__filters">
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
              onChange={(event) =>
                setFilters((current) => ({ ...current, pendingReviewOnly: event.target.checked }))
              }
            />
            Review
          </label>
          <select
            className="field chat-workspace__field"
            value={filters.manualMode}
            onChange={(event) => setFilters((current) => ({ ...current, manualMode: event.target.value }))}
          >
            <option value="">Todas</option>
            <option value="true">Humano</option>
            <option value="false">Automáticas</option>
          </select>
          <input
            className="field chat-workspace__field"
            value={operatorName}
            onChange={(event) => setOperatorName(event.target.value)}
            placeholder="Operador"
          />
        </div>
        {selectedIds.length > 0 ? (
          <div className="chat-workspace__bulk-actions">
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
        <Panel title="Como criar uma conversa" subtitle="Os atalhos principais para não ficar perdido.">
          <div className="inline-actions">
            <Link className="button button--primary" to="/prospecting">
              Fazer pesquisa de clientes
            </Link>
            <Link className="button button--ghost" to="/leads">
              Cadastrar lead manualmente
            </Link>
          </div>
        </Panel>
      ) : null}

      {data && data.items.length > 0 ? (
        <section
          className={`inbox-layout inbox-layout--chat ${
            !showInbox && !showControls
              ? 'inbox-layout--chat-only'
              : !showInbox
                ? 'inbox-layout--no-left'
                : !showControls
                  ? 'inbox-layout--no-right'
                  : ''
          }`}
        >
          {showInbox ? (
          <Panel
            title="Inbox"
            subtitle="Escolha a conversa na lista."
            action={
              <button className="button button--ghost" type="button" onClick={() => setShowInbox(false)}>
                <ChevronLeft size={16} />
                Fechar
              </button>
            }
          >
            <div className="chat-sidebar">
              {data.items.map((item) => (
                <button
                  key={item.id}
                  className={`thread-card thread-card--chat ${
                    selectedConversationId === item.id ? 'thread-card--active' : ''
                  } ${openingConversationId === item.id ? 'thread-card--loading' : ''}`}
                  onClick={() => handleSelectConversation(item.id)}
                >
                  <div className="thread-card__top">
                    <label className="checkbox-inline" onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(item.id)}
                        onChange={() => toggleSelection(item.id)}
                      />
                    </label>
                    <strong>{item.lead_name}</strong>
                    <small>{formatDateTime(item.last_message_at)}</small>
                  </div>
                  <div className="thread-card__meta">
                    <StatusPill tone={item.manual_mode ? 'warning' : 'info'}>
                      {item.manual_mode ? 'humano' : 'agente'}
                    </StatusPill>
                    <StatusPill tone={item.pending_human_review ? 'warning' : 'default'}>
                      {item.pending_human_review ? 'review' : item.stage}
                    </StatusPill>
                    {item.unread_count > 0 ? <span className="thread-card__badge">{item.unread_count}</span> : null}
                  </div>
                  <p>{item.latest_message_preview || 'Sem preview ainda.'}</p>
                  <span className="thread-card__action">
                    {openingConversationId === item.id ? 'Abrindo...' : 'Abrir conversa'}
                  </span>
                </button>
              ))}
            </div>
          </Panel>
          ) : null}

          <Panel
            title="Conversa atual"
            subtitle="Leia, assuma e responda daqui."
            action={
              <div className="inline-actions">
                {!showInbox ? (
                  <button className="button button--ghost" type="button" onClick={() => setShowInbox(true)}>
                    <ChevronRight size={16} />
                    Inbox
                  </button>
                ) : null}
                {!showControls ? (
                  <button className="button button--ghost" type="button" onClick={() => setShowControls(true)}>
                    <SlidersHorizontal size={16} />
                    Controles
                  </button>
                ) : null}
              </div>
            }
          >
            {threadLoading ? (
              <EmptyState title="Abrindo conversa" description="Carregando histórico, lead e controles." />
            ) : !conversation || !lead ? (
              <EmptyState title="Selecione uma conversa" description="Ao clicar na thread, o chat completo aparece aqui." />
            ) : (
              <div className="chat-thread">
                <header className="chat-thread__header">
                  <div>
                    <strong>{lead.business_name}</strong>
                    <p>{lead.niche} em {lead.city}</p>
                  </div>
                  <div className="chat-thread__badges">
                    <StatusPill tone={conversation.manual_mode ? 'warning' : 'info'}>
                      {conversation.manual_mode ? 'Controle humano' : 'Controle do agente'}
                    </StatusPill>
                    <StatusPill tone={conversation.automation_paused ? 'warning' : 'success'}>
                      {conversation.automation_paused ? 'Automação pausada' : 'Automação ativa'}
                    </StatusPill>
                    <StatusPill tone={conversation.pending_human_review ? 'warning' : 'default'}>
                      {conversation.pending_human_review ? 'Review pendente' : conversation.stage}
                    </StatusPill>
                  </div>
                </header>

                <div className="chat-thread__toolbar">
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

                <article className="chat-summary">
                  <strong>Resumo operacional</strong>
                  <p>{conversation.summary || conversation.pending_review_reason || 'Ainda sem resumo automático desta conversa.'}</p>
                </article>

                {pendingAutoReplyTask ? (
                  <article className="chat-queue-card">
                    <strong>Resposta automática agendada</strong>
                    <p>
                      O agente já viu a mensagem e vai responder em{' '}
                      <strong>
                        {formatCountdown(secondsUntil(pendingAutoReplyTask.next_run_at || undefined, nowMs)) || '00:00'}
                      </strong>
                      .
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
                          <strong>
                            {formatCountdown(secondsUntil(scheduledAt(pendingQueuedOutboundTasks[0]), nowMs)) || '00:00'}
                          </strong>
                          {' '}e posição global{' '}
                          <strong>#{queuePositionByTaskId.get(pendingQueuedOutboundTasks[0].id) || 1}</strong>.
                        </>
                      ) : (
                        <>
                          Há mensagem em fila nesta conversa. Próxima saída prevista em{' '}
                          <strong>
                            {formatCountdown(secondsUntil(nextQueuedMessageFallback?.scheduledFor, nowMs)) || '00:00'}
                          </strong>
                          .
                        </>
                      )}
                    </p>
                  </article>
                ) : null}

                <div className="timeline timeline--workspace timeline--chat">
                  <div className="timeline--chat-content">
                  {visibleMessages.map((message) => {
                    const delivery = getMessageDeliveryDetails(message, nowMs)
                    const matchingQueueTask = pendingQueuedOutboundTasks.find(
                      (task) => Number((task.payload?.message_id as number | string | undefined) || 0) === message.id,
                    )
                    return (
                      <article
                        key={message.id}
                        className={`message message--chat ${
                          message.direction === 'outbound' ? 'message--outbound' : 'message--inbound'
                        }`}
                      >
                        <div className="message__meta">
                          <strong>{authorLabel(message)}</strong>
                          <span>{formatDateTime(message.sent_at)}</span>
                        </div>
                        <p>{message.content}</p>
                        {message.direction === 'outbound' ? (
                          <div className="message-status">
                            <StatusPill tone={delivery.tone as 'default' | 'success' | 'warning' | 'danger' | 'info'}>
                              {delivery.label}
                            </StatusPill>
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
                </div>

                <form className="composer composer--chat" onSubmit={onSendManual}>
                  <textarea
                    className="field field--textarea"
                    placeholder="Digite uma mensagem"
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
          </Panel>

          {showControls ? (
          <Panel
            title="Controles da thread"
            subtitle="Ajuste automação e contexto sem sair do chat."
            action={
              <button className="button button--ghost" type="button" onClick={() => setShowControls(false)}>
                <ChevronRight size={16} />
                Fechar
              </button>
            }
          >
            {!conversation || !lead ? (
              <EmptyState title="Sem contexto carregado" description="Selecione uma thread para ver lead, controles e review." />
            ) : (
              <div className="chat-context">
                <section className="context-section">
                  <span className="context-section__title">Resumo rápido</span>
                  <div className="kv-list">
                    <div><span>Telefone</span><strong>{lead.phone_number || lead.whatsapp_number || '—'}</strong></div>
                    <div><span>Responsável</span><strong>{conversation.assignee || 'livre'}</strong></div>
                    <div><span>Última saída</span><strong>{formatDateTime(conversation.last_outbound_at)}</strong></div>
                    <div><span>Última entrada</span><strong>{formatDateTime(conversation.last_inbound_at)}</strong></div>
                    <div><span>Delay atual</span><strong>{conversation.reply_delay_seconds}s</strong></div>
                  </div>
                </section>

                <section className="context-section">
                  <span className="context-section__title">Automação</span>
                  <label className="toggle-card">
                    <input
                      type="checkbox"
                      checked={conversation.auto_reply_enabled}
                      onChange={(event) =>
                        setConversation((current) =>
                          current ? { ...current, auto_reply_enabled: event.target.checked } : current,
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
                        setConversation((current) =>
                          current ? { ...current, automation_paused: event.target.checked } : current,
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
                        setConversation((current) =>
                          current ? { ...current, pending_human_review: event.target.checked } : current,
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
                        setConversation((current) =>
                          current ? { ...current, reply_delay_seconds: Number(event.target.value) } : current,
                        )
                      }
                    />
                  </label>
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

                <button className="button button--primary" onClick={() => void onSaveSettings()}>
                  {actionLoading === 'save-settings' ? 'Salvando...' : 'Salvar controles da conversa'}
                </button>
              </div>
            )}
          </Panel>
          ) : null}
        </section>
      ) : null}
    </div>
  )
}
