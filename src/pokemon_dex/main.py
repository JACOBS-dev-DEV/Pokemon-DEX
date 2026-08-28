"""Linux entry point for Pokemon-DEX."""

from __future__ import annotations

import sys
from pathlib import Path

# Support both direct execution from VS Code (python src/pokemon_dex/main.py)
# and normal package execution (python -m pokemon_dex.main / installed script).
if __package__ in {None, ""}:
    SRC_DIR = Path(__file__).resolve().parents[1]
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

from pokemon_dex import build_indexes, validate_database
from pokemon_dex.database import get_status


def _print_status() -> None:
    status = get_status()
    print("\nPokemon-DEX local status")
    print("------------------------")
    print(f"Database version:       {status.database_version}")
    print(f"Canonical profiles:     {status.canonical_profiles}")
    print(f"Personal profile files: {status.personal_profile_files}")
    print(f"Indexed profile files:  {status.indexed_pokemon}")
    print(f"Indexed art assets:     {status.indexed_art_assets}")
    print(f"Art files on disk:      {status.art_files}")
    print(f"Registered games:       {status.games}")
    print(f"Registered Dexes:       {status.dexes}")
    print(f"Registered forms:       {status.forms}")
    print("Network/API dependency: none")


def main() -> int:
    """Start Pokemon-DEX and verify all local database connections."""
    print("Pokemon-DEX starting in offline mode...")
    build_indexes.main()
    validation_code = validate_database.main()
    _print_status()

    if validation_code:
        print("\nPokemon-DEX started with validation errors.")
        return validation_code

    print("\nPokemon-DEX is connected and ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
