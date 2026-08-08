"""nemotron_client — Client OpenRouter pour Nemotron 3 Ultra (stratège / planificateur).

Nemotron 3 Ultra NE write pas de code : il planifie, raisonne et corrige.
L'exécution appartient à Prime Agent.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"
)
FALLBACK_MODEL = os.environ.get("OR_FALLBACK_MODEL", "google/gemini-3-flash-preview")

SYSTEM_PLAN = """Tu es NEMOTRON 3 ULTRA, le stratège du système RATISS V9 Aeon Prime.
Tu PLANIFIES mais tu n'exécutes rien et tu n'écris pas de code.

Pour chaque tâche utilisateur, retourne UNIQUEMENT un JSON avec :
{
  "task": "reformulation de la tâche",
  "detected_domain": "physics|structural_biology|quantum_computing|topology|cryptography|general",
  "solver": "nom du solveur RATISS ou 'llm_chat'",
  "hardware": "cpu_memory_mapped",
  "subtasks": ["étape 1", "étape 2", ...],
  "expected_artifacts": ["type de fichiers attendus"]
}

Si la tâche est une simple question conversationnelle, utilise
"detected_domain": "general", "solver": "llm_chat" et réponds normalement en français.
"""


class NemotronClient:
    """Client HTTP pur (sans dépendance) vers OpenRouter."""

    def __init__(self) -> None:
        self.api_key = OPENROUTER_API_KEY
        self.base = OPENROUTER_BASE_URL.rstrip("/")
        self.model = OPENROUTER_MODEL

    def chat(self, messages: list[dict], max_tokens: int = 8192) -> str:
        return self._call_model(messages, max_tokens, primary=True)

    def _call_model(self, messages: list[dict], max_tokens: int,
                    primary: bool) -> str:
        url = f"{self.base}/chat/completions"
        payload = {
            "model": self.model if primary else FALLBACK_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://huggingface.co/spaces",
            "X-Title": "RATISS V9 Aeon Prime - Open Views",
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        last_err = ""
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=data_bytes, headers=headers)
                with urllib.request.urlopen(req, timeout=600) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if "choices" not in data or not data["choices"]:
                    raise KeyError("choices")
                return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                body = (e.read() or b"").decode("utf-8", "ignore")
                last_err = str(e)
                # 429 (quota gratuit) sur le modèle principal → bascule vers le
                # modèle de secours sur ce même appel, puis sur les suivants
                if primary and attempt == 0 and ("429" in body or e.code == 429):
                    self.model = FALLBACK_MODEL
                    return self._call_model(messages, max_tokens, primary=False)
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                last_err = str(e)
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Échec après 3 tentatives d'appel Nemotron : {last_err}")

    def plan_task(self, user_message: str) -> dict:
        """Nemotron planifie la tâche (stratège). Retourne le plan JSON."""
        try:
            raw = self.chat([
                {"role": "system", "content": SYSTEM_PLAN},
                {"role": "user", "content": user_message},
            ], max_tokens=2048)
            # Nettoyage robuste du JSON
            start = raw.find("{")
            end = raw.rfind("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            return {
                "task": user_message,
                "detected_domain": "general",
                "solver": "llm_chat",
                "hardware": "cpu_memory_mapped",
                "subtasks": ["Répondre à la question"],
                "expected_artifacts": [],
            }

    def answer_conversation(self, history: list[dict]) -> str:
        """Réponse conversationnelle directe (questions simples)."""
        return self.chat(history)


if __name__ == "__main__":
    nc = NemotronClient()
    plan = nc.plan_task("Fais le routage TransDIPL'Y d'une tâche d'analyse 4MZI")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
