"""websocket_handler — Helpers de streaming temps réel pour l'interface Open Views."""
from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


async def send_step(ws: WebSocket, label: str, text: str = "", status: str = "ok") -> None:
    """Émet un bloc de raisonnement en cascade vers le panneau central."""
    await ws.send_text(json.dumps({
        "type": "step",
        "label": label,
        "text": text,
        "status": status,  # ok | pending | error
    }, ensure_ascii=False))


async def send_assistant(ws: WebSocket, text: str) -> None:
    """Émet la réponse finale de l'agent dans le panneau chat."""
    await ws.send_text(json.dumps({"type": "assistant", "text": text}, ensure_ascii=False))


async def send_error(ws: WebSocket, detail: str) -> None:
    """Émet une erreur (sandbox / invariants physiques) dans le panneau chat."""
    await ws.send_text(json.dumps({"type": "error", "detail": detail}, ensure_ascii=False))


async def send_telemetry(ws: WebSocket, sample: dict[str, Any]) -> None:
    """Pousse un échantillon RAM/CPU vers le graphique D3.js."""
    await ws.send_text(json.dumps({"type": "telemetry", "sample": sample}, ensure_ascii=False))


async def send_artifacts_refresh(ws: WebSocket) -> None:
    """Déclenche le rafraîchissement de l'explorateur d'artéfacts."""
    await ws.send_text(json.dumps({"type": "artifacts"}, ensure_ascii=False))
