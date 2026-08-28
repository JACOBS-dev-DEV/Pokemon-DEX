"""Held-item tracking for the active Pokemon Sword party only.

The tracker is intentionally scoped to the six current party slots. It records
item changes as history so live edits never silently erase what a Pokemon was
holding before.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"
DEFAULT_FILE = PROFILE_ROOT / "JacobS-Dev-1" / "sword_team_items.json"


class TeamItemError(RuntimeError):
    """Raised when a held-item edit cannot be safely applied."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_path(path: Path = DEFAULT_FILE, *, root: Path = ROOT) -> Path:
    root = root.resolve()
    profile_root = (root / "profiles").resolve()
    candidate = path if path.is_absolute() else root / path
    candidate = candidate.resolve()
    if profile_root not in candidate.parents or not candidate.name.endswith("_team_items.json"):
        raise TeamItemError("Held-item edits are limited to profile *_team_items.json files.")
    return candidate


def _load(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise TeamItemError(f"Could not read held-item file: {path.name}") from exc
    data.setdefault("team_items", [])
    return data


def _backup(path: Path, *, root: Path) -> None:
    backup_dir = root / "profiles" / "_backups" / path.parent.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, backup_dir / f"{path.name}.{stamp}.bak")


def _save(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise TeamItemError(f"Could not save held-item file: {path.name}") from exc


def _slot_entry(data: dict, slot: int) -> dict:
    try:
        slot = int(slot)
    except (TypeError, ValueError) as exc:
        raise TeamItemError("Team slot must be between 1 and 6.") from exc
    if not 1 <= slot <= 6:
        raise TeamItemError("Team slot must be between 1 and 6.")
    entry = next((item for item in data.get("team_items", []) if int(item.get("slot", 0)) == slot), None)
    if entry is None:
        raise TeamItemError(f"Team slot {slot} is not configured.")
    entry.setdefault("history", [])
    return entry


def load_team_items(path: Path = DEFAULT_FILE, *, root: Path = ROOT) -> dict:
    return _load(_safe_path(path, root=root))


def item_summary(path: Path = DEFAULT_FILE, *, root: Path = ROOT) -> dict:
    data = load_team_items(path, root=root)
    rows = data.get("team_items", [])
    return {
        "slots": len(rows),
        "holding_items": sum(1 for row in rows if row.get("held_item")),
        "empty_slots": sum(1 for row in rows if not row.get("held_item")),
        "changes_logged": sum(len(row.get("history", [])) for row in rows),
    }


def set_held_item(
    slot: int,
    item: str | None,
    *,
    reason: str = "live held-item edit",
    path: Path = DEFAULT_FILE,
    root: Path = ROOT,
) -> dict:
    """Set or clear one party slot's held item and preserve the old state."""
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    entry = _slot_entry(data, slot)
    old_item = entry.get("held_item")
    new_item = str(item).strip() if item is not None and str(item).strip() else None
    if old_item == new_item:
        return data
    entry["held_item"] = new_item
    entry["history"].append(
        {
            "timestamp": _timestamp(),
            "from": old_item,
            "to": new_item,
            "reason": str(reason),
        }
    )
    _backup(path, root=root)
    _save(path, data)
    return data


def swap_held_items(
    slot_a: int,
    slot_b: int,
    *,
    reason: str = "swap held items",
    path: Path = DEFAULT_FILE,
    root: Path = ROOT,
) -> dict:
    """Swap held items between two current team slots as one atomic save."""
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    a = _slot_entry(data, slot_a)
    b = _slot_entry(data, slot_b)
    if a is b:
        return data
    item_a = a.get("held_item")
    item_b = b.get("held_item")
    if item_a == item_b:
        return data
    stamp = _timestamp()
    a["held_item"], b["held_item"] = item_b, item_a
    a["history"].append({"timestamp": stamp, "from": item_a, "to": item_b, "reason": reason})
    b["history"].append({"timestamp": stamp, "from": item_b, "to": item_a, "reason": reason})
    _backup(path, root=root)
    _save(path, data)
    return data
