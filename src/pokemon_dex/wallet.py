"""Offline game-currency tracking for Pokemon-DEX.

This module tracks in-game currencies only. Wallet files live beside personal
save data under profiles/, are written atomically, and are backed up before
changed saves. Unknown balances remain None until explicitly observed.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = ROOT / "profiles"
DEFAULT_WALLET = PROFILE_ROOT / "JacobS-Dev-1" / "sword_wallet.json"


class WalletError(RuntimeError):
    """Raised when a wallet read/write request cannot be applied safely."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_path(path: Path = DEFAULT_WALLET, *, root: Path = ROOT) -> Path:
    root = root.resolve()
    profile_root = (root / "profiles").resolve()
    candidate = path if path.is_absolute() else root / path
    candidate = candidate.resolve()
    if profile_root not in candidate.parents or not candidate.name.endswith("_wallet.json"):
        raise WalletError("Wallet edits are limited to profile *_wallet.json files.")
    return candidate


def _load(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise WalletError(f"Could not read wallet file: {path.name}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("wallet"), dict):
        raise WalletError("Wallet file is missing its wallet object.")
    data.setdefault("transactions", [])
    data.setdefault("balance_observations", [])
    return data


def _backup(path: Path, *, root: Path) -> Path:
    backup_dir = root / "profiles" / "_backups" / path.parent.name
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, backup)
    return backup


def _atomic_write(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise WalletError(f"Could not save wallet file: {path.name}") from exc


def _amount_value(transaction: dict) -> int:
    """Return a safe signed amount; balance observations may legitimately be None."""
    value = transaction.get("amount")
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_wallet(path: Path = DEFAULT_WALLET, *, root: Path = ROOT) -> dict:
    """Load one local game wallet without changing it."""
    path = _safe_path(path, root=root)
    return _load(path)


def wallet_summary(path: Path = DEFAULT_WALLET, *, root: Path = ROOT) -> dict:
    """Return balances and compact ledger totals for display."""
    data = load_wallet(path, root=root)
    transactions = data.get("transactions", [])
    earned = sum(max(0, _amount_value(tx)) for tx in transactions)
    spent = sum(abs(min(0, _amount_value(tx))) for tx in transactions)
    per_currency: dict[str, dict] = {}
    for currency, value in data.get("wallet", {}).items():
        currency_transactions = [tx for tx in transactions if tx.get("currency") == currency]
        per_currency[currency] = {
            "display_name": value.get("display_name", currency),
            "symbol": value.get("symbol", ""),
            "balance": value.get("balance"),
            "earned": sum(max(0, _amount_value(tx)) for tx in currency_transactions),
            "spent": sum(abs(min(0, _amount_value(tx))) for tx in currency_transactions),
            "transactions": len(currency_transactions),
        }
    return {
        "profile_id": data.get("profile_id"),
        "game": data.get("game"),
        "currencies": per_currency,
        "transactions": len(transactions),
        "earned_total": earned,
        "spent_total": spent,
        "observations": len(data.get("balance_observations", [])),
    }


def set_balance(
    currency: str,
    balance: int,
    *,
    reason: str = "manual balance set",
    location: str | None = None,
    path: Path = DEFAULT_WALLET,
    root: Path = ROOT,
) -> dict:
    """Set an exact observed balance and save a correction transaction."""
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    if currency not in data["wallet"]:
        raise WalletError(f"Unknown wallet currency: {currency}")
    try:
        new_balance = max(0, int(balance))
    except (TypeError, ValueError) as exc:
        raise WalletError("Balance must be a whole number.") from exc

    old_balance = data["wallet"][currency].get("balance")
    if old_balance == new_balance:
        return data

    data["wallet"][currency]["balance"] = new_balance
    data["transactions"].append(
        {
            "timestamp": _timestamp(),
            "currency": currency,
            "kind": "balance_correction" if old_balance is not None else "initial_balance",
            "amount": None if old_balance is None else new_balance - int(old_balance),
            "balance_before": old_balance,
            "balance_after": new_balance,
            "reason": reason,
            "location": location,
        }
    )
    _backup(path, root=root)
    _atomic_write(path, data)
    return data


def add_transaction(
    currency: str,
    amount: int,
    *,
    kind: str,
    reason: str,
    location: str | None = None,
    item: str | None = None,
    source: str = "manual",
    path: Path = DEFAULT_WALLET,
    root: Path = ROOT,
) -> dict:
    """Add earned/spent currency. Positive amounts earn; negative amounts spend."""
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    if currency not in data["wallet"]:
        raise WalletError(f"Unknown wallet currency: {currency}")
    try:
        amount = int(amount)
    except (TypeError, ValueError) as exc:
        raise WalletError("Transaction amount must be a whole number.") from exc
    if amount == 0:
        raise WalletError("Transaction amount cannot be zero.")

    before = data["wallet"][currency].get("balance")
    after = None if before is None else max(0, int(before) + amount)
    applied_amount = amount if before is None else after - int(before)
    if before is not None:
        data["wallet"][currency]["balance"] = after

    data["transactions"].append(
        {
            "timestamp": _timestamp(),
            "currency": currency,
            "kind": str(kind),
            "amount": applied_amount,
            "requested_amount": amount,
            "balance_before": before,
            "balance_after": after,
            "reason": str(reason),
            "location": location,
            "item": item,
            "source": str(source),
        }
    )
    _backup(path, root=root)
    _atomic_write(path, data)
    return data


def adjust_balance(
    currency: str,
    amount: int,
    *,
    reason: str = "live adjustment",
    path: Path = DEFAULT_WALLET,
    root: Path = ROOT,
) -> dict:
    """Convenience wrapper for touch controls that add/subtract currency."""
    kind = "earned" if int(amount) > 0 else "spent"
    return add_transaction(currency, amount, kind=kind, reason=reason, path=path, root=root)


def record_balance_observation(
    currency: str,
    observed_balance: int,
    *,
    source: str,
    source_ref: str | None = None,
    confidence: float | None = None,
    apply: bool = True,
    location: str | None = None,
    path: Path = DEFAULT_WALLET,
    root: Path = ROOT,
) -> dict:
    """Store a balance read from a screen/image/manual observation.

    This is the handoff point for future screenshot extraction. The extraction
    process can supply the digits here without needing to understand wallet
    persistence or reconciliation.
    """
    root = root.resolve()
    path = _safe_path(path, root=root)
    data = _load(path)
    if currency not in data["wallet"]:
        raise WalletError(f"Unknown wallet currency: {currency}")
    try:
        observed_balance = max(0, int(observed_balance))
    except (TypeError, ValueError) as exc:
        raise WalletError("Observed balance must be a whole number.") from exc
    if confidence is not None:
        confidence = min(1.0, max(0.0, float(confidence)))

    observation = {
        "timestamp": _timestamp(),
        "currency": currency,
        "observed_balance": observed_balance,
        "source": str(source),
        "source_ref": source_ref,
        "confidence": confidence,
        "location": location,
        "applied": bool(apply),
    }
    data["balance_observations"].append(observation)

    before = data["wallet"][currency].get("balance")
    if apply:
        data["wallet"][currency]["balance"] = observed_balance
        data["transactions"].append(
            {
                "timestamp": observation["timestamp"],
                "currency": currency,
                "kind": "observed_balance",
                "amount": None if before is None else observed_balance - int(before),
                "balance_before": before,
                "balance_after": observed_balance,
                "reason": f"Balance observation from {source}",
                "location": location,
                "source_ref": source_ref,
            }
        )

    _backup(path, root=root)
    _atomic_write(path, data)
    return data
