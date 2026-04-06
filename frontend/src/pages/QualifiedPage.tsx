import { useEffect, useState } from 'react'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type { QualifiedLead } from '../lib/types'

export function QualifiedPage() {
  const [items, setItems] = useState<QualifiedLead[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .listQualifiedLeads()
      .then((payload) => setItems(payload))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Handoff</span>
          <h1>Leads qualificados</h1>
          <p>Fila pronta para voce entrar manualmente no fechamento comercial.</p>
        </div>
      </section>

      <Panel title="Fila de handoff" subtitle="Somente leads que merecem atencao humana agora.">
        {loading ? <EmptyState title="Carregando qualificados" description="Buscando fila pronta para handoff." /> : null}
        {error ? <EmptyState title="Erro ao carregar qualificados" description={error} /> : null}
        {!loading && !error && items.length === 0 ? (
          <EmptyState title="Nenhum qualificado ainda" description="Quando o agente ou operador qualificar um lead, ele aparece aqui." />
        ) : null}
        {!loading && !error && items.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Lead</th>
                  <th>Score</th>
                  <th>Razao</th>
                  <th>Resumo</th>
                  <th>Quando</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.lead_id}</td>
                    <td>{item.score}</td>
                    <td>{item.qualification_reason}</td>
                    <td>{item.handoff_summary || '—'}</td>
                    <td>{formatDateTime(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Panel>
    </div>
  )
}
