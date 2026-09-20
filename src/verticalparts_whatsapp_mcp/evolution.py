from __future__ import annotations

from typing import Any

import httpx

from .config import settings


class EvolutionClient:
    def __init__(self) -> None:
        self.base_url = settings.evolution_base_url
        self.instance = settings.evolution_instance
        self.headers = {
            "Content-Type": "application/json",
            "apikey": settings.evolution_api_key,
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                **kwargs,
            )
        response.raise_for_status()
        if not response.content:
            return {"ok": True}
        return response.json()

    async def status(self) -> Any:
        return await self._request("GET", f"/instance/connectionState/{self.instance}")

    async def verificar_numero(self, numero: str) -> Any:
        return await self._request(
            "POST",
            f"/chat/whatsappNumbers/{self.instance}",
            json={"numbers": [numero]},
        )

    async def enviar_texto(self, numero: str, texto: str) -> Any:
        return await self._request(
            "POST",
            f"/message/sendText/{self.instance}",
            json={"number": numero, "text": texto},
        )

    async def buscar_mensagens(self, remote_jid: str, limite: int = 20) -> Any:
        return await self._request(
            "POST",
            f"/chat/findMessages/{self.instance}",
            json={
                "where": {"key": {"remoteJid": remote_jid}},
                "limit": max(1, min(limite, 100)),
            },
        )


evolution = EvolutionClient()
