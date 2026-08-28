# Live Play Tracking

Pokemon-DEX keeps live game progress in separate local profile files so a complete Pokédex catalog does not become tangled with one player's current save.

## Personal Pokémon

`profiles/<profile>/sword.json`

Stores Pokémon ownership/progress records such as caught state, owned count, team state, level, battles, form, catch location, and special encounter notes.

Live edits are handled by `pokemon_dex.editor`. Changed profile files are written atomically and copied to `profiles/_backups/` before replacement.

Nicknames are intentionally not part of the current workflow.

## Journey and trainer battles

`profiles/<profile>/sword_journey.json`

Stores story/checkpoint progress, milestones, trainer wins/losses, battle locations, and pending trainer identities separately from Pokémon ownership.

A milestone may be recorded as pending without being marked complete. For example, a player who is about to board a train can have `board_train` as the next step while `train_boarded` remains false.

## Routes / areas

`profiles/<profile>/sword_routes.json`

Each area can independently track:

- visited/current/complete state
- trainers defeated and trainer-check completion
- Pokémon caught in the area
- special encounters such as Brilliant Aura encounters
- possible/pending catches when the species is not yet confirmed
- Pokémon-check completion
- Pokémon Centers associated with the area and Center-check completion
- confirmed item pickups and item-check completion
- notes

`pokemon_dex.routes` provides safe local editing helpers for route check fields, Pokémon Centers, and items.

Unknown route totals, Center visits, and item pickups stay blank until confirmed rather than being guessed.

## Game wallet

`profiles/<profile>/sword_wallet.json`

The wallet is intentionally separate from journey and Pokémon records. It supports multiple in-game currencies:

- Poké Dollars
- Watts
- Battle Points

Balances may remain `null` until the player explicitly reports them or a value is extracted from a provided game screen/image.

`pokemon_dex.wallet` supports:

- exact balance setting
- earned/spent transactions
- purchases, trainer rewards, item sales, and corrections
- balance observations from manual reads or future screenshot extraction
- per-currency summaries
- automatic backup-before-write

The wallet screen is touch/mouse-first. It includes quick +/- controls and an on-screen numeric keypad for exact balance entry.

## App home

Normal startup opens a touch/mouse-first home screen with two main areas:

- **Pokédex / Progress** — My Dex, routes, journey, battles, system status
- **Game Wallet** — in-game currency balances and ledger

The app remains offline. No runtime API, account token, or online service is required.
