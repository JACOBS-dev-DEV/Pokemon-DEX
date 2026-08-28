"""Smoke tests for local personal-Dex and journey data."""

import unittest

from pokemon_dex.journey import journey_summary
from pokemon_dex.my_dex import caught_records, dex_summary
from pokemon_dex.team import load_team, team_summary


class PersonalDexTests(unittest.TestCase):
    def test_caught_records_only_include_caught_pokemon(self):
        records = caught_records()
        self.assertTrue(all(record.get("caught") is True for record in records))

    def test_dex_summary_matches_caught_records(self):
        records = caught_records()
        summary = dex_summary()
        self.assertEqual(summary["caught_records"], len(records))
        self.assertEqual(summary["unique_species"], len({record.get("species_name") for record in records}))

    def test_journey_summary_totals_are_consistent(self):
        summary = journey_summary()
        self.assertGreaterEqual(summary["trainer_battles"], summary["wins"] + summary["losses"])

    def test_team_loader_is_safe_when_team_file_is_missing(self):
        team = load_team()
        summary = team_summary()
        self.assertIsInstance(team, dict)
        self.assertIsInstance(team.get("team", []), list)
        self.assertEqual(summary["members"], len(team.get("team", [])))


if __name__ == "__main__":
    unittest.main()
