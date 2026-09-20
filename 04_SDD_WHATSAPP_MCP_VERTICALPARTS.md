# 04 — SDD — VerticalParts WhatsApp MCP

Versão: 2026-09-20
Status: canônico

---

## 1. Visão geral

~~~text
Claude / Claude Code                    VP Click / Requisições / Pós-Venda / Borderô
        |                                              |
        | HTTPS + MCP Streamable HTTP                  | HTTPS + Bearer <token do sistema>
        v                                              v
Nginx / Gateway público (whatsapp-mcp.vpsistema.com)
TLS
        |                                              |
        | loopback 127.0.0.1:8010 (/mcp)                | loopback 127.0.0.1:8011 (/events)
        v                                              v
VerticalParts WhatsApp MCP (FastMCP)          Gateway de eventos (Starlette + SQLite)
        |                                              |
        +---------------------> Evolution API (instância pv360) <---------------------+
                                          |
                                          v
                                      WhatsApp
~~~

Dois processos, dois serviços systemd, mesmo domínio (paths diferentes: `/mcp` e `/events`), mesma Evolution API por baixo.

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
Mesmo padrão dos três irmãos para o `/mcp`: HTTPS, X-API-Key, proxy para loopback. Já estava implantado antes desta extração — ver `05_RUNBOOK` PARTE E para a migração de caminho (`/root/whatsapp-mcp-hub/whatsapp-mcp` → `/opt/verticalparts-whatsapp-mcp`).

### 2.7 Gateway de eventos — `events_app.py`, `events_registry.py`, `events_store.py`, `phone.py` (novos, 2026-09-20)

Processo separado do MCP (`verticalparts-whatsapp-events`, Starlette + uvicorn, porta 8011), atrás do mesmo domínio Nginx num path diferente (`/events`, sem checagem de `X-API-Key` no Nginx — a autenticação é por sistema de origem, dentro da aplicação).

- `phone.py`: normalização de número/JID extraída de `server.py` para ser reutilizada pelos dois processos sem duplicar código.
- `events_registry.py`: carrega `config/systems.yaml` (token por sistema de origem) e `config/templates.yaml` (nome → texto com placeholders `{campo}`), e renderiza um template com os dados do evento.
- `events_store.py`: idempotência via SQLite (`data/events.sqlite3`) — `idempotency_key` é chave primária; `reserve()` usa a constraint única da própria tabela para detectar concorrência (duas requisições com a mesma chave ao mesmo tempo), `mark_done()`/`mark_failed()` fecham o ciclo.
- `events_app.py`: rotas `POST /events` (recebe o evento), `GET /events/health`, `GET /events/templates` (lista nomes, não os textos completos — evita expor a redação exata de mensagens de negócio a quem só está checando saúde do serviço).

Fluxo de `POST /events`, na ordem: valida campos obrigatórios → autentica `source`+token → checa `WHATSAPP_MCP_ALLOW_WRITES` → normaliza telefone → renderiza template → checa/reserva idempotência → chama Evolution API → grava resultado → audita. Qualquer falha antes da chamada à Evolution API não reserva a idempotência de forma permanente (`mark_failed` libera a chave para nova tentativa).

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

## 4. Fluxo — gateway de eventos

~~~text
POST /events {source, event, record_id?, recipient:{phone}, template, data?, idempotency_key}
  |
  v
authenticate_source(source, bearer_token)     -- 401 se source desconhecido ou token errado
  |
  v
settings.allow_writes == True?                -- 503 se WHATSAPP_MCP_ALLOW_WRITES=false
  |
  v
normalizar_numero(recipient.phone)            -- 400 se número inválido
  |
  v
render_template(template, data)               -- 400 se template desconhecido ou campo faltando
  |
  v
get_processed(idempotency_key)?               -- se já 'sent', devolve o resultado anterior (replay), não reenvia
  |
  v
reserve(idempotency_key, ...)                 -- 'already_processing' se concorrente/duplicado
  |
  v
evolution.enviar_texto(numero, texto)         -- se falhar, mark_failed() libera a chave para retry
  |
  v
mark_done(idempotency_key, message_id)
  |
  v
audit: {source, event, record_id, template, numero, message_id, chars: len(texto), ok: true}
~~~

## 5. Segurança em camadas

**Canal MCP (`/mcp`)**:
1. HTTPS + X-API-Key no gateway;
2. `EVOLUTION_API_KEY` fora do Git;
3. tool semântica com validação/normalização de número;
4. classificação de risco (READ/CRITICAL);
5. **duas travas** para envio: flag de ambiente + confirmação por chamada;
6. auditoria sem conteúdo de mensagem.

