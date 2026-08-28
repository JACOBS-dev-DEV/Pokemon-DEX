"""Offline trainer, wild, move, and type-aware battle engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINERS_FILE = ROOT / "res" / "data" / "trainers" / "trainers.json"
TYPE_CHART_FILE = ROOT / "res" / "data" / "types" / "type_chart.json"
MOVES_FILE = ROOT / "res" / "data" / "moves" / "battle_moves.json"


@dataclass
class BattleMove:
    move_id: str
    name: str
    type_name: str = "Normal"
    category: str = "physical"
    power: int = 40


@dataclass
class BattlePokemon:
    species_name: str
    level: int = 5
    max_hp: int = 20
    attack: int = 10
    defense: int = 10
    special_attack: int | None = None
    special_defense: int | None = None
    speed: int = 10
    types: list[str] = field(default_factory=lambda: ["Normal"])
    moves: list[str] = field(default_factory=lambda: ["tackle"])
    hp: int | None = None

    def __post_init__(self) -> None:
        if self.hp is None:
            self.hp = self.max_hp
        if self.special_attack is None:
            self.special_attack = self.attack
        if self.special_defense is None:
            self.special_defense = self.defense
        self.types = self.types or ["Normal"]
        self.moves = self.moves or ["tackle"]

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
    battle_kind: str = "trainer"

    def active_pair(self) -> tuple[BattlePokemon, BattlePokemon]:
        return self.trainer_a.team[self.active_a], self.trainer_b.team[self.active_b]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_move_registry() -> dict[str, BattleMove]:
    data = _read_json(MOVES_FILE)
    registry: dict[str, BattleMove] = {}
    for raw in data.get("moves", []):
        move = BattleMove(
            move_id=str(raw.get("id", "tackle")),
            name=str(raw.get("name", "Tackle")),
            type_name=str(raw.get("type", "Normal")),
            category=str(raw.get("category", "physical")),
            power=int(raw.get("power", 40)),
        )
        registry[move.move_id] = move
    return registry


def load_type_chart() -> dict[str, dict[str, float]]:
    data = _read_json(TYPE_CHART_FILE)
    return data.get("matrix", {})


def load_trainers() -> list[Trainer]:
    data = _read_json(TRAINERS_FILE)
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


def type_multiplier(move_type: str, defender_types: list[str]) -> float:
    """Return effectiveness using the local sheet-derived defensive-row chart."""
    chart = load_type_chart()
    multiplier = 1.0
    for defender_type in defender_types or ["Normal"]:
        multiplier *= float(chart.get(defender_type, {}).get(move_type, 1.0))
    return multiplier


def _choose_move(pokemon: BattlePokemon) -> BattleMove:
    registry = load_move_registry()
    for move_id in pokemon.moves:
        if move_id in registry:
            return registry[move_id]
    return registry.get("tackle", BattleMove("tackle", "Tackle"))


def _damage(attacker: BattlePokemon, defender: BattlePokemon, move: BattleMove) -> tuple[int, float, bool]:
    if move.category == "special":
        offense = int(attacker.special_attack or attacker.attack)
        defense = int(defender.special_defense or defender.defense)
    else:
        offense = attacker.attack
        defense = defender.defense

    base = (((2 * attacker.level / 5) + 2) * max(1, move.power) * max(1, offense) / max(1, defense)) / 50 + 2
    stab = 1.5 if move.type_name in attacker.types else 1.0
    effectiveness = type_multiplier(move.type_name, defender.types)
    damage = int(base * stab * effectiveness)
    if effectiveness > 0:
        damage = max(1, damage)
    return damage, effectiveness, stab > 1.0


def _effectiveness_text(value: float) -> str:
    if value == 0:
        return "It had no effect."
    if value >= 2:
        return "It's super effective!"
    if value < 1:
        return "It's not very effective."
    return ""


def _attack(state: BattleState, attacker: BattlePokemon, defender: BattlePokemon, prefix: str = "") -> None:
    move = _choose_move(attacker)
    damage, effectiveness, _ = _damage(attacker, defender, move)
    defender.hp = max(0, int(defender.hp or 0) - damage)
    line = f"{prefix}{attacker.species_name} used {move.name} for {damage} damage."
    extra = _effectiveness_text(effectiveness)
    state.log.append(f"{line} {extra}".strip())


def _advance_if_fainted(state: BattleState, side: str) -> None:
    trainer = state.trainer_a if side == "a" else state.trainer_b
    active_attr = "active_a" if side == "a" else "active_b"
    active_index = getattr(state, active_attr)
    if not trainer.team[active_index].fainted:
        return

    state.log.append(f"{trainer.team[active_index].species_name} fainted!")
    for index, pokemon in enumerate(trainer.team):
        if not pokemon.fainted:
            setattr(state, active_attr, index)
            state.log.append(f"{trainer.name} sends out {pokemon.species_name}!")
            return

    opponent = state.trainer_b if side == "a" else state.trainer_a
    state.winner = opponent.name
    state.log.append(f"{opponent.name} wins the battle!")


def perform_turn(state: BattleState) -> BattleState:
    """Run one deterministic local battle turn with moves and type effectiveness."""
    if state.winner:
        return state

    pokemon_a, pokemon_b = state.active_pair()
    first_side = "a" if pokemon_a.speed >= pokemon_b.speed else "b"

    if first_side == "a":
        _attack(state, pokemon_a, pokemon_b, f"Turn {state.turn}: ")
        _advance_if_fainted(state, "b")
        if not state.winner:
            pokemon_a, pokemon_b = state.active_pair()
            _attack(state, pokemon_b, pokemon_a)
            _advance_if_fainted(state, "a")
    else:
        _attack(state, pokemon_b, pokemon_a, f"Turn {state.turn}: ")
        _advance_if_fainted(state, "a")
        if not state.winner:
            pokemon_a, pokemon_b = state.active_pair()
            _attack(state, pokemon_a, pokemon_b)
            _advance_if_fainted(state, "b")

    state.turn += 1
    return state


def new_demo_battle() -> BattleState | None:
    trainers = load_trainers()
    if len(trainers) < 2:
        return None
    return BattleState(trainer_a=trainers[0], trainer_b=trainers[1])


def new_wild_battle(species_name: str = "Bidoof", level: int = 5, type_name: str = "Normal") -> BattleState | None:
    """Create a local wild encounter against the first configured player trainer."""
    trainers = load_trainers()
    if not trainers:
        return None
    wild = Trainer(
        trainer_id="wild-encounter",
        name=f"Wild {species_name}",
        trainer_class="Wild Pokemon",
        game_mode="wild_battle",
        team=[BattlePokemon(species_name=species_name, level=level, max_hp=18 + level, attack=8 + level, defense=8 + level, speed=8 + level, types=[type_name], moves=["tackle"])],
    )
    return BattleState(trainer_a=trainers[0], trainer_b=wild, battle_kind="wild")
