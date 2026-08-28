"""Safe local live editing for Pokemon-DEX personal profile records.

Edits are written atomically to the local profile JSON file. Before a changed
file is replaced, a timestamped .bak copy is stored under profiles/_backups so
backup files are not mistaken for active profile JSON by the normal loader.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_EDITABLE_FIELDS = {
    "caught",
    "complete",
    "evolved",
    "in_team",
    "team_slot",
    "owned_count",
    "obtained_count",
    "battle_count",
    "level",
    "status",
    "notes",
}
_BOOLEAN_FIELDS = {"caught", "complete", "evolved", "in_team"}
_INTEGER_FIELDS = {"owned_count", "obtained_count", "battle_count", "level", "team_slot"}


class ProfileEditError(RuntimeError):
    """Raised when a requested live edit cannot safely be applied."""


def _profile_root(root: Path) -> Path:
    return (root / "profiles").resolve()


def _resolve_profile_path(source_file: str, root: Path) -> Path:
    root = root.resolve()
    path = (root / source_file).resolve()
    profile_root = _profile_root(root)
    if path.suffix.lower() != ".json" or profile_root not in path.parents:
        raise ProfileEditError("Live edits are limited to JSON files inside profiles/.")
    return path


def _load(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileEditError(f"Could not read profile file: {path.name}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("pokemon", []), list):
        raise ProfileEditError("Profile file does not contain an editable pokemon list.")
    return data


def _normalize_update(field: str, value):
    if field not in _EDITABLE_FIELDS:
        raise ProfileEditError(f"Field is not live-editable: {field}")
    if field in _BOOLEAN_FIELDS:
        return bool(value)
    if field in _INTEGER_FIELDS:
        if value is None and field == "team_slot":
            return None
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ProfileEditError(f"{field} must be a number.") from exc
        if field in {"owned_count", "obtained_count", "battle_count"}:
            return max(0, number)
        if field == "level":
            return min(100, max(1, number))
        if field == "team_slot":
            return min(6, max(1, number))
    if field in {"status", "notes"}:
        return str(value)
    return value


def _apply_consistency(record: dict) -> None:
    owned = record.get("owned_count")
    obtained = record.get("obtained_count")
    if isinstance(owned, int) and owned > 0:
        record["caught"] = True
    if owned is None and isinstance(obtained, int) and obtained > 0:
        record["caught"] = True
    if record.get("in_team"):
        record["caught"] = True
        if isinstance(owned, int) and owned < 1:
            record["owned_count"] = 1
        elif owned is None and obtained is None:
            record["owned_count"] = 1
        if record.get("team_slot") is None:
            record["team_slot"] = 1
    if not record.get("caught", False):
        record["in_team"] = False
        record["team_slot"] = None
        if isinstance(owned, int):
            record["owned_count"] = 0


def _backup(path: Path, root: Path) -> Path:
    backup_dir = root / "profiles" / "_backups" / path.parent.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, backup_path)
    return backup_path


def _atomic_write(path: Path, data: dict) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    encoded = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    try:
        temp_path.write_text(encoded, encoding="utf-8")
        temp_path.replace(path)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ProfileEditError(f"Could not save profile file: {path.name}") from exc


def update_record(
    source_file: str,
    species_name: str,
    updates: dict,
    *,
    root: Path = ROOT,
) -> dict:
    """Apply one or more fields to a species record and save immediately."""
    root = root.resolve()
    path = _resolve_profile_path(source_file, root)
    data = _load(path)
    target = None
    for raw in data.get("pokemon", []):
        raw_name = raw.get("species_name") or raw.get("name") or ""
        if str(raw_name).casefold() == species_name.casefold():
            target = raw
            break
    if target is None:
        raise ProfileEditError(f"Pokemon record not found: {species_name}")

    changed = False
    for field, value in updates.items():
        normalized = _normalize_update(field, value)
        if target.get(field) != normalized:
            target[field] = normalized
            changed = True

    before_consistency = dict(target)
    _apply_consistency(target)
    if target != before_consistency:
        changed = True

    if changed:
        _backup(path, root)
        _atomic_write(path, data)
    return dict(target)


def set_field(record: dict, field: str, value, *, root: Path = ROOT) -> dict:
    """Update an editable field using a normalized record from personal.py."""
    source_file = str(record.get("source_file", ""))
    species_name = str(record.get("species_name", ""))
    if not source_file or not species_name:
        raise ProfileEditError("Record is missing source_file or species_name.")
    return update_record(source_file, species_name, {field: value}, root=root)


def toggle_field(record: dict, field: str, *, root: Path = ROOT) -> dict:
    """Toggle a supported boolean field and save it immediately."""
    if field not in _BOOLEAN_FIELDS:
        raise ProfileEditError(f"Field is not toggleable: {field}")
    return set_field(record, field, not bool(record.get(field)), root=root)


def adjust_field(record: dict, field: str, delta: int, *, root: Path = ROOT) -> dict:
    """Increment/decrement an editable numeric field and save immediately."""
    if field not in _INTEGER_FIELDS:
        raise ProfileEditError(f"Field is not adjustable: {field}")
    current = record.get(field)
    if field == "level" and current is None:
        current = record.get("found_at_level") or 1
    elif field == "team_slot" and current is None:
        current = 1
    elif current is None:
        current = 0
    return set_field(record, field, int(current) + int(delta), root=root)