**Canal de eventos (`/events`)**:
1. HTTPS (sem `X-API-Key` de gateway — autenticação é por sistema, dentro da aplicação);
2. token por sistema de origem (`config/systems.yaml`), nunca compartilhado entre sistemas;
3. **template fixo, nunca texto livre** (`config/templates.yaml`) — a mitigação estrutural mais importante deste canal;
4. idempotência (SQLite) contra reenvio duplicado;
5. mesmo flag de ambiente do canal MCP (kill switch único para os dois);
6. auditoria sem conteúdo de mensagem renderizada.

## 6. Threat model

### T-001 — `EVOLUTION_API_KEY` vazada
Risco: controle total da instância WhatsApp corporativa (ler/enviar como o número da empresa).
Mitigação: fora do Git, rotação (`05_RUNBOOK` PARTE F) — pendente desde a documentação original do projeto, sem evidência de ter sido feita.

### T-002 — Trava única, sem confirmação por chamada
Risco real, já materializado: `WHATSAPP_MCP_ALLOW_WRITES=true` ligado em produção sem checklist cumprido, uma única LLM call bastaria para enviar mensagem real.
Mitigação: `confirmation='CONFIRMO'` adicionado (seção 2.3) — a partir de agora as duas condições são necessárias.

### T-003 — Aprovação de negócio por texto livre
Risco: uma resposta ambígua no WhatsApp ("sim", "ok") ser interpretada como decisão financeira/de requisição.
Mitigação: `02_SPEC` seção 6 exige token de uso único + expiração + idempotência antes de qualquer fluxo de aprovação — não implementado ainda, não simular que está.

### T-004 — Sistema de origem migrado para o gateway sem estar pronto
Risco: alguém assume que uma tarefa concluída no VP Click já dispara WhatsApp automaticamente, porque o gateway de eventos existe e aceita o evento — mas o VP Click ainda não foi migrado para emitir.
Mitigação: `01_RAG` RAG-005 documenta explicitamente o que está e o que não está implementado, do lado do gateway e do lado de cada sistema — atualizar assim que um sistema real migrar.

### T-005 — Token de um sistema reutilizado para outro
Risco: se dois sistemas compartilhassem o mesmo token, um comprometido afetaria o outro.
Mitigação: `config/systems.yaml` exige um token por `source`; testado que um token válido para `vpclick` é recusado quando o payload declara `source: requisicoes` (ver `05_RUNBOOK`).

### T-006 — Template vira vetor de texto livre por acidente
Risco: um template mal desenhado (ex.: `"{texto_livre}"` sozinho) reintroduziria a possibilidade de um sistema mandar qualquer texto, quebrando a mitigação estrutural do gateway.
Mitigação: `02_SPEC` FR-007 proíbe esse padrão; revisão de qualquer template novo deve checar isso.

## 7. Estado de implementação (2026-09-20)

Extraído de `whatsapp-mcp-hub/whatsapp-mcp` (já em produção) para este repositório dedicado. Código funcional preservado; adicionado `safety.py` e confirmação por chamada em `whatsapp_enviar_texto`. Gateway de eventos (`events_app.py`) implementado na mesma data.

Homologado: `whatsapp_status`, `whatsapp_verificar_numero`, `whatsapp_buscar_mensagens` testados contra a Evolution API real via o conector; `whatsapp_enviar_texto` testado só até o ponto de bloqueio, nunca até o envio real. Gateway de eventos testado com a Evolution API **mockada** (auth, isolamento entre sistemas, template desconhecido, campo faltando, envio simulado, replay de idempotência) — ainda **não testado contra a Evolution API real** (nenhum sistema real emite eventos ainda, então não há como testar com destinatário controlado sem simular um evento manualmente — ver `05_RUNBOOK` PARTE H para esse teste quando for feito).

**Não implementado ainda**: webhook receiver, fluxo de aprovação segura, tools de mídia — documentados como backlog em `02_SPEC` seção 5.

## 8. Evolução futura (backlog)

Ver `02_SPEC` seção 5 e `01_RAG` RAG-004/RAG-005 para o webhook receiver e a lista de tools planejadas (`whatsapp_enviar_midia`, `whatsapp_solicitar_aprovacao`, etc.) — não implementar sem pedido explícito do operador. Migrar VP Click/Requisições/Pós-Venda/Borderô para emitir eventos reais é trabalho nos repositórios desses sistemas, não neste.

## 9. Referências

Evolution API: documentação interna em `docs/` do `whatsapp-mcp-hub` original (não faz parte deste repositório, ficou no hub).
