"""Offline trainer and battle engine for Pokemon-DEX."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINERS_FILE = ROOT / "res" / "data" / "trainers" / "trainers.json"


@dataclass
class BattlePokemon:
    species_name: str
    level: int = 5
    max_hp: int = 20
    attack: int = 10
    defense: int = 10
    hp: int | None = None

    def __post_init__(self) -> None:
        if self.hp is None:
            self.hp = self.max_hp

    @property
    def fainted(self) -> bool:
        return bool(self.hp is not None and self.hp <= 0)


@dataclass
class Trainer:
    trainer_id: str
    name: str
    trainer_class: str = "Trainer"
    game_mode: str = "standard"
    team: list[BattlePokemon] = field(default_factory=list)


@dataclass
class BattleState:
    trainer_a: Trainer
    trainer_b: Trainer
    active_a: int = 0
    active_b: int = 0
    turn: int = 1
    log: list[str] = field(default_factory=list)
    winner: str | None = None

    def active_pair(self) -> tuple[BattlePokemon, BattlePokemon]:
        return self.trainer_a.team[self.active_a], self.trainer_b.team[self.active_b]


def load_trainers() -> list[Trainer]:
    if not TRAINERS_FILE.exists():
        return []
    with TRAINERS_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    trainers: list[Trainer] = []
    for raw in data.get("trainers", []):
        team = [BattlePokemon(**pokemon) for pokemon in raw.get("team", [])]
        trainers.append(
            Trainer(
                trainer_id=raw.get("trainer_id", "trainer"),
                name=raw.get("name", "Trainer"),
                trainer_class=raw.get("trainer_class", "Trainer"),
                game_mode=raw.get("game_mode", "standard"),
                team=team,
            )
        )
    return trainers


def _damage(attacker: BattlePokemon, defender: BattlePokemon) -> int:
    base = max(1, attacker.attack - defender.defense // 2)
    level_bonus = max(0, attacker.level // 5)
    return max(1, base + level_bonus)


def _advance_if_fainted(state: BattleState, side: str) -> None:
    trainer = state.trainer_a if side == "a" else state.trainer_b
    active_attr = "active_a" if side == "a" else "active_b"
    active_index = getattr(state, active_attr)
    if not trainer.team[active_index].fainted:
        return

    for index, pokemon in enumerate(trainer.team):
        if not pokemon.fainted:
            setattr(state, active_attr, index)
            state.log.append(f"{trainer.name} sends out {pokemon.species_name}!")
            return

    opponent = state.trainer_b if side == "a" else state.trainer_a
    state.winner = opponent.name
    state.log.append(f"{opponent.name} wins the battle!")


def perform_turn(state: BattleState) -> BattleState:
    """Run one deterministic offline battle turn."""
    if state.winner:
        return state

    pokemon_a, pokemon_b = state.active_pair()
    damage_a = _damage(pokemon_a, pokemon_b)
    pokemon_b.hp = max(0, int(pokemon_b.hp or 0) - damage_a)
    state.log.append(
        f"Turn {state.turn}: {pokemon_a.species_name} hits {pokemon_b.species_name} for {damage_a} damage."
    )
    _advance_if_fainted(state, "b")
    if state.winner:
        return state

    pokemon_a, pokemon_b = state.active_pair()
    damage_b = _damage(pokemon_b, pokemon_a)
    pokemon_a.hp = max(0, int(pokemon_a.hp or 0) - damage_b)
    state.log.append(f"{pokemon_b.species_name} hits {pokemon_a.species_name} for {damage_b} damage.")
    _advance_if_fainted(state, "a")
    state.turn += 1
    return state


def new_demo_battle() -> BattleState | None:
    trainers = load_trainers()
    if len(trainers) < 2:
        return None
    return BattleState(trainer_a=trainers[0], trainer_b=trainers[1])
