from __future__ import annotations

from pathlib import Path


def ensure_artifacts_in_output_dir(output_dir: Path, artifact_paths: list[str], legacy_root: Path = Path("outputs")) -> list[Path]:
    """
    Keep artifact paths contract-stable by ensuring required artifacts exist inside
    the caller-selected output_dir. If legacy artifacts are found under outputs/,
    move them into output_dir.
    """
    output_dir = output_dir.resolve()
    legacy_root = legacy_root.resolve()
    moved: list[Path] = []

    for rel in artifact_paths:
        target = output_dir / rel
        if target.exists():
            continue
        legacy = legacy_root / rel
        if legacy.exists() and legacy != target:
            target.parent.mkdir(parents=True, exist_ok=True)
            legacy.replace(target)
            moved.append(target)

    return moved
