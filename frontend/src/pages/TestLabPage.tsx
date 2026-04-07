import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { StatusPill } from '../components/StatusPill'
import { api } from '../lib/api'
import type {
  Campaign,
  DashboardSummary,
  ProspectingBatch,
  ProspectingPrompt,
  ProspectingPromptCategory,
  ProspectingRecipe,
} from '../lib/types'

type FieldCardProps = {
  label: string
  description: string
  children: ReactNode
}

function FieldCard({ label, description, children }: FieldCardProps) {
  return (
    <label className="field-card">
      <span className="field-card__label">{label}</span>
      <small className="field-card__description">{description}</small>
      {children}
    </label>
  )
}

function WorkspaceModal({
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
    <div className="workspace-modal-backdrop" onClick={onClose}>
      <div className="workspace-modal" onClick={(event) => event.stopPropagation()}>
        <div className="workspace-modal__header">
          <div>
            <strong>{title}</strong>
            <p>{subtitle}</p>
          </div>
          <button className="button button--ghost" type="button" onClick={onClose}>
            Fechar
          </button>
        </div>
        <div className="workspace-modal__body">{children}</div>
      </div>
    </div>
  )
}

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
    recipe_id: null as number | null,
    search_goal: '',
    system_prompt: '',
    source_channels: ['google', 'linkedin', 'instagram'] as string[],
    discovery_mode: 'hybrid',
    minimum_valid_contacts: 10,
    require_phone: true,
    fallback_enabled: true,
    search_depth: 2,
    agent_max_credits: 300 as number | null,
  })
  const [advisorHints, setAdvisorHints] = useState<string[]>([])
  const [prospectingForm, setProspectingForm] = useState({
    niche: 'barbearia',
    city: 'Vitoria, ES',
    limit: 10,
    enrich: false,
    validate_phone_format: true,
    campaign_id: null as number | null,
    recipe_id: null as number | null,
    prompt_category_id: null as number | null,
    prompt_id: null as number | null,
    search_goal: '',
    system_prompt: '',
    source_channels: ['google', 'linkedin', 'instagram'] as string[],
    discovery_mode: 'hybrid',
    minimum_valid_contacts: 10,
    require_phone: true,
    fallback_enabled: true,
    search_depth: 2,
    agent_max_credits: 300 as number | null,
  })
  const [batches, setBatches] = useState<ProspectingBatch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<ProspectingBatch | null>(null)
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<number[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [recipes, setRecipes] = useState<ProspectingRecipe[]>([])
  const [promptCategories, setPromptCategories] = useState<ProspectingPromptCategory[]>([])
  const [savedPrompts, setSavedPrompts] = useState<ProspectingPrompt[]>([])
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null)
  const [promptCategoryForm, setPromptCategoryForm] = useState({
    name: '',
    description: '',
    offer_context: '',
    target_niche: '',
  })
  const [promptLibraryForm, setPromptLibraryForm] = useState({
    name: '',
    category_id: null as number | null,
    notes: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [batchActionLoading, setBatchActionLoading] = useState<string | null>(null)
  const [batchActionNotice, setBatchActionNotice] = useState<string | null>(null)
  const [libraryNotice, setLibraryNotice] = useState<string | null>(null)
  const [activeWorkspace, setActiveWorkspace] = useState<'library' | 'analytics' | 'advanced' | null>(null)

  const usesAgent = prospectingForm.discovery_mode === 'agent' || prospectingForm.discovery_mode === 'hybrid'
  const selectedPrompt = useMemo(
    () => savedPrompts.find((item) => item.id === prospectingForm.prompt_id) ?? null,
    [savedPrompts, prospectingForm.prompt_id],
  )
  const selectedPromptCategory = useMemo(
    () => promptCategories.find((item) => item.id === prospectingForm.prompt_category_id) ?? null,
    [promptCategories, prospectingForm.prompt_category_id],
  )
  const categoryPerformanceRows = useMemo(() => {
    const rows = dashboardSummary?.prompt_categories ?? []
    if (!prospectingForm.prompt_category_id) return rows
    return rows.filter((item) => item.id === prospectingForm.prompt_category_id)
  }, [dashboardSummary, prospectingForm.prompt_category_id])
  const promptPerformanceRows = useMemo(() => {
    const rows = dashboardSummary?.prospecting_prompts ?? []
    if (prospectingForm.prompt_id) {
      return rows.filter((item) => item.id === prospectingForm.prompt_id)
    }
    if (prospectingForm.prompt_category_id) {
      return rows.filter((item) => item.category_id === prospectingForm.prompt_category_id)
    }
    return rows
  }, [dashboardSummary, prospectingForm.prompt_category_id, prospectingForm.prompt_id])
  const bestPromptRow = useMemo(
    () =>
      [...promptPerformanceRows].sort((left, right) => {
        const leftScore = left.closed_won * 100 + left.meetings_booked * 10 + left.reply_rate
        const rightScore = right.closed_won * 100 + right.meetings_booked * 10 + right.reply_rate
        return rightScore - leftScore
      })[0] ?? null,
    [promptPerformanceRows],
  )

  const renderedPromptPreview = useMemo(
    () =>
      renderPromptTemplate(
        prospectingForm.system_prompt ||
          'Objetivo: {{search_goal}}. Nicho: {{niche}}. Cidade: {{city}}. Fontes: {{source_channels}}. Continue até conseguir {{minimum_valid_contacts}} contatos válidos. Modo: {{discovery_mode}}. Profundidade: {{search_depth}}. Créditos máximos: {{agent_max_credits}}.',
        prospectingForm,
      ),
    [prospectingForm],
  )

  const formWarnings = useMemo(() => {
    const warnings: string[] = []
    if (usesAgent && !prospectingForm.system_prompt.trim()) {
      warnings.push('Modo agent sem prompt livre tende a gerar busca genérica demais.')
    }
    if (prospectingForm.discovery_mode === 'agent' && !prospectingForm.fallback_enabled) {
      warnings.push('Agent puro sem fallback é mais arriscado quando a busca aberta demora ou não fecha o mínimo válido.')
    }
    if (prospectingForm.minimum_valid_contacts > prospectingForm.limit) {
      warnings.push('O mínimo de contatos válidos está maior que o limite do lote. Isso pode confundir a expectativa da execução.')
    }
    if (prospectingForm.source_channels.length === 0) {
      warnings.push('Você não selecionou nenhuma fonte. Escolha pelo menos um canal.')
    }
    return warnings
  }, [prospectingForm, usesAgent])

  const loadBatches = async () => {
    try {
      const [batchList, campaignList, recipeList, categoryList, promptList, summary] = await Promise.all([
        api.listProspectingBatches(),
        api.listCampaigns(),
        api.listProspectingRecipes(),
        api.listProspectingPromptCategories(),
        api.listProspectingPrompts(),
        api.getDashboardSummary(),
      ])
      setBatches(batchList)
      setCampaigns(campaignList)
      setRecipes(recipeList)
      setPromptCategories(categoryList)
      setSavedPrompts(promptList)
      setDashboardSummary(summary)
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
      recipe_id: response.state.recipe_id ?? null,
      search_goal: response.state.search_goal || '',
      system_prompt: response.state.system_prompt || '',
      source_channels: response.state.source_channels || ['google', 'linkedin', 'instagram'],
      discovery_mode: response.state.discovery_mode,
      minimum_valid_contacts: response.state.minimum_valid_contacts,
      require_phone: response.state.require_phone,
      fallback_enabled: response.state.fallback_enabled,
      search_depth: response.state.search_depth,
      agent_max_credits: response.state.agent_max_credits ?? 300,
    })
    setAdvisorHints(response.supported_niches)
    setProspectingForm((current) => ({
      ...current,
      niche: response.state.niche || current.niche,
      city: response.state.city || current.city,
      limit: response.state.limit,
      enrich: response.state.enrich,
      search_goal: response.state.search_goal || current.search_goal,
      system_prompt: response.state.system_prompt || current.system_prompt,
      source_channels: response.state.source_channels || current.source_channels,
      discovery_mode: response.state.discovery_mode,
      minimum_valid_contacts: response.state.minimum_valid_contacts,
      require_phone: response.state.require_phone,
      fallback_enabled: response.state.fallback_enabled,
      search_depth: response.state.search_depth,
      agent_max_credits: response.state.agent_max_credits ?? current.agent_max_credits,
    }))
    if (response.warnings.length > 0) {
      setAssistantMessages((current) => [
        ...current,
        { role: 'assistant', content: `Alertas: ${response.warnings.join(' | ')}` },
      ])
    }
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

  const toggleSourceChannel = (channel: string) => {
    setProspectingForm((current) => ({
      ...current,
      source_channels: current.source_channels.includes(channel)
        ? current.source_channels.filter((item) => item !== channel)
        : [...current.source_channels, channel],
    }))
  }

  const buildPromptDraft = () => {
    const categoryContext = selectedPromptCategory?.offer_context?.trim()
    const categoryGoal = selectedPromptCategory?.description?.trim()
    const basePrompt = [
      `Objetivo comercial: ${prospectingForm.search_goal || categoryGoal || `gerar oportunidades em ${prospectingForm.niche}`}.`,
      `Nicho alvo: {{niche}}.`,
      `Região alvo: {{city}}.`,
      `Canais prioritários: {{source_channels}}.`,
      usesAgent
        ? `Modo de execução: {{discovery_mode}}. Continue até conseguir {{minimum_valid_contacts}} contatos válidos com profundidade {{search_depth}}.`
        : 'Use busca estruturada, priorizando precisão e sinais comerciais claros.',
      prospectingForm.require_phone
        ? 'Só aceite leads com telefone ou WhatsApp utilizável para outreach.'
        : 'Aceite leads relevantes mesmo sem telefone imediato, desde que haja forte sinal comercial.',
      categoryContext ? `Contexto da oferta: ${categoryContext}.` : null,
      'Priorize negócios com sinais de dor, urgência, dependência excessiva de canais orgânicos ou indícios de necessidade de captação.',
      'Explique implicitamente no resultado por que cada lead entrou no lote.',
    ]
      .filter(Boolean)
      .join(' ')

    setProspectingForm((current) => ({
      ...current,
      system_prompt: basePrompt,
    }))
    setLibraryNotice('Rascunho de prompt base montado automaticamente no formulário.')
  }

  const applySearchPreset = (preset: 'fast' | 'balanced' | 'deep') => {
    if (preset === 'fast') {
      setProspectingForm((current) => ({
        ...current,
        enrich: false,
        discovery_mode: 'search',
        require_phone: true,
        fallback_enabled: true,
        minimum_valid_contacts: Math.max(5, current.limit),
        search_depth: 1,
        agent_max_credits: 120,
      }))
      return
    }
    if (preset === 'balanced') {
      setProspectingForm((current) => ({
        ...current,
        enrich: true,
        discovery_mode: 'hybrid',
        require_phone: true,
        fallback_enabled: true,
        minimum_valid_contacts: Math.max(8, current.limit),
        search_depth: 2,
        agent_max_credits: 300,
      }))
      return
    }
    setProspectingForm((current) => ({
      ...current,
      enrich: true,
      discovery_mode: 'agent',
      require_phone: true,
      fallback_enabled: false,
      minimum_valid_contacts: Math.max(10, current.limit),
      search_depth: 3,
      agent_max_credits: 600,
    }))
  }

  const applySavedPrompt = (prompt: ProspectingPrompt) => {
    setProspectingForm((current) => ({
      ...current,
      prompt_category_id: prompt.category_id ?? current.prompt_category_id,
      prompt_id: prompt.id,
      search_goal: prompt.objective || current.search_goal,
      system_prompt: prompt.prompt_text || current.system_prompt,
      source_channels: prompt.source_channels.length > 0 ? prompt.source_channels : current.source_channels,
      discovery_mode: prompt.discovery_mode || current.discovery_mode,
      minimum_valid_contacts: prompt.minimum_valid_contacts || current.minimum_valid_contacts,
      require_phone: prompt.require_phone,
      fallback_enabled: prompt.fallback_enabled,
      search_depth: prompt.search_depth || current.search_depth,
      agent_max_credits: prompt.agent_max_credits ?? current.agent_max_credits,
    }))
    setPromptLibraryForm((current) => ({
      ...current,
      name: prompt.name,
      category_id: prompt.category_id ?? current.category_id,
    }))
    setLibraryNotice(`Prompt "${prompt.name}" aplicado no formulário.`)
  }

  const savePromptCategory = async () => {
    if (!promptCategoryForm.name.trim()) {
      setError('Dê um nome para a categoria de prompt.')
      return
    }
    try {
      const created = await api.createProspectingPromptCategory({
        ...promptCategoryForm,
        target_niche: promptCategoryForm.target_niche || null,
      })
      setPromptCategories((current) => [created, ...current])
      setProspectingForm((current) => ({
        ...current,
        prompt_category_id: created.id,
      }))
      setPromptLibraryForm((current) => ({
        ...current,
        category_id: created.id,
      }))
      setPromptCategoryForm({ name: '', description: '', offer_context: '', target_niche: prospectingForm.niche })
      setLibraryNotice(`Categoria "${created.name}" criada.`)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const saveCurrentPrompt = async () => {
    if (!promptLibraryForm.name.trim()) {
      setError('Dê um nome para o prompt antes de salvar.')
      return
    }
    try {
      const created = await api.createProspectingPrompt({
        category_id: promptLibraryForm.category_id,
        name: promptLibraryForm.name,
        prompt_text: prospectingForm.system_prompt,
        objective: prospectingForm.search_goal || null,
        source_channels: prospectingForm.source_channels,
        discovery_mode: prospectingForm.discovery_mode,
        minimum_valid_contacts: prospectingForm.minimum_valid_contacts,
        require_phone: prospectingForm.require_phone,
        fallback_enabled: prospectingForm.fallback_enabled,
        search_depth: prospectingForm.search_depth,
        agent_max_credits: prospectingForm.agent_max_credits,
        notes: promptLibraryForm.notes || null,
      })
      setSavedPrompts((current) => [created, ...current])
      setProspectingForm((current) => ({
        ...current,
        prompt_id: created.id,
        prompt_category_id: created.category_id ?? current.prompt_category_id,
      }))
      setPromptLibraryForm((current) => ({
        ...current,
        name: '',
        notes: '',
      }))
      setLibraryNotice(`Prompt "${created.name}" salvo na biblioteca.`)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
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
    <div className="page page--prospecting">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Pesquisa de clientes</span>
          <h1>Montar busca e revisar lote</h1>
          <p>A tela principal agora foca só em definir alvo, escolher a intensidade da busca, revisar o prompt e gerar o lote.</p>
        </div>
      </section>

      <Panel title="Superfícies separadas" subtitle="Recursos pesados ficam fora da tela principal para você não operar no meio de um scroll infinito.">
        <div className="inline-actions">
          <button className="button button--primary" type="button" onClick={() => setActiveWorkspace('library')}>
            Abrir biblioteca de prompts
          </button>
          <button className="button button--ghost" type="button" onClick={() => setActiveWorkspace('advanced')}>
            Abrir configurações avançadas
          </button>
          <button className="button button--ghost" type="button" onClick={() => setActiveWorkspace('analytics')}>
            Abrir analytics de prompts
          </button>
          <Link className="button button--ghost" to="/conversations">
            Ver conversas
          </Link>
        </div>
      </Panel>

      <Panel title="1. Descreva o que quer achar" subtitle="Você pode começar por linguagem natural e depois só ajustar o essencial.">
        <div className="prospecting-layout">
          <div className="stack">
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
                placeholder="Ex: quero achar donos de barbearia em Vitoria, ES que ainda dependem de Instagram e preciso de 20 contatos válidos."
                value={assistantInput}
                onChange={(event) => setAssistantInput(event.target.value)}
              />
              <div className="inline-actions">
                <button className="button button--primary" type="submit">
                  Montar busca com o assistente
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
          </div>

          <div className="prospecting-summary">
            <article className="note-card">
              <strong>Resumo entendido agora</strong>
              <div className="kv-list">
                <div><span>Nicho</span><strong>{advisorState.niche || 'ainda não definido'}</strong></div>
                <div><span>Cidade</span><strong>{advisorState.city || 'ainda não definida'}</strong></div>
                <div><span>Limite</span><strong>{advisorState.limit}</strong></div>
                <div><span>Modo</span><strong>{advisorState.discovery_mode}</strong></div>
                <div><span>Mínimo válido</span><strong>{advisorState.minimum_valid_contacts}</strong></div>
              </div>
            </article>
          </div>
        </div>
      </Panel>

      <form className="stack" onSubmit={runProspecting}>
        <Panel title="2. Preencha só o essencial" subtitle="Esse é o caminho principal. O resto ficou em telas separadas.">
          <div className="prospecting-fields">
            <FieldCard label="Nicho alvo" description="Quem você quer encontrar.">
              <input className="field" value={prospectingForm.niche} onChange={(event) => setProspectingForm({ ...prospectingForm, niche: event.target.value })} />
            </FieldCard>
            <FieldCard label="Cidade / região" description="Onde essa busca deve acontecer.">
              <input className="field" value={prospectingForm.city} onChange={(event) => setProspectingForm({ ...prospectingForm, city: event.target.value })} />
            </FieldCard>
            <FieldCard label="Quantidade do lote" description="Quantos leads você quer revisar nessa rodada.">
              <input className="field" type="number" value={prospectingForm.limit} onChange={(event) => setProspectingForm({ ...prospectingForm, limit: Number(event.target.value) })} />
            </FieldCard>
            <FieldCard label="Objetivo da busca" description="O que você quer encontrar comercialmente nessa rodada.">
              <textarea
                className="field field--textarea"
                placeholder="Ex: donos de barbearia que dependem só de Instagram e precisam captar mais agendamentos."
                value={prospectingForm.search_goal}
                onChange={(event) => setProspectingForm({ ...prospectingForm, search_goal: event.target.value })}
              />
            </FieldCard>
          </div>
          <div className="prospecting-compact-grid">
            <article className="note-card">
              <strong>Reaproveitamento atual</strong>
              <div className="kv-list">
                <div><span>Recipe</span><strong>{recipes.find((item) => item.id === prospectingForm.recipe_id)?.name || 'ad-hoc'}</strong></div>
                <div><span>Categoria</span><strong>{selectedPromptCategory?.name || 'sem categoria'}</strong></div>
                <div><span>Prompt</span><strong>{selectedPrompt?.name || 'livre / nenhum'}</strong></div>
              </div>
              <div className="inline-actions">
                <button className="button button--ghost" type="button" onClick={() => setActiveWorkspace('library')}>
                  Escolher da biblioteca
                </button>
              </div>
            </article>
            <article className="note-card">
              <strong>Intensidade da busca</strong>
              <p>Escolha um preset rápido. Se precisar, refine tudo nas configurações avançadas.</p>
              <div className="inline-actions">
                <button className="button button--ghost" type="button" onClick={() => applySearchPreset('fast')}>
                  Rápida
                </button>
                <button className="button button--primary" type="button" onClick={() => applySearchPreset('balanced')}>
                  Balanceada
                </button>
                <button className="button button--ghost" type="button" onClick={() => applySearchPreset('deep')}>
                  Profunda
                </button>
              </div>
              <p>
                Atual: <strong>{prospectingForm.discovery_mode}</strong> / {prospectingForm.enrich ? 'com enriquecimento' : 'sem enriquecimento'}
              </p>
            </article>
          </div>
        </Panel>

        <Panel title="3. Revisão do prompt" subtitle="Só o necessário para confirmar a lógica da busca antes de rodar.">
          <div className="inline-actions">
            <button className="button button--ghost" type="button" onClick={buildPromptDraft}>
              Montar prompt base automaticamente
            </button>
            <button className="button button--ghost" type="button" onClick={() => setActiveWorkspace('library')}>
              Salvar / abrir biblioteca
            </button>
            <button className="button button--ghost" type="button" onClick={() => setActiveWorkspace('advanced')}>
              Ajustar parâmetros avançados
            </button>
          </div>
          {usesAgent ? (
            <>
              <FieldCard label="Prompt agentico" description="Se estiver em `agent` ou `hybrid`, revise o prompt final aqui.">
                <textarea
                  className="field field--textarea"
                  placeholder="Ex: procure pessoas que demonstrem necessidade recente de ajuda com captação..."
                  value={prospectingForm.system_prompt}
                  onChange={(event) => setProspectingForm({ ...prospectingForm, system_prompt: event.target.value })}
                />
              </FieldCard>
              <article className="note-card">
                <strong>Preview do prompt</strong>
                <pre className="prospecting-preview">{renderedPromptPreview}</pre>
              </article>
            </>
          ) : (
            <article className="note-card">
              <strong>Busca estruturada ativa</strong>
              <p>No modo `search`, o motor usa alvo + canais + filtros. Se quiser investigação guiada por prompt, troque o preset ou abra o avançado.</p>
            </article>
          )}
        </Panel>

        <Panel title="4. Rodar busca" subtitle="Aqui você valida o essencial e gera o lote.">
          {formWarnings.length > 0 ? (
            <article className="note-card note-card--warning">
              <strong>Ajustes recomendados antes de rodar</strong>
              <ul className="prospecting-list">
                {formWarnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </article>
          ) : null}

          {prospectingForm.limit > 5 && prospectingForm.enrich ? (
            <article className="note-card">
              <strong>Aviso de lentidão</strong>
              <p>Com enriquecimento ligado e limite acima de 5, a busca pode demorar bastante.</p>
            </article>
          ) : null}

          {selectedBatch?.search_metrics_json ? (
            <article className="note-card">
              <strong>Última execução</strong>
              <div className="kv-list">
                <div><span>Modo</span><strong>{String(selectedBatch.search_metrics_json.discovery_mode || '—')}</strong></div>
                <div><span>Prompt</span><strong>{String(selectedBatch.search_metrics_json.prompt_name || 'ad-hoc')}</strong></div>
                <div><span>Retornados</span><strong>{String(selectedBatch.search_metrics_json.returned_candidates || 0)}</strong></div>
                <div><span>Gap de cobertura</span><strong>{String(selectedBatch.search_metrics_json.coverage_gap || 0)}</strong></div>
                <div><span>Fontes</span><strong>{String((selectedBatch.search_metrics_json.source_channels as string[] | undefined)?.join(', ') || '—')}</strong></div>
              </div>
            </article>
          ) : null}
          <article className="note-card">
            <strong>Rastreio que será salvo</strong>
            <div className="kv-list">
              <div><span>Categoria</span><strong>{selectedPromptCategory?.name || 'ad-hoc / sem categoria'}</strong></div>
              <div><span>Prompt</span><strong>{selectedPrompt?.name || 'prompt livre do formulário'}</strong></div>
              <div><span>Objetivo</span><strong>{prospectingForm.search_goal || 'não definido'}</strong></div>
            </div>
          </article>

          <div className="inline-actions">
            <button className="button button--primary" type="submit">
              {loading
                ? prospectingForm.enrich
                  ? 'Buscando e enriquecendo...'
                  : 'Buscando rapidamente...'
                : 'Gerar lote para revisão'}
            </button>
          </div>
        </Panel>

        <Panel title="5. Lotes recentes" subtitle="O histórico da operação continua aqui, mas separado da montagem da busca.">
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
                  <p>Prompt: {String(batch.prompt_snapshot_json?.name || 'ad-hoc')}</p>
                  <small>{batch.candidates.length} candidatos</small>
                </button>
              ))}
            </div>
          )}
        </Panel>
      </form>

      {activeWorkspace === 'library' ? (
        <WorkspaceModal
          title="Biblioteca de prompts"
          subtitle="Gerencie categorias, salve prompts e reaplique hipóteses sem poluir a tela principal."
          onClose={() => setActiveWorkspace(null)}
        >
          {libraryNotice ? (
            <article className="note-card note-card--success">
              <strong>Biblioteca atualizada</strong>
              <p>{libraryNotice}</p>
            </article>
          ) : null}
          <div className="prospecting-fields">
            <FieldCard label="Nova categoria" description="Ex: vender landing page para barbeiros.">
              <input className="field" value={promptCategoryForm.name} onChange={(event) => setPromptCategoryForm({ ...promptCategoryForm, name: event.target.value })} />
            </FieldCard>
            <FieldCard label="Nicho da categoria" description="Opcional, para organizar a tese comercial.">
              <input className="field" value={promptCategoryForm.target_niche} onChange={(event) => setPromptCategoryForm({ ...promptCategoryForm, target_niche: event.target.value })} />
            </FieldCard>
            <FieldCard label="Descrição da categoria" description="Resumo da lógica comercial dessa tese.">
              <textarea className="field field--textarea" value={promptCategoryForm.description} onChange={(event) => setPromptCategoryForm({ ...promptCategoryForm, description: event.target.value })} />
            </FieldCard>
            <FieldCard label="Contexto da oferta" description="O contexto do que você está vendendo nessa categoria.">
              <textarea className="field field--textarea" value={promptCategoryForm.offer_context} onChange={(event) => setPromptCategoryForm({ ...promptCategoryForm, offer_context: event.target.value })} />
            </FieldCard>
          </div>
          <div className="inline-actions">
            <button className="button button--ghost" type="button" onClick={() => void savePromptCategory()}>
              Salvar categoria
            </button>
          </div>
          <div className="prospecting-fields">
            <FieldCard label="Nome do prompt" description="Nome da hipótese que você quer guardar.">
              <input className="field" value={promptLibraryForm.name} onChange={(event) => setPromptLibraryForm({ ...promptLibraryForm, name: event.target.value })} />
            </FieldCard>
            <FieldCard label="Categoria do prompt" description="Onde esse prompt vai ser comparado depois.">
              <select className="field" value={promptLibraryForm.category_id ?? ''} onChange={(event) => setPromptLibraryForm({ ...promptLibraryForm, category_id: event.target.value ? Number(event.target.value) : null })}>
                <option value="">Sem categoria</option>
                {promptCategories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </FieldCard>
            <FieldCard label="Notas da hipótese" description="Quando usar ou por que esse prompt existe.">
              <textarea className="field field--textarea" value={promptLibraryForm.notes} onChange={(event) => setPromptLibraryForm({ ...promptLibraryForm, notes: event.target.value })} />
            </FieldCard>
          </div>
          <div className="inline-actions">
            <button className="button button--primary" type="button" onClick={() => void saveCurrentPrompt()}>
              Salvar prompt atual
            </button>
            <button className="button button--ghost" type="button" onClick={buildPromptDraft}>
              Montar prompt base automaticamente
            </button>
          </div>
          {savedPrompts.length > 0 ? (
            <div className="prompt-library-list">
              {savedPrompts.slice(0, 8).map((prompt) => (
                <article key={prompt.id} className="note-card">
                  <strong>{prompt.name}</strong>
                  <p>{prompt.objective || 'Sem objetivo salvo.'}</p>
                  <div className="kv-list">
                    <div><span>Categoria</span><strong>{promptCategories.find((item) => item.id === prompt.category_id)?.name || 'sem categoria'}</strong></div>
                    <div><span>Modo</span><strong>{prompt.discovery_mode}</strong></div>
                    <div><span>Mínimo válido</span><strong>{prompt.minimum_valid_contacts}</strong></div>
                  </div>
                  <div className="inline-actions">
                    <button className="button button--ghost" type="button" onClick={() => { applySavedPrompt(prompt); setActiveWorkspace(null) }}>
                      Aplicar neste fluxo
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </WorkspaceModal>
      ) : null}

      {activeWorkspace === 'advanced' ? (
        <WorkspaceModal
          title="Configurações avançadas"
          subtitle="Aqui fica o poder bruto: recipe, campanha, canais e parâmetros técnicos da busca."
          onClose={() => setActiveWorkspace(null)}
        >
          <div className="prospecting-fields">
            <FieldCard label="Recipe base" description="Reaproveite uma receita já validada.">
              <select className="field" value={prospectingForm.recipe_id ?? ''} onChange={(event) => setProspectingForm({ ...prospectingForm, recipe_id: event.target.value ? Number(event.target.value) : null })}>
                <option value="">Recipe ad-hoc</option>
                {recipes.map((recipe) => (
                  <option key={recipe.id} value={recipe.id}>{recipe.name}</option>
                ))}
              </select>
            </FieldCard>
            <FieldCard label="Campanha ligada" description="Vincule a uma campanha se essa busca fizer parte de uma operação maior.">
              <select className="field" value={prospectingForm.campaign_id ?? ''} onChange={(event) => setProspectingForm({ ...prospectingForm, campaign_id: event.target.value ? Number(event.target.value) : null })}>
                <option value="">Sem campanha</option>
                {campaigns.map((campaign) => (
                  <option key={campaign.id} value={campaign.id}>{campaign.name}</option>
                ))}
              </select>
            </FieldCard>
            <FieldCard label="Categoria de prompt" description="Define a tese comercial a ser lastreada.">
              <select
                className="field"
                value={prospectingForm.prompt_category_id ?? ''}
                onChange={(event) => {
                  const value = event.target.value ? Number(event.target.value) : null
                  setProspectingForm((current) => ({
                    ...current,
                    prompt_category_id: value,
                    prompt_id: value && savedPrompts.some((prompt) => prompt.id === current.prompt_id && prompt.category_id === value) ? current.prompt_id : null,
                  }))
                  setPromptLibraryForm((current) => ({ ...current, category_id: value }))
                }}
              >
                <option value="">Sem categoria</option>
                {promptCategories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </FieldCard>
            <FieldCard label="Prompt salvo" description="Aplique um prompt já validado da biblioteca.">
              <select
                className="field"
                value={prospectingForm.prompt_id ?? ''}
                onChange={(event) => {
                  const promptId = event.target.value ? Number(event.target.value) : null
                  const prompt = savedPrompts.find((item) => item.id === promptId)
                  if (prompt) {
                    applySavedPrompt(prompt)
                    return
                  }
                  setProspectingForm((current) => ({ ...current, prompt_id: null }))
                }}
              >
                <option value="">Prompt ad-hoc</option>
                {savedPrompts.filter((prompt) => (prospectingForm.prompt_category_id ? prompt.category_id === prospectingForm.prompt_category_id : true)).map((prompt) => (
                  <option key={prompt.id} value={prompt.id}>{prompt.name}</option>
                ))}
              </select>
            </FieldCard>
            <FieldCard label="Modo de descoberta" description="`search`, `agent` ou `hybrid`.">
              <select className="field" value={prospectingForm.discovery_mode} onChange={(event) => setProspectingForm({ ...prospectingForm, discovery_mode: event.target.value })}>
                <option value="search">search</option>
                <option value="agent">agent</option>
                <option value="hybrid">hybrid</option>
              </select>
            </FieldCard>
            <FieldCard label="Mínimo válido" description="Meta de contatos válidos.">
              <input className="field" type="number" value={prospectingForm.minimum_valid_contacts} onChange={(event) => setProspectingForm({ ...prospectingForm, minimum_valid_contacts: Number(event.target.value) })} />
            </FieldCard>
            <FieldCard label="Profundidade" description="Profundidade máxima de exploração.">
              <input className="field" type="number" value={prospectingForm.search_depth} onChange={(event) => setProspectingForm({ ...prospectingForm, search_depth: Number(event.target.value) })} />
            </FieldCard>
            <FieldCard label="Créditos do agent" description="Teto de créditos quando houver busca agentica.">
              <input className="field" type="number" value={prospectingForm.agent_max_credits ?? 300} onChange={(event) => setProspectingForm({ ...prospectingForm, agent_max_credits: Number(event.target.value) })} />
            </FieldCard>
          </div>
          <article className="note-card">
            <strong>Canais de busca</strong>
            <div className="inline-actions">
              {['google', 'linkedin', 'instagram', 'facebook'].map((channel) => (
                <button key={channel} className={`button ${prospectingForm.source_channels.includes(channel) ? 'button--primary' : 'button--ghost'}`} type="button" onClick={() => toggleSourceChannel(channel)}>
                  {channel}
                </button>
              ))}
            </div>
          </article>
          <div className="prospecting-toggle-grid">
            <label className="toggle-card">
              <input type="checkbox" checked={prospectingForm.validate_phone_format} onChange={(event) => setProspectingForm({ ...prospectingForm, validate_phone_format: event.target.checked })} />
              <div><strong>Validar telefone</strong><p>Descarta formatos claramente inválidos.</p></div>
            </label>
            <label className="toggle-card">
              <input type="checkbox" checked={prospectingForm.enrich} onChange={(event) => setProspectingForm({ ...prospectingForm, enrich: event.target.checked })} />
              <div><strong>Enriquecer lead</strong><p>Busca mais contexto comercial antes da revisão.</p></div>
            </label>
            <label className="toggle-card">
              <input type="checkbox" checked={prospectingForm.require_phone} onChange={(event) => setProspectingForm({ ...prospectingForm, require_phone: event.target.checked })} />
              <div><strong>Exigir telefone</strong><p>Prioriza leads já prontos para outreach.</p></div>
            </label>
            <label className="toggle-card">
              <input type="checkbox" checked={prospectingForm.fallback_enabled} onChange={(event) => setProspectingForm({ ...prospectingForm, fallback_enabled: event.target.checked })} />
              <div><strong>Fallback ligado</strong><p>Cai para busca estruturada se a aberta não fechar a meta.</p></div>
            </label>
          </div>
        </WorkspaceModal>
      ) : null}

      {activeWorkspace === 'analytics' ? (
        <WorkspaceModal
          title="Analytics de prompts"
          subtitle="Compare teses e prompts sem misturar análise com montagem de busca."
          onClose={() => setActiveWorkspace(null)}
        >
          {!dashboardSummary ? (
            <EmptyState title="Carregando analytics" description="Buscando performance por categoria e prompt." />
          ) : (
            <div className="stack">
              <div className="stats-grid stats-grid--compact">
                <article className="stat-card">
                  <span className="stat-card__label">Categorias com histórico</span>
                  <strong className="stat-card__value">{dashboardSummary.prompt_categories.length}</strong>
                  <span className="stat-card__hint">teses comerciais com lastro</span>
                </article>
                <article className="stat-card">
                  <span className="stat-card__label">Prompts rastreados</span>
                  <strong className="stat-card__value">{dashboardSummary.prospecting_prompts.length}</strong>
                  <span className="stat-card__hint">variantes que já geraram leads</span>
                </article>
                <article className="stat-card">
                  <span className="stat-card__label">Melhor prompt agora</span>
                  <strong className="stat-card__value">{bestPromptRow?.name || 'sem dados'}</strong>
                  <span className="stat-card__hint">ranking por win, reunião e reply</span>
                </article>
              </div>
              {categoryPerformanceRows.length > 0 ? (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Categoria</th><th>Leads</th><th>Reply</th><th>Positiva</th><th>Reuniões</th><th>Fechou</th><th>Fit médio</th></tr></thead>
                    <tbody>
                      {categoryPerformanceRows.map((item) => (
                        <tr key={item.id}><td>{item.name}</td><td>{item.leads}</td><td>{item.reply_rate}%</td><td>{item.positive_reply_rate}%</td><td>{item.meetings_booked}</td><td>{item.closed_won}</td><td>{item.fit_score_avg}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              {promptPerformanceRows.length > 0 ? (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Prompt</th><th>Categoria</th><th>Leads</th><th>Reply</th><th>Positiva</th><th>Reuniões</th><th>Fechou</th><th>Fit médio</th></tr></thead>
                    <tbody>
                      {promptPerformanceRows.map((item) => (
                        <tr key={item.id}><td>{item.name}</td><td>{item.category_name || 'sem categoria'}</td><td>{item.leads}</td><td>{item.reply_rate}%</td><td>{item.positive_reply_rate}%</td><td>{item.meetings_booked}</td><td>{item.closed_won}</td><td>{item.fit_score_avg}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          )}
        </WorkspaceModal>
      ) : null}

      {error ? <EmptyState title="Erro no teste" description={error} /> : null}
      {selectedBatch ? (
        <Panel title="Revisão do lote" subtitle="Selecione quem salvar, contatar agora ou rejeitar.">
          <article className="note-card">
            <strong>Prompt rastreado neste lote</strong>
            <div className="kv-list">
              <div><span>Categoria</span><strong>{String(selectedBatch.prompt_snapshot_json?.category_name || 'sem categoria')}</strong></div>
              <div><span>Prompt</span><strong>{String(selectedBatch.prompt_snapshot_json?.name || 'ad-hoc')}</strong></div>
              <div><span>Objetivo</span><strong>{String(selectedBatch.prompt_snapshot_json?.objective || selectedBatch.recipe_snapshot_json?.objective || '—')}</strong></div>
            </div>
          </article>
          <div className="stats-grid stats-grid--compact">
            <article className="stat-card">
              <span className="stat-card__label">Fit médio do lote</span>
              <strong className="stat-card__value">
                {selectedBatch.candidates.length
                  ? (
                      selectedBatch.candidates.reduce((total, candidate) => total + (candidate.fit_score || 0), 0) /
                      selectedBatch.candidates.length
                    ).toFixed(1)
                  : '0.0'}
              </strong>
              <span className="stat-card__hint">qualidade média da busca</span>
            </article>
            <article className="stat-card">
              <span className="stat-card__label">Fit alto</span>
              <strong className="stat-card__value">
                {selectedBatch.candidates.filter((candidate) => (candidate.fit_score || 0) >= 75).length}
              </strong>
              <span className="stat-card__hint">prioridade de abordagem</span>
            </article>
            <article className="stat-card">
              <span className="stat-card__label">Com contato válido</span>
              <strong className="stat-card__value">
                {selectedBatch.candidates.filter((candidate) => candidate.phone_number).length}/{selectedBatch.candidates.length}
              </strong>
              <span className="stat-card__hint">utilizáveis já no lote</span>
            </article>
            <article className="stat-card">
              <span className="stat-card__label">Duplicados</span>
              <strong className="stat-card__value">
                {selectedBatch.candidates.filter((candidate) => candidate.existing_lead_id).length}
              </strong>
              <span className="stat-card__hint">evita outreach desperdiçado</span>
            </article>
          </div>
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
                  <th>Fit</th>
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
                    <td>
                      <div className="table__primary">
                        <strong>{candidate.fit_score ?? '—'}</strong>
                        <span>{candidate.fit_label || 'sem score'}</span>
                      </div>
                    </td>
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

function renderPromptTemplate(
  template: string,
  values: {
    niche: string
    city: string
    limit: number
    search_goal: string
    source_channels: string[]
    discovery_mode: string
    minimum_valid_contacts: number
    search_depth: number
    agent_max_credits: number | null
  },
) {
  return template
    .replaceAll('{{niche}}', values.niche || 'nicho_nao_definido')
    .replaceAll('{{city}}', values.city || 'cidade_nao_definida')
    .replaceAll('{{limit}}', String(values.limit))
    .replaceAll('{{minimum_valid_contacts}}', String(values.minimum_valid_contacts))
    .replaceAll('{{search_goal}}', values.search_goal || 'objetivo_nao_definido')
    .replaceAll('{{source_channels}}', values.source_channels.join(', ') || 'sem_fontes')
    .replaceAll('{{discovery_mode}}', values.discovery_mode)
    .replaceAll('{{search_depth}}', String(values.search_depth))
    .replaceAll('{{agent_max_credits}}', String(values.agent_max_credits ?? 300))
}
