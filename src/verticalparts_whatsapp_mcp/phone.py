from __future__ import annotations

import re


def normalizar_numero(valor: str) -> str:
    digits = re.sub(r"\D", "", valor or "")

    # Formatos brasileiros comuns podem vir com o zero de chamada antes do DDD:
    # 011997663780 -> 11997663780 -> 5511997663780
    # 55011997663780 -> 5511997663780
    if digits.startswith("550") and len(digits) in {13, 14}:
        digits = "55" + digits[3:]
    elif digits.startswith("0") and len(digits) in {11, 12}:
        digits = digits[1:]

    if len(digits) in {10, 11}:
        digits = "55" + digits

    if len(digits) < 12 or len(digits) > 13:
        raise ValueError(
            "Número inválido. Informe telefone brasileiro com DDD, com ou sem DDI 55 e com ou sem zero inicial."
        )
    return digits


def remote_jid(valor: str) -> str:
    value = (valor or "").strip()
    if value.endswith("@s.whatsapp.net") or value.endswith("@lid") or value.endswith("@c.us"):
        return value
    return f"{normalizar_numero(value)}@s.whatsapp.net"
