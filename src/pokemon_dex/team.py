"""Local player-team records and safe party management for Pokemon-DEX.

The dedicated ``*_team.json`` file preserves detailed per-Pokemon party snapshots,
while the personal game file (``sword.json`` / ``shield.json``) stores broad Dex
ownership flags.  This module reconciles both directions so ``in_team`` markers
show up in Team Manager and Team Manager edits update those markers safely.
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from pokemon_dex.game_switcher import active_game

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = "JacobS-Dev-1"
TEAM_FILE_NAMES = {
    "Pokemon Sword": "sword_team.json",
    "Pokemon Shield": "shield_team.json",
}
PERSONAL_FILE_NAMES = {
    "Pokemon Sword": "sword.json",
    "Pokemon Shield": "shield.json",
}


class TeamError(RuntimeError):
    """Raised when a party edit cannot be applied safely."""


def _profile_dir(root: Path) -> Path:
    return root.resolve() / "profiles" / PROFILE_ID


def team_file_for_game(game: str | None = None, *, root: Path = ROOT) -> Path | None:
    selected = game or active_game()
    name = TEAM_FILE_NAMES.get(selected)
    return _profile_dir(root) / name if name else None


def personal_file_for_game(game: str | None = None, *, root: Path = ROOT) -> Path | None:
    selected = game or active_game()
    name = PERSONAL_FILE_NAMES.get(selected)
    return _profile_dir(root) / name if name else None


def _load_json(path: Path, *, default: dict | None = None) -> dict:
    if not path.exists():
        return dict(default or {})
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise TeamError(f"Could not read team data: {path.name}") from exc


def _backup(path: Path, *, root: Path) -> None:
    if not path.exists():
        return
    backup_dir = root.resolve() / "profiles" / "_backups" / PROFILE_ID
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, backup_dir / f"{path.name}.{stamp}.bak")


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise TeamError(f"Could not save team data: {path.name}") from exc


def _slot(value) -> int | None:
    try:
        slot = int(value)
    except (TypeError, ValueError):
        return None
    return slot if 1 <= slot <= 6 else None


def _member_from_record(record: dict, slot: int) -> dict:
    """Create a lightweight party member from a personal-Dex record."""
    member = {
        "slot": slot,
        "species_name": record.get("species_name", "Unknown"),
        "level": record.get("level"),
        "current_hp": None,
        "max_hp": None,
        "status": "unknown_current",
        "type_1": record.get("type_1"),
        "type_2": record.get("type_2"),
        "source": "Auto-synced from personal Dex in_team marker",
    }
    if record.get("form"):
        member["form"] = record.get("form")
    if record.get("sex"):
        member["sex"] = record.get("sex")
    if record.get("local_id") is not None:
        member["personal_local_id"] = record.get("local_id")
    return member


def _merge_basic_personal_fields(member: dict, record: dict, slot: int) -> dict:
    """Preserve detailed snapshot fields while applying current Dex basics."""
    merged = dict(member)
    merged["slot"] = slot
    for key in ("species_name", "form", "type_1", "type_2", "level", "sex"):
        if record.get(key) is not None:
            merged[key] = record.get(key)
    if record.get("local_id") is not None:
        merged["personal_local_id"] = record.get("local_id")
    return merged


def _personal_team_slots(record: dict) -> list[int]:
    slots: list[int] = []
    raw_slots = record.get("team_slots")
    if isinstance(raw_slots, list):
        for value in raw_slots:
            parsed = _slot(value)
            if parsed is not None and parsed not in slots:
                slots.append(parsed)
    parsed_single = _slot(record.get("team_slot"))
    if parsed_single is not None and parsed_single not in slots:
        slots.append(parsed_single)
    return sorted(slots)


def _reconcile_for_display(team_data: dict, personal_data: dict) -> dict:
    """Overlay explicit personal-Dex team flags without deleting rich snapshots."""
    members = [dict(row) for row in team_data.get("team", []) if _slot(row.get("slot"))]
    by_slot = {_slot(row.get("slot")): row for row in members}
    records = list(personal_data.get("pokemon", []))

    for record in records:
        if not record.get("in_team"):
            continue
        requested_slots = _personal_team_slots(record)
        if not requested_slots:
            continue
        species = record.get("species_name")
        for slot in requested_slots:
            existing = by_slot.get(slot)
            if existing and existing.get("species_name") == species:
                by_slot[slot] = _merge_basic_personal_fields(existing, record, slot)
                continue

            # If the same species already exists elsewhere, reuse its details only
            # when that snapshot is not the slot currently being occupied.
            detail_source = next(
                (row for row in members if row.get("species_name") == species and _slot(row.get("slot")) != slot),
                None,
            )
            by_slot[slot] = (
                _merge_basic_personal_fields(detail_source, record, slot)
                if detail_source
                else _member_from_record(record, slot)
            )

    reconciled = dict(team_data)
    reconciled["team"] = [by_slot[slot] for slot in sorted(by_slot) if slot is not None]
    reconciled.setdefault("game", personal_data.get("game") or team_data.get("game"))
    return reconciled


def load_team(game: str | None = None, *, root: Path = ROOT) -> dict:
    selected_game = game or active_game()
    team_file = team_file_for_game(selected_game, root=root)
    personal_file = personal_file_for_game(selected_game, root=root)
    if team_file is None:
        return {"game": selected_game, "team": [], "snapshot_kind": "not_configured"}

    team_data = _load_json(
        team_file,
        default={"profile_id": PROFILE_ID, "game": selected_game, "team": [], "snapshot_kind": "not_captured"},
    )
    if personal_file is None or not personal_file.exists():
        return team_data
    personal_data = _load_json(personal_file, default={"pokemon": []})
    return _reconcile_for_display(team_data, personal_data)


def team_members(game: str | None = None, *, root: Path = ROOT) -> list[dict]:
    return list(load_team(game, root=root).get("team", []))


def owned_candidates(game: str | None = None, *, root: Path = ROOT) -> list[dict]:
    """Return owned Pokemon with at least one copy available outside the party."""
    selected = game or active_game()
    personal_file = personal_file_for_game(selected, root=root)
    if personal_file is None or not personal_file.exists():
        return []
    personal = _load_json(personal_file, default={"pokemon": []})
    current = team_members(selected, root=root)
    team_counts = Counter(str(row.get("species_name")) for row in current if row.get("species_name"))

    candidates: list[dict] = []
    for record in personal.get("pokemon", []):
        species = record.get("species_name")
        if not species:
            continue
        try:
            owned_count = int(record.get("owned_count", 1 if record.get("caught") else 0) or 0)
        except (TypeError, ValueError):
            owned_count = 0
        if owned_count <= 0:
            continue
        available = owned_count - team_counts.get(str(species), 0)
        if available <= 0:
            continue
        row = dict(record)
        row["available_copies"] = available
        candidates.append(row)
    return sorted(candidates, key=lambda row: (str(row.get("species_name", "")).lower(), int(row.get("local_id", 999999))))


def _sync_personal_flags(personal: dict, members: list[dict]) -> None:
    species_slots: dict[str, list[int]] = {}
    for member in members:
        species = member.get("species_name")
        slot = _slot(member.get("slot"))
        if species and slot is not None:
            species_slots.setdefault(str(species), []).append(slot)

    for record in personal.get("pokemon", []):
        species = str(record.get("species_name", ""))
        slots = sorted(species_slots.get(species, []))
        if slots:
            record["in_team"] = True
            record["team_slot"] = slots[0]
            if len(slots) > 1:
                record["team_slots"] = slots
            else:
                record.pop("team_slots", None)
        else:
            record["in_team"] = False
            record.pop("team_slot", None)
            record.pop("team_slots", None)


def _save_party_state(selected: str, team_data: dict, personal: dict, *, root: Path) -> dict:
    team_file = team_file_for_game(selected, root=root)
    personal_file = personal_file_for_game(selected, root=root)
    if team_file is None or personal_file is None:
        raise TeamError(f"Team management is not configured for {selected}.")
    _backup(team_file, root=root)
    _backup(personal_file, root=root)
    _save_json(team_file, team_data)
    _save_json(personal_file, personal)
    return _reconcile_for_display(team_data, personal)


def replace_team_slot(
    slot: int,
    local_id: int,
    game: str | None = None,
    *,
    root: Path = ROOT,
) -> dict:
    """Place an owned personal-Dex Pokemon into a party slot."""
    selected = game or active_game()
    slot = _slot(slot)
    if slot is None:
        raise TeamError("Team slot must be between 1 and 6.")

    team_file = team_file_for_game(selected, root=root)
    personal_file = personal_file_for_game(selected, root=root)
    if team_file is None or personal_file is None or not personal_file.exists():
        raise TeamError(f"No editable personal team data is available for {selected}.")

    team_data = load_team(selected, root=root)
    personal = _load_json(personal_file, default={"pokemon": []})
    record = next((row for row in personal.get("pokemon", []) if int(row.get("local_id", -1)) == int(local_id)), None)
    if record is None:
        raise TeamError(f"Personal Pokemon local_id {local_id} was not found.")
    try:
        owned_count = int(record.get("owned_count", 1 if record.get("caught") else 0) or 0)
    except (TypeError, ValueError):
        owned_count = 0
    if owned_count <= 0:
        raise TeamError(f"{record.get('species_name', 'That Pokemon')} is not currently owned.")

    members = [dict(row) for row in team_data.get("team", []) if _slot(row.get("slot"))]
    current_count = sum(1 for row in members if row.get("species_name") == record.get("species_name"))
    occupying = next((row for row in members if _slot(row.get("slot")) == slot), None)
    replacing_same_species = occupying is not None and occupying.get("species_name") == record.get("species_name")
    if current_count >= owned_count and not replacing_same_species:
        raise TeamError(f"All owned copies of {record.get('species_name')} are already in the party.")

    detail_source = next(
        (row for row in members if row.get("species_name") == record.get("species_name") and row is not occupying),
        None,
    )
    new_member = (
        _merge_basic_personal_fields(detail_source, record, slot)
        if detail_source
        else _member_from_record(record, slot)
    )
    members = [row for row in members if _slot(row.get("slot")) != slot]
    members.append(new_member)
    members.sort(key=lambda row: _slot(row.get("slot")) or 99)

    team_data["team"] = members
    team_data["snapshot_kind"] = "current_live_party"
    _sync_personal_flags(personal, members)
    return _save_party_state(selected, team_data, personal, root=root)


def remove_team_slot(slot: int, game: str | None = None, *, root: Path = ROOT) -> dict:
    """Remove one party slot while keeping the Pokemon owned in the personal Dex."""
    selected = game or active_game()
    slot = _slot(slot)
    if slot is None:
        raise TeamError("Team slot must be between 1 and 6.")
    personal_file = personal_file_for_game(selected, root=root)
    if personal_file is None or not personal_file.exists():
        raise TeamError(f"No editable personal team data is available for {selected}.")

    team_data = load_team(selected, root=root)
    personal = _load_json(personal_file, default={"pokemon": []})
    members = [dict(row) for row in team_data.get("team", []) if _slot(row.get("slot")) != slot]
    team_data["team"] = sorted(members, key=lambda row: _slot(row.get("slot")) or 99)
    team_data["snapshot_kind"] = "current_live_party"
    _sync_personal_flags(personal, team_data["team"])
    return _save_party_state(selected, team_data, personal, root=root)


def swap_team_slots(slot_a: int, slot_b: int, game: str | None = None, *, root: Path = ROOT) -> dict:
    """Swap/move party members between two slots and sync personal-Dex flags."""
    selected = game or active_game()
    a = _slot(slot_a)
    b = _slot(slot_b)
    if a is None or b is None:
        raise TeamError("Team slots must be between 1 and 6.")
    if a == b:
        return load_team(selected, root=root)

    personal_file = personal_file_for_game(selected, root=root)
    if personal_file is None or not personal_file.exists():
        raise TeamError(f"No editable personal team data is available for {selected}.")
    team_data = load_team(selected, root=root)
    personal = _load_json(personal_file, default={"pokemon": []})
    members = [dict(row) for row in team_data.get("team", []) if _slot(row.get("slot"))]
    member_a = next((row for row in members if _slot(row.get("slot")) == a), None)
    member_b = next((row for row in members if _slot(row.get("slot")) == b), None)
    if member_a is None and member_b is None:
        return team_data
    if member_a is not None:
        member_a["slot"] = b
    if member_b is not None:
        member_b["slot"] = a
    members.sort(key=lambda row: _slot(row.get("slot")) or 99)
    team_data["team"] = members
    team_data["snapshot_kind"] = "current_live_party"
    _sync_personal_flags(personal, members)
    return _save_party_state(selected, team_data, personal, root=root)


def team_summary(game: str | None = None, *, root: Path = ROOT) -> dict:
    data = load_team(game, root=root)
    members = list(data.get("team", []))
    known = [member for member in members if member.get("species_name")]
    return {
        "game": data.get("game", game or active_game()),
        "members": len(known),
        "slots": 6,
        "fainted": sum(
            1
            for member in known
            if str(member.get("status", "")).lower() == "fainted" or member.get("current_hp") == 0
        ),
        "with_level": sum(1 for member in known if member.get("level") is not None),
        "with_moves": sum(1 for member in known if member.get("moves")),
        "snapshot_kind": data.get("snapshot_kind"),
    }
