"""Opponent trainer/faction tracking for live Pokemon Sword progress."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"
DEFAULT_FILE = PROFILE_ROOT / "JacobS-Dev-1" / "sword_opponents.json"


class OpponentError(RuntimeError):
    """Raised when opponent tracking cannot be updated safely."""


def _safe_path(path: Path = DEFAULT_FILE) -> Path:
    candidate = path.resolve()
    profile_root = PROFILE_ROOT.resolve()
    if profile_root not in candidate.parents or not candidate.name.endswith("_opponents.json"):
        raise OpponentError("Opponent edits are limited to profile *_opponents.json files.")
    return candidate


def _load(path: Path = DEFAULT_FILE) -> dict:
    path = _safe_path(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise OpponentError(f"Could not read opponent data: {path.name}") from exc
    data.setdefault("groups", [])
    data.setdefault("opponents", [])
    data.setdefault("pending_opponents", [])
    return data


def load_opponents(path: Path = DEFAULT_FILE) -> dict:
    return _load(path)


def opponent_summary(path: Path = DEFAULT_FILE) -> dict:
    data = _load(path)
    opponents = data.get("opponents", [])
    return {
        "groups": len(data.get("groups", [])),
        "opponents": len(opponents),
        "wins": sum(1 for item in opponents if item.get("result") == "win"),
        "losses": sum(1 for item in opponents if item.get("result") == "loss"),
        "pending": len(data.get("pending_opponents", [])),
        "confirmed_rosters": sum(1 for item in opponents if item.get("roster_status") == "confirmed"),
    }


def _backup(path: Path) -> None:
    backup_dir = PROFILE_ROOT / "_backups" / path.parent.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, backup_dir / f"{path.name}.{stamp}.bak")


def _save(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def confirm_pending_battle(
    *,
    name: str,
    group_id: str | None,
    location: str,
    result: str,
    roster: list[dict] | None = None,
    reward_poke_dollars: int | None = None,
    relationship: str = "story_opposition",
    path: Path = DEFAULT_FILE,
) -> dict:
    """Move a pending opponent into the confirmed battle log."""
    path = _safe_path(path)
    data = _load(path)
    result = result.lower().strip()
    if result not in {"win", "loss"}:
        raise OpponentError("Battle result must be win or loss.")

    pending = data.get("pending_opponents", [])
    match_index = next(
        (
            index
            for index, item in enumerate(pending)
            if (group_id is None or item.get("group_id") == group_id)
            and str(item.get("location", "")).lower() == location.lower()
        ),
        None,
    )
    if match_index is not None:
        pending.pop(match_index)

    sequence = 1 + max((int(item.get("battle_sequence") or 0) for item in data.get("opponents", [])), default=0)
    record = {
        "opponent_id": f"battle-{sequence}-{name.lower().replace(' ', '-')}",
        "name": name,
        "group_id": group_id,
        "relationship": relationship,
        "location": location,
        "result": result,
        "battle_sequence": sequence,
        "roster": roster or [],
        "roster_status": "confirmed" if roster else "unknown",
    }
    if reward_poke_dollars is not None:
        record["reward_poke_dollars"] = max(0, int(reward_poke_dollars))
    data["opponents"].append(record)

    if group_id:
        for group in data.get("groups", []):
            if group.get("group_id") == group_id:
                group["encountered"] = True
                break

    _backup(path)
    _save(path, data)
    return record
