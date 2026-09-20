# CLAUDE.md — VerticalParts WhatsApp MCP

Versão operacional: 2026-09-19
Status: **migração concluída** — deploy real na VPS movido para `/opt/verticalparts-whatsapp-mcp`, `whatsapp-mcp.service` rodando o novo código, validado pelo conector real (`whatsapp_status`) e pelo processo migrado (`CONFIRMO` bloqueando corretamente). Governança elevada: `whatsapp_enviar_texto` agora exige `CONFIRMO` além do flag de ambiente. Ver `00_READ_FIRST` seção 6.

## Leitura obrigatória

1. `00_READ_FIRST_WHATSAPP_MCP.md`
2. `03_INSTRUCTIONS_LLM_WHATSAPP_MCP_VERTICALPARTS.md`
3. `01_RAG_WHATSAPP_MCP_VERTICALPARTS.md`
4. `02_SPEC_WHATSAPP_MCP_VERTICALPARTS.md`
5. `04_SDD_WHATSAPP_MCP_VERTICALPARTS.md`
6. `05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md`

Irmãos: `verticalparts-infrastructure-mcp`, `verticalparts-github-mcp`, `verticalparts-supabase-mcp` — mesma filosofia de governança, quarto membro da família.

## Missão

Interface única de WhatsApp corporativo (via Evolution API) para Claude e, no futuro, para os sistemas internos via gateway de eventos — sem expor endpoint, instância, JID ou chave.

## Diferença central em relação aos outros três

Este é o único MCP da família cujo efeito sai da infraestrutura da VerticalParts e chega a uma pessoa real, instantaneamente, sem lixeira. Trate `whatsapp_enviar_texto` com mais cuidado que qualquer tool dos outros três repositórios.

## Regras obrigatórias

- Nunca invente número de destino — descubra por leitura (`whatsapp_verificar_numero`, `whatsapp_buscar_mensagens`) ou peça ao operador.
- `whatsapp_enviar_texto` exige as duas condições: `WHATSAPP_MCP_ALLOW_WRITES=true` no ambiente **e** `confirmation='CONFIRMO'` por chamada. Uma sem a outra não deve bastar — se você (LLM) estiver implementando isso, não remova nenhuma das duas travas.
- Nunca use um número de exemplo genérico para testar envio de verdade — só para `whatsapp_status`/`whatsapp_verificar_numero`/`whatsapp_buscar_mensagens`, que não têm efeito real.
- Nunca grave o conteúdo de uma mensagem em auditoria — só metadados (número, `message_id`, tamanho).
- Gatilhos de plataforma (VP Click, Requisições, Pós-Venda, Borderô) **não passam por este MCP hoje** — não simule que passam. Ver `01_RAG` RAG-005.
- Nunca mostre `EVOLUTION_API_KEY` nem `X-API-Key` do gateway.
- Mudança estrutural (gateway de eventos implementado, sistema migrado para cá) exige atualizar `01_RAG` RAG-005 na mesma sessão.

## Continuidade operacional

Setup do zero e migração do deploy antigo estão em `05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md`.

Nunca deixe uma mudança arquitetural registrada somente em conversa.
