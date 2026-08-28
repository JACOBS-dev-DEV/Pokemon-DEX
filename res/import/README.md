# Import Staging

This directory is the offline staging area for data and assets before they are normalized into Pokemon-DEX.

## Rules

- No external API is required.
- Raw spreadsheets, JSON exports, text exports, and art packs may be staged here locally.
- Do not treat staged files as canonical database records until they pass validation/import.
- Keep source/provenance information whenever possible.
- Large binary archives may be kept outside Git and referenced by an import manifest when appropriate.

## Suggested local staging folders

- `spreadsheets/`
- `art_packs/`
- `profiles/`
- `manual/`

The importer/validator code under `src/pokemon_dex/` should read from this staging area and write normalized data to `res/data/`, `res/profiles/`, and `res/art/`.
