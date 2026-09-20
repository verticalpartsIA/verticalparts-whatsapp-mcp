# 01 — RAG CANÔNICO — VerticalParts WhatsApp MCP

Versão: 2026-09-19
Classificação: conhecimento operacional canônico

---

## RAG-000 — Regra de uso

Consultas que devem recuperar este RAG incluem: WhatsApp, Evolution API, mensagem, número de telefone, JID, gatilho de plataforma, aprovação por WhatsApp, Pós-Venda 360, pv360.

## RAG-001 — Missão

Dar à VerticalParts uma interface única de WhatsApp — para Claude e, no futuro, para os sistemas internos — sem que ninguém precise conhecer endpoint, instância, chave ou formato de JID da Evolution API. Mesma missão dos três irmãos, com um risco adicional: o efeito de uma mutação sai da infraestrutura e chega a uma pessoa real.

## RAG-002 — Hierarquia de verdade

1. Estado vivo (Evolution API real);
2. `config/systems.yaml` (quando existir o gateway de eventos);
3. Código;
4. Documentos canônicos;
5. Memória de conversa.

## RAG-003 — Por que este MCP foi extraído para um repositório próprio

Nasceu como subdiretório de `whatsapp-mcp-hub`, um monorepo que também continha o agente Hermes, notas de n8n, rotinas de Borderô e documentação da Evolution API — tudo misturado. Isso é exatamente o problema que o operador identificou: WhatsApp é infraestrutura compartilhada (quase toda automação da VerticalParts vai depender dele — VP Click, VP Requisições, Pós-Venda, Borderô), não uma feature acoplada a um site ou hub específico. Deixar acoplado cria dependência escondida: quem mexe no hub pode quebrar o WhatsApp de todo mundo sem saber. Extraído para `verticalparts-whatsapp-mcp` em 2026-09-19, preservando o código e a documentação já reais (não reescritos do zero) — só reorganizados no padrão numerado da família e com o modelo de risco elevado (ver RAG-006A).

## RAG-004 — Arquitetura de três canais (já desenhada antes deste repositório existir)

```text
Comando humano:     Usuário -> Claude -> MCP WhatsApp -> Evolution API -> WhatsApp
Gatilho de sistema:  VP Click / Requisições / Pós-Venda / Borderô -> gateway de eventos -> Evolution API -> WhatsApp
Mensagem recebida:   WhatsApp -> Evolution API -> webhook central -> roteamento -> sistema/IA/humano
```

Três responsabilidades deliberadamente separadas: **MCP** (comandos explícitos, `server.py`), **gateway de eventos** (gatilhos automáticos dos sistemas internos, `events_app.py` — implementado em 2026-09-20), **webhook receiver** (mensagens recebidas — ainda não implementado). Nenhum sistema novo deve falar direto com `/message/*` da Evolution API — só através de um desses três canais.

O gateway de eventos roda como **processo separado** do MCP (`verticalparts-whatsapp-events`, porta 8011, endpoint `POST /events` em `whatsapp-mcp.vpsistema.com/events`) — não é uma tool MCP, porque quem chama é um sistema, não uma LLM. Isso muda o modelo de segurança por completo: ver RAG-006B.

## RAG-005 — Estado real da integração por sistema (não confundir "pretendido" com "implementado")

- **Pós-Venda 360**: já manda WhatsApp de verdade, mas fala **direto com a Evolution API**, contornando tanto o MCP quanto o gateway de eventos (que já existe desde 2026-09-20, mas essa migração específica ainda não foi feita). Documentado como temporário.
- **VP Click**: **religado ao gateway em 2026-09-20** (branch `feature/whatsapp-events-gateway-integration` em `005_vpclick`, ainda não mesclada em `main`) — o motor de trigger→pg_net→Edge Function já existente naquele repo (fases 1-4, 19/09; `supabase/functions/whatsapp-notify-event`) ganhou um caminho de envio real que chama `POST /events` deste gateway (templates `vpclick_watcher_added`/`vpclick_mention`/`vpclick_task_completed`, adicionados a `config/templates.yaml` nesta mesma data), em vez de um dia falar direto com a Evolution API. **Continua em dry-run por padrão**: só ativa quando alguém configurar os secrets `EVENTS_GATEWAY_URL`/`EVENTS_GATEWAY_TOKEN` e `WHATSAPP_REAL_SEND=true` na Edge Function do projeto `vp-click` (ref `sfpnjwllcmentoocylow`) — decisão separada, ainda não tomada. Ligar o envio real de fato afeta usuários reais de produção (quem criou cada tarefa, quem foi mencionado, quem observa) — não fazer sem revisar antes.
- **VP Requisições**: mesma situação — gateway pronto (`requisicoes`, templates `requisition_*`), falta o VP Requisições emitir. O gateway não decide alçada — só transporta e registra; a regra de negócio continua pertencendo ao VP Requisições.
- **Borderô/Hermes**: mesma situação — gateway pronto (`bordero`, template `bordero_relatorio`), falta o Borderô/Hermes emitir. Telegram continua em paralelo, não é substituído.

