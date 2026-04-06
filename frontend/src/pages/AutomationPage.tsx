import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type { ConversationListResponse, TaskListResponse } from '../lib/types'

export function AutomationPage() {
  const [data, setData] = useState<TaskListResponse | null>(null)
  const [reviewQueue, setReviewQueue] = useState<ConversationListResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    Promise.all([
      api.listTasks(new URLSearchParams({ page: '1', page_size: '30' })),
      api.listConversations(new URLSearchParams({ page: '1', page_size: '20', pending_review_only: 'true' })),
    ])
      .then(([tasks, conversations]) => {
        setData(tasks)
        setReviewQueue(conversations)
      })
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    load()
  }, [])

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
    </div>
  )
}
