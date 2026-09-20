from __future__ import annotations

from enum import StrEnum


class Risk(StrEnum):
    READ = "read"
    CRITICAL = "critical"


def require_confirmation(risk: Risk, confirmation: str | None) -> None:
    if risk == Risk.READ:
        return
    expected = {Risk.CRITICAL: "CONFIRMO"}[risk]
    if confirmation != expected:
        raise PermissionError(
            f"Operação {risk} exige confirmação explícita: {expected}. "
            "A LLM deve mostrar o número exato e o texto exato antes de pedir a confirmação."
        )
