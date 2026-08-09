"""async_pipeline — Gestionnaire asynchrone du backend RATISS V9.
Assure l'orchestration non-bloquante Nemotron 3 Ultra + Prime Agent avec Memory Guard (7500 MB).
"""
from __future__ import annotations

import asyncio
import os
import psutil
from typing import Any, Dict

MEMORY_GUARD_LIMIT_MB = float(os.environ.get("MEMORY_GUARD_MB", "7500"))

class MemoryGuardException(Exception):
    pass

def check_memory_guard():
    """Vérifie que la consommation mémoire respecte la limite de 7500 MB."""
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / (1024 * 1024)
    if mem_mb > MEMORY_GUARD_LIMIT_MB:
        raise MemoryGuardException(
            f"Memory Guard activé : consommation actuelle {mem_mb:.1f} MB "
            f"dépasse la limite stricte de {MEMORY_GUARD_LIMIT_MB} MB."
        )
    return mem_mb

async def run_async_pipeline(session_id: str, message: str, nemotron_client: Any, prime_bridge: Any, workspace_path: Any) -> Dict[str, Any]:
    """Exécute le pipeline complet de manière asynchrone avec contrôle Memory Guard."""
    check_memory_guard()
    
    # 1. Planification Nemotron 3 Ultra
    plan = await asyncio.to_thread(nemotron_client.plan_task, message)
    
    check_memory_guard()
    
    # 2. Exécution Prime Agent
    result = await asyncio.to_thread(prime_bridge.execute_task, message, plan, workspace_path)
    
    check_memory_guard()
    
    return {
        "plan": plan,
        "result": result,
        "memory_mb": psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    }
