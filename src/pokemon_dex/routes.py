"""Local route/area checklist support for complete Pokédex progress tracking."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"


def load_route_logs() -> list[dict]:
    logs: list[dict] = []
    if not PROFILE_ROOT.exists():
        return logs
    for path in sorted(PROFILE_ROOT.rglob("*_routes.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        data["_source_file"] = path.relative_to(ROOT).as_posix()
        logs.append(data)
    return logs


def all_areas() -> list[dict]:
    areas: list[dict] = []
    for log in load_route_logs():
        for raw in log.get("areas", []):
            area = dict(raw)
            area["game"] = log.get("game", "Unknown Game")
            area["profile_id"] = log.get("profile_id")
            area["source_file"] = log.get("_source_file")
            areas.append(area)
    return areas


def route_summary() -> dict:
    areas = all_areas()
    return {
        "areas": len(areas),
        "visited": sum(1 for area in areas if area.get("visited")),
        "complete": sum(1 for area in areas if area.get("complete")),
        "trainers_defeated": sum(int(area.get("trainers_defeated") or 0) for area in areas),
        "pokemon_caught": sum(len(area.get("pokemon_caught", [])) for area in areas),
        "pokemon_centers": sum(len(area.get("pokemon_centers", [])) for area in areas),
        "items_found": sum(len(area.get("items_found", [])) for area in areas),
        "center_checks_complete": sum(1 for area in areas if area.get("pokemon_center_check_complete")),
        "item_checks_complete": sum(1 for area in areas if area.get("items_check_complete")),
    }


def _safe_path(source_file: str) -> Path:
    path = (ROOT / source_file).resolve()
    profile_root = PROFILE_ROOT.resolve()
    if profile_root not in path.parents or not path.name.endswith("_routes.json"):
        raise ValueError("Route edits are limited to profile *_routes.json files.")
    return path


def _backup(path: Path) -> None:
    backup_dir = PROFILE_ROOT / "_backups" / path.parent.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, backup_dir / f"{path.name}.{stamp}.bak")


def _save(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)
    except OSError:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _find_area(data: dict, area_id: str) -> dict:
    for raw in data.get("areas", []):
        if raw.get("area_id") == area_id:
            return raw
    raise ValueError("Route area was not found in its source file.")


def _load_target(area: dict) -> tuple[Path, dict, dict]:
    path = _safe_path(str(area.get("source_file", "")))
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    target = _find_area(data, str(area.get("area_id", "")))
    return path, data, target


def _result(path: Path, data: dict, target: dict) -> dict:
    result = dict(target)
    result["game"] = data.get("game", "Unknown Game")
    result["profile_id"] = data.get("profile_id")
    result["source_file"] = path.relative_to(ROOT).as_posix()
    return result


def update_area(area: dict, updates: dict) -> dict:
    """Update route completion/check fields and save them locally with a backup."""
    path, data, target = _load_target(area)
    allowed = {
        "visited",
        "current",
        "complete",
        "trainers_defeated",
        "trainer_check_complete",
        "pokemon_check_complete",
        "pokemon_center_check_complete",
        "items_check_complete",
        "notes",
    }
    boolean_fields = {
        "visited",
        "current",
        "complete",
        "trainer_check_complete",
        "pokemon_check_complete",
        "pokemon_center_check_complete",
        "items_check_complete",
    }
    changed = False
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key == "trainers_defeated":
            value = max(0, int(value))
        elif key in boolean_fields:
            value = bool(value)
        else:
            value = str(value)
        if target.get(key) != value:
            target[key] = value
            changed = True

    if target.get("complete"):
        target["visited"] = True
    if changed:
        _backup(path)
        _save(path, data)
    return _result(path, data, target)


def add_pokemon_center(area: dict, name: str, *, visited: bool = True, notes: str = "") -> dict:
    """Add or update a Pokémon Center entry for an area without inventing progress."""
    path, data, target = _load_target(area)
    centers = target.setdefault("pokemon_centers", [])
    existing = next((center for center in centers if str(center.get("name", "")).casefold() == str(name).casefold()), None)
    if existing is None:
        centers.append({"name": str(name), "visited": bool(visited), "notes": str(notes)})
    else:
        existing["visited"] = bool(visited)
        if notes:
            existing["notes"] = str(notes)
    _backup(path)
    _save(path, data)
    return _result(path, data, target)


def add_item(
    area: dict,
    item_name: str,
    *,
    quantity: int = 1,
    source: str = "field",
    collected: bool = True,
    notes: str = "",
) -> dict:
    """Add a confirmed item pickup/find to an area's item checklist."""
    path, data, target = _load_target(area)
    items = target.setdefault("items_found", [])
    item = {
        "name": str(item_name),
        "quantity": max(1, int(quantity)),
        "source": str(source),
        "collected": bool(collected),
        "notes": str(notes),
    }
    items.append(item)
    _backup(path)
    _save(path, data)
    return _result(path, data, target)
