"""Dependency-free tests for live party/Dex synchronization."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pokemon_dex.team import load_team, owned_candidates, remove_team_slot, replace_team_slot


class TeamManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile_dir = self.root / "profiles" / "JacobS-Dev-1"
        self.profile_dir.mkdir(parents=True)
        self.personal = self.profile_dir / "sword.json"
        self.team = self.profile_dir / "sword_team.json"

    def tearDown(self):
        self.temp.cleanup()

    def _write_personal(self, pokemon: list[dict]) -> None:
        self.personal.write_text(
            json.dumps(
                {
                    "profile_id": "JacobS-Dev-1",
                    "game": "Pokemon Sword",
                    "pokemon": pokemon,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_team(self, members: list[dict]) -> None:
        self.team.write_text(
            json.dumps(
                {
                    "profile_id": "JacobS-Dev-1",
                    "game": "Pokemon Sword",
                    "trainer_name": "Tester",
                    "trainer_id": "123456",
                    "snapshot_kind": "current_live_party",
                    "team": members,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def _read_personal(self) -> dict:
        return json.loads(self.personal.read_text(encoding="utf-8"))

    def test_dex_in_team_marker_appears_in_team_view(self):
        self._write_personal(
            [
                {
                    "local_id": 1,
                    "species_name": "Yamper",
                    "type_1": "Electric",
                    "caught": True,
                    "owned_count": 1,
                    "in_team": True,
                    "team_slot": 2,
                    "level": 14,
                }
            ]
        )
        self._write_team([])

        data = load_team("Pokemon Sword", root=self.root)
        self.assertEqual(len(data["team"]), 1)
        self.assertEqual(data["team"][0]["slot"], 2)
        self.assertEqual(data["team"][0]["species_name"], "Yamper")
        self.assertEqual(data["team"][0]["level"], 14)

    def test_replace_slot_updates_team_and_personal_dex_flags(self):
        self._write_personal(
            [
                {
                    "local_id": 1,
                    "species_name": "Skwovet",
                    "caught": True,
                    "owned_count": 1,
                    "in_team": True,
                    "team_slot": 1,
                    "level": 10,
                },
                {
                    "local_id": 2,
                    "species_name": "Yamper",
                    "caught": True,
                    "owned_count": 1,
                    "in_team": False,
                    "level": 12,
                },
            ]
        )
        self._write_team([{"slot": 1, "species_name": "Skwovet", "level": 10}])

        data = replace_team_slot(1, 2, "Pokemon Sword", root=self.root)
        self.assertEqual(data["team"][0]["species_name"], "Yamper")

        records = {row["species_name"]: row for row in self._read_personal()["pokemon"]}
        self.assertFalse(records["Skwovet"]["in_team"])
        self.assertNotIn("team_slot", records["Skwovet"])
        self.assertTrue(records["Yamper"]["in_team"])
        self.assertEqual(records["Yamper"]["team_slot"], 1)

        backups = list((self.root / "profiles" / "_backups" / "JacobS-Dev-1").glob("*.bak"))
        self.assertGreaterEqual(len(backups), 2)

    def test_remove_slot_keeps_pokemon_owned(self):
        self._write_personal(
            [
                {
                    "local_id": 1,
                    "species_name": "Chewtle",
                    "caught": True,
                    "owned_count": 1,
                    "in_team": True,
                    "team_slot": 5,
                    "level": 12,
                }
            ]
        )
        self._write_team([{"slot": 5, "species_name": "Chewtle", "level": 12}])

        data = remove_team_slot(5, "Pokemon Sword", root=self.root)
        self.assertEqual(data["team"], [])
        saved = self._read_personal()["pokemon"][0]
        self.assertFalse(saved["in_team"])
        self.assertEqual(saved["owned_count"], 1)
        self.assertTrue(saved["caught"])

    def test_owned_candidates_allows_spare_duplicate_copy(self):
        self._write_personal(
            [
                {
                    "local_id": 1,
                    "species_name": "Rookidee",
                    "caught": True,
                    "owned_count": 2,
                    "in_team": True,
                    "team_slot": 2,
                    "level": 12,
                }
            ]
        )
        self._write_team([{"slot": 2, "species_name": "Rookidee", "level": 12}])

        candidates = owned_candidates("Pokemon Sword", root=self.root)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["species_name"], "Rookidee")
        self.assertEqual(candidates[0]["available_copies"], 1)


if __name__ == "__main__":
    unittest.main()
