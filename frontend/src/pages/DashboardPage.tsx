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
        <StatCard
          label="KPI norte"
          value={`${summary.conversion.meetings_qualified_per_100_contacted}%`}
          hint="reuniões qualificadas por 100 contactados"
        />
        <StatCard
          label="Reply rate"
          value={`${summary.conversion.reply_rate}%`}
          hint="responderam após primeiro contato"
        />
        <StatCard
          label="Fit médio"
          value={summary.conversion.lead_fit_score_avg}
          hint="qualidade média do topo do funil"
        />
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
            <StatCard label="Reuniões" value={summary.recent_activity.meetings_booked} />
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

      <div className="page-grid">
        <Panel title="Scorecard de conversão" subtitle="Os KPIs que separam conversão real de volume cego.">
          <div className="stats-grid stats-grid--compact">
            <StatCard label="Opps/100" value={`${summary.conversion.qualified_opportunities_per_100_contacted}%`} />
            <StatCard label="Resposta positiva" value={`${summary.conversion.positive_reply_rate}%`} />
            <StatCard label="Dor confirmada" value={`${summary.conversion.pain_confirmed_rate}%`} />
            <StatCard label="Aceite de reunião" value={`${summary.conversion.meeting_offer_acceptance_rate}%`} />
            <StatCard label="Contato válido" value={`${summary.conversion.valid_contact_rate}%`} />
            <StatCard label="Tempo 1º outreach" value={`${summary.operations.time_to_first_outreach_minutes} min`} />
          </div>
        </Panel>

        <Panel title="Gargalo operacional" subtitle="Aqui voce descobre se a trava e operação ou persuasão.">
          <div className="stats-grid stats-grid--compact">
            <StatCard label="Mensagens outbound" value={summary.operations.outbound_messages} />
            <StatCard label="Falhas de envio" value={summary.operations.outbound_failures} />
            <StatCard label="Taxa de falha" value={`${summary.operations.send_failure_rate}%`} />
            <StatCard label="Fila ativa" value={summary.operations.queued_tasks} />
          </div>
        </Panel>
      </div>

      <div className="page-grid">
        <Panel title="Funil oficial" subtitle="Leitura direta de onde os leads estão travando.">
          <div className="stats-grid stats-grid--compact">
            <StatCard label="Captured" value={summary.funnel.captured} />
            <StatCard label="Contacted" value={summary.funnel.contacted} />
            <StatCard label="Replied" value={summary.funnel.replied} />
            <StatCard label="Positive" value={summary.funnel.positive_reply} />
            <StatCard label="Pain" value={summary.funnel.pain_confirmed} />
            <StatCard label="Meeting" value={summary.funnel.meeting_booked} />
            <StatCard label="Opportunity" value={summary.funnel.qualified_opportunity} />
            <StatCard label="Lost" value={summary.funnel.closed_lost} />
          </div>
        </Panel>

        <Panel title="Campanhas" subtitle="Scorecard por campanha para decidir onde insistir ou cortar.">
          {summary.campaigns.length === 0 ? (
            <EmptyState title="Sem campanhas ainda" description="Crie campanhas para começar a separar KPI por estratégia." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Campanha</th>
                    <th>Status</th>
                    <th>Leads</th>
                    <th>Reply</th>
                    <th>Positiva</th>
                    <th>Reuniões</th>
                    <th>Opps</th>
                    <th>Fit médio</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.campaigns.map((campaign) => (
                    <tr key={campaign.id}>
                      <td>
                        <div className="table__primary">
                          <strong>{campaign.name}</strong>
                          <span>{campaign.is_active ? 'ativa agora' : 'não ativa'}</span>
                        </div>
                      </td>
                      <td>{campaign.status}</td>
                      <td>{campaign.leads}</td>
                      <td>{campaign.reply_rate}%</td>
                      <td>{campaign.positive_reply_rate}%</td>
                      <td>{campaign.meetings_booked}</td>
                      <td>{campaign.qualified_opportunities}</td>
                      <td>{campaign.fit_score_avg}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>

      <div className="page-grid">
        <Panel title="Categorias de prompt" subtitle="Teses comerciais que já têm histórico real de geração e conversão.">
          {summary.prompt_categories.length === 0 ? (
            <EmptyState title="Sem categorias rastreadas ainda" description="Use a biblioteca de prompts na prospecção para começar a medir teses." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Categoria</th>
                    <th>Leads</th>
                    <th>Reply</th>
                    <th>Positiva</th>
                    <th>Reuniões</th>
                    <th>Fechou</th>
                    <th>Fit médio</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.prompt_categories.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name}</td>
                      <td>{item.leads}</td>
                      <td>{item.reply_rate}%</td>
                      <td>{item.positive_reply_rate}%</td>
                      <td>{item.meetings_booked}</td>
                      <td>{item.closed_won}</td>
                      <td>{item.fit_score_avg}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="Prompts vencedores" subtitle="Comparativo das variações que já estão trazendo resultado de verdade.">
          {summary.prospecting_prompts.length === 0 ? (
            <EmptyState title="Sem prompts rastreados ainda" description="Assim que os prompts gerarem leads, o ranking aparece aqui." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Prompt</th>
                    <th>Categoria</th>
                    <th>Leads</th>
                    <th>Reply</th>
                    <th>Positiva</th>
                    <th>Reuniões</th>
                    <th>Fechou</th>
                    <th>Fit médio</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.prospecting_prompts.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name}</td>
                      <td>{item.category_name || 'sem categoria'}</td>
                      <td>{item.leads}</td>
                      <td>{item.reply_rate}%</td>
                      <td>{item.positive_reply_rate}%</td>
                      <td>{item.meetings_booked}</td>
                      <td>{item.closed_won}</td>
                      <td>{item.fit_score_avg}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
