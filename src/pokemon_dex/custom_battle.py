"""Asymmetric local battle formats for Pokemon-DEX sandbox simulations.

This module is deliberately separate from the normal Sword journey log. It can
simulate formats the retail game does not normally offer, including true 1v3
and other uneven simultaneous battles.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pokemon_dex.battle import BattlePokemon, _choose_move, _damage, _effectiveness_text, load_trainers

ROOT = Path(__file__).resolve().parents[2]
PLAYER_TEAM_FILE = ROOT / "profiles" / "JacobS-Dev-1" / "sword_team.json"
OPPONENTS_FILE = ROOT / "profiles" / "JacobS-Dev-1" / "sword_opponents.json"


@dataclass
class MultiBattleState:
    player_name: str
    enemy_name: str
    player_team: list[BattlePokemon]
    enemy_team: list[BattlePokemon]
    player_active_count: int = 1
    enemy_active_count: int = 3
    round_number: int = 1
    log: list[str] = field(default_factory=list)
    winner: str | None = None
    format_name: str = "1v3"

    def active_players(self) -> list[tuple[int, BattlePokemon]]:
        living = [(i, p) for i, p in enumerate(self.player_team) if not p.fainted]
        return living[: self.player_active_count]

    def active_enemies(self) -> list[tuple[int, BattlePokemon]]:
        living = [(i, p) for i, p in enumerate(self.enemy_team) if not p.fainted]
        return living[: self.enemy_active_count]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _move_ids(raw_moves: list[dict] | list[str] | None) -> list[str]:
    result: list[str] = []
    for raw in raw_moves or []:
        name = raw.get("name") if isinstance(raw, dict) else raw
        if name:
            result.append(str(name).strip().lower().replace(" ", "-"))
    return result or ["tackle"]


def _player_pokemon(raw: dict) -> BattlePokemon:
    level = int(raw.get("level") or 5)
    stats = raw.get("stats") or {}
    max_hp = int(raw.get("max_hp") or stats.get("hp") or (18 + level))
    attack = int(stats.get("attack") or (8 + level))
    defense = int(stats.get("defense") or (8 + level))
    sp_attack = int(stats.get("sp_attack") or attack)
    sp_defense = int(stats.get("sp_defense") or defense)
    speed = int(stats.get("speed") or (8 + level))
    types = [value for value in (raw.get("type_1"), raw.get("type_2")) if value]
    if not types:
        fallback_types = {
            "Scorbunny": ["Fire"],
            "Rookidee": ["Flying"],
            "Blipbug": ["Bug"],
            "Skwovet": ["Normal"],
            "Chewtle": ["Water"],
        }
        types = fallback_types.get(str(raw.get("species_name")), ["Normal"])
    return BattlePokemon(
        species_name=str(raw.get("species_name", "Unknown")),
        level=level,
        max_hp=max_hp,
        hp=int(raw.get("current_hp") if raw.get("current_hp") is not None else max_hp),
        attack=attack,
        defense=defense,
        special_attack=sp_attack,
        special_defense=sp_defense,
        speed=speed,
        types=types,
        moves=_move_ids(raw.get("moves")),
    )


def load_live_player_team(limit: int | None = None) -> tuple[str, list[BattlePokemon]]:
    data = _read_json(PLAYER_TEAM_FILE)
    raw_team = list(data.get("team", []))
    if limit is not None:
        raw_team = raw_team[: max(1, limit)]
    return str(data.get("trainer_name", "Player")), [_player_pokemon(raw) for raw in raw_team]


def _confirmed_opponent_pool() -> list[BattlePokemon]:
    pool: list[BattlePokemon] = []

    # Reuse the existing configured training opponent first.
    trainers = load_trainers()
    for trainer in trainers:
        if trainer.trainer_class != "Player":
            pool.extend(trainer.team)

    # Then add confirmed live opponent roster entries such as Lass Lauren.
    data = _read_json(OPPONENTS_FILE)
    for opponent in data.get("opponents", []):
        if opponent.get("roster_status") != "confirmed":
            continue
        for raw in opponent.get("roster", []):
            level = int(raw.get("level") or 5)
            species = str(raw.get("species_name", "Opponent Pokemon"))
            type_map = {"Chewtle": "Water", "Rookidee": "Flying", "Yamper": "Electric"}
            pool.append(
                BattlePokemon(
                    species_name=species,
                    level=level,
                    max_hp=18 + level,
                    attack=8 + level,
                    defense=8 + level,
                    speed=8 + level,
                    types=[type_map.get(species, "Normal")],
                    moves=["tackle"],
                )
            )
    return pool


def _attack(log: list[str], attacker: BattlePokemon, defender: BattlePokemon, prefix: str = "") -> None:
    move = _choose_move(attacker)
    damage, effectiveness, _ = _damage(attacker, defender, move)
    defender.hp = max(0, int(defender.hp or 0) - damage)
    extra = _effectiveness_text(effectiveness)
    log.append(f"{prefix}{attacker.species_name} used {move.name} on {defender.species_name} for {damage} damage. {extra}".strip())
    if defender.fainted:
        log.append(f"{defender.species_name} fainted!")


def perform_multi_round(state: MultiBattleState) -> MultiBattleState:
    """Resolve one simultaneous round in deterministic Speed order."""
    if state.winner:
        return state

    player_active = state.active_players()
    enemy_active = state.active_enemies()
    if not player_active:
        state.winner = state.enemy_name
        return state
    if not enemy_active:
        state.winner = state.player_name
        return state

    actors: list[tuple[int, int, str, BattlePokemon]] = []
    for index, pokemon in player_active:
        actors.append((-pokemon.speed, 0, "player", pokemon))
    for index, pokemon in enemy_active:
        actors.append((-pokemon.speed, 1, "enemy", pokemon))
    actors.sort(key=lambda item: (item[0], item[1]))

    first_action = True
    for _, _, side, attacker in actors:
        if attacker.fainted:
            continue
        if side == "player":
            targets = [pokemon for _, pokemon in state.active_enemies() if not pokemon.fainted]
        else:
            targets = [pokemon for _, pokemon in state.active_players() if not pokemon.fainted]
        if not targets:
            break
        prefix = f"Round {state.round_number}: " if first_action else ""
        _attack(state.log, attacker, targets[0], prefix)
        first_action = False

    if not state.active_players():
        state.winner = state.enemy_name
        state.log.append(f"{state.enemy_name} wins the custom battle!")
    elif not state.active_enemies():
        state.winner = state.player_name
        state.log.append(f"{state.player_name} wins the custom battle!")

    state.round_number += 1
    return state


def new_custom_battle(player_count: int = 1, enemy_count: int = 3) -> MultiBattleState | None:
    """Create an uneven simultaneous sandbox battle such as 1v3."""
    player_count = max(1, min(3, int(player_count)))
    enemy_count = max(1, min(3, int(enemy_count)))
    player_name, player_team = load_live_player_team(limit=player_count)
    enemy_pool = _confirmed_opponent_pool()[:enemy_count]
    if not player_team or not enemy_pool:
        return None
    return MultiBattleState(
        player_name=player_name,
        enemy_name="Custom Opponents",
        player_team=player_team,
        enemy_team=enemy_pool,
        player_active_count=player_count,
        enemy_active_count=enemy_count,
        format_name=f"{player_count}v{enemy_count}",
        log=[f"Custom {player_count}v{enemy_count} sandbox battle ready."],
    )
