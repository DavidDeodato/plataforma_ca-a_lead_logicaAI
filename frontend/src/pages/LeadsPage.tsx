import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/format'
import type { LeadListResponse } from '../lib/types'

export function LeadsPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<LeadListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionNotice, setActionNotice] = useState<string | null>(null)
  const [actionLoadingKey, setActionLoadingKey] = useState<string | null>(null)
  const [selectedLeadIds, setSelectedLeadIds] = useState<number[]>([])
  const [manualLeadForm, setManualLeadForm] = useState({
    business_name: '',
    niche: '',
    city: 'Vitoria, ES',
    phone_number: '',
    whatsapp_number: '',
    website: '',
    instagram_url: '',
    notes: '',
    start_now: true,
  })
  const [filters, setFilters] = useState({
    q: '',
    status: '',
    niche: '',
    city: '',
    sort_by: 'priority',
    sort_direction: 'desc',
  })

  const params = useMemo(() => {
    const value = new URLSearchParams({ page: '1', page_size: '20' })
    Object.entries(filters).forEach(([key, current]) => {
      if (current) value.set(key, current)
    })
    return value
  }, [filters])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api.searchLeads(params))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [params])

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void load()
  }

  const toggleLead = (leadId: number) => {
    setSelectedLeadIds((current) =>
      current.includes(leadId) ? current.filter((id) => id !== leadId) : [...current, leadId],
    )
  }

  const hasContactInfo = (lead: { phone_number?: string | null; whatsapp_number?: string | null }) =>
    Boolean(lead.phone_number || lead.whatsapp_number)

  const runBulk = async (action: string) => {
    if (selectedLeadIds.length === 0) return
    setActionLoadingKey(`bulk:${action}`)
    setActionError(null)
    setActionNotice(null)
    try {
      const validLeadIds =
        action === 'start_outreach'
          ? (data?.items.filter((lead) => selectedLeadIds.includes(lead.id) && hasContactInfo(lead)).map((lead) => lead.id) ?? [])
          : selectedLeadIds
      if (action === 'start_outreach' && validLeadIds.length === 0) {
        setActionError('Nenhum lead selecionado tem telefone/WhatsApp para iniciar contato.')
        return
      }
      await api.bulkLeadAction({
        lead_ids: validLeadIds,
        action,
        status: action === 'set_status' ? 'nurturing' : undefined,
      })
      if (action === 'start_outreach') {
        const skipped = selectedLeadIds.length - validLeadIds.length
        setActionNotice(
          skipped > 0
            ? `Contato iniciado para os leads válidos. ${skipped} lead(s) sem WhatsApp foram ignorados.`
            : 'Contato em lote iniciado com sucesso.',
        )
      } else {
        setActionNotice('Ação em lote concluída.')
      }
      await load()
    } catch (err) {
      setActionError((err as Error).message)
    } finally {
      setActionLoadingKey(null)
    }
  }

  const startSingleOutreach = async (leadId: number) => {
    const lead = data?.items.find((item) => item.id === leadId)
    if (!lead) return
    if (!hasContactInfo(lead)) {
      setActionNotice(null)
      setActionError('Esse lead ainda não tem telefone/WhatsApp. Salve o lead e complemente o contato antes de iniciar.')
      return
    }
    setActionLoadingKey(`start:${leadId}`)
    setActionError(null)
    setActionNotice(null)
    try {
      await api.startOutreach(leadId)
      setActionNotice(`Contato iniciado para ${lead.business_name}. Abrindo a conversa...`)
      await load()
      navigate(`/conversations?leadId=${leadId}`)
    } catch (err) {
      setActionError((err as Error).message)
    } finally {
      setActionLoadingKey(null)
    }
  }

  const createManualLead = async (event: FormEvent) => {
    event.preventDefault()
    setActionLoadingKey('create-manual')
    setActionError(null)
    setActionNotice(null)
    try {
      const created = await api.createLead({
        business_name: manualLeadForm.business_name,
        niche: manualLeadForm.niche,
        city: manualLeadForm.city,
        phone_number: manualLeadForm.phone_number || null,
        whatsapp_number: manualLeadForm.whatsapp_number || manualLeadForm.phone_number || null,
        website: manualLeadForm.website || null,
        instagram_url: manualLeadForm.instagram_url || null,
        notes: manualLeadForm.notes || null,
        status: 'new',
      })
      const createdHasContact = Boolean(manualLeadForm.phone_number || manualLeadForm.whatsapp_number)
      if (manualLeadForm.start_now && createdHasContact) {
        await api.startOutreach(created.id)
        setActionNotice(`Lead ${created.business_name} criado e contato iniciado. Abrindo a conversa...`)
        navigate(`/conversations?leadId=${created.id}`)
        return
      }
      if (manualLeadForm.start_now && !createdHasContact) {
        setActionNotice(`Lead ${created.business_name} salvo, mas não foi iniciado porque falta telefone/WhatsApp.`)
      } else {
        setActionNotice(`Lead ${created.business_name} cadastrado com sucesso.`)
      }
      setManualLeadForm({
        business_name: '',
        niche: '',
        city: 'Vitoria, ES',
        phone_number: '',
        whatsapp_number: '',
        website: '',
        instagram_url: '',
        notes: '',
        start_now: true,
      })
      setFilters((current) => ({ ...current, q: created.business_name }))
      await load()
    } catch (err) {
      setActionError((err as Error).message)
    } finally {
      setActionLoadingKey(null)
    }
  }

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Base comercial</span>
          <h1>Leads e contexto de venda</h1>
          <p>Filtre, revise, requalifique e abra o detalhe completo sem sair do fluxo.</p>
        </div>
      </section>

      <Panel title="Filtros" subtitle="Use poucos campos para chegar rapido no lote certo.">
        <form className="filters-grid" onSubmit={onSubmit}>
          <input
            className="field"
            placeholder="Buscar por nome, telefone ou link"
            value={filters.q}
            onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
          />
          <input
            className="field"
            placeholder="Status"
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
          />
          <input
            className="field"
            placeholder="Nicho"
            value={filters.niche}
            onChange={(event) => setFilters((current) => ({ ...current, niche: event.target.value }))}
          />
          <input
            className="field"
            placeholder="Cidade"
            value={filters.city}
            onChange={(event) => setFilters((current) => ({ ...current, city: event.target.value }))}
          />
          <select
            className="field"
            value={filters.sort_by}
            onChange={(event) => setFilters((current) => ({ ...current, sort_by: event.target.value }))}
          >
            <option value="priority">Prioridade operacional</option>
            <option value="fit_score">Fit score</option>
            <option value="updated_at">Atualizados por último</option>
            <option value="created_at">Criados por último</option>
          </select>
          <select
            className="field"
            value={filters.sort_direction}
            onChange={(event) => setFilters((current) => ({ ...current, sort_direction: event.target.value }))}
          >
            <option value="desc">Maior primeiro</option>
            <option value="asc">Menor primeiro</option>
          </select>
          <button className="button button--primary" type="submit">
            Aplicar
          </button>
        </form>
        {selectedLeadIds.length > 0 ? (
          <div className="inline-actions">
            <button className="button button--ghost" onClick={() => void runBulk('start_outreach')}>
              
              {actionLoadingKey === 'bulk:start_outreach' ? 'Iniciando lote...' : 'Iniciar contato em lote'}
            </button>
            <button className="button button--ghost" onClick={() => void runBulk('do_not_contact')}>
              {actionLoadingKey === 'bulk:do_not_contact' ? 'Salvando...' : 'Marcar como não contatar'}
            </button>
            <button className="button button--ghost" onClick={() => void runBulk('set_status')}>
              {actionLoadingKey === 'bulk:set_status' ? 'Salvando...' : 'Marcar nurturing'}
            </button>
          </div>
        ) : null}
        {actionError ? <article className="note-card note-card--danger"><strong>Falha na ação</strong><p>{actionError}</p></article> : null}
        {actionNotice ? <article className="note-card note-card--success"><strong>Status</strong><p>{actionNotice}</p></article> : null}
      </Panel>

      <Panel title="Cadastrar lead manualmente" subtitle="Quando voce ja tem o contato e quer colocar o agente para trabalhar sem depender da pesquisa.">
        <form className="form-grid" onSubmit={createManualLead}>
          <label>
            <span>Nome do lead/negócio</span>
            <input className="field" value={manualLeadForm.business_name} onChange={(event) => setManualLeadForm((current) => ({ ...current, business_name: event.target.value }))} />
          </label>
          <label>
            <span>Nicho</span>
            <input className="field" value={manualLeadForm.niche} onChange={(event) => setManualLeadForm((current) => ({ ...current, niche: event.target.value }))} />
          </label>
          <label>
            <span>Cidade</span>
            <input className="field" value={manualLeadForm.city} onChange={(event) => setManualLeadForm((current) => ({ ...current, city: event.target.value }))} />
          </label>
          <label>
            <span>Telefone</span>
            <input className="field" value={manualLeadForm.phone_number} onChange={(event) => setManualLeadForm((current) => ({ ...current, phone_number: event.target.value }))} />
          </label>
          <label>
            <span>WhatsApp</span>
            <input className="field" value={manualLeadForm.whatsapp_number} onChange={(event) => setManualLeadForm((current) => ({ ...current, whatsapp_number: event.target.value }))} />
          </label>
          <label>
            <span>Site</span>
            <input className="field" value={manualLeadForm.website} onChange={(event) => setManualLeadForm((current) => ({ ...current, website: event.target.value }))} />
          </label>
          <label>
            <span>Instagram</span>
            <input className="field" value={manualLeadForm.instagram_url} onChange={(event) => setManualLeadForm((current) => ({ ...current, instagram_url: event.target.value }))} />
          </label>
          <label className="form-grid__full">
            <span>Contexto para o agente</span>
            <textarea className="field field--textarea" value={manualLeadForm.notes} onChange={(event) => setManualLeadForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Explique quem e o lead, o que voce ja sabe, qual abordagem faz sentido, objeções, contexto da oferta..." />
          </label>
          <label className="toggle-inline form-grid__full">
            <input type="checkbox" checked={manualLeadForm.start_now} onChange={(event) => setManualLeadForm((current) => ({ ...current, start_now: event.target.checked }))} />
            Criar e já iniciar contato
          </label>
          <div className="inline-actions form-grid__full">
            <button className="button button--primary" type="submit" disabled={actionLoadingKey === 'create-manual'}>
              {actionLoadingKey === 'create-manual'
                ? manualLeadForm.start_now
                  ? 'Criando e iniciando...'
                  : 'Criando lead...'
                : manualLeadForm.start_now
                  ? 'Cadastrar e iniciar contato'
                  : 'Cadastrar lead'}
            </button>
          </div>
        </form>
      </Panel>

      <Panel title="Lista de leads" subtitle="Visão operacional com seleção em lote, preview e entrada no inbox.">
        {!loading && !error && data && data.items.length > 0 ? (
          <div className="stats-grid stats-grid--compact">
            <article className="stat-card">
              <span className="stat-card__label">Fit médio da página</span>
              <strong className="stat-card__value">
                {(data.items.reduce((total, lead) => total + (lead.fit_score || 0), 0) / data.items.length).toFixed(1)}
              </strong>
              <span className="stat-card__hint">qualidade do lote visível</span>
            </article>
            <article className="stat-card">
              <span className="stat-card__label">Com contato válido</span>
              <strong className="stat-card__value">
                {data.items.filter((lead) => hasContactInfo(lead)).length}/{data.items.length}
              </strong>
              <span className="stat-card__hint">prontos para outreach</span>
            </article>
            <article className="stat-card">
              <span className="stat-card__label">Oportunidades</span>
              <strong className="stat-card__value">
                {data.items.filter((lead) => lead.qualified_opportunity_at).length}
              </strong>
              <span className="stat-card__hint">já avançaram no funil</span>
            </article>
          </div>
        ) : null}
        {loading ? <EmptyState title="Carregando leads" description="Buscando a base do banco e os filtros atuais." /> : null}
        {error ? <EmptyState title="Erro ao carregar leads" description={error} /> : null}
        {!loading && !error && data && data.items.length === 0 ? (
          <EmptyState title="Nenhum lead encontrado" description="Ajuste os filtros ou rode uma nova prospeccao." />
        ) : null}
        {!loading && !error && data && data.items.length > 0 ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th></th>
                  <th>Negocio</th>
                  <th>Status</th>
                  <th>Prioridade</th>
                  <th>Próxima ação</th>
                  <th>Funil</th>
                  <th>Fit</th>
                  <th>Nicho</th>
                  <th>Cidade</th>
                  <th>Telefone</th>
                  <th>Atualizado</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((lead) => (
                  <tr key={lead.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedLeadIds.includes(lead.id)}
                        onChange={() => toggleLead(lead.id)}
                      />
                    </td>
                    <td>
                      <div className="table__primary">
                        <strong>{lead.business_name}</strong>
                        <span>{lead.instagram_url || lead.website || 'sem link principal'}</span>
                      </div>
                    </td>
                    <td>
                      <StatusPill tone={lead.status === 'qualified' ? 'success' : 'info'}>{lead.status}</StatusPill>
                    </td>
                    <td>
                      <div className="table__primary">
                        <strong>{lead.priority_score ?? '—'}</strong>
                        <span>{lead.priority_label || 'sem prioridade'}</span>
                      </div>
                    </td>
                    <td>
                      <div className="table__primary">
                        <strong>{lead.recommended_action?.label || '—'}</strong>
                        <span>{lead.recommended_action?.description || 'Sem recomendação ainda.'}</span>
                      </div>
                    </td>
                    <td>
                      <div className="table__primary">
                        <strong>{lead.funnel_stage}</strong>
                        <span>{lead.intent_status}</span>
                      </div>
                    </td>
                    <td>
                      <div className="table__primary">
                        <strong>{lead.fit_score ?? '—'}</strong>
                        <span>{lead.fit_label || 'sem score'}</span>
                      </div>
                    </td>
                    <td>{lead.niche}</td>
                    <td>{lead.city}</td>
                    <td>{lead.phone_number || '—'}</td>
                    <td>{formatDateTime(lead.updated_at)}</td>
                    <td>
                      <div className="inline-actions">
                        <button
                          className="button button--ghost"
                          disabled={!hasContactInfo(lead) || actionLoadingKey === `start:${lead.id}`}
                          onClick={() => void startSingleOutreach(lead.id)}
                        >
                          {!hasContactInfo(lead)
                            ? 'Sem WhatsApp'
                            : actionLoadingKey === `start:${lead.id}`
                              ? 'Iniciando...'
                              : 'Start'}
                        </button>
                        <Link className="button button--ghost" to={`/conversations?leadId=${lead.id}`}>
                          Ver conversa
                        </Link>
                        <Link className="button button--ghost" to={`/leads/${lead.id}`}>
                          Abrir
                        </Link>
                      </div>
                    </td>
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
