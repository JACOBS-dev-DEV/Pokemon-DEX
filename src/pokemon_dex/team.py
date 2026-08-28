"""Local player-team records for Pokemon-DEX."""

from __future__ import annotations

import json
from pathlib import Path

from pokemon_dex.game_switcher import active_game

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "profiles" / "JacobS-Dev-1"
TEAM_FILES = {
    "Pokemon Sword": PROFILE_DIR / "sword_team.json",
    "Pokemon Shield": PROFILE_DIR / "shield_team.json",
}


def team_file_for_game(game: str | None = None) -> Path | None:
    return TEAM_FILES.get(game or active_game())


def load_team(game: str | None = None) -> dict:
    selected_game = game or active_game()
    team_file = team_file_for_game(selected_game)
    if team_file is None or not team_file.exists():
        return {"game": selected_game, "team": [], "snapshot_kind": "not_captured"}
    with team_file.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def team_members(game: str | None = None) -> list[dict]:
    return list(load_team(game).get("team", []))


def team_summary(game: str | None = None) -> dict:
    data = load_team(game)
    members = list(data.get("team", []))
    known = [member for member in members if member.get("species_name")]
    return {
        "game": data.get("game", game or active_game()),
        "members": len(known),
        "slots": len(members),
        "fainted": sum(
            1
            for member in known
            if str(member.get("status", "")).lower() == "fainted" or member.get("current_hp") == 0
        ),
        "with_level": sum(1 for member in known if member.get("level") is not None),
        "with_moves": sum(1 for member in known if member.get("moves")),
        "snapshot_kind": data.get("snapshot_kind"),
    }
