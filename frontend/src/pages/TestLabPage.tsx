import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import type { Campaign, ProspectingBatch } from '../lib/types'

export function TestLabPage() {
  const [assistantMessages, setAssistantMessages] = useState([
    {
      role: 'assistant',
      content:
        'Me fala em linguagem natural quem voce quer achar e onde. Exemplo: quero achar barbearias em Vitoria, ES.',
    },
  ])
  const [assistantInput, setAssistantInput] = useState('')
  const [advisorState, setAdvisorState] = useState({
    niche: null as string | null,
    city: null as string | null,
    limit: 10,
    enrich: false,
  })
  const [advisorHints, setAdvisorHints] = useState<string[]>([])
  const [prospectingForm, setProspectingForm] = useState({
    niche: 'barbearia',
    city: 'Vitoria, ES',
    limit: 10,
    enrich: false,
    validate_phone_format: true,
    campaign_id: null as number | null,
  })
  const [batches, setBatches] = useState<ProspectingBatch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<ProspectingBatch | null>(null)
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<number[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [batchActionLoading, setBatchActionLoading] = useState<string | null>(null)
  const [batchActionNotice, setBatchActionNotice] = useState<string | null>(null)

  const loadBatches = async () => {
    try {
      const [batchList, campaignList] = await Promise.all([api.listProspectingBatches(), api.listCampaigns()])
      setBatches(batchList)
      setCampaigns(campaignList)
      if (selectedBatch) {
        const refreshedSelected = batchList.find((batch) => batch.id === selectedBatch.id)
        if (refreshedSelected) {
          setSelectedBatch(refreshedSelected)
        }
      } else if (batchList[0]) {
        setSelectedBatch(batchList[0])
        setSelectedCandidateIds(batchList[0].candidates.map((item) => item.id))
      }
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  useEffect(() => {
    void loadBatches()
  }, [])

  useEffect(() => {
    const interval = window.setInterval(() => {
      void loadBatches()
    }, 5000)
    return () => window.clearInterval(interval)
  }, [selectedBatch?.id])

  const askAdvisor = async (event: FormEvent) => {
    event.preventDefault()
    if (!assistantInput.trim()) return
    const userMessage = assistantInput.trim()
    setAssistantMessages((current) => [...current, { role: 'user', content: userMessage }])
    const response = await api.adviseProspecting({
      message: userMessage,
      current_state: advisorState,
    })
    setAssistantMessages((current) => [...current, { role: 'assistant', content: response.assistant_message }])
    setAdvisorState({
      niche: response.state.niche ?? null,
      city: response.state.city ?? null,
      limit: response.state.limit,
      enrich: response.state.enrich,
    })
    setAdvisorHints(response.supported_niches)
    setProspectingForm((current) => ({
      ...current,
      niche: response.state.niche || current.niche,
      city: response.state.city || current.city,
      limit: response.state.limit,
      enrich: response.state.enrich,
    }))
    setAssistantInput('')
  }

  const runProspecting = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    try {
      const response = await api.createProspectingBatch(prospectingForm)
      setSelectedBatch(response)
      setSelectedCandidateIds(response.candidates.map((item) => item.id))
      await loadBatches()
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const toggleCandidate = (candidateId: number) => {
    setSelectedCandidateIds((current) =>
      current.includes(candidateId) ? current.filter((id) => id !== candidateId) : [...current, candidateId],
    )
  }

  const applyBatchAction = async (action: string) => {
    if (!selectedBatch || selectedCandidateIds.length === 0) return
    setBatchActionLoading(action)
    setBatchActionNotice(null)
    setError(null)
    try {
      const updated = await api.applyProspectingBatch(selectedBatch.id, {
        candidate_ids: selectedCandidateIds,
        action,
      })
      setSelectedBatch(updated)
      await loadBatches()
      if (action === 'save_and_start_outreach') {
        const contacted = updated.candidates.filter((candidate) => candidate.status === 'contacted')
        const queued = updated.candidates.filter((candidate) => candidate.status === 'queued_contact')
        const failed = updated.candidates.filter((candidate) => candidate.status === 'contact_failed')
        const missingContact = updated.candidates.filter((candidate) => candidate.status === 'saved_missing_contact')
        if (contacted.length || queued.length) {
          setBatchActionNotice(
            `Lote processado: ${contacted.length} contato(s) iniciado(s), ${queued.length} na fila${
              failed.length ? `, ${failed.length} com falha` : ''
            }${missingContact.length ? ` e ${missingContact.length} salvo(s) sem WhatsApp.` : '.'} Abra as conversas para validar o status real do provedor.`,
          )
        } else if (missingContact.length) {
          setBatchActionNotice(
            `Os leads foram salvos, mas ${missingContact.length} selecionado(s) continuam sem telefone/WhatsApp para iniciar contato.`,
          )
        } else {
          setBatchActionNotice('Lote processado.')
        }
      } else {
        setBatchActionNotice('Lote atualizado com sucesso.')
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBatchActionLoading(null)
    }
  }

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Pesquisa de clientes</span>
          <h1>Montar busca, revisar resultados e decidir o próximo passo</h1>
          <p>Se voce estava procurando o botão de pesquisa, é aqui. Essa tela guia a busca e evita salvar ou contactar sem revisão.</p>
        </div>
      </section>

      <Panel title="Atalhos principais" subtitle="Os fluxos que voce mais vai usar no dia a dia.">
        <div className="inline-actions">
          <Link className="button button--ghost" to="/leads">
            Cadastrar lead manualmente
          </Link>
          <Link className="button button--ghost" to="/conversations">
            Ver conversas
          </Link>
          <Link className="button button--ghost" to="/settings">
            Ajustar campanha
          </Link>
        </div>
      </Panel>

      <div className="page-grid page-grid--detail">
        <Panel title="Assistente de pesquisa" subtitle="Converse do jeito natural e eu preencho a busca para voce.">
          <div className="timeline">
            {assistantMessages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={`message message--${message.role === 'user' ? 'outbound' : 'inbound'}`}>
                <div className="message__meta">
                  <strong>{message.role === 'user' ? 'Você' : 'Assistente de pesquisa'}</strong>
                </div>
                <p>{message.content}</p>
              </article>
            ))}
          </div>
          <form className="composer" onSubmit={askAdvisor}>
            <textarea
              className="field field--textarea"
              placeholder="Ex: quero achar barbearias em Vitoria, ES"
              value={assistantInput}
              onChange={(event) => setAssistantInput(event.target.value)}
            />
            <div className="inline-actions">
              <button className="button button--primary" type="submit">
                Perguntar ao assistente
              </button>
            </div>
          </form>
          {advisorHints.length > 0 ? (
            <div className="inline-actions">
              {advisorHints.slice(0, 6).map((hint) => (
                <button
                  key={hint}
                  className="button button--ghost"
                  type="button"
                  onClick={() => setAssistantInput(`quero achar ${hint} em Vitoria, ES`)}
                >
                  {hint}
                </button>
              ))}
            </div>
          ) : null}
          <div className="kv-list">
            <div><span>Nicho entendido</span><strong>{advisorState.niche || 'ainda não definido'}</strong></div>
            <div><span>Cidade entendida</span><strong>{advisorState.city || 'ainda não definida'}</strong></div>
            <div><span>Limite</span><strong>{advisorState.limit}</strong></div>
          </div>
        </Panel>

        <Panel title="Nova busca estruturada" subtitle="Cria um lote em staging para revisão humana.">
          <div className="search-mode-card">
            <div className="inline-actions">
              <button
                className={`button ${!prospectingForm.enrich ? 'button--primary' : 'button--ghost'}`}
                type="button"
                onClick={() => setProspectingForm((current) => ({ ...current, enrich: false }))}
              >
                Modo rápido
              </button>
              <button
                className={`button ${prospectingForm.enrich ? 'button--primary' : 'button--ghost'}`}
                type="button"
                onClick={() => setProspectingForm((current) => ({ ...current, enrich: true }))}
              >
                Modo detalhado
              </button>
            </div>
            <p>
              {!prospectingForm.enrich
                ? 'Modo rápido ativo: busca os leads e monta o lote quase instantaneamente.'
                : 'Modo detalhado ativo: tenta enriquecer cada resultado e pode demorar bastante com limite alto.'}
            </p>
          </div>
          <form className="stack" onSubmit={runProspecting}>
            <input className="field" value={prospectingForm.niche} onChange={(event) => setProspectingForm({ ...prospectingForm, niche: event.target.value })} />
            <input className="field" value={prospectingForm.city} onChange={(event) => setProspectingForm({ ...prospectingForm, city: event.target.value })} />
            <input className="field" type="number" value={prospectingForm.limit} onChange={(event) => setProspectingForm({ ...prospectingForm, limit: Number(event.target.value) })} />
            <select
              className="field"
              value={prospectingForm.campaign_id ?? ''}
              onChange={(event) =>
                setProspectingForm({
                  ...prospectingForm,
                  campaign_id: event.target.value ? Number(event.target.value) : null,
                })
              }
            >
              <option value="">Sem campanha</option>
              {campaigns.map((campaign) => (
                <option key={campaign.id} value={campaign.id}>
                  {campaign.name}
                </option>
              ))}
            </select>
            <label className="toggle-card">
              <input
                type="checkbox"
                checked={prospectingForm.validate_phone_format}
                onChange={(event) =>
                  setProspectingForm({ ...prospectingForm, validate_phone_format: event.target.checked })
                }
              />
              <div>
                <strong>Verificar formato do número</strong>
                <p>Se ligado, descarta telefone curto, longo ou inválido e tenta achar outro lead no lugar.</p>
              </div>
            </label>
            <label className="toggle-inline">
              <input type="checkbox" checked={prospectingForm.enrich} onChange={(event) => setProspectingForm({ ...prospectingForm, enrich: event.target.checked })} />
              Enriquecer resultado (mais lento, melhor para poucos leads)
            </label>
            {prospectingForm.limit > 5 && prospectingForm.enrich ? (
              <article className="note-card">
                <strong>Aviso de lentidão</strong>
                <p>Com enriquecimento ligado e limite acima de 5, a busca pode demorar bastante.</p>
              </article>
            ) : null}
            <button className="button button--primary" type="submit">
              {loading
                ? prospectingForm.enrich
                  ? 'Buscando e enriquecendo...'
                  : 'Buscando rapidamente...'
                : prospectingForm.enrich
                  ? 'Gerar lote detalhado'
                  : 'Gerar lote rápido'}
            </button>
          </form>
        </Panel>

        <Panel title="Lotes recentes" subtitle="Escolha um lote e trabalhe os candidatos antes da persistência.">
          {batches.length === 0 ? (
            <EmptyState title="Sem lotes ainda" description="Gere um lote novo para revisar candidatos." />
          ) : (
            <div className="thread-list">
              {batches.map((batch) => (
                <button
                  key={batch.id}
                  className={`thread-card ${selectedBatch?.id === batch.id ? 'thread-card--active' : ''}`}
                  onClick={() => {
                    setSelectedBatch(batch)
                    setSelectedCandidateIds(batch.candidates.map((item) => item.id))
                  }}
                >
                  <strong>
                    {batch.niche} em {batch.city}
                  </strong>
                  <p>Status: {batch.status}</p>
                  <small>{batch.candidates.length} candidatos</small>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {error ? <EmptyState title="Erro no teste" description={error} /> : null}
      {selectedBatch ? (
        <Panel title="Revisão do lote" subtitle="Selecione quem salvar, contatar agora ou rejeitar.">
          {batchActionNotice ? (
            <article className="note-card note-card--success">
              <strong>Status do lote</strong>
              <p>{batchActionNotice}</p>
            </article>
          ) : null}
          {selectedBatch.candidates.some((candidate) => candidate.status === 'queued_contact') ? (
            <article className="note-card">
              <strong>Fila de envio ativa</strong>
              <p>
                {selectedBatch.candidates.filter((candidate) => candidate.status === 'contacted').length} enviado(s),
                {' '}
                {selectedBatch.candidates.filter((candidate) => candidate.status === 'queued_contact').length} aguardando a
                janela de 1 minuto do provedor.
              </p>
            </article>
          ) : null}
          {selectedCandidateIds.length > 0 ? (
            <div className="inline-actions">
              <button className="button button--ghost" onClick={() => void applyBatchAction('save_only')}>
                {batchActionLoading === 'save_only' ? 'Salvando...' : 'Salvar selecionados'}
              </button>
              <button className="button button--primary" onClick={() => void applyBatchAction('save_and_start_outreach')}>
                {batchActionLoading === 'save_and_start_outreach' ? 'Salvando e iniciando...' : 'Salvar e iniciar contato'}
              </button>
              <button className="button button--ghost" onClick={() => void applyBatchAction('reject')}>
                {batchActionLoading === 'reject' ? 'Rejeitando...' : 'Rejeitar selecionados'}
              </button>
            </div>
          ) : null}
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th></th>
                  <th>Negócio</th>
                  <th>Contato</th>
                  <th>Origem</th>
                  <th>Resumo</th>
                  <th>Duplicado?</th>
                  <th>Status</th>
                  <th>Entrega / conversa</th>
                </tr>
              </thead>
              <tbody>
                {selectedBatch.candidates.map((candidate) => (
                  <tr key={candidate.id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedCandidateIds.includes(candidate.id)}
                        onChange={() => toggleCandidate(candidate.id)}
                      />
                    </td>
                    <td>
                      <div className="table__primary">
                        <strong>{candidate.business_name}</strong>
                        <span>{candidate.city}</span>
                      </div>
                    </td>
                    <td>{candidate.phone_number || candidate.instagram_url || candidate.website || '—'}</td>
                    <td>{candidate.source_platform || '—'}</td>
                    <td>{candidate.research_summary || candidate.notes || 'Sem resumo ainda.'}</td>
                    <td>
                      {candidate.existing_lead_id ? (
                        <StatusPill tone="warning">já existe ({candidate.existing_lead_status || 'na base'})</StatusPill>
                      ) : (
                        <StatusPill tone="success">novo</StatusPill>
                      )}
                      {!candidate.phone_number ? <p>Sem telefone/WhatsApp para start imediato.</p> : null}
                    </td>
                    <td>{candidate.status}</td>
                    <td>
                      <div className="table__primary">
                        <strong>{candidate.delivery_status || '—'}</strong>
                        <span>{candidate.delivery_note || 'Sem retorno operacional ainda.'}</span>
                      </div>
                      {candidate.conversation_id ? (
                        <Link className="button button--ghost" to={`/conversations?conversationId=${candidate.conversation_id}`}>
                          Abrir conversa
                        </Link>
                      ) : candidate.lead_id ? (
                        <Link className="button button--ghost" to={`/conversations?leadId=${candidate.lead_id}`}>
                          Procurar conversa
                        </Link>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}
    </div>
  )
}
