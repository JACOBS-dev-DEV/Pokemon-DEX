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
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def update_area(area: dict, updates: dict) -> dict:
    path = _safe_path(str(area.get("source_file", "")))
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    target = None
    for raw in data.get("areas", []):
        if raw.get("area_id") == area.get("area_id"):
            target = raw
            break
    if target is None:
        raise ValueError("Route area was not found in its source file.")

    allowed = {
        "visited", "current", "complete", "trainers_defeated",
        "trainer_check_complete", "pokemon_check_complete", "items_check_complete", "notes"
    }
    changed = False
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key == "trainers_defeated":
            value = max(0, int(value))
        elif key in {"visited", "current", "complete", "trainer_check_complete", "pokemon_check_complete", "items_check_complete"}:
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
    result = dict(target)
    result["game"] = data.get("game", "Unknown Game")
    result["profile_id"] = data.get("profile_id")
    result["source_file"] = path.relative_to(ROOT).as_posix()
    return result
