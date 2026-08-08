# -*- coding: utf-8 -*-
"""
================================================================================
       GESTIONNAIRE DE SESSIONS SÉCURISÉ — RATISS CYPHER ODV V3 (Open Views)
================================================================================
Propriété Intellectuelle : JohnKing0 & Architecte Jonathan Evina
Version du Système       : RATISS V9 AEON PRIME — RATISS-CYPHER-ODV-SCIENTIST-V3

Sécurité souveraine, 100% Python pur local (pas de service cloud) :
1. Authentification locale par identifiant + mot de passe (PBKDF2-SHA256).
2. Jeton d'accès UUID fort, stocké uniquement en hachage SHA-256 (jamais en clair).
3. Expiration configurable des sessions (défaut : 24h).
4. Isolation stricte des workspaces : ./workspace/{user_id}/{session_id}/
5. Verrouillage par fichier (thread-safe) des accès SQLite.
================================================================================
"""
import hashlib
import os
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path

SESSION_TTL_HOURS = float(os.environ.get("SESSION_TTL_HOURS", "24"))
ADMIN_PASSWORD = os.environ.get("RATISS_PASSWORD", "ratiss2026")


def sha256(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def pbkdf2_sha256(password: str, salt: str) -> str:
    """Hachage PBKDF2-SHA256 (200 000 itérations) pour les mots de passe."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()


class SessionManager:
    """Sessions locales multi-utilisateurs, jetons hachés, workspaces isolés."""

    _local = threading.local()

    def __init__(self, db_path: str = "data/sessions.db", ttl_hours: float = SESSION_TTL_HOURS):
        self.ttl_hours = ttl_hours
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        os.makedirs("workspace", exist_ok=True)
        self._init_db()

    @property
    def _conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        c = self._conn
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at REAL NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                workspace TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'active'
            )"""
        )
        c.commit()
        # Premier compte admin local
        if not c.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            salt = secrets.token_hex(8)
            c.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?)",
                ("admin", pbkdf2_sha256(ADMIN_PASSWORD, salt), salt, time.time()),
            )
            c.commit()

    # ------------------------------------------------------------------
    def create(self, username: str, password: str) -> dict | None:
        """Authentifie (ou enregistre au premier accès) et crée la session."""
        c = self._conn
        row = c.execute("SELECT password_hash, salt FROM users WHERE username=?", (username,)).fetchone()
        if row:
            if pbkdf2_sha256(password, row["salt"]) != row["password_hash"]:
                return None
        else:
            # Auto-enregistrement au premier accès (mot de passe haché)
            salt = secrets.token_hex(8)
            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                      (username, pbkdf2_sha256(password, salt), salt, time.time()))
            c.commit()

        session_id = str(uuid.uuid4())
        raw_token = secrets.token_urlsafe(48)
        now = time.time()
        workspace = Path("workspace") / username / session_id
        workspace.mkdir(parents=True, exist_ok=True)
        c.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, 'active')",
            (session_id, username, sha256(raw_token), now, now + self.ttl_hours * 3600, str(workspace)),
        )
        c.commit()
        return {
            "session_id": session_id,
            "token": raw_token,   # remis UNE SEULE fois au client
            "expires_at": now + self.ttl_hours * 3600,
            "workspace": str(workspace),
        }

    def validate(self, raw_token: str) -> dict | None:
        """Valide un jeton (hachage SHA-256) et retourne le contexte de session."""
        if not raw_token:
            return None
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE token_hash=? AND state='active'",
            (sha256(raw_token),),
        ).fetchone()
        if row is None:
            return None
        if time.time() > row["expires_at"]:
            self.revoke(row["session_id"])
            return None
        return {"session_id": row["session_id"], "username": row["username"],
                "workspace": row["workspace"], "expires_at": row["expires_at"]}

    def revoke(self, session_id: str):
        c = self._conn
        c.execute("UPDATE sessions SET state='revoked' WHERE session_id=?", (session_id,))
        c.commit()

    def cleanup_expired(self) -> int:
        c = self._conn
        rows = c.execute(
            "SELECT session_id, workspace FROM sessions WHERE state='active' AND expires_at < ?",
            (time.time(),),
        ).fetchall()
        for row in rows:
            c.execute("UPDATE sessions SET state='expired' WHERE session_id=?", (row["session_id"],))
            ws = Path(row["workspace"])
            if ws.exists():
                for f in ws.iterdir():
                    try:
                        f.unlink()
                    except OSError:
                        pass
                try:
                    ws.rmdir()
                except OSError:
                    pass
        c.commit()
        return len(rows)


if __name__ == "__main__":
    mgr = SessionManager()
    s = mgr.create("admin", ADMIN_PASSWORD)
    print("Session:", s["session_id"], "expir.", s["expires_at"])
    print("Valide:", mgr.validate(s["token"]) is not None)
    print("Invalide:", mgr.validate("bad-token") is None)
