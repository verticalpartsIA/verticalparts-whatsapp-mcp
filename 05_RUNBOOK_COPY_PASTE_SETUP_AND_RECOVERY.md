# 05 — RUNBOOK COPY/PASTE — Setup, Deploy e Recuperação

Versão: 2026-09-19
Status: canônico
Nota: este MCP já estava em produção antes deste repositório existir. Este runbook cobre tanto a reconstrução do zero quanto a migração real feita em 2026-09-19 (`/root/whatsapp-mcp-hub/whatsapp-mcp` → `/opt/verticalparts-whatsapp-mcp`).

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
# manter o override allow-writes.conf existente (ou revisar — ver PARTE D)
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

# PARTE D — DECISÃO PENDENTE: `WHATSAPP_MCP_ALLOW_WRITES`

O override `/etc/systemd/system/whatsapp-mcp.service.d/allow-writes.conf` liga `WHATSAPP_MCP_ALLOW_WRITES=true` desde 15/09, sem evidência de que o checklist do `docs/security.md` original foi cumprido. Agora que `confirmation='CONFIRMO'` existe como segunda trava (ver `04_SDD` seção 2.3), decidir com o operador:

- **manter ligado**: envio funciona para qualquer chamada com `CONFIRMO` correto;
- **desligar até revisão completa**: remover o override (`sudo rm /etc/systemd/system/whatsapp-mcp.service.d/allow-writes.conf && sudo systemctl daemon-reload && sudo systemctl restart whatsapp-mcp.service`) — nenhum envio funciona até religar deliberadamente.

Não desligar nem religar sem confirmar com o operador primeiro — pode haver uso real dependendo do estado atual.

---

# PARTE E — ROTACIONAR A `EVOLUTION_API_KEY`

Pendência documentada desde a criação do projeto original, sem evidência de execução:

1. Gerar/obter a nova chave na configuração da Evolution API (fora deste MCP — é uma instância compartilhada, coordenar antes);
2. Atualizar `.env` em `/opt/verticalparts-whatsapp-mcp`;
3. Reiniciar o serviço;
4. Validar com `whatsapp_status`;
5. Revogar a chave antiga na Evolution API.

---

# PARTE F — CRITÉRIO DE SUCESSO

- `whatsapp_status` retorna estado real da instância;
- `whatsapp_verificar_numero` normaliza os três formatos aceitos;
- `whatsapp_buscar_mensagens` não expõe dado além do pedido;
- `whatsapp_enviar_texto` recusa sem `CONFIRMO`, recusa com `WHATSAPP_MCP_ALLOW_WRITES=false` mesmo com `CONFIRMO` certo, e só executa com as duas condições verdadeiras;
- nenhuma auditoria contém texto de mensagem;
- `EVOLUTION_API_KEY`/`X-API-Key` nunca apareceram em nenhuma resposta.
