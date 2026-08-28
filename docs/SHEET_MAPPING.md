# Google Sheet Source Mapping

This document records the Google Sheets currently feeding the personal Pokédex schema.

## Core National/Regional Dex

**Pokemon DEX(Gen-1|Gen-9)**

- 2,824 rows
- 13 columns
- Includes generation/region groupings, Pokédex IDs, species names, image placeholders, and alternate regional forms such as Alolan forms.

## Personal caught/progress tracker

**Pokemon_Caught**

Tabs include:

- `let's go (Eevee/Pikachu)`
- `Brilliant diamond`
- `Pokemon (Violet/Scarlet)`
- `log`

The Scarlet/Violet tab tracks regional and DLC Pokédex totals plus fields including ID, name, Type1, Type2, Tera Type, caught state, obtain state, gym/town progress, Path of Legends, Elite Four, and Starfall Street.

## Brilliant Diamond

**Pokemon-(Brilliant_Diamond)**

Tabs include:

- `Pokemon`
- `LOG`
- hidden `Ribbons`

The Pokémon sheet has 70 columns and includes regional/national Dex state, species name, types, team membership, team slot, caught/obtain state, EV/stat fields, ability fields, and a large ribbon-tracking section.

## Sword

**Pokemon-(Sword)**

Tracks fields including local ID, Dex ID, name, Type1, Type2, caught state, total owned count, duplicate/threshold tracking, and battle counts.

## Other identified Pokémon sheets

- `Pokémon legend Arceus`
- `Pokemon_Type_Chart_Colored (2)`
- `Pokémon rules`
- `Pokemon world`
- `Pokemon Infinite`
- `Pokemon Uranium`

These will be normalized into the repo only after their useful fields are mapped.

## Import principle

Google Sheets remain the historical source material. Repo data should be normalized into stable JSON/schema files while preserving the original game-specific meaning of every field.
