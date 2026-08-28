#!/usr/bin/env python3
"""Import cleaned Pokémon artwork from a Pokemon_Art_Project ZIP.

Normal operation is offline. This script reads a local archive and copies the
clean transparent trace images into res/art/archive/<pokemon>/.
"""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

TRACE_MARKER = "/05_Trace_Templates/"
TRANSPARENT_MARKER = "_Trace_Transparent"
SKIP_DIRS = {
    "Poke_Ball_Reference",
    "Transparent_Background",
    "Koraidon_and_Miraidon",
}


def normalize_slug(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def import_archive(archive: Path, repo_root: Path) -> tuple[int, int]:
    output_root = repo_root / "res" / "art" / "archive"
    output_root.mkdir(parents=True, exist_ok=True)

    pokemon_count: set[str] = set()
    file_count = 0

    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if info.is_dir() or TRACE_MARKER not in info.filename:
                continue
            if TRANSPARENT_MARKER not in info.filename:
                continue

            relative = info.filename.split(TRACE_MARKER, 1)[1]
            parts = relative.split("/")
            if len(parts) < 2:
                continue

            pokemon = parts[0]
            if pokemon in SKIP_DIRS:
                continue

            pokemon_slug = normalize_slug(pokemon)
            filename = Path(parts[-1]).name
            destination_dir = output_root / pokemon_slug
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / filename

            with zf.open(info) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)

            pokemon_count.add(pokemon_slug)
            file_count += 1

    return len(pokemon_count), file_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path, help="Path to Pokemon_Art_Project.zip")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Pokemon-DEX repository root",
    )
    args = parser.parse_args()

    pokemon, files = import_archive(args.archive.resolve(), args.repo_root.resolve())
    print(f"Imported {files} transparent artwork files for {pokemon} Pokémon.")


if __name__ == "__main__":
    main()
