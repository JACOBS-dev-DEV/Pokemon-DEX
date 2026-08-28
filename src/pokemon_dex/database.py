"""Local/offline data access for Pokemon-DEX."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "res"
DATA = RES / "data"
CANONICAL_PROFILES = RES / "profiles"
PERSONAL_PROFILES = ROOT / "profiles"
ART = RES / "art"


@dataclass(frozen=True)
class DexStatus:
    database_version: str
    canonical_profiles: int
    personal_profile_files: int
    indexed_pokemon: int
    indexed_art_assets: int
    art_files: int
    games: int
    dexes: int
    forms: int


def load_json(path: Path, default: Any = None) -> Any:
    """Read JSON from disk without any network dependency."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def _json_count(folder: Path) -> int:
    return sum(1 for path in folder.rglob("*.json") if path.is_file()) if folder.exists() else 0


def _art_count() -> int:
    extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    if not ART.exists():
        return 0
    return sum(1 for path in ART.rglob("*") if path.is_file() and path.suffix.lower() in extensions)


def _registry_count(filename: str, key: str) -> int:
    data = load_json(DATA / "registries" / filename, {}) or {}
    value = data.get(key, []) if isinstance(data, dict) else []
    return len(value) if isinstance(value, list) else 0


def get_status() -> DexStatus:
    """Return a compact health/status snapshot of all connected local resources."""
    version_data = load_json(DATA / "database_version.json", {}) or {}
    pokemon_index = load_json(DATA / "indexes" / "pokemon_index.json", {}) or {}
    art_index = load_json(DATA / "indexes" / "art_index.json", {}) or {}

    indexed_profiles = pokemon_index.get("profiles", []) if isinstance(pokemon_index, dict) else []
    indexed_art = art_index.get("assets", []) if isinstance(art_index, dict) else []

    return DexStatus(
        database_version=str(version_data.get("database_version", version_data.get("version", "unknown"))),
        canonical_profiles=_json_count(CANONICAL_PROFILES),
        personal_profile_files=_json_count(PERSONAL_PROFILES),
        indexed_pokemon=len(indexed_profiles) if isinstance(indexed_profiles, list) else 0,
        indexed_art_assets=len(indexed_art) if isinstance(indexed_art, list) else 0,
        art_files=_art_count(),
        games=_registry_count("games.json", "games"),
        dexes=_registry_count("dexes.json", "dexes"),
        forms=_registry_count("forms.json", "forms"),
    )
