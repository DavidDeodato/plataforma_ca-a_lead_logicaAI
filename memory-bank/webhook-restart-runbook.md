# Runbook de Reinicio do Webhook

## Objetivo
Este arquivo existe para registrar o procedimento operacional que sempre precisa ser feito quando:
- a maquina reinicia
- a internet cai
- voce troca de Wi-Fi
- o tunnel `trycloudflare` morre
- o WASender para de entregar inbound/status no chat

## Gatilho curto combinado
Se o usuario disser algo como:
- `troquei aqui`
- `sube dnv`
- `manda o webhook`
- `sobe a api dnv`
- `troquei de wifi`
- `reiniciei aqui`

Interpretar isso como pedido para executar o procedimento completo abaixo.

## Resultado esperado ao fim
Ao terminar, eu preciso devolver para o usuario:
- a URL publica nova do tunnel
- a URL exata do webhook
- confirmacao de que a API local respondeu
- confirmacao de que o webhook publico respondeu
- aviso claro de que o painel do WASender precisa estar apontando para a URL nova, se ele ainda nao estiver

## Procedimento padrao
1. Confirmar se a API local esta no ar.
2. Se nao estiver, subir a API com:
```powershell
.\scripts\start-local.ps1
```
3. Confirmar se o frontend precisa ser reaberto. Se necessario, subir com:
```powershell
.\scripts\start-frontend.ps1
```
4. Subir um tunnel novo com:
```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```
5. Se o tunnel em `quic` ficar instavel, cair logo apos subir, retornar `503` externamente ou o DNS nao resolver, repetir forçando `http2`:
```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2
```
6. Ler a saida do `cloudflared` e capturar a URL publica `https://...trycloudflare.com`.
7. Montar a URL final do webhook:
```text
https://SEU-TUNNEL.trycloudflare.com/webhooks/wasender
```
8. Validar externamente:
- `GET /health`
- `GET /api/readiness`
- `POST /webhooks/wasender` com assinatura correta
9. Atualizar a `webhook_url` da sessao ativa local no banco para a URL nova, para a UI refletir a verdade atual.
10. Informar ao usuario a URL exata que deve estar configurada no painel do WASender.

## Regra importante
Nunca assumir que a URL antiga ainda vale.
Sempre gerar e validar uma URL nova quando houver troca de Wi-Fi, reinicio ou perda do tunnel.

## Regra importante sobre sintomas
Se o chat ficar preso em `Enviando` ou a resposta inbound nao aparecer:
- nao assumir que eh credencial
- primeiro checar se o webhook publico ainda esta vivo
- conferir logs do backend
- conferir a `webhook_url` salva na sessao ativa

## Comandos de verificacao
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/readiness"
```

```powershell
Invoke-RestMethod -Method Post -Uri "https://SEU-TUNNEL.trycloudflare.com/webhooks/wasender" -Headers @{"x-webhook-signature"="SEU_WEBHOOK_SECRET"; "Content-Type"="application/json"} -Body '{"event":"messages.received","data":{"messages":[{"key":{"id":"public-webhook-test","remoteJid":"5527999999999@s.whatsapp.net","fromMe":false,"cleanedSenderPn":"+5527999999999"},"messageBody":"teste webhook publico"}]}}'
```

## Estado operacional mais recente conhecido
- tunnel validado nesta sessao: `https://isolated-tab-fixtures-andrea.trycloudflare.com`
- webhook correspondente: `https://isolated-tab-fixtures-andrea.trycloudflare.com/webhooks/wasender`
- observacao adicional desta rede: o tunnel em `quic` ficou instavel e derrubou a URL; o modo `http2` funcionou e deve ser o fallback padrao quando isso acontecer
- observacao: URL de `trycloudflare` eh temporaria e pode morrer a qualquer momento; por isso este runbook existe
