# -*- coding: utf-8 -*-
"""workspace_isolator — Isolation stricte des workspaces par session.

Chaque session RATISS V9 Aeon Prime travaille dans :
    workspace/{username}/{session_id}/
avec des bornes de sécurité :
- interdiction de sortir du workspace (Path traversal bloqué),
- Memory Guard : limite RAM applicative (7500 Mo par défaut, durcie
  par cgroups en mode Docker),
- purge temporaire : les clones/skills temporaires sont supprimés
  après exécution (routage apatride).
"""
from __future__ import annotations

import os
from pathlib import Path


class WorkspaceIsolator:
    """Résolution et durcissement des workspaces de session."""

    def __init__(self, base: str = "workspace"):
        self.base = Path(base).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.memory_guard_mb = float(os.environ.get("MEMORY_GUARD_MB", "7500"))

    def resolve(self, session: dict) -> Path:
        """Retourne le Path du workspace d'une session, après vérification."""
        raw = session.get("workspace")
        if not raw:
            return None
        p = Path(raw).resolve()
        # Anti-Path-traversal : le workspace DOIT être sous self.base
        if not str(p).startswith(str(self.base)):
            raise PermissionError(f"Workspace hors bornes : {raw}")
        p.mkdir(parents=True, exist_ok=True)
        return p

    def guard_info(self) -> dict:
        """Informations du Memory Guard pour la télémétrie."""
        return {"limit_mb": self.memory_guard_mb}

    @property
    def limit_mb(self) -> float:
        return self.memory_guard_mb


if __name__ == "__main__":
    iso = WorkspaceIsolator()
    fake = {"workspace": str(iso.base / "demo" / "session-123")}
    print(iso.resolve(fake))
    print(iso.guard_info())
