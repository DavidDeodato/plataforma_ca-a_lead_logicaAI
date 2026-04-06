import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatCard } from '../components/StatCard'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatRelativeBoolean } from '../lib/format'
import type { DashboardSummary, Readiness } from '../lib/types'

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [readiness, setReadiness] = useState<Readiness | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.getDashboardSummary(), api.getReadiness()])
      .then(([dashboard, readinessData]) => {
        setSummary(dashboard)
        setReadiness(readinessData)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  if (error) {
    return <EmptyState title="Nao consegui carregar o cockpit" description={error} />
  }

  if (!summary || !readiness) {
    return <EmptyState title="Carregando cockpit" description="Buscando status, segurancas e metricas do sistema." />
  }

  return (
    <div className="page">
      <section className="hero-banner">
        <div>
          <span className="eyebrow">Controle operacional</span>
          <h1>Painel central da automação comercial</h1>
          <p>
            Aqui voce ve rapido se o sistema esta pronto, em teste ou em modo ao vivo. A ideia e nunca te deixar
            adivinhar o que esta acontecendo.
          </p>
        </div>
        <div className="hero-banner__status">
          <StatusPill tone={readiness.ready_for_local_tests ? 'success' : 'warning'}>
            Local: {readiness.ready_for_local_tests ? 'pronto' : 'faltando ajuste'}
          </StatusPill>
          <StatusPill tone={readiness.ready_for_live_outreach ? 'success' : 'info'}>
            Ao vivo: {readiness.ready_for_live_outreach ? 'habilitado' : 'bloqueado'}
          </StatusPill>
        </div>
      </section>

      <div className="stats-grid">
        <StatCard label="Leads totais" value={summary.totals.leads} hint="base consolidada" />
        <StatCard label="Qualificados" value={summary.totals.qualified} hint="prontos para handoff" />
        <StatCard label="Conversas" value={summary.totals.conversations} hint="threads no banco" />
        <StatCard label="Tasks pendentes" value={summary.totals.tasks_pending} hint="fila operacional" />
      </div>

      <div className="page-grid">
        <Panel title="Modo do sistema" subtitle="Leitura simples do estado operacional atual.">
          <div className="kv-list">
            <div>
              <span>Outbound</span>
              <strong>{formatRelativeBoolean(summary.safe_mode.outbound_enabled)}</strong>
            </div>
            <div>
              <span>Auto reply</span>
              <strong>{formatRelativeBoolean(summary.safe_mode.auto_reply_enabled)}</strong>
            </div>
            <div>
              <span>Nicho padrao</span>
              <strong>{summary.runtime.default_niche}</strong>
            </div>
            <div>
              <span>Cidade padrao</span>
              <strong>{summary.runtime.default_city}</strong>
            </div>
          </div>
        </Panel>

        <Panel title="Oferta configurada" subtitle="O que o agente esta tentando vender agora.">
          <div className="stack">
            <div className="offer-card">
              <strong>{summary.runtime.offer_name}</strong>
              <p>{summary.runtime.offer_summary}</p>
            </div>
            <div className="kv-list">
              <div>
                <span>Objetivo</span>
                <strong>{summary.runtime.offer_goal}</strong>
              </div>
              <div>
                <span>Tom</span>
                <strong>{summary.runtime.sales_tone}</strong>
              </div>
              <div>
                <span>CTA</span>
                <strong>{summary.runtime.cta_style}</strong>
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Ações rápidas" subtitle="Os três caminhos principais para operar sem ficar caçando botão.">
        <div className="inline-actions">
          <Link className="button button--primary" to="/prospecting">
            Fazer pesquisa de clientes
          </Link>
          <Link className="button button--ghost" to="/leads">
            Cadastrar lead manualmente
          </Link>
          <Link className="button button--ghost" to="/conversations">
            Abrir conversas
          </Link>
        </div>
      </Panel>

      <div className="page-grid">
        <Panel title="Atividade recente" subtitle="Onde o pipeline esta andando agora.">
          <div className="stats-grid stats-grid--compact">
            <StatCard label="Novos" value={summary.recent_activity.new_leads} />
            <StatCard label="Contactados" value={summary.recent_activity.contacted} />
            <StatCard label="Responderam" value={summary.recent_activity.replied} />
            <StatCard label="Qualificados" value={summary.recent_activity.qualified} />
          </div>
        </Panel>

        <Panel title="Checklist de prontidao" subtitle="Leitura binaria do que falta para operar sem duvida.">
          <ul className="check-list">
            {readiness.missing.length === 0 ? <li>Credenciais principais presentes.</li> : null}
            {readiness.missing.map((item) => (
              <li key={item}>Falta credencial: {item}</li>
            ))}
            {readiness.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  )
}
