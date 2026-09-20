# 00 — LEIA PRIMEIRO — VerticalParts WhatsApp MCP

Versão documental: 2026-09-20
Status: canônico, **migração concluída e homologada** — código já rodava em produção antes deste repositório existir; nesta data foi extraído, com governança elevada, e o deploy real na VPS foi migrado para o novo repositório
Escopo: WhatsApp corporativo da VerticalParts (via Evolution API) por LLM e, no futuro, por gatilhos internos

## 1. Finalidade deste conjunto

Este repositório contém o MCP de WhatsApp da VerticalParts. Ele existia antes como um subdiretório dentro de um hub maior (`whatsapp-mcp-hub`, que também tinha Hermes, n8n, Borderô e docs da Evolution API misturados) — foi extraído para cá porque WhatsApp é infraestrutura compartilhada (quase toda solução da VerticalParts vai depender dele), não uma feature de um site só. Ver `01_RAG` RAG-003 para o detalhe da extração.

Irmãos deste projeto: `verticalparts-infrastructure-mcp`, `verticalparts-github-mcp`, `verticalparts-supabase-mcp` — mesma filosofia de governança (classificação de risco, confirmação proporcional, auditoria sem segredo), quarto membro da família.

## 2. Diferença central em relação aos três irmãos

Os três primeiros MCPs administram **sistemas internos** (VPS, GitHub, Supabase) — o pior caso de uma mutação errada é interno, corrigível. Este MCP manda **mensagem real para uma pessoa real**, instantaneamente, sem lixeira. Isso muda a régua de risco: `whatsapp_enviar_texto` é a única tool deste catálogo que sai da infraestrutura da VerticalParts e chega no mundo real.

## 3. Ordem obrigatória de leitura para LLMs

1. `00_READ_FIRST_WHATSAPP_MCP.md`
2. `03_INSTRUCTIONS_LLM_WHATSAPP_MCP_VERTICALPARTS.md`
3. `01_RAG_WHATSAPP_MCP_VERTICALPARTS.md`
4. `02_SPEC_WHATSAPP_MCP_VERTICALPARTS.md`
5. `04_SDD_WHATSAPP_MCP_VERTICALPARTS.md`
6. `05_RUNBOOK_COPY_PASTE_SETUP_AND_RECOVERY.md`
7. `README.md`, `config/*.example.yaml`, código-fonte.

## 4. Hierarquia de verdade

1. Estado vivo observado (chamada real à Evolution API — `whatsapp_status`, etc.);
2. `config/systems.yaml` do runtime — quais sistemas internos têm permissão de originar mensagens (quando o gateway de eventos existir — ver seção 6);
3. Código em execução;
4. Documentos canônicos numerados;
5. Memória de conversa.

## 5. Estado atual conhecido em 2026-09-19

**Homologado e em produção há dias**, antes mesmo deste repositório existir — o código já rodava como `whatsapp-mcp.service` na VPS (`/root/whatsapp-mcp-hub/whatsapp-mcp`), atrás de Nginx + TLS em `https://whatsapp-mcp.vpsistema.com/mcp`, protegido por `X-API-Key`, instância Evolution API `pv360`.

Testado nesta sessão, via o conector real conectado ao claude.ai (não script):
- `whatsapp_status` → `{"instance": {"instanceName": "pv360", "state": "open"}}` — instância corporativa conectada e saudável;
- `whatsapp_verificar_numero` → funcionou corretamente para um número de teste inexistente (`exists: false`);
- `whatsapp_buscar_mensagens` → funcionou corretamente, histórico vazio para o número de teste (não tocou dado real de cliente);
- `whatsapp_enviar_texto` → **achado real**: a chamada foi processada de verdade pela Evolution API (não bloqueada pelo MCP), porque `WHATSAPP_MCP_ALLOW_WRITES=true` estava ligado em produção via um override de systemd (`/etc/systemd/system/whatsapp-mcp.service.d/allow-writes.conf`, criado em 15/09) — **sem que o checklist do próprio `docs/security.md` original (autenticação externa pronta, teste com destinatário controlado, auditoria validada, rotação de credenciais expostas) tivesse evidência de estar cumprido**. Só não houve envio real porque o número de teste usado não existe no WhatsApp.

