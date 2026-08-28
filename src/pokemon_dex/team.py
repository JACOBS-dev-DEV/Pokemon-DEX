"""Local player-team records for Pokemon-DEX."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEAM_FILE = ROOT / "profiles" / "JacobS-Dev-1" / "sword_team.json"


def load_team() -> dict:
    if not TEAM_FILE.exists():
        return {"game": "Pokemon Sword", "team": []}
    with TEAM_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def team_members() -> list[dict]:
    return list(load_team().get("team", []))


def team_summary() -> dict:
    members = team_members()
    return {
        "members": len(members),
        "fainted": sum(1 for member in members if str(member.get("status", "")).lower() == "fainted" or member.get("current_hp") == 0),
        "with_level": sum(1 for member in members if member.get("level") is not None),
        "with_moves": sum(1 for member in members if member.get("moves")),
    }
