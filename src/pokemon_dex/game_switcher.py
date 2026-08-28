"""Personal Pokemon game switching and local save summaries."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "profiles" / "JacobS-Dev-1"
PREF_FILE = PROFILE_DIR / "game_preferences.json"
REGISTRY_FILE = ROOT / "res" / "data" / "registries" / "games.json"

PERSONAL_GAME_FILES = {
    "Pokemon Sword": PROFILE_DIR / "sword.json",
    "Pokemon Brilliant Diamond": PROFILE_DIR / "brilliant_diamond.json",
    "Pokemon Legends: Arceus": PROFILE_DIR / "legends_arceus.json",
}


class GameSwitcherError(RuntimeError):
    """Raised when the local active-game preference cannot be changed safely."""


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise GameSwitcherError(f"Could not read {path.name}.") from exc


def available_personal_games() -> list[str]:
    return [name for name, path in PERSONAL_GAME_FILES.items() if path.exists()]


def supported_games() -> list[str]:
    if not REGISTRY_FILE.exists():
        return available_personal_games()
    data = _read_json(REGISTRY_FILE)
    return [str(row.get("name")) for row in data.get("games", []) if row.get("name")]


def load_preferences() -> dict:
    if not PREF_FILE.exists():
        return {
            "profile_id": "JacobS-Dev-1",
            "active_game": "Pokemon Sword",
            "default_battle_role": "attacker",
        }
    return _read_json(PREF_FILE)


def active_game() -> str:
    selected = str(load_preferences().get("active_game") or "Pokemon Sword")
    games = available_personal_games()
    return selected if selected in games else (games[0] if games else "Pokemon Sword")


def _summary_sword(data: dict) -> dict:
    rows = list(data.get("pokemon", []))
    caught = [row for row in rows if row.get("caught")]
    return {
        "recorded_species": len(rows),
        "caught_species_records": len(caught),
        "owned_total": sum(int(row.get("owned_count") or 0) for row in caught),
        "team_records": sum(1 for row in rows if row.get("in_team")),
        "pending_encounters": sum(1 for row in rows if row.get("encountered") and not row.get("caught")),
    }


def _summary_brilliant_diamond(data: dict) -> dict:
    rows = list(data.get("pokemon", []))
    return {
        "recorded_species": len(rows),
        "caught_species_records": sum(1 for row in rows if row.get("caught")),
        "team_records": sum(1 for row in rows if row.get("in_team")),
    }


def _summary_legends_arceus(data: dict) -> dict:
    rows = list(data.get("pokemon", []))
    progress = dict(data.get("progress", {}))
    return {
        "recorded_species": len(rows),
        "caught_species_records": sum(1 for row in rows if row.get("caught")),
        "complete_entries": sum(1 for row in rows if row.get("complete")),
        "obtained_total": int(progress.get("obtained_total") or 0),
        "regional_goal": progress.get("regional_goal"),
    }


def game_summary(game: str) -> dict:
    path = PERSONAL_GAME_FILES.get(game)
    if path is None or not path.exists():
        return {"personal_data": false, "game": game}
    data = _read_json(path)
    if game == "Pokemon Sword":
        summary = _summary_sword(data)
    elif game == "Pokemon Brilliant Diamond":
        summary = _summary_brilliant_diamond(data)
    elif game == "Pokemon Legends: Arceus":
        summary = _summary_legends_arceus(data)
    else:
        summary = {"recorded_species": len(data.get("pokemon", []))}
    return {"personal_data": True, "game": game, **summary}


def game_rows() -> list[dict]:
    personal = set(available_personal_games())
    rows = [
        {
            "game": game,
            "active": game == active_game(),
            "personal_data": True,
            "summary": game_summary(game),
        }
        for game in available_personal_games()
    ]
    for game in supported_games():
        if game not in personal:
            rows.append({"game": game, "active": False, "personal_data": False, "summary": {}})
    return rows


def set_active_game(game: str) -> dict:
    """Set the active personal game. Supported-only games cannot fake a save."""
    if game not in available_personal_games():
        raise GameSwitcherError(f"No imported personal save data exists for {game}.")
    prefs = load_preferences()
    if prefs.get("active_game") == game:
        return prefs
    backup_dir = PROFILE_DIR / "_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if PREF_FILE.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(PREF_FILE, backup_dir / f"game_preferences.json.{stamp}.bak")
    prefs["active_game"] = game
    temp = PREF_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(prefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(PREF_FILE)
    return prefs
