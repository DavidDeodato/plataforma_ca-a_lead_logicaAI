# Roadmap de KPIs de Conversão

## North Star
- reuniões qualificadas agendadas por 100 leads contactados

## KPI executivo complementar
- oportunidades qualificadas por 100 leads contactados

## Guardrails
- nunca otimizar por volume bruto de mensagens
- tratar reply rate qualificada, fit do lead e aceite de reunião como sinais principais
- pausar campanhas/abordagens com rejeição alta ou falha de personalização

## Taxonomia oficial do funil
- `captured`
- `contacted`
- `replied`
- `positive_reply`
- `pain_confirmed`
- `fit_confirmed`
- `meeting_offered`
- `meeting_booked`
- `qualified_opportunity`
- `closed_won`
- `closed_lost`
- `do_not_contact`

## Sinais comerciais da IA
- `intent_status`: `unknown`, `curious`, `interested`, `high_intent`, `objection`, `not_interested`
- `pain_status`: `unknown`, `suspected`, `confirmed`
- `authority_status`: `unknown`, `influencer`, `decision_maker`, `not_decision_maker`
- `urgency_status`: `unknown`, `low`, `medium`, `high`
- `meeting_status`: `not_offered`, `offered`, `booked`, `won`, `lost`
- `objection_status`: `none`, `price`, `timing`, `already_has_solution`, `no_need`, `other`

## Lead Fit Score
- objetivo: ranquear quem merece abordagem primeiro
- escala: `0-100`
- faixas:
  - `alto`: >= 75
  - `medio`: >= 45 e < 75
  - `baixo`: < 45
- componentes:
  - qualidade do contato
  - aderência ao ICP
  - gap digital / necessidade de landing page
  - riqueza de contexto para personalização
  - potencial comercial aparente

## KPIs a instrumentar primeiro
- meetings_qualified_per_100_contacted
- qualified_opportunities_per_100_contacted
- reply_rate
- positive_reply_rate
- lead_fit_score_avg
- valid_contact_rate
- pain_confirmed_rate
- meeting_offer_acceptance_rate
- send_failure_rate
- time_to_first_outreach_minutes

## Hipóteses iniciais
- leads com `fit_score` alto e contexto suficiente devem responder melhor do que leads medianos
- mensagens que confirmam dor antes do CTA final devem gerar mais aceites de reunião
- campanhas com nicho/cidade mais estreitos tendem a converter melhor do que campanhas genéricas
- enriquecimento só vale o custo quando aumenta `positive_reply_rate` ou `meeting_booked_rate`

## Regras de decisão
- se `reply_rate` subir, mas `positive_reply_rate` não subir, a copy está atraindo curiosidade ruim
- se `positive_reply_rate` subir, mas `meeting_offer_acceptance_rate` não subir, o CTA ou timing está ruim
- se `fit_score_avg` do lote cair, o problema está na busca, não no agente
- se `send_failure_rate` subir, o problema é operacional/provedor, não de persuasão

## Próximas frentes depois desta fase
- A/B test de primeira abordagem
- score de objeção por nicho
- best next action por estágio
- analytics históricos por campanha

## Execução registrada
- `DashboardPage`, `LeadsPage`, `LeadDetailPage`, `ConversationsPage`, `SettingsPage` e `TestLabPage` já exibem scorecards e sinais desta fase
- lacuna fechada depois da primeira entrega: `AutomationPage` agora também mostra KPIs operacionais de fila, SLA e falha, alinhando a UI ao roadmap original
- camada seguinte já executada: `search_leads` e `list_conversations` passaram a anexar `priority_score`, `priority_label` e razões derivadas de `fit`, estágio, intenção e sinais operacionais, permitindo ordenar a operação por oportunidade real
- novo degrau executado: leads e conversas agora também expõem `recommended_action`, transformando o cockpit de leitura/ordenação em uma camada inicial de decisão operacional guiada por KPI
- novo degrau executado: `LeadDetail` e `Conversations` agora também recebem `suggested_playbook`, conectando a camada de decisão operacional ao repertório real de abordagem cadastrado no sistema
- novo degrau executado: `RuntimeConfigService.build_sales_instruction(...)` passou a aceitar contexto de `lead` e `conversation`, fazendo o motor real usar `recommended_action` e `suggested_playbook` no `agent-preview`, no primeiro outreach e nos workers de `follow_up` e `delayed_auto_reply`
- validação registrada: teste novo cobrindo instrução contextual do preview com playbook sugerido; suíte `tests/test_management_api.py` com `26 passed`, build do frontend ok e sem novos lints
