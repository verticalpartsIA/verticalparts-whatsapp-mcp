# VerticalParts WhatsApp MCP

Camada corporativa de WhatsApp da VerticalParts (via Evolution API) — interface única para Claude e, no futuro, para os sistemas internos — com confirmação proporcional ao risco e auditoria sem conteúdo de mensagem.

Status: **em produção**, com dois canais implementados: o **MCP** (comandos explícitos, migrado em 2026-09-20 de um monorepo maior — `whatsapp-mcp-hub`, que também continha o agente Hermes, notas de n8n e rotinas de Borderô misturadas) e o **gateway de eventos** (`POST /events`, construído em 2026-09-20 para os gatilhos automáticos das plataformas internas). Governança elevada: `whatsapp_enviar_texto` exige `confirmation='CONFIRMO'` além do flag `WHATSAPP_MCP_ALLOW_WRITES` (que sozinho já foi encontrado ligado em produção sem confirmação por chamada); o gateway de eventos não usa `CONFIRMO` (não há humano/LLM na chamada) — usa token por sistema de origem + template fixo + idempotência. Nenhum sistema real (VP Click/Requisições/Pós-Venda/Borderô) emite eventos ainda — o gateway está pronto, falta o lado emissor. Ver `00_READ_FIRST_WHATSAPP_MCP.md` seções 6-8 para o relato completo.

Este é o quarto de uma família de MCPs administrativos da VerticalParts, junto com [`verticalparts-infrastructure-mcp`](https://github.com/verticalpartsIA/verticalparts-infrastructure-mcp), [`verticalparts-github-mcp`](https://github.com/verticalpartsIA/verticalparts-github-mcp) e [`verticalparts-supabase-mcp`](https://github.com/verticalpartsIA/verticalparts-supabase-mcp).

---

## Por que este projeto existe separado

Quase toda automação da VerticalParts vai depender de WhatsApp (VP Click, VP Requisições, Pós-Venda 360, Borderô) — deixá-lo acoplado a um site ou hub específico cria dependência escondida: quem mexe nesse hub pode quebrar o WhatsApp de todo mundo sem saber. Este repositório é a porta de entrada única, separada de qualquer sistema que a consuma.

## Arquitetura de três canais

```text
Comando humano:     Usuário -> Claude -> MCP (/mcp, porta 8010) -> Evolution API -> WhatsApp
Gatilho de sistema:  VP Click / Requisições / Pós-Venda / Borderô -> gateway de eventos (/events, porta 8011) -> Evolution API -> WhatsApp
Mensagem recebida:   WhatsApp -> Evolution API -> webhook receiver (ainda não implementado) -> roteamento
```

Este repositório implementa os dois primeiros canais. O gateway de eventos está pronto para receber, mas nenhum sistema real foi migrado para emitir ainda — ver `01_RAG` RAG-005 para o estado real por sistema. Webhook receiver é backlog documentado, não implementado.

## Catálogo de tools MCP (4)

Leitura: `whatsapp_status`, `whatsapp_verificar_numero`, `whatsapp_buscar_mensagens`

Escrita (única do catálogo, dupla trava): `whatsapp_enviar_texto`

## Gateway de eventos (`POST /events`)

Recebe eventos de sistemas internos e envia mensagens a partir de templates fixos — nunca texto livre. Autenticação por token por sistema de origem (`config/systems.yaml`), idempotência via `idempotency_key` (nunca reenvia a mesma notificação duas vezes). Ver `04_SDD` seção 2.7 e `01_RAG` RAG-006B para o modelo de segurança completo (por que não tem `CONFIRMO`).

## Leia primeiro

1. [00_READ_FIRST_WHATSAPP_MCP.md](./00_READ_FIRST_WHATSAPP_MCP.md)
2. [03_INSTRUCTIONS_LLM_WHATSAPP_MCP_VERTICALPARTS.md](./03_INSTRUCTIONS_LLM_WHATSAPP_MCP_VERTICALPARTS.md)
3. [01_RAG_WHATSAPP_MCP_VERTICALPARTS.md](./01_RAG_WHATSAPP_MCP_VERTICALPARTS.md)
4. [02_SPEC_WHATSAPP_MCP_VERTICALPARTS.md](./02_SPEC_WHATSAPP_MCP_VERTICALPARTS.md)
5. [04_SDD_WHATSAPP_MCP_VERTICALPARTS.md](./04_SDD_WHATSAPP_MCP_VERTICALPARTS.md)
6. [05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md](./05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md)

## Segurança

Nunca versionar: `EVOLUTION_API_KEY`, `X-API-Key` do gateway MCP, tokens de `config/systems.yaml`.

Confirmações:
- `CONFIRMO` — necessário para `whatsapp_enviar_texto`, **junto com** `WHATSAPP_MCP_ALLOW_WRITES=true` no ambiente. As duas condições são obrigatórias, nenhuma sozinha basta.
- gateway de eventos — sem `CONFIRMO`; protegido por token por sistema + template fixo + idempotência + o mesmo `WHATSAPP_MCP_ALLOW_WRITES`.

## Desenvolvimento

~~~bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
cp .env.example .env
verticalparts-whatsapp-mcp
~~~

## Claude

Conector (já homologado, pronto para uso):

Nome: VerticalParts WhatsApp
URL: `https://whatsapp-mcp.vpsistema.com/mcp`
Autenticação: Sem login
Header: `X-API-Key`
