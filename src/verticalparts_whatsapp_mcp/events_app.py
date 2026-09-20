from __future__ import annotations

from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .audit import write_audit
from .config import settings
from .evolution import evolution
from .events_registry import authenticate_source, load_templates, render_template
from .events_store import get_processed, mark_done, mark_failed, reserve
from .phone import normalizar_numero

REQUIRED_FIELDS = ("source", "event", "recipient", "template", "idempotency_key")


def _bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return ""
    return header[7:].strip()


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


async def list_templates(request: Request) -> JSONResponse:
    return JSONResponse({"templates": sorted(load_templates().keys())})


async def receive_event(request: Request) -> JSONResponse:
    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "corpo não é JSON válido"}, status_code=400)

    missing = [f for f in REQUIRED_FIELDS if not body.get(f)]
    if missing:
        return JSONResponse({"ok": False, "error": f"campos obrigatórios ausentes: {missing}"}, status_code=400)

    source = str(body["source"])
    token = _bearer_token(request)
    if not authenticate_source(source, token):
        write_audit("events_auth_falhou", {"source": source, "ok": False})
        return JSONResponse({"ok": False, "error": "origem não autorizada ou token inválido"}, status_code=401)

    if not settings.allow_writes:
        write_audit("events_bloqueado_allow_writes", {"source": source, "event": body.get("event"), "ok": False})
        return JSONResponse({"ok": False, "error": "envio desabilitado por WHATSAPP_MCP_ALLOW_WRITES=false"}, status_code=503)

    recipient = body.get("recipient") or {}
    phone = recipient.get("phone")
    if not phone:
        return JSONResponse({"ok": False, "error": "recipient.phone é obrigatório"}, status_code=400)

    try:
        numero = normalizar_numero(str(phone))
    except ValueError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    template_name = str(body["template"])
    data = body.get("data") or {}
    try:
        texto = render_template(template_name, data)
    except KeyError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    idempotency_key = str(body["idempotency_key"])
    event_name = str(body["event"])
    record_id = body.get("record_id")

    existing = get_processed(idempotency_key)
    if existing and existing["status"] == "sent":
        return JSONResponse({"ok": True, "message_id": existing["message_id"], "idempotency_key": idempotency_key, "replay": True})

    reserved = reserve(idempotency_key, source, event_name, record_id, template_name, numero)
    if not reserved:
        # Já reservado por outra requisição concorrente ou em processamento -- não reenviar.
        return JSONResponse({"ok": True, "idempotency_key": idempotency_key, "status": "already_processing"})

    try:
        result = await evolution.enviar_texto(numero, texto)
    except Exception as exc:
        mark_failed(idempotency_key)
        write_audit(
            "events_enviar_falhou",
            {"source": source, "event": event_name, "record_id": record_id, "template": template_name, "ok": False, "erro": str(exc)},
        )
        return JSONResponse({"ok": False, "error": f"falha ao enviar via Evolution API: {exc}"}, status_code=502)

    message_id = None
    if isinstance(result, dict):
        message_id = (result.get("key") or {}).get("id")
    mark_done(idempotency_key, message_id)

    write_audit(
        "events_enviar",
        {
            "source": source,
            "event": event_name,
            "record_id": record_id,
            "template": template_name,
            "numero": numero,
            "message_id": message_id,
            "chars": len(texto),
            "ok": True,
        },
    )
    return JSONResponse({"ok": True, "message_id": message_id, "idempotency_key": idempotency_key})


app = Starlette(
    routes=[
        Route("/events/health", health, methods=["GET"]),
        Route("/events/templates", list_templates, methods=["GET"]),
        Route("/events", receive_event, methods=["POST"]),
    ]
)


def main() -> None:
    settings.validate()
    uvicorn.run(app, host=settings.events_host, port=settings.events_port)


if __name__ == "__main__":
    main()
