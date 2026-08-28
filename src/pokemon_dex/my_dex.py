"""Build the user's personal caught-Pokemon Dex from local profile records."""

from __future__ import annotations

from collections import defaultdict

from pokemon_dex.personal import load_personal_records


def caught_records() -> list[dict]:
    """Return only records currently marked as caught."""
    return [record for record in load_personal_records() if record.get("caught")]


def caught_by_game() -> dict[str, list[dict]]:
    """Group caught Pokemon records by game name."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in caught_records():
        grouped[str(record.get("game", "Unknown Game"))].append(record)
    return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))


def unique_caught_species() -> list[str]:
    """Return alphabetized unique species names across all local saves."""
    names = {str(record.get("species_name", "Unknown")) for record in caught_records()}
    return sorted(names, key=str.lower)


def dex_summary() -> dict:
    """Return compact totals for the personal Dex UI."""
    caught = caught_records()
    grouped = caught_by_game()
    return {
        "caught_records": len(caught),
        "unique_species": len(unique_caught_species()),
        "games_with_caught_data": len(grouped),
        "by_game": {
            game: {
                "caught_records": len(records),
                "unique_species": len({r.get("species_name") for r in records}),
                "team_members": sum(1 for r in records if r.get("in_team")),
                "complete_entries": sum(1 for r in records if r.get("complete")),
            }
            for game, records in grouped.items()
        },
    }
