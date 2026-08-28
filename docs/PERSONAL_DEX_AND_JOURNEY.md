# Personal Dex and Journey Data

Pokemon-DEX keeps three kinds of player data separate so the project can grow to many games without mixing unrelated information.

## Master Catalog

The master catalog describes Pokemon species and forms that exist in the database. It is not a record of what the player owns.

## My Dex

`src/pokemon_dex/my_dex.py` builds the player's caught-only Dex from the local files under `profiles/`.

A Pokemon appears in My Dex only when its profile record contains:

```json
"caught": true
```

My Dex provides:

- caught records across every local game profile
- unique caught species totals
- per-game caught totals
- per-game unique-species totals
- team-member counts when team flags are present
- complete-entry counts for games such as Pokemon Legends: Arceus

The touch UI exposes My Dex as its own tab and can filter the caught list by game.

## Journey Logs

Journey logs are stored separately from Pokemon ownership records. Files use the suffix:

```text
*_journey.json
```

They can track:

- trainer battles
- wins and losses
- named or explicitly unrecorded opponents
- story phase
- major progression milestones
- game-specific unlocks such as the Dynamax Band

The current Pokemon Sword journey log records the user's early-game trainer progress before receiving the Dynamax Band.

## Team Data

`src/pokemon_dex/team.py` reads an optional explicit team file. A caught Pokemon is not automatically assumed to be on the active team.

This keeps collection data and active-team data accurate even when the current team has not been entered yet.

## Offline Rule

All of these systems read local JSON only. They do not require an API, account login, network request, or token.
