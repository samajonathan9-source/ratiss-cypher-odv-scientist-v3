# RATISS V9 Aeon Prime — Open Views (`ratiss-cypher-odv-scientist-v3`)

**Propriété Intellectuelle : JohnKing0 & Architecte Jonathan Evina**

Interface scientifique souveraine de type « Open Views » (style Manus IA) pilotée par **Prime Agent** (PrimeIntellect, agent RLM auto-améliorant officiel) et le modèle stratège **Nemotron 3 Ultra** via OpenRouter, avec le cerveau de calcul **RATISS V9** comme skill principal.

## Architecture

```
Open Views (interface 3 panneaux)
├── Panneau gauche  : Chat (WebSocket temps réel)
├── Panneau central : Raisonnement en cascade
│     Nemotron 3 Ultra (planification) → Prime Agent (exécution) → RATISS V9 (calcul)
└── Panneau droit   : Télémétrie D3.js (RAM/CPU, Memory Guard 7500 Mo) + Artéfacts téléchargeables
```

## Fonctionnalités

- **Génération de tâches complexes** : Prime Agent génère du code, des fichiers (CSV, Excel, PDF, PDB, Python) et clone des dépôts GitHub (`git clone --depth 1`).
- **Routage TransDIPL'Y** : détection de domaine (physique, biologie structurale, topologie, cryptographie…) et sélection du solveur RATISS.
- **Stress-test GR-QM (p53)** : diagonalisation Lanczos avec invariants physiques (E₀ < 0, ||Ψ||² = 1).
- **Réponses conversationnelles** via Nemotron 3 Ultra pour les questions simples.
- **Sécurité souveraine** : sessions SQLite locales (UUID4, 24 h), jetons hachés SHA-256, mots de passe PBKDF2-SHA256, workspaces isolés par session, sandbox durcie (2 Go, 1 CPU), purge apatride des clones/skills.
- **Cerveau RATISS V9** : 27 modules (agentic_light, backend_pur, transdipl_y, connectors IBM/Quandela/PennyLane, file_manager, terminal_commands, browser_integration…).

## Installation

```bash
curl -fsSL https://app.primeintellect.ai/prime-agent/install.sh | sh
pip install -r requirements.txt
cp .env.example .env   # renseigner les clés API
python3 scripts/init_vault.py
uvicorn interface.app:app --host 0.0.0.0 --port 7860
```

Premier accès : identifiant de votre choix + mot de passe (auto-enregistrement, compte `admin` par défaut).

## Quota gratuit OpenRouter (modèles `:free`)

La clé OpenRouter en mode gratuit est limitée à **50 requêtes/jour** (limite globale couvrant tous les modèles `:free` d'OpenRouter, dont Nemotron 3 Ultra). Lorsqu'elle est épuisée, le chat affiche un message clair (« ⏳ Quota gratuit OpenRouter épuisé pour aujourd'hui… ») et le **Stress-Test RATISS et la télémétrie restent pleinement fonctionnels**. Le quota se réinitialise automatiquement à **00:00 UTC (02:00 heure de Paris)**. Pour un usage illimité : fournir une clé OpenRouter avec crédits (variable `OPENROUTER_API_KEY`) — aucun changement de code nécessaire.

## Hugging Face Space (Docker)

Le `Dockerfile` est prêt pour un HF Space de type Docker (port 7860). Secrets HF à définir : `OPENROUTER_API_KEY`, `HF_TOKEN`, `IBM_QUANTUM_TOKEN`, `QUANDELA_API_KEY`.

## Scripts utilitaires

| Script | Rôle |
|---|---|
| `scripts/import_skill.py` | Clone un skill GitHub, l'exécute, le purge (routage apatride) |
| `scripts/align_agent.py` | Alignement éthique + jugement Nemotron (`--full` / `--local`) |
| `scripts/init_vault.py` | Coffre local des empreintes SHA-256 des clés API |

## Sécurité

Aucune clé API n'est jamais écrite en clair dans le code, les logs ou le dépôt. Les clés réelles vivent exclusivement dans les variables d'environnement (secrets de déploiement) ; seules leurs empreintes SHA-256 sont stockées localement pour vérification.
