"""Open Views — Interface FastAPI + WebSockets pour RATISS V9 Aeon Prime.

Point d'entrée : uvicorn interface.app:app --host 0.0.0.0 --port 7860

Panneaux : Chat (gauche) · Raisonnement en cascade (centre) ·
Télémétrie + Artéfacts (droite).
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "security"))
sys.path.insert(0, str(ROOT / "skills" / "ratiss"))
sys.path.insert(0, str(ROOT / "skills" / "ratiss" / "ratiss_v9_aeon_prime"))

from security.session_manager import SessionManager
from orchestrator.prime_agent_wrapper import PrimeAgentBridge
from orchestrator.nemotron_client import NemotronClient
from orchestrator.skill_manager import SkillManager
from orchestrator.ratiss_skill import node_health, stress_test_p53
from security.workspace_isolator import WorkspaceIsolator

app = FastAPI(title="Open Views — RATISS V9 Aeon Prime", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS = SessionManager(db_path=str(ROOT / "data" / "sessions.db"))
WORKSPACES = WorkspaceIsolator(base=str(ROOT / "workspace"))
PRIME = PrimeAgentBridge()
NEMOTRON = NemotronClient()
SKILLS = SkillManager(manifest_path=str(ROOT / "config" / "skills_manifest.py"))

# Registres WebSocket par session
WS_REGISTRY: Dict[str, set] = {}


def get_session(x_ratiss_token: str = Header(default=""), token: str = ""):
    raw = x_ratiss_token or token
    if not raw:
        raise HTTPException(status_code=401, detail="Token manquant")
    session = SESSIONS.validate(raw)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")
    return session


# ---------- Pages statiques ----------
app.mount("/static", StaticFiles(directory=str(ROOT / "interface" / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (ROOT / "interface" / "templates" / "index.html").read_text(encoding="utf-8")


# ---------- Authentification locale ----------
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    """Authentification locale Python pur (pas de service cloud)."""
    session = SESSIONS.create(username=req.username, password=req.password)
    if not session:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    return {"token": session["token"], "expires_at": session["expires_at"]}


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str


async def ws_broadcast(session_id: str, payload: dict):
    for ws in list(WS_REGISTRY.get(session_id, [])):
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass


@app.post("/api/chat")
async def chat(req: ChatRequest, session: dict = Depends(get_session)):  # header X-Ratiss-Token
    """Pipeline : Nemotron planifie → Prime Agent exécute → RATISS calcule."""
    sid = session["session_id"]
    loop = asyncio.get_running_loop()
    task = loop.create_task(_run_pipeline(sid, req.message, session))
    return {"status": "started", "session_id": sid}


async def _run_pipeline(session_id: str, message: str, session: dict | None = None):
    ws_b = lambda payload: ws_broadcast(session_id, payload)
    try:
        await ws_b({"type": "step", "label": "🧠 Panthéon Cognitif & Planification Macro",
                    "text": "Nemotron 3 Ultra planifie la tâche…", "status": "pending"})
        plan = await asyncio.to_thread(NEMOTRON.plan_task, message)
        await ws_b({"type": "step", "label": "🧠 Panthéon Cognitif & Planification Macro",
                    "text": json.dumps(plan, ensure_ascii=False)[:400], "status": "ok"})

        await ws_b({"type": "step", "label": "🛠️ Génération de Code (Prime Agent)",
                    "text": "Prime Agent génère et exécute…", "status": "pending"})
        ws_path = WORKSPACES.resolve(session)
        result = await asyncio.to_thread(PRIME.execute_task, message, plan, ws_path)
        await ws_b({"type": "step", "label": "🛠️ Génération de Code (Prime Agent)",
                    "text": (result.get("summary") or "")[:300], "status": "ok"})

        if result.get("artifacts"):
            await ws_b({"type": "artifacts"})
            await ws_b({"type": "step", "label": "📦 Artéfacts générés",
                        "text": ", ".join(result["artifacts"]), "status": "ok"})

        await ws_b({"type": "assistant", "text": result.get("response") or "Tâche exécutée."})
    except Exception as e:
        await ws_b({"type": "step", "label": "❌ Erreur", "text": str(e)[:300], "status": "error"})
        await ws_b({"type": "error", "detail": str(e)})


# ---------- Stress-test GR-QM (p53) ----------
@app.post("/api/stress-test")
async def stress_test(session: dict = Depends(get_session)):
    sid = session["session_id"]
    loop = asyncio.get_running_loop()
    loop.create_task(_run_stress(sid))
    return {"status": "started"}


async def _run_stress(session_id: str):
    ws_b = lambda payload: ws_broadcast(session_id, payload)
    try:
        await ws_b({"type": "step", "label": "⚡ Stress-Test GR-QM (p53)",
                    "text": "Lanczos ED sur le réseau p53…", "status": "pending"})
        res = await asyncio.to_thread(stress_test_p53)
        await ws_b({"type": "step", "label": "⚡ Stress-Test GR-QM (p53)",
                    "text": (res.get("summary") or "")[:300], "status": "ok"})
        if res.get("artifacts"):
            await ws_b({"type": "artifacts"})
        await ws_b({"type": "assistant", "text": res.get("response") or "Stress-test terminé."})
    except Exception as e:
        await ws_b({"type": "error", "detail": str(e)})


# ---------- WebSocket streaming ----------
@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket, token: str = ""):
    await ws.accept()
    session = SESSIONS.validate(token)
    if not session:
        await ws.send_text(json.dumps({"type": "error", "detail": "Session invalide"}))
        await ws.close(code=4001)
        return
    sid = session["session_id"]
    WS_REGISTRY.setdefault(sid, set()).add(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive
    except WebSocketDisconnect:
        WS_REGISTRY[sid].discard(ws)


# ---------- Télémétrie ----------
@app.get("/api/telemetry")
def telemetry(session: dict = Depends(get_session)):  # header X-Ratiss-Token
    import psutil
    p = psutil.Process()
    mem_mb = p.memory_info().rss / (1024 * 1024)
    limit_mb = float(os.environ.get("MEMORY_GUARD_MB", "7500"))
    return {
        "ram_mb": round(mem_mb, 1),
        "cpu_pct": round(psutil.cpu_percent(interval=0.1), 1),
        "limit_mb": limit_mb,
        "timestamp": time.time(),
    }


# ---------- Artéfacts ----------
@app.get("/api/artifacts")
def artifacts(session: dict = Depends(get_session)):  # header X-Ratiss-Token
    ws = WORKSPACES.resolve(session)
    out = []
    if ws and ws.exists():
        for f in sorted(ws.rglob("*"), key=lambda x: -x.stat().st_mtime):
            if f.is_file():
                out.append({
                    "name": f.relative_to(ws).as_posix(),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
    return out[:50]


@app.get("/api/artifacts/download/{path:path}")
def download_artifact(path: str, session: dict = Depends(get_session)):
    from fastapi.responses import FileResponse
    ws = WORKSPACES.resolve(session)
    target = (ws / path).resolve()
    if not target.exists() or not str(target).startswith(str(ws.resolve())):
        raise HTTPException(status_code=404, detail="Artéfact introuvable")
    return FileResponse(str(target), filename=target.name)
