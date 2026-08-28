# JacobS Personal Pokédex

This repository is the source-controlled home for JacobS/Dev's personal Pokémon database and Pokédex.

## Purpose

The project combines canonical Pokédex structure with personal game/profile tracking pulled from JacobS's Google Sheets. It is designed to preserve game-specific progress instead of flattening everything into a generic species list.

## Data tracked

- National and regional Pokédex identifiers
- Species names and alternate forms
- Types and game-specific typing fields
- Caught / obtained status
- Team membership and team slots
- EV/stat records
- Abilities
- Ribbons
- Battle counts
- Story and gym progress
- Scarlet/Violet DLC Pokédex progress
- Game-specific records for titles such as Sword, Brilliant Diamond, Legends: Arceus, Let's Go, Scarlet, and Violet
- Artwork, sprites, and trace-template assets

## Repository layout

- `database/` — normalized Pokémon reference data
- `profiles/JacobS-Dev-1/` — personal Pokémon/profile records
- `games/` — game-specific schemas and progress
- `assets/` — sprite/artwork intake and manifests
- `data/` — machine-readable JSON datasets
- `docs/` — schema and source mapping documentation

## Source of truth

The initial schema is derived from JacobS's existing Google Sheets, including the Gen 1–9 Dex, Pokémon Caught tracker, Sword tracker, Brilliant Diamond tracker, Legends: Arceus data, type charts, and rules sheets.

This repo started by repurposing the previously empty `New-Era` repository.
