# 05 — RUNBOOK COPY/PASTE — Setup, Deploy e Recuperação

Versão: 2026-09-20
Status: canônico
Nota: este MCP já estava em produção antes deste repositório existir. Este runbook cobre a reconstrução do zero, a migração real feita em 2026-09-19 (`/root/whatsapp-mcp-hub/whatsapp-mcp` → `/opt/verticalparts-whatsapp-mcp`) e o deploy do gateway de eventos feito em 2026-09-20.

---

# PARTE A — CONFIGURAR O AMBIENTE

## A1. Credenciais necessárias

- `EVOLUTION_API_KEY`: chave da instância Evolution API já em produção (`pv360`). Recuperar do host, nunca gerar uma nova sem coordenar com quem mantém a Evolution API (afetaria produção real).
- `EVOLUTION_BASE_URL`: normalmente `http://127.0.0.1:8080` se a Evolution API roda na mesma VPS.

## A2. Preencher `.env`

~~~bash
cp .env.example .env
~~~

Preencher `EVOLUTION_API_KEY`, `EVOLUTION_BASE_URL`, `EVOLUTION_INSTANCE`.

## A3. Instalar dependências

~~~bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
~~~

## A4. Configurar o gateway de eventos (se for usá-lo)

~~~bash
cp config/systems.example.yaml config/systems.yaml
# gerar um token forte por sistema:
openssl rand -hex 32
# substituir cada SUBSTITUA_POR_UM_TOKEN_FORTE_UNICO em config/systems.yaml
~~~

`config/templates.yaml` já vem com os templates iniciais (VP Click/Requisições/Borderô) — editar/adicionar conforme necessário, nunca com um placeholder que vire texto livre (ver `02_SPEC` FR-007).

---

# PARTE B — TESTE LOCAL (stdio)

## B1. Rodar localmente

~~~bash
MCP_TRANSPORT=stdio verticalparts-whatsapp-mcp
~~~

## B2. Testes reais, na ordem

1. `whatsapp_status` — deve retornar `state` da instância (`open` = conectada);
2. `whatsapp_verificar_numero` com um número real conhecido — deve retornar `exists: true`;
3. `whatsapp_buscar_mensagens` com um contato real — deve retornar histórico real, sem erro;
4. `whatsapp_enviar_texto` **só** com `WHATSAPP_MCP_ALLOW_WRITES=true`, `confirmation="CONFIRMO"` e um **destinatário de teste controlado** (número que você mesmo pode conferir recebendo a mensagem) — nunca um número de exemplo genérico.

Só depois desses 4 testes reais este MCP pode ser considerado homologado.

## B3. Testar o gateway de eventos localmente (com Evolution mockada ou real)

~~~bash
MCP_TRANSPORT=stdio verticalparts-whatsapp-events
# ou, se preferir rodar via módulo diretamente:
python3 -m verticalparts_whatsapp_mcp.events_app
~~~

Testes na ordem, contra `http://127.0.0.1:8011`:

1. `GET /events/health` → `{"ok": true}`;
2. `GET /events/templates` → lista os nomes de `config/templates.yaml`;
3. `POST /events` sem header `Authorization` → `401`;
4. `POST /events` com token errado → `401`;
5. `POST /events` com `source`/token corretos mas `template` inexistente → `400`;
6. `POST /events` com template correto mas `data` faltando um campo do template → `400`;
7. Só com `WHATSAPP_MCP_ALLOW_WRITES=true`, `source`/token corretos, `template` e `data` completos, e um **destinatário de teste controlado**: `POST /events` deve retornar `200` com `message_id`; reenviar a **mesma** `idempotency_key` deve retornar `200` com `"replay": true`, sem mandar a mensagem de novo.

---

# PARTE C — MIGRAÇÃO DE `/root/whatsapp-mcp-hub/whatsapp-mcp` PARA `/opt/verticalparts-whatsapp-mcp`

Feita em 2026-09-19, ao extrair este repositório do monorepo original. Passos executados:

## C1. Clonar o novo repositório dedicado

~~~bash
sudo git clone https://github.com/verticalpartsIA/verticalparts-whatsapp-mcp.git /opt/verticalparts-whatsapp-mcp
cd /opt/verticalparts-whatsapp-mcp
sudo python3 -m venv .venv
sudo .venv/bin/pip install -e .
~~~

## C2. Copiar o `.env` real do local antigo (nunca recriar a chave à toa)

~~~bash
sudo cp /root/whatsapp-mcp-hub/whatsapp-mcp/.env /opt/verticalparts-whatsapp-mcp/.env
sudo chmod 600 /opt/verticalparts-whatsapp-mcp/.env
~~~

## C3. Atualizar o systemd unit para o novo caminho

~~~bash
sudo cp systemd/verticalparts-whatsapp-mcp.service.example /etc/systemd/system/whatsapp-mcp.service
# manter o override allow-writes.conf existente (ou revisar — ver PARTE E)
sudo systemctl daemon-reload
sudo systemctl restart whatsapp-mcp.service
sudo systemctl is-active whatsapp-mcp.service
~~~

## C4. Nginx e DNS

Não mudam — `whatsapp-mcp.vpsistema.com` já aponta para `127.0.0.1:8010`, mesma porta. Só validar que o serviço voltou a responder:

~~~bash
curl -i https://whatsapp-mcp.vpsistema.com/mcp
# esperado: 401 sem X-API-Key
~~~

## C5. Descomissionar o caminho antigo

