from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .audit import write_audit
from .config import settings
from .evolution import evolution
from .phone import normalizar_numero as _numero
from .phone import remote_jid as _remote_jid
from .safety import Risk, require_confirmation

mcp = FastMCP(
    "VerticalParts WhatsApp",
    host=settings.mcp_host,
    port=settings.mcp_port,
)


@mcp.tool()
async def whatsapp_status() -> Any:
    """Consulta o estado da instância corporativa de WhatsApp na Evolution API."""
    result = await evolution.status()
    write_audit("whatsapp_status", {"ok": True})
    return result


@mcp.tool()
async def whatsapp_verificar_numero(numero: str) -> Any:
    """Verifica se um telefone está no WhatsApp. Aceita 011997663780, 11997663780 ou 5511997663780."""
    normalized = _numero(numero)
    result = await evolution.verificar_numero(normalized)
    write_audit("whatsapp_verificar_numero", {"numero": normalized, "ok": True})
    return result


@mcp.tool()
async def whatsapp_enviar_texto(numero: str, mensagem: str, confirmation: str | None = None) -> Any:
    """Envia uma mensagem de texto pelo WhatsApp corporativo. Irreversível: chega de verdade no celular do destinatário.
    Exige confirmation='CONFIRMO' e WHATSAPP_MCP_ALLOW_WRITES=true no ambiente — as duas condições são obrigatórias."""
    require_confirmation(Risk.CRITICAL, confirmation)
    if not settings.allow_writes:
        raise PermissionError(
            "Envio bloqueado por WHATSAPP_MCP_ALLOW_WRITES=false. Isso é uma decisão do operador do ambiente, "
            "não da confirmação desta chamada — as duas condições são exigidas juntas."
        )
    normalized = _numero(numero)
    text = (mensagem or "").strip()
    if not text:
        raise ValueError("A mensagem não pode ser vazia.")
    result = await evolution.enviar_texto(normalized, text)
    message_id = None
    if isinstance(result, dict):
        message_id = (result.get("key") or {}).get("id")
    write_audit(
        "whatsapp_enviar_texto",
        {
            "numero": normalized,
            "message_id": message_id,
            "chars": len(text),
            "ok": True,
        },
    )
    return result


@mcp.tool()
async def whatsapp_buscar_mensagens(contato: str, limite: int = 20) -> Any:
    """Busca o histórico recente de mensagens de um telefone ou remoteJid. Não altera dados."""
    jid = _remote_jid(contato)
    result = await evolution.buscar_mensagens(jid, limite)
    write_audit("whatsapp_buscar_mensagens", {"remote_jid": jid, "limite": limite, "ok": True})
    return result


def main() -> None:
    settings.validate()
    transport = settings.mcp_transport.strip().lower()
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise RuntimeError(f"MCP_TRANSPORT inválido: {transport}")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
