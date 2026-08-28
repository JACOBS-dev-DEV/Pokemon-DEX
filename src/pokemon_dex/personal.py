"""Load and normalize local personal Pokemon save/profile records."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_personal_records() -> list[dict]:
    """Return normalized Pokemon records from every local personal profile file."""
    records: list[dict] = []
    if not PROFILE_ROOT.exists():
        return records

    for path in sorted(PROFILE_ROOT.rglob("*.json")):
        try:
            data = _load_json(path)
        except (OSError, json.JSONDecodeError):
            continue

        profile_id = str(data.get("profile_id", path.parent.name))
        game = str(data.get("game", path.stem.replace("_", " ").title()))
        for raw in data.get("pokemon", []):
            species = raw.get("species_name") or raw.get("name") or "Unknown"
            owned_count = raw.get("owned_count")
            if owned_count is None:
                owned_count = raw.get("obtained_count")
            record = {
                "profile_id": profile_id,
                "game": game,
                "species_name": str(species),
                "caught": bool(raw.get("caught", False)),
                "complete": bool(raw.get("complete", False)),
                "evolved": bool(raw.get("evolved", False)),
                "in_team": bool(raw.get("in_team", False)),
                "team_slot": raw.get("team_slot"),
                "owned_count": owned_count,
                "obtained_count": raw.get("obtained_count"),
                "battle_count": raw.get("battle_count"),
                "research_total": raw.get("research_total"),
                "regional_id": raw.get("regional_id"),
                "national_dex": raw.get("national_dex") or raw.get("dex_id"),
                "local_id": raw.get("local_id"),
                "form": raw.get("form"),
                "type_1": raw.get("type_1"),
                "type_2": raw.get("type_2"),
                "found_at_level": raw.get("found_at_level"),
                "level": raw.get("level"),
                "status": raw.get("status"),
                "notes": raw.get("notes"),
                "caught_location": raw.get("caught_location"),
                "stats": raw.get("stats") or {},
                "source_file": path.relative_to(ROOT).as_posix(),
            }
            records.append(record)
    return records


def summarize_games(records: list[dict] | None = None) -> list[dict]:
    """Build compact per-game totals for the GUI."""
    source = records if records is not None else load_personal_records()
    grouped: dict[str, dict] = {}
    for record in source:
        game = record["game"]
        summary = grouped.setdefault(
            game,
            {
                "game": game,
                "records": 0,
                "caught": 0,
                "complete": 0,
                "evolved": 0,
                "team": 0,
                "owned_total": 0,
                "battles": 0,
                "research_total": 0,
            },
        )
        summary["records"] += 1
        summary["caught"] += int(record["caught"])
        summary["complete"] += int(record.get("complete", False))
        summary["evolved"] += int(record.get("evolved", False))
        summary["team"] += int(record["in_team"])
        if isinstance(record.get("owned_count"), int):
            summary["owned_total"] += record["owned_count"]
        if isinstance(record.get("battle_count"), int):
            summary["battles"] += record["battle_count"]
        if isinstance(record.get("research_total"), int):
            summary["research_total"] += record["research_total"]
    return sorted(grouped.values(), key=lambda item: item["game"])
