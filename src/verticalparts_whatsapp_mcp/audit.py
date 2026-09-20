from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import settings

SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "APIKEY", "AUTHORIZATION")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            upper = str(k).upper()
            out[k] = "[REDACTED]" if any(m in upper for m in SENSITIVE_MARKERS) else _redact(v)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def write_audit(event: str, payload: dict[str, Any]) -> None:
    path: Path = settings.audit_log
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **_redact(payload),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
