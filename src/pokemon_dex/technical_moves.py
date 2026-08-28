"""Safe local TM/TR inventory tracking for Pokemon Sword/Shield.

Sword/Shield TMs are reusable. TRs are single-use and are consumed one copy at
a time. This module keeps those mechanics separate so the UI can safely track
obtained copies and use history without treating TMs as consumables.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"
DEFAULT_FILE = PROFILE_ROOT / "JacobS-Dev-1" / "sword_technical_moves.json"


class TechnicalMoveError(RuntimeError):
    """Raised when a TM/TR tracking operation cannot be applied safely."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_path(path: Path = DEFAULT_FILE, *, root: Path = ROOT) -> Path:
    root = root.resolve()
    profile_root = (root / "profiles").resolve()
    candidate = path if path.is_absolute() else root / path
    candidate = candidate.resolve()
    if profile_root not in candidate.parents or not candidate.name.endswith("_technical_moves.json"):
        raise TechnicalMoveError("TM/TR edits are limited to profile *_technical_moves.json files.")
    return candidate


def _load(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise TechnicalMoveError(f"Could not read TM/TR file: {path.name}") from exc
    data.setdefault("inventory", {}).setdefault("tms", [])
    data.setdefault("inventory", {}).setdefault("trs", [])
    data.setdefault("use_history", [])
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
        raise TechnicalMoveError(f"Could not save TM/TR file: {path.name}") from exc


def _kind_parts(kind: str) -> tuple[str, str]:
    value = str(kind).strip().lower()
    if value == "tm":
        return "tms", "TM"
    if value == "tr":
        return "trs", "TR"
    raise TechnicalMoveError("Technical move kind must be TM or TR.")


def _number(value: int | str) -> int:
    try:
        number = int(str(value).upper().replace("TM", "").replace("TR", ""))
    except (TypeError, ValueError) as exc:
        raise TechnicalMoveError("TM/TR number must be between 00 and 99.") from exc
    if not 0 <= number <= 99:
        raise TechnicalMoveError("TM/TR number must be between 00 and 99.")
    return number


def load_tracker(path: Path = DEFAULT_FILE, *, root: Path = ROOT) -> dict:
    return _load(_safe_path(path, root=root))


def tracker_summary(path: Path = DEFAULT_FILE, *, root: Path = ROOT) -> dict:
    data = load_tracker(path, root=root)
    tms = data["inventory"]["tms"]
    trs = data["inventory"]["trs"]
    return {
        "tms_obtained": len(tms),
        "trs_obtained": len(trs),
        "tr_copies_remaining": sum(max(0, int(item.get("quantity", 0))) for item in trs),
        "uses_logged": len(data.get("use_history", [])),
    }


def record_obtained(
    kind: str,
    number: int | str,
    *,
    move: str | None = None,
    quantity: int = 1,
    location: str | None = None,
    source: str = "manual",
    path: Path = DEFAULT_FILE,
    root: Path = ROOT,
) -> dict:
    """Record an obtained TM or one/more copies of a TR."""
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    bucket, prefix = _kind_parts(kind)
    num = _number(number)
    quantity = max(1, int(quantity))
    entry = next((item for item in data["inventory"][bucket] if int(item.get("number", -1)) == num), None)

    if entry is None:
        entry = {
            "number": num,
            "code": f"{prefix}{num:02d}",
            "move": move,
            "obtained": true,
            "quantity": 1 if prefix == "TM" else quantity,
            "obtained_location": location,
            "source": source,
        }
        data["inventory"][bucket].append(entry)
    else:
        entry["obtained"] = True
        if move:
            entry["move"] = move
        if location:
            entry["obtained_location"] = location
        if prefix == "TR":
            entry["quantity"] = max(0, int(entry.get("quantity", 0))) + quantity
        else:
            entry["quantity"] = 1

    data["inventory"][bucket].sort(key=lambda item: int(item.get("number", 999)))
    _backup(path, root=root)
    _save(path, data)
    return data


def record_use(
    kind: str,
    number: int | str,
    *,
    pokemon: str,
    move: str | None = None,
    notes: str | None = None,
    path: Path = DEFAULT_FILE,
    root: Path = ROOT,
) -> dict:
    """Log a TM/TR use. TR use consumes one copy; TM use never does."""
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    bucket, prefix = _kind_parts(kind)
    num = _number(number)
    entry = next((item for item in data["inventory"][bucket] if int(item.get("number", -1)) == num), None)
    if entry is None or not entry.get("obtained"):
        raise TechnicalMoveError(f"{prefix}{num:02d} is not marked as obtained.")

    before = int(entry.get("quantity", 1 if prefix == "TM" else 0))
    if prefix == "TR":
        if before <= 0:
            raise TechnicalMoveError(f"No copies of TR{num:02d} remain.")
        entry["quantity"] = before - 1
    else:
        entry["quantity"] = 1

    data["use_history"].append(
        {
            "timestamp": _timestamp(),
            "kind": prefix,
            "number": num,
            "code": f"{prefix}{num:02d}",
            "move": move or entry.get("move"),
            "pokemon": str(pokemon),
            "consumed": prefix == "TR",
            "quantity_before": before,
            "quantity_after": entry.get("quantity"),
            "notes": notes,
        }
    )
    _backup(path, root=root)
    _save(path, data)
    return data
