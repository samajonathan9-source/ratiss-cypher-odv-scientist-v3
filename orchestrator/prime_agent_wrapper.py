"""prime_agent_wrapper — Pont vers Prime Agent officiel (sans modifier son repo).

Prime Agent (PrimeIntellect, MIT) garde toute sa logique : sessions sauvegardées,
IPython persistant, sous-agents RLM, /refine auto-améliorant, skills importables.

Nous le pilotons en mode non-interactif via `prime-agent -p ... --mode json`.
Le working directory = workspace isolé de la session utilisateur.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PROVIDER = os.environ.get("PRIME_AGENT_PROVIDER", "openrouter")
MODEL = os.environ.get("PRIME_AGENT_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
TIMEOUT = int(os.environ.get("PRIME_AGENT_TIMEOUT", "900"))
MAX_OUTPUT_CHARS = 3000

INSTRUCTION = """TRAVAILLE EN FRANÇAIS. Tu exécutes dans le répertoire courant.
Tu peux générer des fichiers (Python, CSV, PDF, Excel via openpyxl, PDB),
cloner des dépôts GitHub (git clone --depth 1), installer des paquets Python
(pip3 install) et exécuter du code. À la fin, écris un fichier RESULT.md résumant
ton travail et la liste des artéfacts produits. Sois concis."""


class PrimeAgentBridge:
    """Pilote Prime Agent via son CLI (mode JSON), sans toucher à son repo."""

    def __init__(self) -> None:
        self.binary = shutil.which("prime-agent")
        if not self.binary:
            raise RuntimeError(
                "prime-agent introuvable. Installez-le : "
                "curl -fsSL https://app.primeintellect.ai/prime-agent/install.sh | sh"
            )

    def execute_task(self, task: str, plan: dict | None = None, dest: Path | None = None) -> dict[str, Any]:
        """Lance une tâche Prime Agent dans un workspace isolé (routage apatride).

        Si dest est fourni (workspace de session), les artéfacts y sont copiés
        avant la purge du workspace temporaire.
        """
        cwd = self._prepare_workspace()
        try:
            prompt = INSTRUCTION + "\n\nTÂCHE : " + task
            if plan:
                prompt += "\n\nPLAN STRATÉGIQUE (Nemotron) : " + json.dumps(plan, ensure_ascii=False)

            cmd = [
                self.binary, "-p", prompt,
                "--provider", PROVIDER, "--model", MODEL, "--mode", "json",
            ]
            result = subprocess.run(
                cmd, cwd=str(cwd), capture_output=True, text=True,
                timeout=TIMEOUT, env=self._agent_env(),
            )
            parsed = self._parse_result(cwd, result)
            # Copie apatride des artéfacts vers le workspace de session
            if dest:
                for name in parsed.get("artifacts", []):
                    src = cwd / name
                    if src.exists():
                        dst = Path(dest) / name
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, dst)
            return parsed
        except subprocess.TimeoutExpired:
            return {
                "summary": "Tâche arrêtée (délai dépassé — Memory Guard / timeout).",
                "response": "La tâche a dépassé la limite de temps. Vérifie la complexité.",
                "artifacts": [],
            }
        finally:
            # Routage apatride : le workspace temporaire de travail est purgé
            shutil.rmtree(cwd, ignore_errors=True)

    def _prepare_workspace(self) -> Path:
        cwd = Path(tempfile.mkdtemp(prefix="prime_task_"))
        return cwd

    def _agent_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PRIME_AGENT_NONINTERACTIVE"] = "1"
        env.setdefault("OPENROUTER_API_KEY", "")
        return env

    def _parse_result(self, cwd: Path, result: subprocess.CompletedProcess) -> dict:
        events: list[dict] = []
        for line in (result.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        response = ""
        thinking = []
        for ev in events:
            if ev.get("type") == "message_update":
                for content in ev.get("message", {}).get("content", []):
                    if content.get("type") == "text":
                        response += content.get("text", "")
                    elif content.get("type") == "thinking":
                        thinking.append(content.get("thinking", ""))

        # Récupérer RESULT.md s'il existe
        summary = response[-MAX_OUTPUT_CHARS:] if response else (result.stdout or "")[-MAX_OUTPUT_CHARS:]
        artifacts = []
        result_md = cwd / "RESULT.md"
        if result_md.exists():
            summary = result_md.read_text(encoding="utf-8")[-MAX_OUTPUT_CHARS:]

        for f in sorted(cwd.rglob("*"), key=lambda p: -p.stat().st_mtime):
            if f.is_file() and f.suffix.lower() in {
                ".py", ".csv", ".json", ".pdb", ".pdf", ".xlsx", ".txt", ".md", ".html", ".png",
            }:
                artifacts.append(f.name)
        # Dédoublonner tout en gardant RESULT.md / fichier résultat
        artifacts = sorted(set(artifacts))[:25]

        if result.returncode != 0:
            err = (result.stderr or "")[-600:]
            summary = (summary or "") + f"\n[ERREUR CLI] {err}" if summary else f"[ERREUR CLI] {err}"

        return {
            "summary": summary,
            "response": summary,
            "artifacts": artifacts,
            "returncode": result.returncode,
        }


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


if __name__ == "__main__":
    bridge = PrimeAgentBridge()
    res = bridge.execute_task("Crée un fichier RESULT.md qui dit bonjour et liste le répertoire.")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:1500])
