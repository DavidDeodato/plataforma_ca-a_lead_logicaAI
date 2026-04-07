# Memory Bank do Projeto

## Objetivo
Construir um MVP de prospecção que:
- encontre negócios locais com potencial para comprar landing page
- enriqueça o contexto comercial de cada lead com Firecrawl
- inicie e continue conversas no WhatsApp via WASender
- registre tudo no Postgres
- separe leads qualificados para handoff humano

## Stack confirmada
- Python
- FastAPI
- Postgres
- Firecrawl
- OpenAI
- WASender

## Credenciais
- `firecrawl_api`: presente no `.env`
- `openai_api_key`: presente no `.env`
- `database_url`: presente no `.env`, mas atualmente veio com prefixo duplicado `DATABASE_URL=` dentro do valor
- `wasender_api_key`: presente no `.env`
- `wasender_webhook_secret`: presente no `.env` e validado em runtime

## Decisões do MVP
- foco inicial em um nicho/cidade por execução
- prospecção primeiro, expansão depois
- nada de links na primeira mensagem
- auto-resposta apenas para mensagens recebidas de leads
- classificação operacional de lead: `cold`, `warm`, `hot`, `qualified`, `do_not_contact`

## Estrutura criada
- `app/main.py`: inicialização da API
- `app/core`: config e banco
- `app/db`: modelos e schemas
- `app/api`: rotas HTTP e webhook
- `app/services`: integração Firecrawl, WASender e motor conversacional
- `app/workers`: rotinas de prospecção e follow-up
- `app/api/routes/management.py`: API gerencial para detalhe, filtros, tasks e ações manuais
- `app/services/runtime_config.py`: configuração operacional dinâmica em banco
- `frontend`: painel React operacional separado do backend Python
- `scripts`: atalhos PowerShell de operacao
- `OPERATIONS.md`: runbook operacional

## Pendências operacionais
- ligar a URL pública atual no painel do WASender quando quiser webhook real do provedor
- validar envio real para um número de teste controlado quando houver alvo explícito
- decidir se vai continuar no plano gratuito do WASender, que na tela atual mostra limite de `1 request por minuto`
- considerar upgrade do WASender se quiser operação contínua, porque o plano gratuito está retornando `429` quando tenta enviar mais de 1 mensagem por minuto

## Validacoes executadas
- import e inicializacao da aplicacao: ok
- inicializacao do banco: ok
- testes automatizados de smoke + API gerencial: `15 passed`
- Firecrawl search real com 1 resultado: ok
- `POST /api/prospecting/run` real com `limit=1`: respondeu `200` e retornou lead
- túnel HTTPS público com `cloudflared`: ok
- `POST` externo real no webhook público: ok
- criação de lead/conversa via webhook público: ok
- auto-reply da LLM em modo seguro (`draft_only`): ok
- `messages.update` externo atualizando status persistido: ok
- build do frontend React: ok
- servidor local do frontend em `http://127.0.0.1:5173`: ok
- lead sintético de validação pública removido após o teste: ok
- rotas novas do cockpit interno carregando no backend real: ok (`/api/campaigns`, `/api/playbooks`, `/api/knowledge-items`, `/api/prospecting/batches`)
- lead operacional de demonstração criado via API: `Cockpit Demo Lead`
- conversa operacional de demonstração criada em `draft_only`: ok
- task de follow-up vinculada à conversa operacional de demonstração: ok
- takeover manual, delay por conversa e envio manual humano validados na API local com a thread demo: ok
- assistente de pesquisa validado na API real com interpretação de `barbearias em Vitoria`: ok
- correção de typo próximo em cidade no assistente de pesquisa validada na API real (`Bitoria Es` -> `Vitoria, ES`): ok
- cadastro manual de lead validado na API real com contexto salvo em `notes`: ok
- busca parcial por nome do lead manual no endpoint de leads: ok
- UI de pesquisa agora destaca `Modo rápido` sem enriquecimento como padrão e avisa quando o modo detalhado pode demorar: ok
- nova rodada de `pytest` focada em `tests/test_management_api.py`: `13 passed`
- nova rodada de `npm run build` no frontend após refactor do inbox/chat: ok
- `POST /api/outreach/4/start` validado na API real após correções: criou conversa `draft_only` e retornou thread com mensagem do agente
- `POST /api/prospecting/batches/preview` real com `limit=3` e `enrich=false`: retornou somente candidatos com `phone_number`
- `POST /api/prospecting/batches/preview` real com `limit=3`, `enrich=false` e `validate_phone_format=true`: retornou somente candidatos com telefone em formato válido
- backend local travou novamente no reload do `watchfiles` após patch e precisou restart manual do script `start-local.ps1`: corrigido operacionalmente nesta sessão
- validação visual clicando na UI: bloqueada nesta sessão por indisponibilidade real da automação de navegador
- nova rodada de `npm run build` após ajustes de UX da inbox/chat: ok
- novo teste real de envio manual em `/api/conversations/4/messages/manual-send`: sucesso no WASender com `msgId=39677036`, `jid=+5527999000202` e status inicial `in_progress`
- teste real de envio manual em threads com falha aparente confirmou erro externo do provedor: `429` do WASender com mensagem `You are on a free trial. You can send 1 message every 1 minute.`

