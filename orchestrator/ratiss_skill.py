"""ratiss_skill — RATISS V9 Aeon Prime exposé comme skill principal de l'orchestrateur.

Le noyau physique (RATISSCorePhysics), le routeur TransDIPL'Y et les
diagnostics du nœud sont importés depuis skills/ratiss/ratiss_v9_aeon_prime.
Invariants physiques : E₀ < 0, ||Ψ||² = 1.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).parent.parent / "skills" / "ratiss"
sys.path.insert(0, str(SKILL_ROOT))


def stress_test_p53(**_kwargs: Any) -> dict[str, Any]:
    """Stress-test GR-QM sur le réseau p53 : Hamiltonien + invariants physiques."""
    try:
        from ratiss_v9_aeon_prime.backend_pur import RATISSCorePhysics
        core = RATISSCorePhysics()
        # Stress-test GR-QM : Lanczos t-J (cohérence quantique réseau p53)
        r1 = core.solve_lanczos_tj(num_sites=12)
        E0 = r1.get("energy_0", 0)
        inv = "Invariant E₀ < 0 validé ✓" if E0 < 0 else "⚠ Invariant E₀ < 0 non satisfait"
        result = {**r1, "invariant_E0": inv}
        return {
            "summary": str(result)[:1500],
            "response": f"Stress-test GR-QM (p53) : E₀ = {E0} eV. {inv}",
            "artifacts": [],
        }
    except Exception as e:
        return {
            "summary": f"Stress-test GR-QM (p53) : mode dégradé — {e}",
            "response": "Stress-test exécuté en mode dégradé (dépendances physiques limitées).",
            "artifacts": [],
        }


def transdipl_route(task: str) -> dict[str, Any]:
    """Route une tâche via TransDIPL'Y (détection de domaine + solveur + matériel)."""
    try:
        from ratiss_v9_aeon_prime.transdipl_y import TransDIPLY
        router = TransDIPLY()
        return {"routing": router.route_task(task)}
    except Exception as e:
        return {"error": str(e)}


def node_health() -> dict[str, Any]:
    """Diagnostic du nœud de calcul (outil health)."""
    try:
        from ratiss_v9_aeon_prime.terminal_commands import get_ram_usage, print_status
        import io
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            print_status()
        return {
            "status": "OK",
            "ram_mb": get_ram_usage(),
            "stdout": buf.getvalue()[:1200],
        }
    except Exception as e:
        import psutil
        p = psutil.Process()
        return {
            "status": "OK (dégradé)",
            "ram_mb": round(p.memory_info().rss / 1024 / 1024, 1),
            "error": str(e),
        }


if __name__ == "__main__":
    print(node_health())
