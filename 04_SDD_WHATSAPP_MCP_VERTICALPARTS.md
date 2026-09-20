# 04 — SDD — VerticalParts WhatsApp MCP

Versão: 2026-09-19
Status: canônico

---

## 1. Visão geral

~~~text
Claude / Claude Code
        |
        | HTTPS + MCP Streamable HTTP
        v
Nginx / Gateway público
TLS + X-API-Key
        |
        | loopback (127.0.0.1:8010)
        v
VerticalParts WhatsApp MCP (FastMCP)
        |
        v
Evolution API (instância pv360)
        |
        v
    WhatsApp
~~~

## 2. Componentes

### 2.1 FastMCP server — `src/verticalparts_whatsapp_mcp/server.py`
Registra as 4 tools, normaliza número/JID, aplica classificação de risco, chama o client Evolution, escreve auditoria.

### 2.2 Settings — `config.py`
Carrega `.env`: base URL/chave/instância da Evolution API, transporte/bind MCP, path de auditoria, flag `WHATSAPP_MCP_ALLOW_WRITES`.

### 2.3 Safety — `safety.py` (novo, adicionado na extração para repositório dedicado)
Idêntico em espírito aos três irmãos: `Risk` (READ/CRITICAL) e `require_confirmation`. Antes desta extração, `whatsapp_enviar_texto` checava só `settings.allow_writes` diretamente no `server.py`, sem exigir uma string de confirmação por chamada — uma única trava, controlada só por quem tem acesso ao ambiente. Homologação de 2026-09-19 encontrou essa trava ligada em produção (`WHATSAPP_MCP_ALLOW_WRITES=true` via override de systemd) sem confirmação de que o checklist de segurança do projeto original tinha sido cumprido. Corrigido: agora exige **as duas condições** — `settings.allow_writes` (kill switch de ambiente) **e** `confirmation='CONFIRMO'` (decisão explícita por chamada, no mesmo padrão dos três irmãos).

### 2.4 Evolution client — `evolution.py`
Wrapper HTTP fino sobre a Evolution API (`status`, `verificar_numero`, `enviar_texto`, `buscar_mensagens`) — único ponto de contato com a API real, mesma decisão de design já presente no código original ("Evolution API = detalhe interno escondido dos consumidores").

### 2.5 Audit — `audit.py`
Grava timestamp, evento e payload. O payload de `whatsapp_enviar_texto` já vinha, no código original, sem o conteúdo da mensagem (só `chars`, o tamanho) — decisão de privacidade correta, preservada. Adicionada redação automática por nome de campo (mesmo padrão dos três irmãos) para qualquer campo futuro que contenha `TOKEN`/`SECRET`/`API_KEY`/`PASSWORD`.

### 2.6 Gateway Nginx / systemd
Mesmo padrão dos três irmãos: HTTPS, X-API-Key, proxy para loopback. Já estava implantado antes desta extração — ver `05_RUNBOOK` PARTE E para a migração de caminho (`/root/whatsapp-mcp-hub/whatsapp-mcp` → `/opt/verticalparts-whatsapp-mcp`).

## 3. Fluxo — enviar mensagem (depois da correção)

~~~text
whatsapp_enviar_texto(numero, mensagem, confirmation="CONFIRMO")
  |
  v
require_confirmation(CRITICAL, "CONFIRMO")   -- bloqueia se confirmation != "CONFIRMO"
  |
  v
settings.allow_writes == True?                -- bloqueia se WHATSAPP_MCP_ALLOW_WRITES=false
  |
  v
normaliza número (formatos BR comuns -> E.164 sem +)
  |
  v
POST /message/sendText/{instancia} na Evolution API
  |
  v
audit: {numero, message_id, chars: len(texto), ok: true}  -- texto nunca gravado
~~~

## 4. Segurança em camadas

1. HTTPS + X-API-Key no gateway;
2. `EVOLUTION_API_KEY` fora do Git;
3. tool semântica com validação/normalização de número;
4. classificação de risco (READ/CRITICAL);
5. **duas travas** para envio: flag de ambiente + confirmação por chamada;
6. auditoria sem conteúdo de mensagem.

## 5. Threat model

### T-001 — `EVOLUTION_API_KEY` vazada
Risco: controle total da instância WhatsApp corporativa (ler/enviar como o número da empresa).
Mitigação: fora do Git, rotação (`05_RUNBOOK` PARTE F) — pendente desde a documentação original do projeto, sem evidência de ter sido feita.

### T-002 — Trava única, sem confirmação por chamada
Risco real, já materializado: `WHATSAPP_MCP_ALLOW_WRITES=true` ligado em produção sem checklist cumprido, uma única LLM call bastaria para enviar mensagem real.
Mitigação: `confirmation='CONFIRMO'` adicionado (seção 2.3) — a partir de agora as duas condições são necessárias.

### T-003 — Aprovação de negócio por texto livre
Risco: uma resposta ambígua no WhatsApp ("sim", "ok") ser interpretada como decisão financeira/de requisição.
Mitigação: `02_SPEC` seção 6 exige token de uso único + expiração + idempotência antes de qualquer fluxo de aprovação — não implementado ainda, não simular que está.

### T-004 — Gatilho de plataforma confundido com automação real
Risco: alguém (humano ou LLM) assume que uma tarefa concluída no VP Click já dispara WhatsApp automaticamente, porque a documentação descreve a arquitetura pretendida.
Mitigação: `01_RAG` RAG-005 documenta explicitamente o que está e o que não está implementado — atualizar assim que mudar.

## 6. Estado de implementação (2026-09-19)

Extraído de `whatsapp-mcp-hub/whatsapp-mcp` (já em produção) para este repositório dedicado. Código funcional preservado; adicionado `safety.py` e confirmação por chamada em `whatsapp_enviar_texto`. Homologado nesta sessão via o conector real (`whatsapp_status`, `whatsapp_verificar_numero`, `whatsapp_buscar_mensagens` testados contra a Evolution API real; `whatsapp_enviar_texto` testado só até o ponto de bloqueio, nunca até o envio real, para não mandar mensagem para um número de teste).

**Não implementado ainda**: gateway de eventos, webhook receiver, fluxo de aprovação segura, tools de mídia — todos documentados como backlog em `02_SPEC` seção 4.

## 7. Evolução futura (backlog)

Ver `02_SPEC` seção 4 e `01_RAG` RAG-004/RAG-005 para a arquitetura já desenhada do gateway de eventos e a lista de tools planejadas (`whatsapp_enviar_midia`, `whatsapp_solicitar_aprovacao`, etc.) — não implementar sem pedido explícito do operador.

## 8. Referências

Evolution API: documentação interna em `docs/` do `whatsapp-mcp-hub` original (não faz parte deste repositório, ficou no hub).