## Modo operacional atual
- `outbound_enabled=true`
- `auto_reply_enabled=false`
- resultado: envio manual e outbound do agente saem de verdade; resposta automática continua desligada por padrão

## UI gerencial React
- dashboard com readiness, safe mode, métricas e oferta atual
- listagem de leads com filtros
- detalhe do lead com pesquisa, timeline, preview e ações
- inbox operacional em 3 painéis com takeover humano, mark-as-read, delay por conversa e composer manual
- inbox refinado para visual mais próximo de WhatsApp: lista de threads à esquerda, header da conversa, toolbar de ações, bolhas inbound/outbound distintas e painel lateral de contexto
- página de conversas agora trava a altura útil e usa scroll interno nas colunas da inbox em vez de empurrar a página toda
- hierarquia visual da conversa foi reforçada com `Inbox`, `Conversa atual` e `Controles da thread`, além de cards clicáveis mais evidentes
- layout da tela de conversas foi comprimido para estilo mais próximo de WhatsApp Web: coluna esquerda menor, centro dominante e topo compacto
- sidebar principal agora pode ser recolhida por hamburger para liberar espaço operacional
- hamburger duplicado removido; agora só fica o botão externo ao menu lateral
- bloco visual `LeadOS`/ícone de IA removido da sidebar; menu lateral ficou só com as opções de navegação
- fila de automação/tasks com destaque para revisão humana pendente
- configuração operacional sem editar `.env` para rotinas normais
- campanhas, playbooks e knowledge base operacionais na UI
- pesquisa de clientes em rota dedicada com assistente guiado, lote em staging, revisão e ações `save_only`, `save_and_start_outreach` e `reject`
- pesquisa agora nasce em `Modo rápido` (`enrich=false`) e permite ligar `Modo detalhado` explicitamente
- cadastro manual de lead na tela de leads com opção de iniciar contato imediatamente
- atalhos explícitos no dashboard para `Pesquisa de clientes`, `Cadastrar lead manualmente` e `Abrir conversas`
- ações críticas do frontend agora mostram loading e status textual em `Leads`, `LeadDetail`, `Conversas` e revisão de lote
- `Start` individual agora abre a conversa quando funciona e mostra claramente quando o lead está sem telefone/WhatsApp
- `save_and_start_outreach` não quebra mais o lote inteiro quando o candidato não tem telefone; o candidato fica como `saved_missing_contact`
- preview de prospecção agora descarta candidatos sem telefone/WhatsApp antes de entrar no lote; a busca passa a priorizar consultas com `whatsapp`, `telefone` e `contato`
- busca agora aceita opção de validar formato do número; quando ligada, telefones com comprimento/padrão inválido são descartados e a prospecção continua buscando candidatos válidos
- a página `Automação` agora também expõe scorecards operacionais da fase de KPI: fila ativa, falhas outbound, taxa de falha, tempo até primeiro outreach, `queued_outbound`, `delayed_auto_reply`, `follow_up`, tasks atrasadas e risco de SLA
- leads e conversas agora também podem ser priorizados operacionalmente por um score derivado de `fit_score`, estágio do funil, intenção, dor confirmada, reunião, unread e review humano; `LeadsPage` e `ConversationsPage` ganharam ordenação por prioridade/fitting/recência
- a operação agora também recebe `recommended_action` derivada de contexto comercial e operacional (`review_now`, `reply_now`, `fix_contact`, `ask_for_meeting`, `handle_objection`, `confirm_fit`, `continue_conversation`, `start_outreach`), exibida em `LeadsPage`, `ConversationsPage` e `LeadDetailPage`
- o cockpit agora também sugere `playbook` contextual por lead/thread com base em `niche`, `funnel_stage`, objeção e qualificação, reutilizando a base já cadastrada em `Playbooks`
- composer do chat manual foi ajustado para UX de mensageria: `Enter` envia, `Shift+Enter` quebra linha, envio atualiza a thread local sem recarregar a tela inteira e o botão virou ação circular com ícone
- runtime atual foi ajustado para `outbound_enabled=true` e `auto_reply_enabled=false`; envio manual e outbound do agente devem sair de verdade, mas resposta automática segue desligada
- o padrão do projeto foi trocado para outbound ativo por default (`app/core/config.py`, `app/services/runtime_config.py`, `.env`, `.env.example`)
- a UI de configuração não expõe mais toggle para desligar outbound real
- teste real de envio manual em `/api/conversations/4/messages/manual-send`: sucesso no WASender com `msgId=39676067`, `jid=+5527999000202` e status inicial `in_progress`
- a tela de conversas agora permite fechar e reabrir a coluna `Inbox` e o painel `Controles da thread`, deixando o centro mais próximo de um layout estilo WhatsApp Web
- os toggles de `Inbox` e `Controles` foram reforçados com alças flutuantes na borda do workspace do chat para não depender de botão escondido no header
- o layout interno dos painéis da inbox foi corrigido com `flex` em vez de `height: 100%` no `panel__body`, reduzindo o corte do rodapé/composer na conversa
- a thread selecionada agora fica persistida na URL com `conversationId`, então recarregar a página mantém a mesma conversa aberta em vez de voltar para outra thread aleatória
- a tela de conversas agora faz polling automático de inbox e thread ativa a cada 5 segundos para refletir mensagens novas sem exigir reload manual
- o composer do chat continua no rodapé do painel central e o botão de envio mostra loading visível com `Enviando...`
- a UI do chat agora transforma `send_failed` em motivo legível, incluindo mensagem do WASender e dica de espera quando o provedor devolve `retry_after`
- a causa real dos `faild` recentes não era bug cego da plataforma: o WASender respondeu `429` por limite do plano gratuito
- a marca `NexLead` agora usa os PNGs reais fornecidos em `assets`: logo completa no sidebar (`logo_sem_fundi_e_com_nome.png`) e logo sem nome no favicon (`logo_sem_fundo_e_sem_nome.png`)
- teste local no webhook `/webhooks/wasender` com `messages.upsert` inbound sintético confirmou atualização correta no backend: `unread_count`, `last_inbound_at`, `last_message_at` e preview da inbox mudaram imediatamente
- os envios outbound agora respeitam a janela do provedor: quando não dá para mandar na hora, a mensagem vira `queued_waiting`/`queued_retry` e entra em task `queued_outbound`
- o backend local agora roda um loop interno do worker de follow-up/fila a cada 5 segundos durante a vida da API, sem depender de disparo manual do script para processar `queued_outbound`, `delayed_auto_reply` e `follow_up`
- a conversa agora mostra countdown para auto-reply pendente e para mensagens na fila de envio, usando `lead.tasks` filtradas pela thread atual
- a revisão de lotes em `Pesquisa de clientes` não redireciona mais automaticamente ao salvar e iniciar; ela passa a mostrar quantos contatos já saíram e quantos estão na fila aguardando a janela de 1 minuto
- validação real via API local confirmou mensagem manual enfileirada com status `queued_waiting` e `scheduled_for` retornado no metadata
- bug de navegação na inbox identificado e corrigido: o `leadId` antigo ficava preso na URL e o polling podia forçar a UI de volta para outra thread; agora a seleção manual limpa `leadId`, mantém `conversationId` e usa polling mais curto
- diagnóstico operacional confirmado para inbound real ausente: não apareceu nenhum `POST /webhooks/wasender` recente nos logs da API local, então o backend não está recebendo eventos reais do WASender nesta sessão
- correção operacional aplicada no `.env`: a chave estava como `API_SECRET_WEEBHOOK`, mas o backend lê `wasender_webhook_secret`; a API foi reiniciada e passou a carregar o secret corretamente
- novo teste externo no webhook público após corrigir o nome da variável: ok, mensagem `public-webhook-test-002` persistida na conversa `4` com `status=received`
- diagnóstico fechado do inbound real: a doc oficial do WASender mostra que `messages.received` é um evento separado de `messages.upsert` e envia `data.messages` como objeto único
- correção aplicada no backend para aceitar tanto `messages.upsert` quanto `messages.received`, normalizando `data.messages` quando vier como objeto ou lista
- validação automatizada nova em `tests/test_smoke.py`: cobertura para `messages.upsert` e `messages.received`, ambas passando
- novo teste externo realista via webhook público com evento `messages.received`: ok, mensagem `public-webhook-test-003` persistida na conversa `4` com `status=received`
- bug crítico da inbox identificado: havia duas rotas diferentes usando o mesmo caminho `/api/conversations/{id}`; o frontend abria por `conversation_id`, mas uma rota antiga interpretava o mesmo número como `lead_id`, fazendo várias threads abrirem erro ou conversa errada
- correção aplicada: a rota por lead foi movida para `/api/leads/{lead_id}/conversation`, enquanto `/api/conversations/{conversation_id}` ficou exclusivamente para thread real
- validação real após o patch: `GET /api/conversations/22` agora retorna a conversa `22`, enquanto `GET /api/leads/22/conversation` retorna corretamente a conversa do lead `22`
- melhoria operacional na revisão de lotes: `prospecting_candidates` agora persistem `lead_id`, `conversation_id`, `outreach_external_message_id`, `delivery_status` e `delivery_note`
- `save_and_start_outreach` deixou de resumir tudo como "enviado": agora grava o status inicial real do provedor/filas e a UI do lote ganhou coluna de entrega com botão para abrir a conversa quando ela existir
- sincronização adicional: quando o WASender atualiza o status de uma mensagem outbound, o candidato do lote correspondente também é atualizado para refletir `contacted`, `queued_contact` ou `contact_failed`
- validação automatizada após essas correções: `25 passed` em `tests/test_smoke.py` + `tests/test_management_api.py`; `npm run build`: ok
- ajuste visual adicional na inbox/chat: quando a thread tem poucas mensagens, o histórico agora fica ancorado no rodapé do painel (`justify-content: flex-end` em `.timeline--chat`), eliminando o "buraco" grande acima do composer
- correção lógica adicional na inbox: `loadList` e `loadSelected` agora usam guards por `requestId` e validam a thread ainda selecionada antes de aplicar resposta assíncrona, evitando que polling/resposta velha faça a conversa "piscar" ou volte para outro contato
- causa operacional do sumiço do timer de auto-reply identificada: o runtime global estava com `auto_reply_enabled=false`, então threads com auto-reply local ligado não criavam `delayed_auto_reply`
- correção operacional aplicada nesta sessão: runtime global atualizado para `auto_reply_enabled=true` e backfill manual executado na conversa `28`, gerando `delayed_auto_reply` e depois `queued_outbound` por limite de 1/min do provedor
- causa principal da duplicidade de mensagens identificada: a plataforma salvava a outbound no momento do envio e depois o `webhook` `fromMe` do WASender chegava como nova `provider_outbound`, gerando segunda linha
- correção aplicada no backend para reconciliar o `webhook fromMe` com a outbound já existente em vez de criar uma nova mensagem; teste focado passou em `tests/test_management_api.py`
- mitigação adicional na UI: a tela de conversas agora oculta a cópia `provider_outbound` quando já existe a outbound original (`agent`/`human`) com o mesmo texto na mesma thread
- limpeza operacional executada no banco: 4 duplicatas antigas `provider_outbound` foram removidas com segurança; algumas entradas antigas ficaram preservadas quando não havia merge inequívoco
- ajuste de UX na inbox/chat: o scroll voltou a funcionar no histórico interno usando wrapper `.timeline--chat-content` com espaçador flexível, em vez de ancorar diretamente a área scrollável
- ajuste de fila na conversa: a UI agora cruza tasks pendentes globais com os `message_id` da thread para exibir countdown e posição real na fila; quando a task ainda não estiver disponível, cai em fallback pelo `metadata.queue.scheduled_for` da própria mensagem
- orientação operacional confirmada para troca de número/sessão no WASender: o código local depende de `wasender_api_key`, `wasender_webhook_secret` e `wasender_api_base_url`; ao criar uma nova sessão/instância, o mais seguro é atualizar no `.env` a `api_key` e o `webhook_secret` exibidos pela sessão nova e manter o mesmo `webhook_url`/eventos no painel
- diagnóstico operacional do webhook local: o endpoint público `trycloudflare` pode ficar indisponível mesmo com a API local viva; quando isso acontecer, o WASender mostra erro no domínio/webhook, e a correção é reiniciar o túnel público e atualizar no painel da sessão o novo `Webhook URL (POST)`
- procedimento operacional revalidado em 2026-04-06: ao trocar internet/religar a máquina, primeiro subir `.\scripts\start-local.ps1`, depois recriar o túnel `cloudflared tunnel --url http://127.0.0.1:8000`; a URL pública atual validada é `https://introduce-dictionaries-advertisements-explains.trycloudflare.com` e o webhook correspondente é `https://introduce-dictionaries-advertisements-explains.trycloudflare.com/webhooks/wasender`
- validação do túnel atual: `GET /health` público retornou `200 ok` e `POST /webhooks/wasender` público alcançou o backend retornando `401 Invalid webhook signature`, confirmando conectividade ponta a ponta
- suporte inicial a múltiplas sessões/números do WhatsApp implementado: foi criada a entidade `whatsapp_sessions` no backend com `is_active`, `api_key`, `webhook_secret`, `wasender_session_id`, `phone_number`, `status` e metadados de webhook
- a inbox e as conversas agora podem ser separadas por sessão WhatsApp: `Conversation` passou a carregar `whatsapp_session_id`, a API de conversas aceita filtro por linha ativa/sessão específica/legado, e o frontend mostra a linha da thread e filtra por número
- o backend agora possui API para gestão de sessões WhatsApp: listar, cadastrar manualmente, ativar, sincronizar do WASender via PAT, iniciar conexão e buscar QR code
- integração validada com a doc do WASender: criação/listagem/conexão/QR usam endpoints de sessão autenticados por `WASENDER_PERSONAL_ACCESS_TOKEN`; sem PAT, ainda é possível cadastrar sessões manualmente na plataforma para rastreio e ativação
- compatibilidade preservada com o setup antigo: na subida da API, uma sessão “importada do .env” é criada/atualizada automaticamente a partir de `WASENDER_API_KEY` e `WASENDER_WEBHOOK_SECRET`, evitando quebrar a operação atual enquanto a UI assume o controle gradualmente
- validação operacional pós-implementação das sessões WhatsApp: `pytest` passou com `29/29`, `npm run build` passou, backend local e frontend local subiram corretamente, `/api/whatsapp-sessions` respondeu com a sessão importada do `.env` e a sessão manual temporária, criação e ativação de sessão manual foram validadas por API e a sessão original do `.env` foi restaurada como ativa ao final
- validação dos filtros por sessão na API: `active_session_only=true` retornou `0` conversas para a sessão ativa atual sem threads atribuídas; `whatsapp_session_id=2` também retornou `0`; `legacy_only=true` retornou o histórico antigo existente com `whatsapp_session_id=null`, confirmando separação de escopo por sessão vs legado
- gap atual de verificação: a validação visual/automatizada no navegador da nova UI (`Configuração -> Linhas WhatsApp` e filtro de sessão em `Conversas`) não pôde ser concluída nesta sessão por indisponibilidade da automação de browser, então a camada UI foi validada por build + leitura de código + contratos de API, mas não por clique/screenshot end-to-end

