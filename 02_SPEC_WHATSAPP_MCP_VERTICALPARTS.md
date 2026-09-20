# 02 — SPEC — VerticalParts WhatsApp MCP

Versão: 2026-09-19
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

## 4. Fora do MVP, documentado como backlog (não implementar sem pedido explícito)

Mídia (imagem/documento/áudio/localização/contato), resposta e marcação de leitura, sumarização/sugestão de resposta por IA, aprovações seguras (`approval_id` + token de uso único + expiração + idempotência), gateway de eventos (`events/`), webhook receiver, resolução de contato (`contacts/`).

## 5. Requisitos não funcionais

- **Segurança**: `EVOLUTION_API_KEY` e `X-API-Key` fora do Git; break-glass não existe neste MCP (não há chamada genérica à API, ver seção 2).
- **Auditabilidade**: toda chamada de `whatsapp_enviar_texto` gera registro com número, `message_id`, tamanho do texto e resultado — nunca o conteúdo da mensagem.
- **Reversibilidade**: `whatsapp_enviar_texto` é a única tool irreversível do catálogo — uma vez entregue, não há como desmandar. Tratamento de risco deve refletir isso (dupla trava, ver `01_RAG` RAG-006A).
- **Portabilidade de LLM**: qualquer LLM autorizada deve entender, só pela documentação, que os gatilhos de plataforma não passam por aqui ainda.

## 6. Contrato de aprovação segura (para quando `whatsapp_solicitar_aprovacao` for implementado)

Uma aprovação por WhatsApp deve usar no mínimo: `approval_id`, usuário/aprovador esperado, telefone/JID autorizado, token aleatório de uso único, expiração, registro de `used_at`, decisão recebida, idempotency key, trilha de auditoria. A palavra isolada "aprovo" nunca deve executar uma decisão financeira.

## 7. Critérios de aceite do MCP

1. `whatsapp_status` retorna o estado real da instância, batendo com o painel da Evolution API;
2. `whatsapp_verificar_numero` normaliza corretamente os três formatos de entrada aceitos;
3. `whatsapp_buscar_mensagens` não grava nem expõe dado além do solicitado;
4. `whatsapp_enviar_texto` sem `confirmation` é recusado; com `confirmation` errado é recusado; com `WHATSAPP_MCP_ALLOW_WRITES=false` é recusado mesmo com `CONFIRMO` certo; só com as duas condições verdadeiras executa;
5. auditoria de envio nunca contém o texto da mensagem;
6. nenhuma tool expõe `EVOLUTION_API_KEY`.

## 8. Definition of Done

Qualquer feature deste MCP só está concluída quando: implementada, classificada por risco, auditada sem vazar conteúdo de mensagem, testada contra a Evolution API real (não só localmente), documentada, sem segredo no Git, e incorporada ao RAG/Instructions se alterar comportamento.
