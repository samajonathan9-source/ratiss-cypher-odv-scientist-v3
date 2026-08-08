# -*- coding: utf-8 -*-
"""
skills_manifest — Registre apatride des skills RATISS clonables depuis GitHub.

Chaque skill est cloné (git clone --depth 1), exécuté dans la sandbox,
puis purgé (routage apatride). Le cerveau RATISS V9 est copié localement
dans skills/ratiss/ (pas de clone nécessaire).

Propriété Intellectuelle : JohnKing0 & Architecte Jonathan Evina
"""

SKILLS: dict[str, dict[str, str]] = {
    "agentic_scientist": {
        "repo": "https://github.com/evinajonathan13-max/agentic-scientist.git",
        "description": "Scientifique agentique universel RATISS (230 modules).",
    },
    "prime-agent": {
        "repo": "https://github.com/PrimeIntellect-ai/prime-agent.git",
        "description": "Agent RLM auto-améliorant Prime Intellect (référence).",
    },
    "ransomguard": {
        "repo": "https://github.com/johnkingzero/ransomware-guard.git",
        "description": "Module de défense anti-ransomware (sandbox durcie).",
    },
}
