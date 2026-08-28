"""Dependency-free tests for offline game-wallet tracking."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pokemon_dex.wallet import add_transaction, record_balance_observation, set_balance, wallet_summary


class WalletTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile_dir = self.root / "profiles" / "Tester"
        self.profile_dir.mkdir(parents=True)
        self.wallet_path = self.profile_dir / "sword_wallet.json"
        self.wallet_path.write_text(
            json.dumps(
                {
                    "profile_id": "Tester",
                    "game": "Pokemon Sword",
                    "wallet": {
                        "poke_dollars": {"display_name": "Poké Dollars", "symbol": "₽", "balance": None},
                        "watts": {"display_name": "Watts", "symbol": "W", "balance": None},
                    },
                    "transactions": [],
                    "balance_observations": [],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def _read(self):
        return json.loads(self.wallet_path.read_text(encoding="utf-8"))

    def test_initial_balance_creates_backup(self):
        set_balance("poke_dollars", 5000, path=self.wallet_path, root=self.root)
        self.assertEqual(self._read()["wallet"]["poke_dollars"]["balance"], 5000)
        backups = list((self.root / "profiles" / "_backups" / "Tester").glob("*.bak"))
        self.assertEqual(len(backups), 1)

    def test_transaction_updates_known_balance(self):
        set_balance("poke_dollars", 5000, path=self.wallet_path, root=self.root)
        add_transaction(
            "poke_dollars",
            -200,
            kind="purchase",
            reason="Bought Poké Balls",
            path=self.wallet_path,
            root=self.root,
        )
        self.assertEqual(self._read()["wallet"]["poke_dollars"]["balance"], 4800)

    def test_unknown_balance_can_still_log_relative_transaction(self):
        add_transaction(
            "poke_dollars",
            120,
            kind="trainer_reward",
            reason="Trainer win",
            path=self.wallet_path,
            root=self.root,
        )
        data = self._read()
        self.assertIsNone(data["wallet"]["poke_dollars"]["balance"])
        self.assertEqual(data["transactions"][0]["amount"], 120)

    def test_observation_can_initialize_balance(self):
        record_balance_observation(
            "poke_dollars",
            4321,
            source="screenshot",
            source_ref="sample.png",
            confidence=0.98,
            path=self.wallet_path,
            root=self.root,
        )
        data = self._read()
        self.assertEqual(data["wallet"]["poke_dollars"]["balance"], 4321)
        self.assertEqual(data["balance_observations"][0]["source"], "screenshot")

    def test_summary_handles_initial_observation_without_numeric_delta(self):
        record_balance_observation(
            "poke_dollars",
            1000,
            source="manual",
            path=self.wallet_path,
            root=self.root,
        )
        summary = wallet_summary(path=self.wallet_path, root=self.root)
        self.assertEqual(summary["currencies"]["poke_dollars"]["balance"], 1000)
        self.assertEqual(summary["earned_total"], 0)
        self.assertEqual(summary["spent_total"], 0)


if __name__ == "__main__":
    unittest.main()
