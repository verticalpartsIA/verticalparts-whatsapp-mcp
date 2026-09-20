from __future__ import annotations

from typing import Any

import yaml

from .config import settings


def load_systems() -> dict[str, dict[str, Any]]:
    """Carrega config/systems.yaml: quais sistemas internos podem originar eventos e o token de cada um."""
    path = settings.events_systems_file
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("systems", {})


def authenticate_source(source: str, token: str) -> bool:
    systems = load_systems()
    entry = systems.get(source)
    if not entry:
        return False
    expected = entry.get("token", "")
    return bool(expected) and token == expected


def load_templates() -> dict[str, str]:
    """Carrega config/templates.yaml: nome do template -> texto com placeholders {campo}."""
    path = settings.events_templates_file
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("templates", {})


def render_template(name: str, data: dict[str, Any]) -> str:
    templates = load_templates()
    template_text = templates.get(name)
    if template_text is None:
        raise KeyError(f"Template '{name}' não está registrado em config/templates.yaml")
    try:
        return template_text.format(**data)
    except KeyError as exc:
        raise KeyError(f"Campo obrigatório do template '{name}' ausente em 'data': {exc}") from exc
