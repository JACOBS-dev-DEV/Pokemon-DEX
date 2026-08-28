"""Offline game-journey and trainer-battle log reader."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILES_ROOT = ROOT / "profiles"


def load_journey_logs() -> list[dict]:
    logs: list[dict] = []
    if not PROFILES_ROOT.exists():
        return logs
    for path in PROFILES_ROOT.rglob("*_journey.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            data["_source_file"] = str(path.relative_to(ROOT))
            logs.append(data)
        except (OSError, json.JSONDecodeError):
            continue
    return logs


def journey_summary(game: str | None = None) -> dict:
    logs = load_journey_logs()
    if game:
        logs = [log for log in logs if str(log.get("game", "")).lower() == game.lower()]
    battles = [battle for log in logs for battle in log.get("trainer_battles", [])]
    return {
        "games": len(logs),
        "trainer_battles": len(battles),
        "wins": sum(1 for battle in battles if battle.get("result") == "win"),
        "losses": sum(1 for battle in battles if battle.get("result") == "loss"),
        "logs": logs,
    }
