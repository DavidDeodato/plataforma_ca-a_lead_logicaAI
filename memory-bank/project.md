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
