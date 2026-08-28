# Pokemon-DEX Data Sources

Pokemon-DEX separates canonical game data from personal/custom artwork.

## Canonical Pokemon data

Primary community source: PokéAPI / PokéAPI data repositories.

Use this lane for facts such as:
- National Dex number
- species name
- forms
- types
- abilities
- base stats
- height and weight
- generation
- game availability
- evolution relationships

The repository should store a local snapshot after import so the application does not require a network connection during normal use.

## Standard sprites / official-artwork mirror

PokéAPI's public sprites repository contains front sprites and additional artwork sets, including an `official-artwork` area. Pokemon image content remains copyright The Pokémon Company; keep the upstream license/disclaimer with any mirrored assets.

Recommended repository destination:

`res/art/canonical/<national_dex>/<form>/`

## JacobS archive artwork

The uploaded Pokemon Art Project archive is a separate personal/custom source. Keep it isolated from canonical artwork so files can be replaced or reorganized without touching the Pokédex records.

Recommended destination:

`res/art/archive/<pokemon>/`

Clean transparent trace images should be preferred for the main display asset. Raw downloads, reference images, duplicates, PDFs, and source material should remain in an archive/source area rather than becoming the default Pokédex art.

## Profile layout

Each Pokémon receives one canonical profile JSON file:

`res/profiles/<national_dex>-<slug>/profile.json`

Personal ownership/caught/team/save-game information remains separate under:

`profiles/JacobS-Dev-1/`

This prevents canonical Pokémon facts from being mixed with JacobS's save-specific data.
