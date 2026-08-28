"""Dependency-free tests for safe live local profile editing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pokemon_dex.editor import adjust_field, toggle_field, update_record


class LiveEditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile_dir = self.root / "profiles" / "Tester"
        self.profile_dir.mkdir(parents=True)
        self.profile = self.profile_dir / "sword.json"
        self.profile.write_text(
            json.dumps(
                {
                    "profile_id": "Tester",
                    "game": "Pokemon Sword",
                    "pokemon": [
                        {
                            "local_id": 1,
                            "species_name": "Yamper",
                            "caught": True,
                            "owned_count": 1,
                            "battle_count": 0,
                            "in_team": False,
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.record = {
            "species_name": "Yamper",
            "source_file": "profiles/Tester/sword.json",
            "caught": True,
            "owned_count": 1,
            "battle_count": 0,
            "in_team": False,
        }

    def tearDown(self):
        self.temp.cleanup()

    def _read_record(self):
        data = json.loads(self.profile.read_text(encoding="utf-8"))
        return data["pokemon"][0]

    def test_update_record_creates_backup_before_write(self):
        update_record(
            "profiles/Tester/sword.json",
            "Yamper",
            {"owned_count": 2},
            root=self.root,
        )
        self.assertEqual(self._read_record()["owned_count"], 2)
        backups = list((self.root / "profiles" / "_backups" / "Tester").glob("*.bak"))
        self.assertEqual(len(backups), 1)
        old_data = json.loads(backups[0].read_text(encoding="utf-8"))
        self.assertEqual(old_data["pokemon"][0]["owned_count"], 1)

    def test_team_toggle_keeps_record_caught_and_owned(self):
        toggle_field(self.record, "in_team", root=self.root)
        saved = self._read_record()
        self.assertTrue(saved["in_team"])
        self.assertTrue(saved["caught"])
        self.assertGreaterEqual(saved["owned_count"], 1)
        self.assertEqual(saved["team_slot"], 1)

    def test_owned_count_never_goes_below_zero(self):
        adjust_field(self.record, "owned_count", -20, root=self.root)
        self.assertEqual(self._read_record()["owned_count"], 0)

    def test_level_is_clamped_to_game_range(self):
        update_record(
            "profiles/Tester/sword.json",
            "Yamper",
            {"level": 999},
            root=self.root,
        )
        self.assertEqual(self._read_record()["level"], 100)


if __name__ == "__main__":
    unittest.main()