## Cockpit interno completo - fase atual
- conversa agora tem estado operacional próprio: `manual_mode`, `automation_paused`, `auto_reply_enabled`, `reply_delay_seconds`, `assignee`, `taken_over_at`, `taken_over_by`, `unread_count`, `last_inbound_at`, `last_outbound_at`, `pending_human_review` e `pending_draft`
- envio manual humano agora existe no backend e fica registrado em mensagem com `author_role="human"`
- webhook inbound agora atualiza fila operacional e agenda `delayed_auto_reply` por conversa em vez de responder imediatamente em linha
- worker de follow-up agora trata `follow_up` e `delayed_auto_reply`
- worker de follow-up agora também processa `queued_outbound`
- bulk actions foram adicionadas para leads e conversas
- inteligência comercial foi adicionada com tabelas/rotas de `campaigns`, `playbooks`, `knowledge_items`, `prospecting_batches` e `prospecting_candidates`
- `prospecting_candidates` agora marcam duplicidade (`existing_lead_id`, `existing_lead_status`) antes de salvar na base
- o contexto manual do lead em `notes` agora entra no snapshot usado pelo agente
- o assistente e a criação do lote agora normalizam cidade com fuzzy match para evitar zero resultados por erro pequeno de digitação

## Observacao importante de validacao
- eu consegui validar build, testes, contratos da API real e estado operacional persistido
- eu consegui validar por API real tanto cenário de sucesso quanto cenário de falha do envio manual
- eu nao consegui validar visualmente clicando nas telas nesta sessao porque a automacao de navegador nao estava disponivel quando tentei usar o browser
- o proximo passo operacional ideal e uma rodada curta de validacao manual na UI ou nova sessao com browser automation funcional

