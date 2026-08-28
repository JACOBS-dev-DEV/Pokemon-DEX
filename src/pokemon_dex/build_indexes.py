"""Build fast local indexes for Pokemon-DEX without network access."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "res"
PROFILES = RES / "profiles"
ART = RES / "art"
INDEX_DIR = RES / "data" / "indexes"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_profile_index() -> dict:
    records = []
    if PROFILES.exists():
        for path in sorted(PROFILES.rglob("*.json")):
            try:
                data = _load_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            records.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "id": data.get("national_dex") or data.get("id"),
                    "name": data.get("name"),
                    "form": data.get("form", "base"),
                }
            )
    return {"schema_version": "1", "profiles": records}


def build_art_index() -> dict:
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    assets = []
    if ART.exists():
        for path in sorted(ART.rglob("*")):
            if path.is_file() and path.suffix.lower() in extensions:
                assets.append({"path": path.relative_to(ROOT).as_posix()})
    return {"schema_version": "1", "assets": assets}


def write_index(name: str, data: dict) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    path = INDEX_DIR / name
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> None:
    write_index("pokemon_index.json", build_profile_index())
    write_index("art_index.json", build_art_index())
    print("Pokemon-DEX indexes rebuilt locally.")


if __name__ == "__main__":
    main()