**Descoberta estrutural importante**: os gatilhos de plataforma (VP Click, VP Requisições, Borderô) **não passam por este MCP hoje** — não existe integração implementada ainda (só documentada como "pretendida"). O Pós-Venda 360 já manda WhatsApp de verdade, mas fala **direto com a Evolution API**, contornando o MCP — documentado como temporário até migração controlada. Ou seja: a trava de escrita deste MCP protege o canal Claude/humano, não a automação de produção — as duas coisas nunca estiveram no mesmo caminho.

## 6. Migração real concluída (2026-09-20)

- Repositório publicado em `github.com/verticalpartsIA/verticalparts-whatsapp-mcp`;
- deploy na VPS migrado de `/root/whatsapp-mcp-hub/whatsapp-mcp` para `/opt/verticalparts-whatsapp-mcp` (mesmo padrão dos três irmãos), `.env` real copiado sem recriar a `EVOLUTION_API_KEY`;
- `whatsapp-mcp.service` (systemd) atualizado para o novo `WorkingDirectory`/`ExecStart`, reiniciado, `active`;
- validado pelo conector real conectado ao claude.ai: `whatsapp_status` → `{"instance": {"instanceName": "pv360", "state": "open"}}`, mesmo resultado de antes da migração;
- validado direto no processo migrado (import fresco, sem depender de cache de schema de cliente MCP): `whatsapp_enviar_texto` sem `confirmation` → bloqueado com a nova mensagem exigindo `CONFIRMO`, nenhuma chamada de rede feita;
- override `/etc/systemd/system/whatsapp-mcp.service.d/allow-writes.conf` (`WHATSAPP_MCP_ALLOW_WRITES=true`) **mantido como estava** — não foi alterado nesta migração, decisão pendente com o operador (ver seção 7).

## 7. Próximos passos (não-bloqueantes, na ordem de prioridade)

1. ~~Decidir com o operador se `WHATSAPP_MCP_ALLOW_WRITES=true` deve continuar ligado~~ — **decidido em 2026-09-20: mantido ligado**, agora que o gate por confirmação (`CONFIRMO`) está ativo em produção (ver seção 6). A dupla trava (flag + `CONFIRMO`) é considerada suficiente pelo operador; reavaliar se o uso real mostrar necessidade de mais controle (ex.: quando o gateway de eventos existir).
2. Construir o "gateway de eventos" já desenhado em `01_RAG` RAG-004/RAG-005 — hoje é só documentação, a implementação real (`events/`) ainda não existe.
3. Migrar o Pós-Venda 360 do acesso direto à Evolution API para o gateway central (trabalho no repositório do Pós-Venda 360, não neste).
4. Rotacionar a `EVOLUTION_API_KEY` — não há evidência de que isso já tenha sido feito desde que o projeto documentou essa pendência.
5. Descomissionar `/root/whatsapp-mcp-hub/whatsapp-mcp` (caminho antigo) depois de um período de observação do novo deploy — ver `05_RUNBOOK` PARTE C5.

## 7. Segredos

Nunca versionar nem reproduzir:
- `EVOLUTION_API_KEY` (autentica contra a Evolution API real);
- `X-API-Key` do gateway deste MCP.

## 8. Confirmações de risco

- leitura: sem confirmação (`whatsapp_status`, `whatsapp_verificar_numero`, `whatsapp_buscar_mensagens`);
- envio de mensagem: exige `WHATSAPP_MCP_ALLOW_WRITES=true` no servidor **e** `confirmation='CONFIRMO'` por chamada — dupla trava, porque é a única tool desta família que produz um efeito irreversível fora da infraestrutura da VerticalParts.

## 9. Regra final

Uma LLM que leia os arquivos canônicos deve conseguir: entender por que WhatsApp é infraestrutura compartilhada e não feature de um site, descobrir o estado real da instância, nunca mandar mensagem sem confirmação explícita e justificada, e saber que os gatilhos de plataforma ainda não passam por aqui.