## URL pública temporária atual
- `https://handy-head-outsourcing-reduce.trycloudflare.com`
- webhook esperado: `https://handy-head-outsourcing-reduce.trycloudflare.com/webhooks/wasender`

## Observações importantes
- o código foi escrito para aceitar o `.env` atual mesmo com `database_url=DATABASE_URL=...`
- a primeira execução deve usar volume baixo para reduzir risco no WhatsApp

## Framework de KPIs de conversão
- north star KPI definido para a plataforma: `reuniões qualificadas agendadas por 100 leads contactados`
- objetivo primário da IA no fluxo comercial: levar o lead a aceitar uma próxima etapa concreta (`call`, diagnóstico, briefing ou proposta)
- objetivo secundário da IA: detectar e registrar `intenção de compra`, `dor confirmada`, `autoridade`, `urgência` e `fit` antes do handoff humano
- guardrail principal anti-spam: não medir sucesso por mensagens enviadas; medir por `reply rate qualificada`, `meeting rate`, `positive intent rate` e `lead quality`
- KPIs do topo do funil definidos: `% de leads com perfil ideal`, `% de leads com dor aparente`, `% com contato válido`, `% sem duplicidade`, `% com enriquecimento útil`
- KPIs de conversa definidos: `reply rate`, `positive reply rate`, `intent detection accuracy`, `tempo até primeira resposta`, `taxa de continuidade após 2ª mensagem`, `meeting ask acceptance rate`
- KPIs de conversão definidos: `qualified opportunity rate`, `meeting booked rate`, `show-up rate`, `proposal rate`, `closed-won rate`, `receita por lote`
- KPIs operacionais definidos: `tempo entre captura e primeiro outreach`, `tempo entre inbound e resposta`, `taxa de falha de envio`, `taxa de fila`, `custo por lead contactado`, `custo por reunião`
- KPIs de qualidade da IA definidos: `personalização percebida`, `aderência ao contexto do lead`, `clareza do CTA`, `taxa de objeção bem tratada`, `taxa de fallback para humano`, `falsos positivos de intenção`
- direção estratégica consolidada: a plataforma deve otimizar `quem contactar`, `como abrir a conversa`, `como adaptar a argumentação`, `quando pedir reunião` e `quando parar`, sempre maximizando conversão real e não volume bruto
- lacuna fechada nesta sessão: `frontend/src/pages/AutomationPage.tsx` deixou de ser só uma tabela de tasks e passou a refletir a frente de KPIs operacionais prometida no roadmap
- próximo degrau já iniciado e entregue: a operação deixou de ser só leitura de KPI e passou a usar um `priority_score` derivado para ordenar base e inbox por urgência/oportunidade comercial
- degrau seguinte entregue nesta sessão: além de ordenar, o cockpit passou a sugerir a próxima ação concreta para cada lead/thread com base no funil e nos sinais comerciais
- degrau adicional entregue: o cockpit passou a sugerir também o `playbook` mais aderente para conduzir a conversa ou o próximo contato, aproximando a recomendação operacional do motor real de vendas
- fechamento adicional desta sessão: o `agent-preview`, a primeira mensagem de outreach, o auto-reply e o follow-up passaram a receber instrução contextual por lead, incluindo `recommended_action`, estágio/sinais atuais e o `suggested_playbook` mais aderente
- validação desta etapa: `tests/test_management_api.py` com `26 passed`, `npm run build` ok no frontend e `ReadLints` sem novos erros
- validação externa real do Firecrawl `v2/agent` concluída nesta sessão: funcionou bem para descoberta aberta com `schema` e critério mínimo de leads válidos, mas um cenário mais aberto de sinais recentes ficou em `processing` além do timeout local; decisão consolidada: o motor de prospecção passa a operar com `discovery_mode=search|agent|hybrid`, preservando fallback híbrido como caminho seguro
- nova fundação modular entregue no backend: `offer_products`, `agent_strategies`, `prompt_templates` e `prospecting_recipes` agora existem no domínio e já podem ser vinculados a `campaigns`, `leads`, `messages` e `prospecting_batches`
- o resolvedor do agente deixou de depender só de string monolítica: agora cada mensagem pode carregar `instruction_snapshot`, `prompt_phase` e contexto resolvido por fase (`outreach`, `reply`, `followup`) a partir de oferta, estratégia, template, knowledge, playbook e sinais do lead
- política explícita de inbound desconhecido entregue: runtime ganhou `inbound_auto_reply_scope` (`known_only`/`all`) e `persist_unknown_inbound`; por padrão seguro o sistema persiste o inbound desconhecido com `source_origin=inbound_unknown` e `inbound_unverified=true`, mas não agenda auto-reply quando o escopo está em `known_only`
- nova superfície de configuração entregue na UI/API: `Settings` agora expõe inbound scope, defaults modulares, CRUD básico de ofertas, estratégias, templates e recipes, além de permitir vincular campanha a `offer_product`, `agent_strategy` e `prospecting_recipe`
- novo workbench de prospecção entregue sobre a página de pesquisa: seleção de `recipe`, `prompt` livre, canais, `discovery_mode`, profundidade, mínimo de contatos válidos, fallback híbrido e créditos máximos do agent; o assistente agora devolve `recipe_preview`, warnings e variáveis sugeridas
- melhoria adicional de UX entregue na workbench de prospecção: a página foi reorganizada em etapas verticais claras, todos os campos passaram a ter nome + descrição visível, o uso de `search|agent|hybrid` ficou explícito, foram adicionadas variáveis prontas para o prompt (`{{niche}}`, `{{city}}`, `{{minimum_valid_contacts}}`, etc.) e a UI agora mostra um preview renderizado do prompt final antes da execução
- analytics iniciais por `offer`, `strategy` e `recipe` foram adicionados ao `dashboard summary`, permitindo medir volume, contactados, `reply_rate`, reuniões e `fit_score_avg` por módulo
- validação final desta fase: `tests/test_management_api.py` com `28 passed`, `npm run build` ok no frontend e `ReadLints` sem novos erros
- evolução desta sessão na workbench de prospecção: a UI ficou mais guiada por contexto, com controles condicionais por `discovery_mode` para esconder parâmetros sem sentido quando o fluxo está em `search`
- biblioteca de prompts de prospecção entregue no backend/frontend com dois níveis de lastro: `prospecting_prompt_categories` (tese comercial, ex: vender landing page para barbeiros) e `prospecting_prompts` (variações testadas dentro da tese)
- a execução do lote agora persiste `prompt_category_id`, `prompt_id` e `prompt_snapshot` em `prospecting_batches`, propaga esse lastro para `prospecting_candidates` e grava o mesmo vínculo em `leads`, permitindo relacionar resultados posteriores do funil ao prompt que originou o contato
- o `dashboard summary` agora expõe analytics também por `prompt_categories` e `prospecting_prompts`, abrindo caminho para comparar performance real de prompts dentro da mesma categoria comercial
- validação desta sessão: `npm run build` ok no frontend, `ReadLints` sem erros novos e `python -m py_compile` ok nos arquivos Python alterados
- limitação de validação desta sessão: `pytest tests/test_management_api.py` não pôde rodar no ambiente atual porque o Python disponível não tem `fastapi` instalado (`ModuleNotFoundError` na coleta), então a cobertura automatizada de API ficou preparada mas não executada aqui
- refinamento adicional entregue na workbench: agora existe botão para `montar prompt base automaticamente` a partir do alvo atual, categoria selecionada e modo (`search|agent|hybrid`), reduzindo o trabalho manual de escrever prompt do zero
- a workbench agora também mostra analytics operacionais por `prompt_categories` e `prospecting_prompts` na própria tela de prospecção, filtrando pelo contexto selecionado quando houver categoria/prompt ativo
- o `DashboardPage` passou a exibir scorecards tabelados de categorias de prompt e prompts vencedores, conectando o lastro do topo do funil com leitura executiva de reply, reuniões, fechamento e fit médio
- validação desta rodada incremental: `npm run build` ok novamente após os refinamentos de analytics/UI e `ReadLints` continuou sem erros novos
- correção estrutural de UX entregue após feedback direto do uso real: a `TestLabPage` deixou de tentar concentrar biblioteca, analytics, criação de categorias e montagem da busca no mesmo scroll
- a tela principal de prospecção agora virou um fluxo curto com 4 passos: descrever a busca, preencher o essencial, revisar o prompt e rodar o lote
- biblioteca de prompts, analytics de prompts e configurações avançadas passaram para superfícies separadas abertas sob demanda (`workspace modals`), reduzindo carga cognitiva sem remover poder operacional
- presets de intensidade (`rápida`, `balanceada`, `profunda`) foram adicionados para o caminho principal, deixando o ajuste fino técnico fora da jornada inicial
- validação desta reestruturação: `npm run build` ok no frontend e `ReadLints` sem erros novos após a refatoração da `TestLabPage`
- debug operacional desta sessão: a rota local e o backend estavam no ar (`127.0.0.1:8000`), então o problema de `start` não era indisponibilidade da API
- causa 1 confirmada no start: a sessão ativa estava errada; a conversa nova caiu na `Sessão importada do .env` (id `1`, sem número visível) em vez da sessão manual nova. A linha ativa foi trocada operacionalmente para a sessão `2` (`Sessao QA Temporaria`, `+5527999000999`)
- causa 2 confirmada na inbox: `ConversationsPage` estava chamando `/api/tasks` com `page_size=200`, mas a API aceita no máximo `100`; isso gerava `422` e quebrava a leitura da fila operacional. O frontend foi corrigido para `100`
- causa 3 confirmada na fila outbound: o cálculo de `next_outbound_slot` estava reservando janela de envio globalmente, misturando filas de sessões diferentes. O backend foi corrigido para respeitar a `whatsapp_session_id` da conversa ao reservar a próxima saída
- causa 4 confirmada em takeover/manual: mensagem agent já enfileirada podia continuar e sair mesmo após takeover humano. O worker agora cancela `queued_outbound` de `author_role=agent` quando a thread entra em controle manual
- validação operacional após correções: a conversa `32` (sessão errada/manual) teve a mensagem `108` cancelada corretamente; a conversa `31` (sessão `2`) foi reprocessada e retornou `send_failed` com erro real do provedor: `401 invalid API key`
- estado final deste debug: a plataforma agora mostra a fila sem `422`, usa a sessão ativa correta para novos starts e não deve mais deixar mensagem agent enfileirada sair após takeover; o bloqueio restante para envio real na sessão `2` é credencial inválida do WASender
- correção focada na workspace de conversas entregue nesta sessão: o miolo do chat foi despoluído, o histórico ganhou mais largura útil e o composer ficou alto/largo o suficiente para leitura e digitação sem a sensação de thread esmagada
- a leitura operacional saiu da coluna central e foi movida para `Controles da thread`, preservando resumo, próxima ação e playbook sem roubar altura do histórico de mensagens
- o outbound agora tem base modular por sessão: `whatsapp_sessions` ganhou `outbound_cooldown_seconds`; quando a linha não tem cooldown configurado, a janela fixa preventiva deixa de ser `60s` e passa a ser efetivamente zero
- a UI agora expõe esse cooldown no cadastro/listagem de sessões e também mostra no cabeçalho do chat qual é a janela real da linha usada na thread (`sem limite`, `Xs`, `Ym Zs`)
- validação desta rodada: `python -m py_compile` ok nos arquivos Python alterados, `npm run build` ok no frontend, `ReadLints` sem erros novos e `/api/whatsapp-sessions` já respondeu com `outbound_cooldown_seconds` para a sessão ativa
- causa raiz do `invalid API key` confirmada nesta rodada: o `.env` estava correto, mas a sessão ativa `David` no banco ainda apontava para credenciais antigas (`qa-temp...`), e o backend prioriza `session.api_key` antes da chave global do `.env`
- correção operacional aplicada: a sessão sombra importada do `.env` (`id 1`) foi esvaziada de `api_key/webhook_secret` e a sessão ativa real `David` (`id 2`) passou a carregar exatamente os valores do `.env`, preservando as conversas já vinculadas a ela
- validação real da autenticação concluída sem assumir: comparação `db == env` passou para `True` em `api_key` e `webhook_secret`, e uma chamada ao endpoint `/api/send-message` com destino propositalmente inválido retornou `422` de validação de número, não `401`, comprovando que a autenticação deixou de falhar
- nova causa operacional confirmada na mesma trilha: o webhook da sessão ativa não estava funcional em produção real porque `David` estava apontando para `https://qa.example/webhooks/wasender`, enquanto o backend local rodava em `http://localhost:8000` e não havia nenhum hit real de `/webhooks/wasender` nos logs
- validação fim-a-fim do webhook concluída nesta rodada: a rota local respondeu com assinatura correta, um túnel público `cloudflared` foi aberto em `https://wishing-stainless-retained-carey.trycloudflare.com`, e tanto `GET /health` quanto `POST /webhooks/wasender` funcionaram através dele
- URL operacional atual do webhook alinhada na sessão local `David`: `https://wishing-stainless-retained-carey.trycloudflare.com/webhooks/wasender`; isso elimina a mentira da UI local, mas o painel do WASender também precisa estar apontado para essa URL viva para os eventos reais começarem a chegar
- runbook operacional dedicado criado em `memory-bank/webhook-restart-runbook.md` para o caso recorrente de reinicio/troca de Wi-Fi/morte do tunnel; quando o usuario disser algo como `troquei aqui`, `manda o webhook` ou `sobe dnv`, devo seguir esse procedimento e devolver a URL publica nova + webhook validado
- reformulação estrutural da plataforma entregue nesta sessão: `frontend/src/index.css` virou um design system claro global com base off-white/bege, acento laranja suave, sombras leves, superfícies premium e shell novo sem a marca `NexLead`; o estilo se propagou para sidebar, header, painéis, tabelas, formulários, modais e páginas operacionais
- `frontend/src/pages/ConversationsPage.tsx` foi refeito para um fluxo tipo WhatsApp: inbox à esquerda, thread dominante no centro, cabeçalho enxuto, composer largo, histórico legível e controles/detalhes movidos para overlays dedicados em vez de coluna fixa esmagando o chat
- o fluxo de dados de `Conversas` foi enxugado no backend/frontend: `app/api/routes/management.py` ganhou `/api/conversations/{conversation_id}/workspace`, a listagem deixou de carregar todas as mensagens na inbox, previews passaram a ser resolvidos de forma leve e a thread deixou de fazer cascata `getConversation -> getLead`
- `app/db/schemas.py`, `frontend/src/lib/types.ts` e `frontend/src/lib/api.ts` agora têm contratos específicos para workspace de conversa (`ConversationWorkspaceRead` / `ConversationWorkspace` e `LeadWorkspaceRead` / `LeadWorkspace`), reduzindo payload e acoplamento do chat com o detalhe completo do lead
- polimento técnico desta fase: `frontend/src/pages/AutomationPage.tsx` foi ajustada para evitar `Date.now()` impuro em render, o chat novo foi limpo para satisfazer lint sem erros, e o frontend passou em `npm run build` e `npm run lint` (restaram apenas warnings antigos de `exhaustive-deps` em arquivos não alterados nesta rodada)
- validação desta reforma: `npm run build` ok no frontend após a nova UI, `npm run lint` sem erros, `python -m py_compile app/api/routes/management.py app/db/schemas.py` ok no backend alterado; validação visual automatizada fim-a-fim ainda não foi feita por browser nesta sessão
