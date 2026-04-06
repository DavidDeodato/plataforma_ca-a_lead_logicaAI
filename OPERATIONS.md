# Operacao do MVP

## Estado atual
- backend pronto
- testes de smoke e cockpit passando
- prospeccao real minima validada
- modo seguro ligado por padrao
- cockpit interno ampliado com inbox operacional, takeover humano, envio manual, staging de prospeccao e inteligencia comercial

## Regra de seguranca
Enquanto `outbound_enabled=false` no `.env`, o sistema:
- nao envia mensagem real no WhatsApp
- registra mensagens como `draft_only`
- permite testar fluxo sem disparo externo

## Ordem recomendada
1. Rodar testes: `.\scripts\run-tests.ps1`
2. Subir API local: `.\scripts\start-local.ps1`
3. Subir frontend React: `.\scripts\start-frontend.ps1`
4. Conferir readiness: abrir `http://localhost:8000/api/readiness`
5. Abrir cockpit: `http://127.0.0.1:5173`
6. Criar/ativar campanha e defaults na tela `Configuracao`
7. Rodar pesquisa de clientes na tela `Pesquisa de clientes`
8. Revisar duplicados/lote antes de salvar ou disparar
9. Revisar leads e iniciar outreach pela UI ou cadastrar lead manualmente em `Leads`
10. Operar takeover/manual send na tela `Conversas`
11. So depois habilitar envio real pela tela `Configuracao` ou pela API de settings

## Quando habilitar envio real
Voce so deve trocar para `outbound_enabled=true` quando:
- aceitar o limite/plano do WASender
- tiver certeza do numero correto
- quiser realmente disparar mensagens

## Webhook em producao
Quando expor a API publicamente:
- configurar URL: `https://SEU-DOMINIO/webhooks/wasender`
- salvar `wasender_webhook_secret` no `.env`
- se quiser resposta automatica, ligar `auto_reply_enabled=true`

## Tunel temporario validado
- URL pública temporária usada na validação: `https://handy-head-outsourcing-reduce.trycloudflare.com`
- webhook temporário validado: `https://handy-head-outsourcing-reduce.trycloudflare.com/webhooks/wasender`
- observação: para receber eventos reais do WASender ainda falta apontar essa URL no dashboard da sessão

## Comandos uteis
```powershell
.\scripts\run-tests.ps1
.\scripts\start-local.ps1
.\scripts\start-frontend.ps1
.\scripts\smoke-prospect.ps1
.\scripts\run-followups.ps1
```

## O que ja foi validado
- `pytest`: `15 passed`
- Firecrawl search real: retornou resultado valido
- `POST /api/prospecting/run` real: respondeu `200` e retornou `1` lead
- webhook público temporário acessível externamente
- inbound externo criou lead/conversa
- auto-reply da LLM em `draft_only`
- `messages.update` atualizou status persistido
- frontend React buildando e servindo localmente
- novas rotas do cockpit interno respondendo no backend real
- conversa demo operacional criada em modo seguro
- task demo vinculada à conversa operacional
- takeover manual, ajuste de delay e envio manual humano validados na API local da conversa demo

## Fluxos novos do cockpit
- `Configuracao`: runtime global, campanhas, playbooks e knowledge base
- `Pesquisa de clientes`: assistente guiado + lote em staging com preview e ações `save_only`, `save_and_start_outreach`, `reject`
- `Leads`: seleção em lote, cadastro manual com contexto e `start outreach`
- `Conversas`: inbox 3 painéis, `Assumir controle`, `Liberar controle`, `Marcar como lida`, delay por conversa, reply toggle e envio manual
- `Automação`: tasks + fila de revisão humana

## O que ainda e operacionalmente pendente
- decidir plano do WASender
- configurar webhook publico
- definir nicho/cidade oficial do primeiro lote
- validar visualmente a UI clicando nas telas em uma sessao com browser automation funcional ou manualmente no navegador
