import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { api } from '../lib/api'
import type {
  AgentStrategy,
  Campaign,
  DashboardSummary,
  KnowledgeItem,
  OfferProduct,
  Playbook,
  PromptTemplate,
  ProspectingRecipe,
  RuntimeSettings,
  WhatsappSessionQr,
  WhatsappSessionWorkspace,
} from '../lib/types'

export function SettingsPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null)
  const [playbooks, setPlaybooks] = useState<Playbook[]>([])
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([])
  const [offerProducts, setOfferProducts] = useState<OfferProduct[]>([])
  const [agentStrategies, setAgentStrategies] = useState<AgentStrategy[]>([])
  const [promptTemplates, setPromptTemplates] = useState<PromptTemplate[]>([])
  const [prospectingRecipes, setProspectingRecipes] = useState<ProspectingRecipe[]>([])
  const [sessionWorkspace, setSessionWorkspace] = useState<WhatsappSessionWorkspace | null>(null)
  const [sessionQr, setSessionQr] = useState<WhatsappSessionQr | null>(null)
  const [sessionLoading, setSessionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [sessionForm, setSessionForm] = useState({
    name: '',
    phone_number: '',
    api_key: '',
    webhook_secret: '',
    webhook_url: '',
    outbound_cooldown_seconds: '',
    create_on_provider: false,
    set_active: true,
    account_protection: true,
    log_messages: true,
    read_incoming_messages: false,
    webhook_enabled: true,
  })
  const [campaignForm, setCampaignForm] = useState({
    name: '',
    niche: '',
    city: '',
    offer_product_id: null as number | null,
    agent_strategy_id: null as number | null,
    prospecting_recipe_id: null as number | null,
    offer_name: 'landing page',
    offer_summary: '',
    offer_goal: '',
    sales_tone: 'consultivo',
    cta_style: '',
    auto_reply_enabled: false,
    reply_delay_seconds: 30,
    start_outreach_on_approve: false,
    is_active: false,
  })
  const [offerForm, setOfferForm] = useState({
    name: '',
    category: '',
    summary: '',
    objective: '',
    target_customer: '',
    pains: '',
    differentiators: '',
    proof_points: '',
    cta_primary: '',
    allowed_claims: '',
    forbidden_claims: '',
    active: true,
  })
  const [strategyForm, setStrategyForm] = useState({
    name: '',
    persona: '',
    primary_goal: '',
    tone: '',
    opening_strategy: '',
    qualification_strategy: '',
    objection_strategy: '',
    follow_up_strategy: '',
    handoff_strategy: '',
    guardrails: '',
    active: true,
  })
  const [promptTemplateForm, setPromptTemplateForm] = useState({
    agent_strategy_id: null as number | null,
    name: '',
    phase: 'outreach',
    channel: 'whatsapp',
    system_prompt: '',
    instructions: '',
    output_contract: '',
    active: true,
  })
  const [recipeForm, setRecipeForm] = useState({
    name: '',
    objective: '',
    system_prompt: '',
    source_channels: ['google', 'linkedin', 'instagram'] as string[],
    inclusion_rules: '',
    exclusion_rules: '',
    minimum_valid_contacts: 10,
    max_total_results: 25,
    search_depth: 2,
    require_phone: true,
    validate_phone_format: true,
    discovery_mode: 'hybrid',
    fallback_enabled: true,
    scoring_guidance: '',
    assistant_notes: '',
    agent_max_credits: 300,
    active: true,
  })
  const [playbookForm, setPlaybookForm] = useState({
    name: '',
    niche: '',
    stage: '',
    instructions: '',
    objection_handling: '',
    qualification_rules: '',
    active: true,
  })
  const [knowledgeForm, setKnowledgeForm] = useState({
    title: '',
    category: '',
    niche: '',
    content: '',
    active: true,
  })

  const loadWorkspace = async () => {
    const [
      runtime,
      currentCampaigns,
      currentPlaybooks,
      currentKnowledge,
      currentSessionWorkspace,
      currentSummary,
      currentOffers,
      currentStrategies,
      currentTemplates,
      currentRecipes,
    ] = await Promise.all([
      api.getRuntimeSettings(),
      api.listCampaigns(),
      api.listPlaybooks(),
      api.listKnowledgeItems(),
      api.listWhatsappSessions(),
      api.getDashboardSummary(),
      api.listOfferProducts(),
      api.listAgentStrategies(),
      api.listPromptTemplates(),
      api.listProspectingRecipes(),
    ])
    setSettings({ ...runtime, outbound_enabled: true })
    setCampaigns(currentCampaigns)
    setPlaybooks(currentPlaybooks)
    setKnowledgeItems(currentKnowledge)
    setOfferProducts(currentOffers)
    setAgentStrategies(currentStrategies)
    setPromptTemplates(currentTemplates)
    setProspectingRecipes(currentRecipes)
    setSessionWorkspace(currentSessionWorkspace)
    setDashboardSummary(currentSummary)
  }

  useEffect(() => {
    loadWorkspace().catch((err: Error) => setError(err.message))
  }, [])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!settings) return
    setSaving(true)
    try {
      const updated = await api.updateRuntimeSettings({ ...settings, outbound_enabled: true })
      setSettings(updated)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const activeSession = sessionWorkspace?.items.find((item) => item.id === sessionWorkspace.active_session_id) ?? null

  const runSessionAction = async (key: string, action: () => Promise<void>) => {
    setSessionLoading(key)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSessionLoading(null)
    }
  }

  if (!settings) {
    return <EmptyState title="Carregando configuracao" description={error || 'Buscando parametros atuais do sistema.'} />
  }

  return (
    <div className="page">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Configuracao</span>
          <h1>O que vender, como vender e em que modo operar</h1>
          <p>Essa tela existe para reduzir mexida em `.env` e deixar o agente mais controlavel.</p>
        </div>
      </section>

      <form className="stack" onSubmit={onSubmit}>
        <Panel title="Linhas WhatsApp" subtitle="Escolha a linha ativa, preserve histórico por sessão e conecte novas linhas sem depender só do .env.">
          <div className="stack">
            <article className="note-card">
              <strong>Linha ativa agora</strong>
              <p>
                {activeSession
                  ? `${activeSession.name}${activeSession.phone_number ? ` • ${activeSession.phone_number}` : ''}`
                  : 'Nenhuma sessão ativa cadastrada ainda.'}
              </p>
              <small>
                {sessionWorkspace?.provider_management_available
                  ? 'PAT do WASender detectado. Dá para criar, sincronizar e abrir QR code pela plataforma.'
                  : 'PAT do WASender ausente. Dá para rastrear e ativar sessões na plataforma, mas criar/sincronizar no provedor exige o token pessoal.'}
              </small>
            </article>

            <div className="inline-actions">
              <button
                className="button button--ghost"
                type="button"
                onClick={() =>
                  void runSessionAction('sync-sessions', async () => {
                    const workspace = await api.syncWhatsappSessions()
                    setSessionWorkspace(workspace)
                  })
                }
              >
                {sessionLoading === 'sync-sessions' ? 'Sincronizando...' : 'Sincronizar do WASender'}
              </button>
            </div>

            <div className="form-grid">
              <label>
                <span>Nome da sessão</span>
                <input
                  className="field"
                  value={sessionForm.name}
                  onChange={(event) => setSessionForm({ ...sessionForm, name: event.target.value })}
                  placeholder="Ex.: Comercial principal"
                />
              </label>
              <label>
                <span>Número</span>
                <input
                  className="field"
                  value={sessionForm.phone_number}
                  onChange={(event) => setSessionForm({ ...sessionForm, phone_number: event.target.value })}
                  placeholder="+55 27 99999-0000"
                />
              </label>
              <label>
                <span>Webhook URL</span>
                <input
                  className="field"
                  value={sessionForm.webhook_url}
                  onChange={(event) => setSessionForm({ ...sessionForm, webhook_url: event.target.value })}
                  placeholder="https://seu-dominio/webhooks/wasender"
                />
              </label>
              <label>
                <span>Cooldown outbound da linha (segundos)</span>
                <input
                  className="field"
                  type="number"
                  min="0"
                  value={sessionForm.outbound_cooldown_seconds}
                  onChange={(event) =>
                    setSessionForm({ ...sessionForm, outbound_cooldown_seconds: event.target.value })
                  }
                  placeholder="Vazio = sem limite fixo"
                />
              </label>
              <label className="toggle-inline">
                <input
                  type="checkbox"
                  checked={sessionForm.create_on_provider}
                  onChange={(event) => setSessionForm({ ...sessionForm, create_on_provider: event.target.checked })}
                />
                Criar no WASender
              </label>
              <label className="toggle-inline">
                <input
                  type="checkbox"
                  checked={sessionForm.set_active}
                  onChange={(event) => setSessionForm({ ...sessionForm, set_active: event.target.checked })}
                />
                Definir como ativa
              </label>
              {!sessionForm.create_on_provider ? (
                <>
                  <label>
                    <span>API key da sessão</span>
                    <input
                      className="field"
                      value={sessionForm.api_key}
                      onChange={(event) => setSessionForm({ ...sessionForm, api_key: event.target.value })}
                    />
                  </label>
                  <label>
                    <span>Webhook secret</span>
                    <input
                      className="field"
                      value={sessionForm.webhook_secret}
                      onChange={(event) => setSessionForm({ ...sessionForm, webhook_secret: event.target.value })}
                    />
                  </label>
                </>
              ) : null}
            </div>

            <div className="inline-actions">
              <button
                className="button button--primary"
                type="button"
                onClick={() =>
                  void runSessionAction('create-session', async () => {
                    await api.createWhatsappSession({
                      ...sessionForm,
                      outbound_cooldown_seconds:
                        sessionForm.outbound_cooldown_seconds === ''
                          ? null
                          : Number(sessionForm.outbound_cooldown_seconds),
                      webhook_events: [
                        'messages.received',
                        'messages.upsert',
                        'messages.update',
                        'message.sent',
                        'session.status',
                      ],
                    })
                    const workspace = await api.listWhatsappSessions()
                    setSessionWorkspace(workspace)
                    setSessionForm({
                      name: '',
                      phone_number: '',
                      api_key: '',
                      webhook_secret: '',
                      webhook_url: sessionForm.webhook_url,
                      outbound_cooldown_seconds: '',
                      create_on_provider: false,
                      set_active: true,
                      account_protection: true,
                      log_messages: true,
                      read_incoming_messages: false,
                      webhook_enabled: true,
                    })
                  })
                }
              >
                {sessionLoading === 'create-session' ? 'Salvando sessão...' : 'Cadastrar sessão'}
              </button>
            </div>

            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Sessão</th>
                    <th>Status</th>
                    <th>Cooldown</th>
                    <th>Origem</th>
                    <th>Credenciais</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {sessionWorkspace?.items.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.name}</strong>
                        <div>
                          <small>{item.phone_number || sessionWorkspace.legacy_label}</small>
                        </div>
                      </td>
                      <td>{item.is_active ? `ativa • ${item.status}` : item.status}</td>
                      <td>{item.outbound_cooldown_seconds ? `${item.outbound_cooldown_seconds}s` : 'sem limite'}</td>
                      <td>{item.source}</td>
                      <td>{item.has_api_key && item.has_webhook_secret ? 'completas' : 'incompletas'}</td>
                      <td>
                        <div className="inline-actions">
                          <button
                            className="button button--ghost"
                            type="button"
                            onClick={() =>
                              void runSessionAction(`activate:${item.id}`, async () => {
                                await api.activateWhatsappSession(item.id)
                                const workspace = await api.listWhatsappSessions()
                                setSessionWorkspace(workspace)
                              })
                            }
                          >
                            {sessionLoading === `activate:${item.id}` ? 'Ativando...' : 'Ativar'}
                          </button>
                          <button
                            className="button button--ghost"
                            type="button"
                            onClick={() =>
                              void runSessionAction(`connect:${item.id}`, async () => {
                                const qr = await api.connectWhatsappSession(item.id)
                                setSessionQr(qr)
                                const workspace = await api.listWhatsappSessions()
                                setSessionWorkspace(workspace)
                              })
                            }
                          >
                            {sessionLoading === `connect:${item.id}` ? 'Abrindo QR...' : 'Conectar'}
                          </button>
                          <button
                            className="button button--ghost"
                            type="button"
                            onClick={() =>
                              void runSessionAction(`qr:${item.id}`, async () => {
                                const qr = await api.getWhatsappSessionQr(item.id)
                                setSessionQr(qr)
                              })
                            }
                          >
                            {sessionLoading === `qr:${item.id}` ? 'Buscando QR...' : 'Ver QR'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {sessionQr?.qr_code ? (
              <article className="note-card">
                <strong>QR code da sessão {sessionQr.session_id}</strong>
                <p>Escaneie com o WhatsApp do número desejado.</p>
                <img
                  alt="QR code da sessão do WhatsApp"
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=280x280&data=${encodeURIComponent(sessionQr.qr_code)}`}
                  style={{ width: 280, height: 280, borderRadius: 16, background: '#fff', padding: 12 }}
                />
              </article>
            ) : null}
          </div>
        </Panel>

        <Panel title="Modo operacional" subtitle="Automação pode ser controlada aqui, mas envio outbound fica ativo por padrão.">
          <div className="toggles-grid">
            <article className="toggle-card">
              <div>
                <strong>Outbound real sempre ativo</strong>
                <p>Mensagens do agente e mensagens manuais devem sair de verdade para o WhatsApp.</p>
              </div>
            </article>

            <label className="toggle-card">
              <input
                type="checkbox"
                checked={settings.auto_reply_enabled}
                onChange={(event) => setSettings((current) => current && ({ ...current, auto_reply_enabled: event.target.checked }))}
              />
              <div>
                <strong>Auto reply</strong>
                <p>Se desligado, inbound nao dispara resposta automatica.</p>
              </div>
            </label>
            <article className="toggle-card">
              <div>
                <strong>Escopo do auto reply inbound</strong>
                <p>Define se contatos desconhecidos podem receber resposta automática.</p>
                <select
                  className="field"
                  value={settings.inbound_auto_reply_scope}
                  onChange={(event) => setSettings((current) => current && ({ ...current, inbound_auto_reply_scope: event.target.value }))}
                >
                  <option value="known_only">Responder só base cadastrada</option>
                  <option value="all">Responder todos</option>
                </select>
              </div>
            </article>
            <label className="toggle-card">
              <input
                type="checkbox"
                checked={settings.persist_unknown_inbound}
                onChange={(event) => setSettings((current) => current && ({ ...current, persist_unknown_inbound: event.target.checked }))}
              />
              <div>
                <strong>Persistir inbound desconhecido</strong>
                <p>Se desligado, o sistema não cria lead/conversa nova quando um número fora da base escreve.</p>
              </div>
            </label>
          </div>
        </Panel>

        <Panel title="Arquitetura modular do agente" subtitle="Escolha os módulos default usados quando a campanha ou o lead não apontarem algo mais específico.">
          <div className="form-grid">
            <label>
              <span>Oferta default</span>
              <select
                className="field"
                value={settings.active_offer_product_id ?? ''}
                onChange={(event) => setSettings({ ...settings, active_offer_product_id: event.target.value ? Number(event.target.value) : null })}
              >
                <option value="">Fallback do runtime atual</option>
                {offerProducts.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Estratégia default</span>
              <select
                className="field"
                value={settings.active_agent_strategy_id ?? ''}
                onChange={(event) => setSettings({ ...settings, active_agent_strategy_id: event.target.value ? Number(event.target.value) : null })}
              >
                <option value="">Fallback do runtime atual</option>
                {agentStrategies.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Recipe default de prospecção</span>
              <select
                className="field"
                value={settings.active_prospecting_recipe_id ?? ''}
                onChange={(event) => setSettings({ ...settings, active_prospecting_recipe_id: event.target.value ? Number(event.target.value) : null })}
              >
                <option value="">Sem recipe default</option>
                {prospectingRecipes.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
          </div>
        </Panel>

        <Panel title="Oferta e discurso" subtitle="Configura o que o agente tenta vender e o tom da abordagem.">
          <div className="form-grid">
            <label>
              <span>Nome da oferta</span>
              <input className="field" value={settings.offer_name} onChange={(event) => setSettings({ ...settings, offer_name: event.target.value })} />
            </label>
            <label>
              <span>Tom de venda</span>
              <input className="field" value={settings.sales_tone} onChange={(event) => setSettings({ ...settings, sales_tone: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Resumo da oferta</span>
              <textarea className="field field--textarea" value={settings.offer_summary} onChange={(event) => setSettings({ ...settings, offer_summary: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Objetivo comercial</span>
              <textarea className="field field--textarea" value={settings.offer_goal} onChange={(event) => setSettings({ ...settings, offer_goal: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>CTA desejado</span>
              <textarea className="field field--textarea" value={settings.cta_style} onChange={(event) => setSettings({ ...settings, cta_style: event.target.value })} />
            </label>
          </div>
        </Panel>

        <Panel title="Padroes de operacao" subtitle="Defaults para prospeccao e fila.">
          <div className="form-grid">
            <label>
              <span>Nicho padrao</span>
              <input className="field" value={settings.default_niche} onChange={(event) => setSettings({ ...settings, default_niche: event.target.value })} />
            </label>
            <label>
              <span>Cidade padrao</span>
              <input className="field" value={settings.default_city} onChange={(event) => setSettings({ ...settings, default_city: event.target.value })} />
            </label>
            <label>
              <span>Limite diario</span>
              <input className="field" type="number" value={settings.outreach_daily_limit} onChange={(event) => setSettings({ ...settings, outreach_daily_limit: Number(event.target.value) })} />
            </label>
            <label>
              <span>Atraso entre follow-ups (s)</span>
              <input className="field" type="number" value={settings.outreach_delay_seconds} onChange={(event) => setSettings({ ...settings, outreach_delay_seconds: Number(event.target.value) })} />
            </label>
            <label>
              <span>Delay default do auto reply (s)</span>
              <input className="field" type="number" value={settings.default_auto_reply_delay_seconds} onChange={(event) => setSettings({ ...settings, default_auto_reply_delay_seconds: Number(event.target.value) })} />
            </label>
          </div>
        </Panel>

        <Panel title="Ofertas / produtos" subtitle="Define exatamente o que está sendo vendido e quais claims a IA pode usar.">
          <div className="form-grid">
            <label>
              <span>Nome</span>
              <input className="field" value={offerForm.name} onChange={(event) => setOfferForm({ ...offerForm, name: event.target.value })} />
            </label>
            <label>
              <span>Categoria</span>
              <input className="field" value={offerForm.category} onChange={(event) => setOfferForm({ ...offerForm, category: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Resumo</span>
              <textarea className="field field--textarea" value={offerForm.summary} onChange={(event) => setOfferForm({ ...offerForm, summary: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Objetivo</span>
              <textarea className="field field--textarea" value={offerForm.objective} onChange={(event) => setOfferForm({ ...offerForm, objective: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>ICP / cliente ideal</span>
              <textarea className="field field--textarea" value={offerForm.target_customer} onChange={(event) => setOfferForm({ ...offerForm, target_customer: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Dores</span>
              <textarea className="field field--textarea" value={offerForm.pains} onChange={(event) => setOfferForm({ ...offerForm, pains: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Diferenciais / prova</span>
              <textarea className="field field--textarea" value={offerForm.differentiators} onChange={(event) => setOfferForm({ ...offerForm, differentiators: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>CTA primário</span>
              <textarea className="field field--textarea" value={offerForm.cta_primary} onChange={(event) => setOfferForm({ ...offerForm, cta_primary: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createOfferProduct(offerForm)
                setOfferProducts((current) => [created, ...current])
              }}
            >
              Criar oferta modular
            </button>
          </div>
          <div className="stack">
            {offerProducts.map((item) => (
              <article key={item.id} className="note-card">
                <strong>{item.name}</strong>
                <p>{item.summary}</p>
                <small>{item.category || 'sem categoria'} | objetivo: {item.objective || 'não definido'}</small>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Estratégias do agente" subtitle="Controla como a IA abre conversa, qualifica, trata objeção e faz handoff.">
          <div className="form-grid">
            <label>
              <span>Nome</span>
              <input className="field" value={strategyForm.name} onChange={(event) => setStrategyForm({ ...strategyForm, name: event.target.value })} />
            </label>
            <label>
              <span>Persona</span>
              <input className="field" value={strategyForm.persona} onChange={(event) => setStrategyForm({ ...strategyForm, persona: event.target.value })} />
            </label>
            <label>
              <span>Tom</span>
              <input className="field" value={strategyForm.tone} onChange={(event) => setStrategyForm({ ...strategyForm, tone: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Objetivo principal</span>
              <textarea className="field field--textarea" value={strategyForm.primary_goal} onChange={(event) => setStrategyForm({ ...strategyForm, primary_goal: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Estratégia de abertura</span>
              <textarea className="field field--textarea" value={strategyForm.opening_strategy} onChange={(event) => setStrategyForm({ ...strategyForm, opening_strategy: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Qualificação</span>
              <textarea className="field field--textarea" value={strategyForm.qualification_strategy} onChange={(event) => setStrategyForm({ ...strategyForm, qualification_strategy: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Objeções</span>
              <textarea className="field field--textarea" value={strategyForm.objection_strategy} onChange={(event) => setStrategyForm({ ...strategyForm, objection_strategy: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Follow-up</span>
              <textarea className="field field--textarea" value={strategyForm.follow_up_strategy} onChange={(event) => setStrategyForm({ ...strategyForm, follow_up_strategy: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Handoff / guardrails</span>
              <textarea className="field field--textarea" value={strategyForm.handoff_strategy} onChange={(event) => setStrategyForm({ ...strategyForm, handoff_strategy: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createAgentStrategy(strategyForm)
                setAgentStrategies((current) => [created, ...current])
              }}
            >
              Criar estratégia
            </button>
          </div>
          <div className="stack">
            {agentStrategies.map((item) => (
              <article key={item.id} className="note-card">
                <strong>{item.name}</strong>
                <p>{item.primary_goal}</p>
                <small>{item.persona || 'sem persona'} | {item.tone || 'sem tom explícito'}</small>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Templates de prompt" subtitle="Templates por fase para o resolvedor modular do agente.">
          <div className="form-grid">
            <label>
              <span>Estratégia</span>
              <select
                className="field"
                value={promptTemplateForm.agent_strategy_id ?? ''}
                onChange={(event) =>
                  setPromptTemplateForm({ ...promptTemplateForm, agent_strategy_id: event.target.value ? Number(event.target.value) : null })
                }
              >
                <option value="">Template global</option>
                {agentStrategies.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Nome</span>
              <input className="field" value={promptTemplateForm.name} onChange={(event) => setPromptTemplateForm({ ...promptTemplateForm, name: event.target.value })} />
            </label>
            <label>
              <span>Fase</span>
              <select className="field" value={promptTemplateForm.phase} onChange={(event) => setPromptTemplateForm({ ...promptTemplateForm, phase: event.target.value })}>
                <option value="outreach">outreach</option>
                <option value="reply">reply</option>
                <option value="followup">followup</option>
              </select>
            </label>
            <label className="form-grid__full">
              <span>System prompt</span>
              <textarea className="field field--textarea" value={promptTemplateForm.system_prompt} onChange={(event) => setPromptTemplateForm({ ...promptTemplateForm, system_prompt: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Instruções extras</span>
              <textarea className="field field--textarea" value={promptTemplateForm.instructions} onChange={(event) => setPromptTemplateForm({ ...promptTemplateForm, instructions: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createPromptTemplate(promptTemplateForm)
                setPromptTemplates((current) => [created, ...current])
              }}
            >
              Criar template
            </button>
          </div>
          <div className="stack">
            {promptTemplates.map((item) => (
              <article key={item.id} className="note-card">
                <strong>{item.name}</strong>
                <p>{item.system_prompt}</p>
                <small>{item.phase} | {item.agent_strategy_id ? `strategy ${item.agent_strategy_id}` : 'global'}</small>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Recipes de prospecção" subtitle="Receitas reutilizáveis para a nova busca agentica.">
          <div className="form-grid">
            <label>
              <span>Nome</span>
              <input className="field" value={recipeForm.name} onChange={(event) => setRecipeForm({ ...recipeForm, name: event.target.value })} />
            </label>
            <label>
              <span>Modo de descoberta</span>
              <select className="field" value={recipeForm.discovery_mode} onChange={(event) => setRecipeForm({ ...recipeForm, discovery_mode: event.target.value })}>
                <option value="search">search</option>
                <option value="agent">agent</option>
                <option value="hybrid">hybrid</option>
              </select>
            </label>
            <label>
              <span>Mínimo de contatos válidos</span>
              <input className="field" type="number" value={recipeForm.minimum_valid_contacts} onChange={(event) => setRecipeForm({ ...recipeForm, minimum_valid_contacts: Number(event.target.value) })} />
            </label>
            <label>
              <span>Profundidade</span>
              <input className="field" type="number" value={recipeForm.search_depth} onChange={(event) => setRecipeForm({ ...recipeForm, search_depth: Number(event.target.value) })} />
            </label>
            <label className="form-grid__full">
              <span>Objetivo</span>
              <textarea className="field field--textarea" value={recipeForm.objective} onChange={(event) => setRecipeForm({ ...recipeForm, objective: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Prompt do agente de busca</span>
              <textarea className="field field--textarea" value={recipeForm.system_prompt} onChange={(event) => setRecipeForm({ ...recipeForm, system_prompt: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            {['google', 'linkedin', 'instagram', 'facebook'].map((channel) => (
              <button
                key={channel}
                className={`button ${recipeForm.source_channels.includes(channel) ? 'button--primary' : 'button--ghost'}`}
                type="button"
                onClick={() =>
                  setRecipeForm((current) => ({
                    ...current,
                    source_channels: current.source_channels.includes(channel)
                      ? current.source_channels.filter((item) => item !== channel)
                      : [...current.source_channels, channel],
                  }))
                }
              >
                {channel}
              </button>
            ))}
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createProspectingRecipe(recipeForm)
                setProspectingRecipes((current) => [created, ...current])
              }}
            >
              Criar recipe
            </button>
          </div>
          <div className="stack">
            {prospectingRecipes.map((item) => (
              <article key={item.id} className="note-card">
                <strong>{item.name}</strong>
                <p>{item.objective}</p>
                <small>{item.discovery_mode} | canais: {item.source_channels.join(', ') || 'nenhum'}</small>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Campanhas" subtitle="Define ângulo, nicho e oferta por lote operacional.">
          {dashboardSummary?.campaigns?.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Scorecard</th>
                    <th>Leads</th>
                    <th>Contactados</th>
                    <th>Reply</th>
                    <th>Positiva</th>
                    <th>Reuniões</th>
                    <th>Opps</th>
                    <th>Fit médio</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboardSummary.campaigns.map((campaign) => (
                    <tr key={`score-${campaign.id}`}>
                      <td>
                        <div className="table__primary">
                          <strong>{campaign.name}</strong>
                          <span>{campaign.is_active ? 'ativa agora' : campaign.status}</span>
                        </div>
                      </td>
                      <td>{campaign.leads}</td>
                      <td>{campaign.contacted}</td>
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
          ) : null}
          <div className="form-grid">
            <label>
              <span>Nome</span>
              <input className="field" value={campaignForm.name} onChange={(event) => setCampaignForm({ ...campaignForm, name: event.target.value })} />
            </label>
            <label>
              <span>Nicho</span>
              <input className="field" value={campaignForm.niche} onChange={(event) => setCampaignForm({ ...campaignForm, niche: event.target.value })} />
            </label>
            <label>
              <span>Cidade</span>
              <input className="field" value={campaignForm.city} onChange={(event) => setCampaignForm({ ...campaignForm, city: event.target.value })} />
            </label>
            <label>
              <span>Oferta modular</span>
              <select
                className="field"
                value={campaignForm.offer_product_id ?? ''}
                onChange={(event) =>
                  setCampaignForm({ ...campaignForm, offer_product_id: event.target.value ? Number(event.target.value) : null })
                }
              >
                <option value="">Sem vínculo explícito</option>
                {offerProducts.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Estratégia modular</span>
              <select
                className="field"
                value={campaignForm.agent_strategy_id ?? ''}
                onChange={(event) =>
                  setCampaignForm({ ...campaignForm, agent_strategy_id: event.target.value ? Number(event.target.value) : null })
                }
              >
                <option value="">Sem vínculo explícito</option>
                {agentStrategies.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Recipe de prospecção</span>
              <select
                className="field"
                value={campaignForm.prospecting_recipe_id ?? ''}
                onChange={(event) =>
                  setCampaignForm({ ...campaignForm, prospecting_recipe_id: event.target.value ? Number(event.target.value) : null })
                }
              >
                <option value="">Sem vínculo explícito</option>
                {prospectingRecipes.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Delay reply (s)</span>
              <input className="field" type="number" value={campaignForm.reply_delay_seconds} onChange={(event) => setCampaignForm({ ...campaignForm, reply_delay_seconds: Number(event.target.value) })} />
            </label>
            <label className="toggle-inline">
              <input type="checkbox" checked={campaignForm.is_active} onChange={(event) => setCampaignForm({ ...campaignForm, is_active: event.target.checked })} />
              Ativar campanha
            </label>
            <label className="form-grid__full">
              <span>Oferta</span>
              <input className="field" value={campaignForm.offer_name} onChange={(event) => setCampaignForm({ ...campaignForm, offer_name: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Resumo</span>
              <textarea className="field field--textarea" value={campaignForm.offer_summary} onChange={(event) => setCampaignForm({ ...campaignForm, offer_summary: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Objetivo</span>
              <textarea className="field field--textarea" value={campaignForm.offer_goal} onChange={(event) => setCampaignForm({ ...campaignForm, offer_goal: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createCampaign(campaignForm)
                setCampaigns((current) => [created, ...current])
              }}
            >
              Criar campanha
            </button>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Campanha</th>
                  <th>Status</th>
                  <th>Nicho</th>
                  <th>Cidade</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr key={campaign.id}>
                    <td>{campaign.name}</td>
                    <td>{campaign.is_active ? 'ativa' : campaign.status}</td>
                    <td>{campaign.niche}</td>
                    <td>{campaign.city}</td>
                    <td>
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={async () => {
                          const updated = await api.updateCampaign(campaign.id, { is_active: true })
                          setCampaigns((current) => current.map((item) => (item.id === campaign.id ? updated : { ...item, is_active: false })))
                        }}
                      >
                        Ativar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Playbooks" subtitle="Regras e instruções por nicho e estágio de conversa.">
          <div className="form-grid">
            <label>
              <span>Nome</span>
              <input className="field" value={playbookForm.name} onChange={(event) => setPlaybookForm({ ...playbookForm, name: event.target.value })} />
            </label>
            <label>
              <span>Nicho</span>
              <input className="field" value={playbookForm.niche} onChange={(event) => setPlaybookForm({ ...playbookForm, niche: event.target.value })} />
            </label>
            <label>
              <span>Stage</span>
              <input className="field" value={playbookForm.stage} onChange={(event) => setPlaybookForm({ ...playbookForm, stage: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Instruções</span>
              <textarea className="field field--textarea" value={playbookForm.instructions} onChange={(event) => setPlaybookForm({ ...playbookForm, instructions: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Objeções</span>
              <textarea className="field field--textarea" value={playbookForm.objection_handling} onChange={(event) => setPlaybookForm({ ...playbookForm, objection_handling: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createPlaybook(playbookForm)
                setPlaybooks((current) => [created, ...current])
              }}
            >
              Criar playbook
            </button>
          </div>
          <div className="stack">
            {playbooks.map((playbook) => (
              <article key={playbook.id} className="note-card">
                <strong>{playbook.name}</strong>
                <p>{playbook.instructions}</p>
                <small>{playbook.niche || 'geral'} | {playbook.stage || 'qualquer estágio'}</small>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Knowledge base" subtitle="Provas, objeções e contexto permanente para o agente vender melhor.">
          <div className="form-grid">
            <label>
              <span>Título</span>
              <input className="field" value={knowledgeForm.title} onChange={(event) => setKnowledgeForm({ ...knowledgeForm, title: event.target.value })} />
            </label>
            <label>
              <span>Categoria</span>
              <input className="field" value={knowledgeForm.category} onChange={(event) => setKnowledgeForm({ ...knowledgeForm, category: event.target.value })} />
            </label>
            <label>
              <span>Nicho</span>
              <input className="field" value={knowledgeForm.niche} onChange={(event) => setKnowledgeForm({ ...knowledgeForm, niche: event.target.value })} />
            </label>
            <label className="form-grid__full">
              <span>Conteúdo</span>
              <textarea className="field field--textarea" value={knowledgeForm.content} onChange={(event) => setKnowledgeForm({ ...knowledgeForm, content: event.target.value })} />
            </label>
          </div>
          <div className="inline-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={async () => {
                const created = await api.createKnowledgeItem(knowledgeForm)
                setKnowledgeItems((current) => [created, ...current])
              }}
            >
              Criar item
            </button>
          </div>
          <div className="stack">
            {knowledgeItems.map((item) => (
              <article key={item.id} className="note-card">
                <strong>{item.title}</strong>
                <p>{item.content}</p>
                <small>{item.category} | {item.niche || 'geral'}</small>
              </article>
            ))}
          </div>
        </Panel>

        <div className="inline-actions">
          <button className="button button--primary" type="submit" disabled={saving}>
            {saving ? 'Salvando...' : 'Salvar configuracao'}
          </button>
          {error ? <span className="error-text">{error}</span> : null}
        </div>
      </form>
    </div>
  )
}
