"""Offline validation checks for Pokemon-DEX data files."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "res"


def iter_json_files() -> list[Path]:
    return sorted((RES / "data").rglob("*.json")) + sorted((RES / "profiles").rglob("*.json"))


def main() -> int:
    errors: list[str] = []
    seen_national_ids: dict[str, Path] = {}

    for path in iter_json_files():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON: {path.relative_to(ROOT)} :: {exc}")
            continue

        if isinstance(data, dict) and data.get("national_dex"):
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

    print(f"Pokemon-DEX validation passed ({len(iter_json_files())} JSON files checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
