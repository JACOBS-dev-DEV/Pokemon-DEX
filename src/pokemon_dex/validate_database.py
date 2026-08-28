"""Offline validation checks for Pokemon-DEX data files."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "res"
RUNTIME_DIR_NAMES = {"_backups", "_backup", "_tmp", "_temp"}


def _is_runtime_artifact(path: Path) -> bool:
    """Return True for local runtime files that should not block startup."""
    return any(part in RUNTIME_DIR_NAMES for part in path.parts)


def iter_json_files() -> list[Path]:
    files: list[Path] = []
    for folder in (RES / "data", RES / "profiles", ROOT / "profiles"):
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*.json")):
            if not _is_runtime_artifact(path):
                files.append(path)
    return files


def main() -> int:
    errors: list[str] = []
    seen_national_ids: dict[str, Path] = {}
    files = iter_json_files()

    for path in files:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON: {path.relative_to(ROOT)} :: {exc}")
            continue

        # Only canonical single-Pokemon profiles participate in duplicate Dex/form checks.
        if path.is_relative_to(RES / "profiles") and isinstance(data, dict) and data.get("national_dex"):
            dex_id = str(data["national_dex"]).zfill(4)
            form = str(data.get("form", "base"))
            key = f"{dex_id}:{form}"
            if key in seen_national_ids:
                errors.append(
                    f"Duplicate Pokemon/form key {key}: "
                    f"{seen_national_ids[key].relative_to(ROOT)} and {path.relative_to(ROOT)}"
                )
            else:
                seen_national_ids[key] = path

    if errors:
        print("Pokemon-DEX validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Pokemon-DEX validation passed ({len(files)} JSON files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
