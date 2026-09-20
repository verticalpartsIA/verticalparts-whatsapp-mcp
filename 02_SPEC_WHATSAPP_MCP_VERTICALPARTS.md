# 02 — SPEC — VerticalParts WhatsApp MCP

Versão: 2026-09-20
Status: canônico

---

## 1. Objetivo

Dar a Claude (e, no futuro, aos sistemas internos via gateway de eventos) uma interface única de WhatsApp corporativo, com confirmação proporcional ao risco e auditoria, sem expor detalhes da Evolution API.

## 2. Fora de escopo por padrão

- Enviar mensagem sem `confirmation='CONFIRMO'`, mesmo com `WHATSAPP_MCP_ALLOW_WRITES=true`;
- decidir aprovação de negócio (financeira, requisição) com base só em texto livre recebido no WhatsApp;
- expor uma tool de chamada genérica à Evolution API (`whatsapp_chamar_api`) — quebraria o propósito do MCP;
- migrar o Pós-Venda 360 para este gateway sem homologação end-to-end prévia (decisão já registrada no projeto original).

## 3. Requisitos funcionais

### FR-001 — Status da instância
`whatsapp_status`: consulta estado da instância Evolution (conectada/desconectada). READ.

### FR-002 — Verificação de número
`whatsapp_verificar_numero`: normaliza formatos brasileiros comuns (com/sem DDI 55, com/sem zero inicial de DDD) e verifica existência no WhatsApp. READ.

### FR-003 — Histórico de mensagens
`whatsapp_buscar_mensagens`: busca mensagens recentes de um contato (telefone ou `remoteJid`), limite configurável (máx. 100). READ. Não grava conteúdo de mensagem em auditoria além de metadados.

### FR-004 — Envio de mensagem
`whatsapp_enviar_texto`: envia texto para um número. **CRITICAL**, exige `confirmation='CONFIRMO'` **e** `WHATSAPP_MCP_ALLOW_WRITES=true` no ambiente. Auditoria grava número, `message_id` retornado pela Evolution e tamanho do texto — nunca o conteúdo.

### FR-005 — Normalização de número
Toda tool que recebe telefone deve aceitar formatos comuns (`011997663780`, `11997663780`, `5511997663780`) e normalizar para o formato E.164 sem `+` esperado pela Evolution API antes de qualquer chamada.

### FR-006 — Gateway de eventos (`POST /events`, implementado em 2026-09-20)

Serviço HTTP separado do MCP (porta própria, `events_app.py`), para gatilhos automáticos dos sistemas internos. Contrato: `{source, event, record_id?, recipient: {phone, user_id?}, template, data?, idempotency_key}`.

- autentica por `Authorization: Bearer <token>` verificado contra `config/systems.yaml` (um token por sistema de origem, nunca compartilhado);
- **nunca aceita texto livre** — só `template` registrado em `config/templates.yaml`, renderizado com `data`; template desconhecido ou campo de template ausente → `400`;
- idempotência via `idempotency_key` (SQLite) — reenviar a mesma chave devolve o resultado já processado (`replay: true`), nunca manda a mensagem de novo;
- respeita o mesmo `WHATSAPP_MCP_ALLOW_WRITES` do MCP — se desligado, o gateway recusa com `503`, sem chamar a Evolution API;
- **não tem `CONFIRMO`** — não há humano/LLM na chamada, a segurança vem das quatro camadas acima (ver `01_RAG` RAG-006B), não de confirmação por chamada.
- auditoria (`events_enviar`/`events_auth_falhou`/`events_bloqueado_allow_writes`/`events_enviar_falhou`) grava origem, evento, `record_id`, template, número, `message_id`, tamanho do texto — nunca o texto renderizado.

`GET /events/health` (status do serviço) e `GET /events/templates` (lista os templates disponíveis) são leitura, sem autenticação.

### FR-007 — Templates

