#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_vault — Initialise le coffre local des clés API (hachage SHA-256).

Les clés ne sont JAMAIS stockées en clair : seules leurs empreintes
SHA-256 sont conservées dans la SQLite locale (data/token_vault.db),
pour vérification sans exposition. Les clés réelles restent dans les
variables d'environnement (secrets de déploiement).

Usage :
    python3 scripts/init_vault.py              # initie la base
    python3 scripts/init_vault.py --verify     # vérifie les empreintes vs env
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "token_vault.db"

KEYS = ["OPENROUTER_API_KEY", "HF_TOKEN", "IBM_QUANTUM_TOKEN", "QUANDELA_API_KEY"]


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS token_vault (
            name TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            created_at REAL NOT NULL
        )"""
    )
    import time
    now = time.time()
    for name in KEYS:
        value = os.environ.get(name, "")
        if value:
            conn.execute(
                "INSERT OR REPLACE INTO token_vault VALUES (?, ?, ?)",
                (name, sha256(value), now),
            )
            print(f"[+] {name} → empreinte {sha256(value)[:16]}… enregistrée (jamais en clair)")
        else:
            print(f"[ ] {name} : non définie dans l'environnement")
    conn.commit()
    conn.close()


def verify() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    rows = {r[0]: r[1] for r in conn.execute("SELECT name, fingerprint FROM token_vault")}
    conn.close()
    ok = 0
    for name, fp in rows.items():
        value = os.environ.get(name, "")
        if value and sha256(value) == fp:
            print(f"[✓] {name} : cohérente")
            ok += 1
        else:
            print(f"[✗] {name} : manquante ou divergente")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    sys.exit(verify() if args.verify else init())