Contrato de evento real (implementado em 2026-09-20, `POST /events` no gateway):

~~~json
{
  "source": "vpclick",
  "event": "task.completed",
  "record_id": "uuid-ou-codigo",
  "recipient": {"user_id": "uuid-opcional", "phone": "5511999999999"},
  "template": "task_completed",
  "data": {"title": "Tarefa X", "url": "https://..."},
  "idempotency_key": "vpclick:task.completed:uuid:versao"
}
~~~

## RAG-006 — Política de risco

READ: sem confirmação — `whatsapp_status`, `whatsapp_verificar_numero`, `whatsapp_buscar_mensagens`.

CRITICAL (`CONFIRMO` **e** `WHATSAPP_MCP_ALLOW_WRITES=true`): `whatsapp_enviar_texto` — única tool, tratamento reforçado (ver RAG-006A).

## RAG-006A — Por que `whatsapp_enviar_texto` tem duas travas, não uma

Descoberto na homologação de 2026-09-19: a trava original (só o flag `WHATSAPP_MCP_ALLOW_WRITES`) estava ligada em produção via override de systemd, sem confirmação de que o checklist de segurança do próprio projeto (`docs/security.md` original) tinha sido cumprido — nenhuma tool chegou a mandar mensagem real só porque o número de teste usado não existia. Uma trava única, controlada só por quem tem acesso ao host, não protege contra uma LLM (esta mesma, em qualquer sessão futura) decidir enviar uma mensagem real sem que ninguém tenha pedido. Por isso agora são duas: o flag (kill switch de infraestrutura, "este ambiente pode mandar mensagem real ou não") **e** `confirmation='CONFIRMO'` por chamada (a LLM precisa justificar e confirmar cada envio, não só o ambiente permitir). As duas precisam estar verdadeiras — uma sem a outra não basta.

## RAG-006B — Segurança do gateway de eventos (`POST /events`) — não é o mesmo modelo do MCP

O gateway de eventos não tem `CONFIRMO` porque não há humano nem LLM na chamada — quem chama é um sistema (VP Click, Requisições, Pós-Venda, Borderô). A segurança vem de quatro camadas diferentes, todas obrigatórias:

1. **Token por sistema de origem** (`config/systems.yaml`, `Authorization: Bearer <token>`) — cada sistema tem o seu; um token vazado só compromete aquele sistema, não os outros (testado: um token válido para `vpclick` é recusado se o payload declarar `source: requisicoes`).
2. **Template fixo, nunca texto livre** (`config/templates.yaml`) — o gateway recusa (`400`) qualquer `template` não registrado. Isso é o que impede um sistema com bug ou comprometido de mandar qualquer mensagem arbitrária pelo WhatsApp corporativo — o pior que pode acontecer é mandar um template legítimo com dados errados, não texto arbitrário.
3. **Idempotência** (SQLite, `idempotency_key`) — reenviar a mesma chave nunca manda a mensagem de novo; devolve o resultado já processado (`replay: true`).
4. **Mesmo kill switch do MCP** (`WHATSAPP_MCP_ALLOW_WRITES`) — se o operador desligar envios, os dois canais param juntos.

Não adicionar `CONFIRMO` aqui — quebraria o próprio propósito de automação. Não remover nenhuma das quatro camadas acima achando que é redundante.

## RAG-007 — Segredos

- `EVOLUTION_API_KEY`: autentica contra a Evolution API real (WhatsApp corporativo inteiro). Nunca versionar, nunca logar.
- `X-API-Key` do gateway MCP (`/mcp`): mesmo padrão dos três irmãos.
- Token por sistema (`config/systems.yaml`, canal `/events`): nunca versionar (arquivo já no `.gitignore`), nunca reutilizar entre sistemas diferentes.
- Conteúdo de mensagem: `audit.py` grava `chars` (tamanho) do texto enviado, não o texto em si — decisão deliberada de privacidade, já presente no código original. O gateway de eventos segue a mesma regra: audita `template`+`data_keys` implícitos via `chars`, nunca o texto renderizado.

## RAG-008 — Anti-padrões

Nunca como padrão:
- mandar mensagem de teste para um número real sem que o operador peça explicitamente e sem saber quem é o dono do número;
- tratar aprovação de negócio (financeira, requisição) como decidível só por uma mensagem de texto livre recebida no WhatsApp — precisa de `approval_id`, token de uso único, expiração e idempotência (ver `02_SPEC`);
- assumir que um sistema (VP Click, Requisições, Borderô) já emite eventos para o gateway só porque o gateway existe e está pronto para receber — confirme antes (RAG-005);
- aceitar template livre no gateway de eventos, ou adicionar um jeito de o `data` de um evento virar texto arbitrário — o ponto inteiro do gateway é nunca aceitar texto livre de um sistema;
- criar uma tool genérica tipo `whatsapp_chamar_api` que exponha a Evolution API diretamente — o objetivo deste MCP é justamente esconder esse detalhe.

