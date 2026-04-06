import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import { EmptyState } from '../components/EmptyState'
import { Panel } from '../components/Panel'
import { api } from '../lib/api'
import type { Campaign, KnowledgeItem, Playbook, RuntimeSettings } from '../lib/types'

export function SettingsPage() {
  const [settings, setSettings] = useState<RuntimeSettings | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [playbooks, setPlaybooks] = useState<Playbook[]>([])
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [campaignForm, setCampaignForm] = useState({
    name: '',
    niche: '',
    city: '',
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

  useEffect(() => {
    Promise.all([api.getRuntimeSettings(), api.listCampaigns(), api.listPlaybooks(), api.listKnowledgeItems()])
      .then(([runtime, currentCampaigns, currentPlaybooks, currentKnowledge]) => {
        setSettings({ ...runtime, outbound_enabled: true })
        setCampaigns(currentCampaigns)
        setPlaybooks(currentPlaybooks)
        setKnowledgeItems(currentKnowledge)
      })
      .catch((err: Error) => setError(err.message))
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

        <Panel title="Campanhas" subtitle="Define ângulo, nicho e oferta por lote operacional.">
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
