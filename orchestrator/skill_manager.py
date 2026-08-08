"""skill_manager — Gestion apatride des skills (clone, exécute, purge).

Les skills sont listés dans config/skills_manifest.py, clonés depuis GitHub
(git clone --depth 1) ou chargés localement, exécutés dans la sandbox,
puis purgés. Zéro poids mort entre les exécutions.
"""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class SkillManager:
    """Charge et exécute les skills déclarés dans skills_manifest.py."""

    def __init__(self, manifest_path: str | None = None) -> None:
        self.manifest: dict[str, dict] = {}
        if manifest_path and Path(manifest_path).exists():
            sys.path.insert(0, str(Path(manifest_path).parent))
            try:
                spec = importlib.util.spec_from_file_location("skills_manifest", manifest_path)
                mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
                self.manifest = dict(getattr(mod, "SKILLS", {}))
            except Exception as e:
                print(f"[skill_manager] Manifest introuvable ou invalide : {e}", file=sys.stderr)

    def clone_skill(self, name: str) -> Path:
        """Clone un repo skill depuis le manifest (routage apatride)."""
        spec = self.manifest.get(name)
        if not spec:
            raise KeyError(f"Skill '{name}' absent du manifeste")
        dest = Path(tempfile.mkdtemp(prefix=f"skill_{name}_"))
        subprocess.run(
            ["git", "clone", "--depth", "1", spec["repo"], str(dest / "repo")],
            check=True, capture_output=True, timeout=300,
        )
        return dest / "repo"

    def run_skill(self, name: str, entry: str, **kwargs: Any) -> dict[str, Any]:
        """Exécute un skill local (RATISS) ou cloné, puis le purge."""
        if name in self.manifest:
            path = self.clone_skill(name)
            try:
                return self._run_local(path, entry, **kwargs)
            finally:
                shutil.rmtree(path, ignore_errors=True)  # purge apatride
        local = Path(__file__).parent.parent / "skills" / name
        if local.exists():
            return self._run_local(local, entry, **kwargs)
        raise KeyError(f"Skill '{name}' introuvable (local ou manifeste)")

    def _run_local(self, path: Path, entry: str, **kwargs: Any) -> dict[str, Any]:
        """Exécute un point d'entrée Python dans le skill."""
        entry_point = (path / f"{entry}.py").resolve() if not entry.endswith(".py") else path / entry
        if not entry_point.exists():
            return {
                "summary": f"Point d'entrée '{entry}' introuvable dans le skill.",
                "response": f"Aucun module {entry}.py dans ce skill.",
                "artifacts": [],
            }
        result = subprocess.run(
            [sys.executable, str(entry_point), *(kwargs.get("args") or [])],
            cwd=str(path), capture_output=True, text=True, timeout=600,
        )
        summary = (result.stdout or "")[-3000]
        if result.returncode != 0:
            summary += f"\n[ERREUR] {(result.stderr or '')[-600]}"
        return {
            "summary": summary or "(skill exécuté, sortie vide)",
            "response": summary or "(skill exécuté, sortie vide)",
            "artifacts": [f.name for f in path.rglob("*") if f.is_file() and f.suffix.lower()
                          in {".py", ".csv", ".json", ".pdb", ".pdf", ".xlsx", ".txt", ".png"}][:25],
            "returncode": result.returncode,
        }

    def list_skills(self) -> list[dict[str, str]]:
        local = Path(__file__).parent.parent / "skills"
        skills = []
        for d in sorted(local.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                skills.append({
                    "name": d.name,
                    "source": "local",
                    "files": sum(1 for _ in d.rglob("*.py")),
                })
        for name, spec in self.manifest.items():
            skills.append({"name": name, "source": "github", "repo": spec.get("repo", "")})
        return skills


if __name__ == "__main__":
    sm = SkillManager(str(Path(__file__).parent.parent / "config" / "skills_manifest.py"))
    print(sm.list_skills())