## RAG-010 — Teste real do gateway de eventos contra a Evolution API (2026-09-20)

Executado o runbook PARTE H pela primeira vez: evento simulado manualmente (mesmo formato que o VP Click emitiria — `source: vpclick`, template `task_completed`, token real de `config/systems.yaml`) contra `POST /events` em produção, para um destinatário de teste explicitamente autorizado pelo operador. Resultado: `200`, `message_id` real da Evolution API — mensagem chegou de verdade. Reenvio da mesma `idempotency_key` devolveu `replay: true`, mesmo `message_id`, sem mandar uma segunda mensagem.

**Bug real encontrado e corrigido durante esse teste**: `WHATSAPP_MCP_ALLOW_WRITES` estava `false` nos dois serviços (`whatsapp-mcp.service` e `whatsapp-events.service`) no processo real, apesar de:
- a documentação (`05_RUNBOOK` PARTE E, `00_READ_FIRST` seção 6) registrar a decisão de 2026-09-20 como "mantido ligado, protege os dois canais igualmente";
- os drop-ins systemd `*.service.d/allow-writes.conf` existirem e declararem `Environment="WHATSAPP_MCP_ALLOW_WRITES=true"`.

Causa raiz: neste host, quando a mesma variável aparece em `EnvironmentFile=` (o `.env`, que tinha `false`) e em `Environment=` de um drop-in (`true`), **o valor do `EnvironmentFile=` prevalece no processo real** — o oposto do que a intuição sobre ordem de carregamento sugere. Verificado lendo `/proc/<pid>/environ` do processo real, não só `systemctl show` (que mostra os fragmentos declarados, não necessariamente o valor resolvido). Ou seja: o canal MCP (`whatsapp_enviar_texto`) também estava, na prática, bloqueado por escrita há um tempo indeterminado, sem que a documentação refletisse isso — a "hierarquia de verdade" (RAG-002) existe exatamente para este tipo de caso: o que a documentação registra como decisão não é o mesmo que o estado vivo observado.

Correção aplicada: valor real editado direto no `.env` (`WHATSAPP_MCP_ALLOW_WRITES=true`, fonte única compartilhada pelos dois serviços via `EnvironmentFile=`), drop-ins `allow-writes.conf` removidos dos dois serviços (eram inertes/enganosos). Confirmado após a correção, lendo `/proc/<pid>/environ` dos dois processos reiniciados: ambos `true`.

**O que este teste NÃO prova**: o VP Click (`005_vpclick`) ainda não tem, no seu próprio código, nenhuma chamada real a `POST /events` — o evento usado neste teste foi simulado manualmente com o token real de `vpclick`, não emitido pela aplicação. Não atualizar RAG-005 para "implementado" até que exista uma chamada real partindo do código do VP Click.

**Lição estrutural**: nunca confiar em `systemctl show -p Environment` nem na existência de um drop-in como prova de que uma flag de ambiente está de fato ativa num processo — validar sempre lendo o ambiente do processo em execução (`/proc/<pid>/environ`) ou o comportamento observado (uma chamada real recusada/aceita). Isso vale para qualquer flag crítica desta família de MCPs, não só `WHATSAPP_MCP_ALLOW_WRITES`.

**Incidente relacionado, achado no mesmo teste (2026-09-20)**: a Edge Function `whatsapp-notify-event` do VP Click (`005_vpclick`) estava retornando `503 BOOT_ERROR` em produção — e isso já era verdade **antes** de qualquer mudança nesta sessão (confirmado reimplantando o código original sem alteração, mesmo erro). Só havia uma linha em `notification_dispatch_log` desde 19/09 18:04, apesar de mais de um dia de uso real depois disso — o motor de avisos do VP Click estava efetivamente fora do ar, sem alerta (disparo via `pg_net`, fire-and-forget, sem monitoramento). Causa raiz isolada por bissecção: o import `jsr:@supabase/supabase-js@2` falhava ao resolver/bootar nessa function especificamente no momento do deploy; trocar para `npm:@supabase/supabase-js@2` resolveu (confirmado: 503 → 401 normal). Corrigido e mesclado em `main` do `005_vpclick` (commit `166d47f`, PR de merge `ad70cf3`), junto com a integração do gateway. Detalhe completo em `01_RAG-005` acima e no histórico de commits daquele repositório.

## RAG-009 — Quando parar

Pedir clarificação se:
- o número de destino é ambíguo ou não foi confirmado pelo operador;
- o pedido é para desligar `WHATSAPP_MCP_ALLOW_WRITES` sem entender o impacto em quem já depende disso;
- uma "aprovação" chegou só como texto livre no WhatsApp, sem os campos de segurança do RAG-008.