Só depois de confirmar que o novo caminho está ativo e testado: remover `/root/whatsapp-mcp-hub/whatsapp-mcp` do monorepo antigo (ou deixar um `README` apontando para o novo repositório, se preferir não apagar imediatamente).

---

# PARTE D — DEPLOY DO GATEWAY DE EVENTOS (feito em 2026-09-20)

## D1. Configurar `config/systems.yaml` real no host

~~~bash
sudo cp /opt/verticalparts-whatsapp-mcp/config/systems.example.yaml /opt/verticalparts-whatsapp-mcp/config/systems.yaml
# gerar um token por sistema:
openssl rand -hex 32
# editar /opt/verticalparts-whatsapp-mcp/config/systems.yaml com os tokens reais
sudo chmod 600 /opt/verticalparts-whatsapp-mcp/config/systems.yaml
~~~

## D2. Instalar o systemd unit do gateway

~~~bash
sudo cp /opt/verticalparts-whatsapp-mcp/systemd/verticalparts-whatsapp-events.service.example /etc/systemd/system/whatsapp-events.service
sudo systemctl daemon-reload
sudo systemctl enable --now whatsapp-events.service
sudo systemctl is-active whatsapp-events.service
~~~

## D3. Adicionar o `location /events` ao vhost Nginx existente

~~~bash
sudo cp /opt/verticalparts-whatsapp-mcp/nginx/whatsapp-mcp.vpsistema.com.example.conf /etc/nginx/sites-available/whatsapp-mcp.vpsistema.com
sudo nginx -t
sudo systemctl reload nginx
~~~

## D4. Validar o endpoint público

~~~bash
curl -s https://whatsapp-mcp.vpsistema.com/events/health
# esperado: {"ok": true}
curl -s -X POST https://whatsapp-mcp.vpsistema.com/events -d '{}' -H "Content-Type: application/json"
# esperado: 401 (sem Authorization) ou 400 (campos ausentes) -- nunca 200
~~~

## D5. Registrar cada sistema real quando ele for migrado

Quando VP Click/Requisições/Borderô forem de fato atualizados para emitir eventos: confirmar o token entregue a cada um bate com `config/systems.yaml`, testar um evento real de ponta a ponta com destinatário controlado (mesmo cuidado da PARTE B3 item 7), só então considerar aquela integração "implementada" em `01_RAG` RAG-005.

---

# PARTE E — DECISÃO PENDENTE: `WHATSAPP_MCP_ALLOW_WRITES`

O override `/etc/systemd/system/whatsapp-mcp.service.d/allow-writes.conf` liga `WHATSAPP_MCP_ALLOW_WRITES=true` desde 15/09, sem evidência de que o checklist do `docs/security.md` original foi cumprido. Agora que `confirmation='CONFIRMO'` existe como segunda trava (ver `04_SDD` seção 2.3), decidir com o operador:

- **manter ligado**: envio funciona para qualquer chamada com `CONFIRMO` correto;
- **desligar até revisão completa**: remover o override (`sudo rm /etc/systemd/system/whatsapp-mcp.service.d/allow-writes.conf && sudo systemctl daemon-reload && sudo systemctl restart whatsapp-mcp.service`) — nenhum envio funciona até religar deliberadamente.

Não desligar nem religar sem confirmar com o operador primeiro — pode haver uso real dependendo do estado atual.

**Decidido em 2026-09-20: mantido ligado.** O flag agora protege os dois canais (MCP e gateway de eventos) igualmente.

---

# PARTE F — ROTACIONAR A `EVOLUTION_API_KEY`

Pendência documentada desde a criação do projeto original, sem evidência de execução:

1. Gerar/obter a nova chave na configuração da Evolution API (fora deste MCP — é uma instância compartilhada, coordenar antes);
2. Atualizar `.env` em `/opt/verticalparts-whatsapp-mcp`;
3. Reiniciar o serviço;
4. Validar com `whatsapp_status`;
5. Revogar a chave antiga na Evolution API.

---

# PARTE G — CRITÉRIO DE SUCESSO

- `whatsapp_status` retorna estado real da instância;
- `whatsapp_verificar_numero` normaliza os três formatos aceitos;
- `whatsapp_buscar_mensagens` não expõe dado além do pedido;
- `whatsapp_enviar_texto` recusa sem `CONFIRMO`, recusa com `WHATSAPP_MCP_ALLOW_WRITES=false` mesmo com `CONFIRMO` certo, e só executa com as duas condições verdadeiras;
- `POST /events` recusa sem token válido do `source` declarado, recusa template desconhecido/campo faltando, recusa com `WHATSAPP_MCP_ALLOW_WRITES=false`, e reenviar a mesma `idempotency_key` nunca manda a mensagem duas vezes;
- nenhuma auditoria contém texto de mensagem, renderizado ou não;
- `EVOLUTION_API_KEY`/`X-API-Key`/tokens de `config/systems.yaml` nunca apareceram em nenhuma resposta.

---

# PARTE H — TESTAR O GATEWAY DE EVENTOS CONTRA A EVOLUTION API REAL (pendente)

Ainda não feito porque nenhum sistema real emite eventos — quando for a hora:

1. Escolher um destinatário de teste controlado (mesma regra da PARTE B2 item 4);
2. Simular manualmente o evento que o sistema real vai mandar (`curl -X POST https://whatsapp-mcp.vpsistema.com/events` com o token real daquele `source`);
3. Confirmar que a mensagem chegou de verdade no destinatário de teste;
4. Reenviar a mesma `idempotency_key` e confirmar que não chega uma segunda mensagem;
5. Só então atualizar `01_RAG` RAG-005 marcando aquela integração como implementada.
