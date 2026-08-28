"""Offline badge tracking for personal Pokemon game progress."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"
DEFAULT_BADGES = PROFILE_ROOT / "JacobS-Dev-1" / "sword_badges.json"


class BadgeError(RuntimeError):
    """Raised when badge data cannot be read or saved safely."""


def _safe_path(path: Path = DEFAULT_BADGES) -> Path:
    candidate = path.resolve()
    profile_root = PROFILE_ROOT.resolve()
    if profile_root not in candidate.parents or not candidate.name.endswith("_badges.json"):
        raise BadgeError("Badge edits are limited to profile *_badges.json files.")
    return candidate


def _load(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise BadgeError(f"Could not read badge file: {path.name}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("badges"), list):
        raise BadgeError("Badge file is missing its badges list.")
    return data


def _backup(path: Path) -> None:
    backup_dir = PROFILE_ROOT / "_backups" / path.parent.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, backup_dir / f"{path.name}.{stamp}.bak")


def _save(path: Path, data: dict) -> None:
    data["summary"] = {
        "obtained": sum(1 for badge in data.get("badges", []) if badge.get("obtained")),
        "total": len(data.get("badges", [])),
    }
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def load_badges(path: Path = DEFAULT_BADGES) -> dict:
    return _load(_safe_path(path))


def badge_summary(path: Path = DEFAULT_BADGES) -> dict:
    data = load_badges(path)
    badges = data.get("badges", [])
    return {
        "game": data.get("game"),
        "obtained": sum(1 for badge in badges if badge.get("obtained")),
        "total": len(badges),
        "next_badge": next((badge for badge in badges if not badge.get("obtained")), None),
    }


def set_badge_obtained(badge_id: str, obtained: bool, path: Path = DEFAULT_BADGES) -> dict:
    path = _safe_path(path)
    data = _load(path)
    target = next((badge for badge in data.get("badges", []) if badge.get("badge_id") == badge_id), None)
    if target is None:
        raise BadgeError(f"Unknown badge id: {badge_id}")
    obtained = bool(obtained)
    if bool(target.get("obtained")) == obtained:
        return target
    target["obtained"] = obtained
    _backup(path)
    _save(path, data)
    return target


def toggle_badge(badge_id: str, path: Path = DEFAULT_BADGES) -> dict:
    data = load_badges(path)
    target = next((badge for badge in data.get("badges", []) if badge.get("badge_id") == badge_id), None)
    if target is None:
        raise BadgeError(f"Unknown badge id: {badge_id}")
    return set_badge_obtained(badge_id, not bool(target.get("obtained")), path)