`config/templates.yaml` é a única fonte de texto que o gateway de eventos pode enviar. Adicionar um template novo é uma mudança de conteúdo (não requer confirmação especial), mas nunca deve permitir que `data` vire texto arbitrário (ex.: nunca um template do tipo `"{texto_livre}"` sem mais nada ao redor).

## 5. Fora do MVP, documentado como backlog (não implementar sem pedido explícito)

Mídia (imagem/documento/áudio/localização/contato), resposta e marcação de leitura, sumarização/sugestão de resposta por IA, aprovações seguras (`approval_id` + token de uso único + expiração + idempotência — ver seção 7), webhook receiver, resolução de contato (`contacts/`), migração efetiva de VP Click/Requisições/Pós-Venda/Borderô para emitir eventos reais (o gateway já aceita, falta o lado emissor).

## 5. Requisitos não funcionais

- **Segurança**: `EVOLUTION_API_KEY`, `X-API-Key` e tokens de `config/systems.yaml` fora do Git; break-glass não existe neste MCP (não há chamada genérica à API, ver seção 2).
- **Auditabilidade**: toda chamada de `whatsapp_enviar_texto` e todo evento processado pelo gateway geram registro com número, `message_id`, tamanho do texto e resultado — nunca o conteúdo/texto renderizado.
- **Reversibilidade**: envio de mensagem (por MCP ou por evento) é a única operação irreversível do catálogo — uma vez entregue, não há como desmandar. Tratamento de risco reflete isso: dupla trava no MCP (`01_RAG` RAG-006A), quatro camadas no gateway de eventos (`01_RAG` RAG-006B).
- **Isolamento entre sistemas**: um token de `config/systems.yaml` comprometido nunca deve permitir agir em nome de outro `source` — testado (ver `05_RUNBOOK`).
- **Portabilidade de LLM**: qualquer LLM autorizada deve entender, só pela documentação, que o gateway de eventos existe mas nenhum sistema de origem foi migrado para emitir eventos reais ainda (`01_RAG` RAG-005).

## 6. Contrato de aprovação segura (para quando `whatsapp_solicitar_aprovacao`/webhook receiver forem implementados)

Uma aprovação por WhatsApp deve usar no mínimo: `approval_id`, usuário/aprovador esperado, telefone/JID autorizado, token aleatório de uso único, expiração, registro de `used_at`, decisão recebida, idempotency key, trilha de auditoria. A palavra isolada "aprovo" nunca deve executar uma decisão financeira. Isso é diferente da idempotência de `POST /events` (que evita reenvio duplicado de uma notificação de saída) — aprovação é sobre uma decisão de negócio chegando por uma mensagem de entrada, canal que ainda não existe (webhook receiver).

## 7. Critérios de aceite do MCP

1. `whatsapp_status` retorna o estado real da instância, batendo com o painel da Evolution API;
2. `whatsapp_verificar_numero` normaliza corretamente os três formatos de entrada aceitos;
3. `whatsapp_buscar_mensagens` não grava nem expõe dado além do solicitado;
4. `whatsapp_enviar_texto` sem `confirmation` é recusado; com `confirmation` errado é recusado; com `WHATSAPP_MCP_ALLOW_WRITES=false` é recusado mesmo com `CONFIRMO` certo; só com as duas condições verdadeiras executa;
5. `POST /events` sem token válido do `source` declarado é recusado (`401`); com template desconhecido ou campo de template ausente é recusado (`400`); com `WHATSAPP_MCP_ALLOW_WRITES=false` é recusado (`503`) mesmo com token e template corretos; reenviar a mesma `idempotency_key` nunca manda a mensagem duas vezes;
6. auditoria de envio (MCP ou gateway) nunca contém o texto da mensagem;
7. nenhuma tool ou endpoint expõe `EVOLUTION_API_KEY` ou tokens de `config/systems.yaml`.

## 8. Definition of Done

Qualquer feature deste MCP só está concluída quando: implementada, classificada por risco, auditada sem vazar conteúdo de mensagem, testada contra a Evolution API real (não só localmente), documentada, sem segredo no Git, e incorporada ao RAG/Instructions se alterar comportamento.
