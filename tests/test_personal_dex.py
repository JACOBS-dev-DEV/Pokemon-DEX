"""Smoke tests for local personal-Dex and journey data."""

from pokemon_dex.journey import journey_summary
from pokemon_dex.my_dex import caught_records, dex_summary
from pokemon_dex.team import load_team, team_summary


def test_caught_records_only_include_caught_pokemon():
    records = caught_records()
    assert all(record.get("caught") is True for record in records)


def test_dex_summary_matches_caught_records():
    records = caught_records()
    summary = dex_summary()
    assert summary["caught_records"] == len(records)
    assert summary["unique_species"] == len({record.get("species_name") for record in records})


def test_journey_summary_totals_are_consistent():
    summary = journey_summary()
    assert summary["trainer_battles"] >= summary["wins"] + summary["losses"]


def test_team_loader_is_safe_when_team_file_is_missing():
    team = load_team()
    summary = team_summary()
    assert isinstance(team, dict)
    assert isinstance(team.get("team", []), list)
    assert summary["members"] == len(team.get("team", []))
