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

Três responsabilidades deliberadamente separadas: **MCP** (comandos explícitos, este repositório), **gateway de eventos** (gatilhos automáticos dos sistemas internos — ainda não implementado, só desenhado), **webhook receiver** (mensagens recebidas — ainda não implementado). Nenhum sistema novo deve falar direto com `/message/*` da Evolution API — só através de um desses três canais.

## RAG-005 — Estado real da integração por sistema (não confundir "pretendido" com "implementado")

- **Pós-Venda 360**: já manda WhatsApp de verdade, mas fala **direto com a Evolution API**, contornando tanto o MCP quanto o gateway de eventos (que ainda não existe). Documentado como temporário, migração ainda não feita.
- **VP Click**: integração pretendida (gatilhos de tarefa: `status_changed`, `priority_changed`, `assignee_changed`, `due_date_arrives`, `task_created`, `task_moved`), **não implementada**.
- **VP Requisições**: integração pretendida (aviso de aprovação, resumo, link seguro), **não implementada**. O gateway não decide alçada — só transporta e registra; a regra de negócio pertence ao VP Requisições.
- **Borderô/Hermes**: integração pretendida (envio de relatórios/borderôs, Telegram continua em paralelo), **não implementada**.

Contrato de evento proposto (ainda não versionado em produção):

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

## RAG-007 — Segredos

- `EVOLUTION_API_KEY`: autentica contra a Evolution API real (WhatsApp corporativo inteiro). Nunca versionar, nunca logar.
- `X-API-Key` do gateway deste MCP: mesmo padrão dos três irmãos.
- Conteúdo de mensagem: `audit.py` grava `chars` (tamanho) do texto enviado, não o texto em si — decisão deliberada de privacidade, já presente no código original.

## RAG-008 — Anti-padrões

Nunca como padrão:
- mandar mensagem de teste para um número real sem que o operador peça explicitamente e sem saber quem é o dono do número;
- tratar aprovação de negócio (financeira, requisição) como decidível só por uma mensagem de texto livre recebida no WhatsApp — precisa de `approval_id`, token de uso único, expiração e idempotência (ver `02_SPEC`);
- assumir que os gatilhos de plataforma já passam por este MCP — hoje não passam (RAG-005);
- criar uma tool genérica tipo `whatsapp_chamar_api` que exponha a Evolution API diretamente — o objetivo deste MCP é justamente esconder esse detalhe.

## RAG-009 — Quando parar

Pedir clarificação se:
- o número de destino é ambíguo ou não foi confirmado pelo operador;
- o pedido é para desligar `WHATSAPP_MCP_ALLOW_WRITES` sem entender o impacto em quem já depende disso;
- uma "aprovação" chegou só como texto livre no WhatsApp, sem os campos de segurança do RAG-008.
