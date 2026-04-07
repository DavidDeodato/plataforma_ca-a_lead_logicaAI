import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatCard } from '../components/StatCard'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type { ConversationListResponse, DashboardSummary, TaskListResponse } from '../lib/types'

export function AutomationPage() {
  const [data, setData] = useState<TaskListResponse | null>(null)
  const [reviewQueue, setReviewQueue] = useState<ConversationListResponse | null>(null)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [nowMs, setNowMs] = useState(() => Date.now())

  const load = () => {
    Promise.all([
      api.listTasks(new URLSearchParams({ page: '1', page_size: '30' })),
      api.listConversations(new URLSearchParams({ page: '1', page_size: '20', pending_review_only: 'true' })),
      api.getDashboardSummary(),
    ])
      .then(([tasks, conversations, dashboardSummary]) => {
        setData(tasks)
        setReviewQueue(conversations)
        setSummary(dashboardSummary)
      })
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    load()
    const interval = window.setInterval(load, 5000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => setNowMs(Date.now()), 5000)
    return () => window.clearInterval(interval)
  }, [])

  const taskBreakdown = useMemo(() => {
    const items = data?.items || []
    return {
      queuedOutbound: items.filter((task) => task.task_type === 'queued_outbound' && task.status === 'pending').length,
      delayedAutoReply: items.filter((task) => task.task_type === 'delayed_auto_reply' && task.status === 'pending').length,
      followUps: items.filter((task) => task.task_type === 'follow_up' && task.status === 'pending').length,
      overdue: items.filter((task) => task.status === 'pending' && task.next_run_at && new Date(task.next_run_at).getTime() < nowMs).length,
      reviewRequired: items.filter((task) => task.review_required).length,
    }
  }, [data, nowMs])

  const runNow = async (taskId: number) => {
    await api.runTaskNow(taskId)
    load()
  }

  const cancel = async (taskId: number) => {
    await api.cancelTask(taskId)
    load()
  }

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Fila de execucao</span>
          <h1>Automação, follow-ups e controle manual</h1>
          <p>Aqui voce ve o que esta agendado, antecipa task e cancela o que nao deve rodar.</p>
        </div>
      </section>

      <Panel title="Scorecard operacional" subtitle="Fila, SLA e falha para separar gargalo técnico de gargalo comercial.">
        {!summary ? (
          <EmptyState title="Carregando métricas operacionais" description="Buscando scorecard de operação." />
        ) : (
          <div className="stats-grid stats-grid--compact">
            <StatCard label="Fila ativa" value={summary.operations.queued_tasks} hint="tasks pendentes críticas" />
            <StatCard label="Falhas outbound" value={summary.operations.outbound_failures} hint="envios rejeitados/timeout" />
            <StatCard label="Taxa de falha" value={`${summary.operations.send_failure_rate}%`} hint="saúde do provedor" />
            <StatCard
              label="Tempo 1º outreach"
              value={`${summary.operations.time_to_first_outreach_minutes} min`}
              hint="captura até primeiro contato"
            />
            <StatCard label="Queued outbound" value={taskBreakdown.queuedOutbound} hint="mensagens esperando janela" />
            <StatCard label="Auto reply pendente" value={taskBreakdown.delayedAutoReply} hint="leads aguardando resposta" />
            <StatCard label="Follow-ups" value={taskBreakdown.followUps} hint="reativações programadas" />
            <StatCard label="Tasks atrasadas" value={taskBreakdown.overdue} hint="já passaram do horário" />
          </div>
        )}
      </Panel>

      <Panel title="Tasks do sistema" subtitle="A fila operacional principal do agente.">
        {error ? <EmptyState title="Erro ao carregar tasks" description={error} /> : null}
        {!error && !data ? <EmptyState title="Carregando tasks" description="Buscando a fila no backend." /> : null}
        {data && data.items.length === 0 ? (
          <EmptyState title="Sem tasks" description="As tasks aparecem aqui quando uma conversa gera follow-up." />
        ) : null}
        {data && data.items.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Lead</th>
                  <th>Status</th>
                  <th>Tentativas</th>
                  <th>Proxima execucao</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((task) => (
                  <tr key={task.id}>
                    <td>{task.task_type}</td>
                    <td>{task.lead_id}</td>
                    <td>
                      <StatusPill tone={task.status === 'pending' ? 'warning' : 'default'}>{task.status}</StatusPill>
                    </td>
                    <td>{task.current_attempt}</td>
                    <td>{formatDateTime(task.next_run_at)}</td>
                    <td>
                      <div className="inline-actions">
                        <button className="button button--ghost" onClick={() => runNow(task.id)}>
                          Rodar agora
                        </button>
                        <button className="button button--ghost" onClick={() => cancel(task.id)}>
                          Cancelar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>

      <Panel title="Fila de revisão humana" subtitle="Conversas onde o agente deixou rascunho para aprovação.">
        {error ? null : !reviewQueue ? (
          <EmptyState title="Carregando fila de revisão" description="Buscando conversas pendentes." />
        ) : reviewQueue.items.length === 0 ? (
          <EmptyState title="Sem revisão pendente" description="Quando uma conversa exigir aprovação humana, ela aparece aqui." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Preview</th>
                  <th>Modo</th>
                  <th>Última atividade</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {reviewQueue.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.lead_name}</td>
                    <td>{item.latest_message_preview || '—'}</td>
                    <td>
                      <StatusPill tone={item.manual_mode ? 'warning' : 'info'}>
                        {item.manual_mode ? 'humano' : 'bot'}
                      </StatusPill>
                    </td>
                    <td>{formatDateTime(item.last_message_at)}</td>
                    <td>
                      <Link className="button button--ghost" to="/conversations">
                        Abrir inbox
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title="Leitura rápida da fila" subtitle="Resumo executivo para saber se deve mexer em operação ou em copy/agente.">
        <div className="stats-grid stats-grid--compact">
          <StatCard label="Threads em review" value={reviewQueue?.items.length || 0} hint="demandam olho humano" />
          <StatCard label="Tasks review_required" value={taskBreakdown.reviewRequired} hint="pedem intervenção" />
          <StatCard label="Mensagens em janela" value={taskBreakdown.queuedOutbound} hint="limitadas pelo provedor" />
          <StatCard label="SLA em risco" value={taskBreakdown.overdue + taskBreakdown.delayedAutoReply} hint="atrasadas ou aguardando" />
        </div>
      </Panel>
    </div>
  )
}
