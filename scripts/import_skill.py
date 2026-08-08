#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""import_skill — Clone un skill depuis GitHub, l'exécute, puis le purge.

Routage apatride : le skill n'a aucun poids mort entre deux exécutions.
Zéro poids mort, zéro dérive.

Usage :
    python3 scripts/import_skill.py <nom_du_skill> [--entry <point_d_entree>] [--run]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "config"))

from skills_manifest import SKILLS


def import_skill(name: str, run: bool = False, entry: str = "main") -> int:
    spec = SKILLS.get(name)
    if not spec:
        print(f"[!] Skill '{name}' absent du manifeste. Skills disponibles : {list(SKILLS)}")
        return 2

    workdir = Path(tempfile.mkdtemp(prefix=f"skill_{name}_"))
    print(f"[+] Clone de {spec['repo']} → {workdir}")
    res = subprocess.run(
        ["git", "clone", "--depth", "1", spec["repo"], str(workdir)],
        capture_output=True, text=True, timeout=300,
    )
    if res.returncode != 0:
        print(f"[!] Échec du clone : {res.stderr[-400:]}")
        shutil.rmtree(workdir, ignore_errors=True)
        return 1

    if not run:
        print(f"[✓] Skill '{name}' cloné (non exécuté) : {workdir}")
        print("[!] Suppression programmée pour libérer la sandbox. Exécutez avec --run si nécessaire.")
        shutil.rmtree(workdir, ignore_errors=True)
        print("[✓] Purge apatride effectuée.")
        return 0

    entry_point = (workdir / f"{entry}.py") if not entry.endswith(".py") else (workdir / entry)
    if entry_point.exists():
        print(f"[+] Exécution de {entry_point}")
        res2 = subprocess.run([sys.executable, str(entry_point)], cwd=str(workdir), timeout=600)
        print(f"[✓] Retour : {res2.returncode}")
    else:
        print(f"[!] Point d'entrée '{entry}' introuvable dans le skill.")

    shutil.rmtree(workdir, ignore_errors=True)
    print("[✓] Purge apatride effectuée (zéro poids mort).")
    return res.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importation apatride de skills RATISS")
    parser.add_argument("name", help="Nom du skill (voir config/skills_manifest.py)")
    parser.add_argument("--entry", default="main", help="Point d'entrée à exécuter (défaut: main.py)")
    parser.add_argument("--run", action="store_true", help="Exécuter le skill après le clone")
    sys.exit(import_skill(**vars(parser.parse_args())))
