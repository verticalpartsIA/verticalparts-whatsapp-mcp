from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    evolution_base_url: str = os.getenv("EVOLUTION_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    evolution_api_key: str = os.getenv("EVOLUTION_API_KEY", "")
    evolution_instance: str = os.getenv("EVOLUTION_INSTANCE", "pv360")
    mcp_transport: str = os.getenv("MCP_TRANSPORT", "stdio")
    mcp_host: str = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port: int = int(os.getenv("MCP_PORT", "8010"))
    audit_log: Path = Path(os.getenv("WHATSAPP_MCP_AUDIT_LOG", "./data/audit.jsonl"))
    allow_writes: bool = _bool("WHATSAPP_MCP_ALLOW_WRITES", False)

    def validate(self) -> None:
        if not self.evolution_api_key:
            raise RuntimeError("EVOLUTION_API_KEY não configurada")
        if not self.evolution_instance:
            raise RuntimeError("EVOLUTION_INSTANCE não configurada")


settings = Settings()
