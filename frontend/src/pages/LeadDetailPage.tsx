import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type { AgentPreview, LeadDetail } from '../lib/types'

export function LeadDetailPage() {
  const navigate = useNavigate()
  const { leadId } = useParams()
  const [lead, setLead] = useState<LeadDetail | null>(null)
  const [preview, setPreview] = useState<AgentPreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<string | null>(null)

  const load = async () => {
    if (!leadId) return
    setLoading(true)
    setError(null)
    try {
      setLead(await api.getLead(Number(leadId)))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [leadId])

  const onPreview = async () => {
    if (!leadId) return
    setActionLoading('preview')
    setError(null)
    try {
      setPreview(await api.previewAgent(Number(leadId)))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const onOutreach = async () => {
    if (!leadId) return
    if (!lead?.phone_number && !lead?.whatsapp_number) {
      setError('Esse lead ainda não tem telefone/WhatsApp para iniciar contato.')
      return
    }
    setActionLoading('outreach')
    setError(null)
    try {
      await api.startOutreach(Number(leadId))
      setActionNotice('Contato iniciado. Abrindo a conversa...')
      await load()
      navigate(`/conversations?leadId=${leadId}`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  const onReprocess = async () => {
    if (!leadId) return
    setActionLoading('reprocess')
    setError(null)
    try {
      await api.reprocessLead(Number(leadId))
      setActionNotice('Lead reprocessado com sucesso.')
      await load()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) return <EmptyState title="Carregando lead" description="Buscando pesquisa, conversa e tasks do lead." />
  if (error || !lead) return <EmptyState title="Nao consegui abrir o lead" description={error || 'Lead inexistente.'} />

  const latestConversation = lead.conversations[0]

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Lead detail</span>
          <h1>{lead.business_name}</h1>
          <p>{lead.niche} em {lead.city}</p>
        </div>
        <div className="inline-actions">
          <StatusPill tone={lead.status === 'qualified' ? 'success' : 'info'}>{lead.status}</StatusPill>
          <button className="button button--ghost" onClick={onPreview}>
            {actionLoading === 'preview' ? 'Gerando...' : 'Gerar preview'}
          </button>
          <button className="button button--ghost" onClick={onReprocess}>
            {actionLoading === 'reprocess' ? 'Reprocessando...' : 'Reprocessar'}
          </button>
          <button className="button button--primary" onClick={onOutreach}>
            {actionLoading === 'outreach' ? 'Iniciando...' : 'Dar start'}
          </button>
        </div>
      </section>

      {actionNotice ? (
        <article className="note-card note-card--success">
          <strong>Status</strong>
          <p>{actionNotice}</p>
        </article>
      ) : null}

      <div className="page-grid page-grid--detail">
        <Panel title="Contato e origem" subtitle="Tudo o que foi identificado sobre esse lead.">
          <div className="kv-list">
            <div><span>Telefone</span><strong>{lead.phone_number || '—'}</strong></div>
            <div><span>Instagram</span><strong>{lead.instagram_url || '—'}</strong></div>
            <div><span>Website</span><strong>{lead.website || '—'}</strong></div>
            <div><span>Origem</span><strong>{lead.source_platform || '—'}</strong></div>
          </div>
        </Panel>

        <Panel title="Pesquisa comercial" subtitle="Contexto objetivo coletado para personalizar a venda.">
          {lead.research_entries.length === 0 ? (
            <EmptyState title="Sem pesquisa salva" description="Use reprocessar para gerar um enriquecimento novo." />
          ) : (
            <div className="stack">
              {lead.research_entries.map((entry) => (
                <article key={entry.id} className="note-card">
                  <strong>{entry.summary || 'Sem resumo'}</strong>
                  <p>Pain points: {(entry.pain_points || []).join(', ') || '—'}</p>
                  <p>Oportunidades: {(entry.opportunities || []).join(', ') || '—'}</p>
                  <p>Evidencias: {(entry.evidence || []).join(', ') || '—'}</p>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <div className="page-grid page-grid--detail">
        <Panel title="Conversa" subtitle="Timeline da thread principal.">
          {!latestConversation ? (
            <EmptyState title="Nenhuma conversa ainda" description="Use Dar start para gerar a primeira abordagem." />
          ) : (
            <div className="stack">
              <div className="kv-list">
                <div><span>Stage</span><strong>{latestConversation.stage}</strong></div>
                <div><span>Temperatura</span><strong>{latestConversation.temperature}</strong></div>
                <div><span>Ultima interacao</span><strong>{formatDateTime(latestConversation.last_message_at)}</strong></div>
              </div>
              <div className="timeline">
                {latestConversation.messages.map((message) => (
                  <article key={message.id} className={`message message--${message.direction}`}>
                    <div className="message__meta">
                      <strong>{message.direction}</strong>
                      <span>{formatDateTime(message.sent_at)}</span>
                    </div>
                    <p>{message.content}</p>
                    <small>Status: {message.status || '—'}</small>
                  </article>
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Fila e qualificacao" subtitle="Tasks, handoff e preview do agente.">
          <div className="stack">
            {lead.qualified_lead ? (
              <article className="note-card note-card--success">
                <strong>Lead qualificado</strong>
                <p>{lead.qualified_lead.qualification_reason}</p>
                <p>Score: {lead.qualified_lead.score}</p>
                <p>Resumo: {lead.qualified_lead.handoff_summary || '—'}</p>
              </article>
            ) : (
              <EmptyState title="Ainda nao qualificado" description="A qualificacao pode vir do agente ou do operador." />
            )}

            {preview ? (
              <article className="note-card">
                <strong>Preview do agente</strong>
                <p>{preview.preview_message}</p>
                <small>{preview.runtime_instruction}</small>
              </article>
            ) : null}

            <div className="stack">
              {lead.tasks.map((task) => (
                <article key={task.id} className="note-card">
                  <strong>{task.task_type}</strong>
                  <p>Status: {task.status}</p>
                  <p>Proxima execucao: {formatDateTime(task.next_run_at)}</p>
                </article>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </div>
  )
}
