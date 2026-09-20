# VerticalParts WhatsApp MCP

Camada corporativa de WhatsApp da VerticalParts (via Evolution API) — interface única para Claude e, no futuro, para os sistemas internos — com confirmação proporcional ao risco e auditoria sem conteúdo de mensagem.

Status: **código já em produção**, extraído em 2026-09-19 de um monorepo maior (`whatsapp-mcp-hub`, que também continha o agente Hermes, notas de n8n e rotinas de Borderô misturadas) para este repositório dedicado — porque WhatsApp é infraestrutura compartilhada, não uma feature de um site só. Governança elevada nesta extração: `whatsapp_enviar_texto` agora exige `confirmation='CONFIRMO'` além do flag de ambiente `WHATSAPP_MCP_ALLOW_WRITES`, que sozinho já foi encontrado ligado em produção sem confirmação por chamada. Ver `00_READ_FIRST_WHATSAPP_MCP.md` para o relato completo.

Este é o quarto de uma família de MCPs administrativos da VerticalParts, junto com [`verticalparts-infrastructure-mcp`](https://github.com/verticalpartsIA/verticalparts-infrastructure-mcp), [`verticalparts-github-mcp`](https://github.com/verticalpartsIA/verticalparts-github-mcp) e [`verticalparts-supabase-mcp`](https://github.com/verticalpartsIA/verticalparts-supabase-mcp).

---

## Por que este projeto existe separado

Quase toda automação da VerticalParts vai depender de WhatsApp (VP Click, VP Requisições, Pós-Venda 360, Borderô) — deixá-lo acoplado a um site ou hub específico cria dependência escondida: quem mexe nesse hub pode quebrar o WhatsApp de todo mundo sem saber. Este repositório é a porta de entrada única, separada de qualquer sistema que a consuma.

## Arquitetura de três canais

```text
Comando humano:     Usuário -> Claude -> este MCP -> Evolution API -> WhatsApp
Gatilho de sistema:  VP Click / Requisições / Pós-Venda / Borderô -> gateway de eventos (ainda não implementado) -> Evolution API -> WhatsApp
Mensagem recebida:   WhatsApp -> Evolution API -> webhook receiver (ainda não implementado) -> roteamento
```

Este repositório implementa hoje só o primeiro canal (**MCP**). Gateway de eventos e webhook receiver são backlog documentado, não implementado — ver `01_RAG` RAG-004/RAG-005 para o estado real de cada integração pretendida.

## Catálogo de tools (4)

Leitura: `whatsapp_status`, `whatsapp_verificar_numero`, `whatsapp_buscar_mensagens`

Escrita (única do catálogo, dupla trava): `whatsapp_enviar_texto`

## Leia primeiro

1. [00_READ_FIRST_WHATSAPP_MCP.md](./00_READ_FIRST_WHATSAPP_MCP.md)
2. [03_INSTRUCTIONS_LLM_WHATSAPP_MCP_VERTICALPARTS.md](./03_INSTRUCTIONS_LLM_WHATSAPP_MCP_VERTICALPARTS.md)
3. [01_RAG_WHATSAPP_MCP_VERTICALPARTS.md](./01_RAG_WHATSAPP_MCP_VERTICALPARTS.md)
4. [02_SPEC_WHATSAPP_MCP_VERTICALPARTS.md](./02_SPEC_WHATSAPP_MCP_VERTICALPARTS.md)
5. [04_SDD_WHATSAPP_MCP_VERTICALPARTS.md](./04_SDD_WHATSAPP_MCP_VERTICALPARTS.md)
6. [05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md](./05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md)

## Segurança

Nunca versionar: `EVOLUTION_API_KEY`, `X-API-Key` do gateway.

Confirmações:
- `CONFIRMO` — necessário para `whatsapp_enviar_texto`, **junto com** `WHATSAPP_MCP_ALLOW_WRITES=true` no ambiente. As duas condições são obrigatórias, nenhuma sozinha basta.

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
