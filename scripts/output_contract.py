from __future__ import annotations

import os
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


def normalize_cli_path_arg(path_value: str) -> Path:
    """
    Normalize CLI path values so Windows-style separators also work on POSIX shells.

    Notes:
    - If a user passes `outputs\\spot_15m` in bash without quoting, the shell strips
      backslashes and argparse receives `outputsspot_15m`.
    - We apply conservative heuristics for the known project path roots (`outputs`,
      `data`) to recover expected paths in those cases.
    """
    cleaned = path_value.strip().strip("\"'")
    if os.sep == "/":
        cleaned = cleaned.replace("\\", "/")
        if "/" not in cleaned:
            if cleaned.startswith("outputs") and cleaned != "outputs":
                cleaned = f"outputs/{cleaned[len('outputs') :]}"
            elif cleaned.startswith("datasamples") and cleaned != "datasamples":
                cleaned = f"data/samples/{cleaned[len('datasamples') :]}"
    return Path(cleaned).expanduser()
