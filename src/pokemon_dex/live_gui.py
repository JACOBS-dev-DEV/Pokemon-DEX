"""Live-edit, touch/mouse-first Pokemon-DEX interface.

This UI keeps the existing offline Pokédex browsing and battle tools while
adding safe on-screen editing for personal Pokémon records and route checklists.
Keyboard input remains optional and is only used for search text.
"""

from __future__ import annotations

import json
from pathlib import Path

from pokemon_dex.battle import new_demo_battle, new_wild_battle, perform_turn
from pokemon_dex.database import get_status
from pokemon_dex.editor import ProfileEditError, adjust_field, toggle_field
from pokemon_dex.journey import journey_summary, load_journey_logs
from pokemon_dex.my_dex import caught_by_game, caught_records, dex_summary
from pokemon_dex.personal import load_personal_records, summarize_games
from pokemon_dex.routes import all_areas, route_summary, update_area
from pokemon_dex.team import team_members, team_summary

ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "res" / "data" / "catalog" / "kanto_verified.json"
TABS = ("Catalog", "My Dex", "Games", "Routes", "Journey", "Battles", "System")


def _load_catalog() -> list[dict]:
    if not CATALOG_FILE.exists():
        return []
    with CATALOG_FILE.open("r", encoding="utf-8") as handle:
        return list(json.load(handle).get("entries", []))


def _text(screen, font, value, x, y, color=(225, 228, 235)) -> None:
    screen.blit(font.render(str(value), True, color), (x, y))


def _button(screen, pygame, font, label: str, rect, active: bool = False):
    fill = (72, 79, 98) if active else (43, 48, 60)
    pygame.draw.rect(screen, fill, rect, border_radius=9)
    pygame.draw.rect(screen, (93, 100, 120), rect, width=1, border_radius=9)
    surface = font.render(label, True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _tab_rects(pygame, width: int):
    gap = 6
    left = 18
    usable = width - left * 2 - gap * (len(TABS) - 1)
    tab_w = max(88, usable // len(TABS))
    return [pygame.Rect(left + i * (tab_w + gap), 82, tab_w, 44) for i in range(len(TABS))]


def _nav_rects(pygame, width: int, height: int):
    labels = ("Up", "Down", "Page Up", "Page Down", "Clear Search")
    button_w = 126
    gap = 8
    total = len(labels) * button_w + (len(labels) - 1) * gap
    start_x = max(20, (width - total) // 2)
    y = height - 58
    return {label: pygame.Rect(start_x + i * (button_w + gap), y, button_w, 40) for i, label in enumerate(labels)}


def _list_layout(pygame, width: int, height: int):
    top = 174
    bottom = height - 76
    left_panel = pygame.Rect(24, top, max(430, int(width * 0.52)), bottom - top)
    right_x = left_panel.right + 18
    right_panel = pygame.Rect(right_x, top, width - right_x - 24, bottom - top)
    return left_panel, right_panel


def _visible_rows(panel, row_h: int, header_h: int) -> int:
    return max(1, (panel.height - header_h) // row_h)


def _row_rects(pygame, panel, count: int, scroll: int, row_h: int, start_y: int):
    rects = []
    visible = max(1, (panel.bottom - start_y - 10) // row_h)
    for offset in range(min(visible, max(0, count - scroll))):
        index = scroll + offset
        rect = pygame.Rect(panel.x + 10, start_y + offset * row_h, panel.width - 20, row_h - 3)
        rects.append((rect, index))
    return rects, visible


def _filtered_catalog(catalog: list[dict], search: str) -> list[dict]:
    needle = search.lower().strip()
    if not needle:
        return catalog
    return [
        entry for entry in catalog
        if needle in str(entry.get("name", "")).lower()
        or needle in str(entry.get("national_dex", "")).lower()
        or needle in str(entry.get("form", "")).lower()
    ]


def _filtered_mydex(records: list[dict], search: str, game_filter: str) -> list[dict]:
    needle = search.lower().strip()
    data = records
    if game_filter != "All":
        data = [record for record in data if record.get("game") == game_filter]
    if needle:
        data = [
            record for record in data
            if needle in str(record.get("species_name", "")).lower()
            or needle in str(record.get("game", "")).lower()
            or needle in str(record.get("type_1", "")).lower()
            or needle in str(record.get("type_2", "")).lower()
        ]
    return data


def _game_filter_rects(pygame, left, game_names: list[str]):
    labels = ["All"] + game_names
    gap = 6
    available = left.width - 28 - gap * (len(labels) - 1)
    width = max(82, available // max(1, len(labels)))
    width = min(158, width)
    x = left.x + 14
    y = left.y + 72
    return {label: pygame.Rect(x + i * (width + gap), y, width, 36) for i, label in enumerate(labels)}


def _edit_rects(pygame, right):
    x = right.x + 18
    y = right.y + 340
    w = 108
    gap = 8
    return {
        "Owned -": pygame.Rect(x, y, w, 38),
        "Owned +": pygame.Rect(x + w + gap, y, w, 38),
        "Team": pygame.Rect(x + 2 * (w + gap), y, w, 38),
        "Level -": pygame.Rect(x, y + 48, w, 38),
        "Level +": pygame.Rect(x + w + gap, y + 48, w, 38),
        "Complete": pygame.Rect(x + 2 * (w + gap), y + 48, w, 38),
        "Evolved": pygame.Rect(x, y + 96, w, 38),
        "Battles -": pygame.Rect(x + w + gap, y + 96, w, 38),
        "Battles +": pygame.Rect(x + 2 * (w + gap), y + 96, w, 38),
    }


def _route_edit_rects(pygame, right):
    x = right.x + 18
    y = right.y + 302
    w = 112
    gap = 8
    return {
        "Visited": pygame.Rect(x, y, w, 38),
        "Trainers -": pygame.Rect(x + w + gap, y, w, 38),
        "Trainers +": pygame.Rect(x + 2 * (w + gap), y, w, 38),
        "Trainer Check": pygame.Rect(x, y + 48, w, 38),
        "Pokemon Check": pygame.Rect(x + w + gap, y + 48, w, 38),
        "Items Check": pygame.Rect(x + 2 * (w + gap), y + 48, w, 38),
        "Area Complete": pygame.Rect(x, y + 96, w * 2 + gap, 38),
    }


def _draw_catalog(screen, pygame, fonts, catalog, personal, search, selected, scroll, left, right):
    heading, body, small = fonts
    data = _filtered_catalog(catalog, search)
    visible = _visible_rows(left, 34, 92)
    selected = min(max(0, selected), max(0, len(data) - 1))
    scroll = min(max(0, scroll), max(0, len(data) - visible))
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + visible:
        scroll = selected - visible + 1

    _text(screen, heading, f"Complete Catalog ({len(data)} shown)", left.x + 16, left.y + 14)
    _text(screen, body, f"Search: {search or '(all Pokémon)'}", left.x + 16, left.y + 48, (180, 186, 200))
    rows, _ = _row_rects(pygame, left, len(data), scroll, 34, left.y + 84)
    for rect, index in rows:
        entry = data[index]
        if index == selected:
            pygame.draw.rect(screen, (64, 71, 88), rect, border_radius=6)
        label = f"#{entry.get('national_dex', '---')}  {entry.get('name', 'Unknown')}"
        if entry.get("form", "base") != "base":
            label += f" [{entry.get('form')}]"
        _text(screen, body, label, rect.x + 10, rect.y + 6)

    _text(screen, heading, "Pokémon details", right.x + 16, right.y + 14)
    if data:
        entry = data[selected]
        details = [
            f"National Dex: {entry.get('national_dex', '---')}",
            f"Name: {entry.get('name', 'Unknown')}",
            f"Form: {entry.get('form', 'base')}",
            "Source: local imported data",
        ]
        for i, line in enumerate(details):
            _text(screen, body, line, right.x + 18, right.y + 62 + i * 30)
        matches = [r for r in personal if r.get("species_name", "").lower() == entry.get("name", "").lower()]
        if matches:
            _text(screen, heading, "Your records", right.x + 18, right.y + 206)
            for i, record in enumerate(matches[:9]):
                marker = "CAUGHT" if record.get("caught") else "not caught"
                _text(screen, small, f"{record.get('game')}: {marker}", right.x + 18, right.y + 242 + i * 25)
    return data, rows, selected, scroll


def _draw_mydex(screen, pygame, fonts, records, search, game_filter, selected, scroll, left, right, edit_buttons, save_message):
    heading, body, small = fonts
    summary = dex_summary()
    games = list(caught_by_game().keys())
    data = _filtered_mydex(records, search, game_filter)
    visible = _visible_rows(left, 38, 146)
    selected = min(max(0, selected), max(0, len(data) - 1))
    scroll = min(max(0, scroll), max(0, len(data) - visible))
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + visible:
        scroll = selected - visible + 1

    _text(screen, heading, "My Dex — live local edits", left.x + 16, left.y + 12)
    _text(screen, small, f"Unique: {summary.get('unique_species', 0)} | caught records: {summary.get('caught_records', 0)} | games: {summary.get('games_with_caught_data', 0)}", left.x + 16, left.y + 44, (180, 186, 200))
    filters = _game_filter_rects(pygame, left, games)
    for label, rect in filters.items():
        _button(screen, pygame, small, label, rect, label == game_filter)
    _text(screen, small, f"Search: {search or '(optional)'}", left.x + 16, left.y + 118, (180, 186, 200))

    rows, _ = _row_rects(pygame, left, len(data), scroll, 38, left.y + 142)
    for rect, index in rows:
        record = data[index]
        if index == selected:
            pygame.draw.rect(screen, (64, 71, 88), rect, border_radius=6)
        owned = record.get("owned_count")
        owned_text = f" x{owned}" if isinstance(owned, int) and owned > 1 else ""
        team_text = " | TEAM" if record.get("in_team") else ""
        form_text = f" [{record.get('form')}]" if record.get("form") else ""
        _text(screen, body, f"{record.get('species_name', 'Unknown')}{form_text}{owned_text} — {record.get('game')}{team_text}", rect.x + 10, rect.y + 8)

    _text(screen, heading, "Caught record", right.x + 16, right.y + 14)
    if data:
        record = data[selected]
        types = [value for value in (record.get("type_1"), record.get("type_2")) if value]
        level = record.get("level") if record.get("level") is not None else record.get("found_at_level")
        details = [
            f"Pokémon: {record.get('species_name')}",
            f"Game: {record.get('game')}",
            f"Types: {' / '.join(types) if types else '-'}",
            f"Caught at: {record.get('caught_location') or '-'}",
            f"Owned / obtained: {record.get('owned_count') if record.get('owned_count') is not None else '-'}",
            f"Level: {level if level is not None else '-'}",
            f"In team: {'yes' if record.get('in_team') else 'no'} | slot: {record.get('team_slot') or '-'}",
            f"Complete: {'yes' if record.get('complete') else 'no'} | evolved: {'yes' if record.get('evolved') else 'no'}",
            f"Battles logged: {record.get('battle_count') if record.get('battle_count') is not None else '-'}",
        ]
        for i, line in enumerate(details):
            _text(screen, body, line, right.x + 18, right.y + 58 + i * 27)
        _text(screen, small, "Tap a control to save immediately to the local profile.", right.x + 18, right.y + 312, (180, 186, 200))
        for label, rect in edit_buttons.items():
            active = (label == "Team" and record.get("in_team")) or (label == "Complete" and record.get("complete")) or (label == "Evolved" and record.get("evolved"))
            _button(screen, pygame, small, label, rect, active)
        if save_message:
            _text(screen, small, save_message[:72], right.x + 18, right.y + 488, (190, 220, 190))
    else:
        _text(screen, body, "No caught Pokémon match this filter yet.", right.x + 18, right.y + 64)
    return data, rows, filters, selected, scroll


def _draw_games(screen, pygame, fonts, games, left, right):
    heading, body, small = fonts
    _text(screen, heading, "Game save profiles", left.x + 18, left.y + 16)
    y = left.y + 58
    for game in games:
        if y + 106 > left.bottom:
            break
        card = pygame.Rect(left.x + 14, y, left.width - 28, 98)
        pygame.draw.rect(screen, (40, 45, 56), card, border_radius=8)
        _text(screen, heading, game.get("game"), card.x + 14, card.y + 10)
        _text(screen, body, f"Records {game.get('records')} | Caught {game.get('caught')} | Complete {game.get('complete')}", card.x + 14, card.y + 42)
        _text(screen, small, f"Owned {game.get('owned_total')} | Battles {game.get('battles')} | Research {game.get('research_total')}", card.x + 14, card.y + 70, (185, 191, 203))
        y += 108
    summary = dex_summary()
    _text(screen, heading, "My Dex across games", right.x + 18, right.y + 16)
    lines = [
        f"Unique caught species: {summary.get('unique_species', 0)}",
        f"Caught records: {summary.get('caught_records', 0)}",
        f"Games with caught data: {summary.get('games_with_caught_data', 0)}",
        "Each game keeps its own local record.",
        "Live edits write only to local JSON files.",
        "No online account or API is required.",
    ]
    for i, line in enumerate(lines):
        _text(screen, body, line, right.x + 18, right.y + 62 + i * 31)


def _draw_routes(screen, pygame, fonts, areas, selected, scroll, left, right, edit_buttons, save_message):
    heading, body, small = fonts
    summary = route_summary()
    selected = min(max(0, selected), max(0, len(areas) - 1))
    visible = _visible_rows(left, 56, 88)
    scroll = min(max(0, scroll), max(0, len(areas) - visible))
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + visible:
        scroll = selected - visible + 1

    _text(screen, heading, "Route / area check-off", left.x + 16, left.y + 14)
    _text(screen, small, f"Areas: {summary.get('areas', 0)} | visited: {summary.get('visited', 0)} | complete: {summary.get('complete', 0)} | trainers: {summary.get('trainers_defeated', 0)}", left.x + 16, left.y + 48, (180, 186, 200))
    rows, _ = _row_rects(pygame, left, len(areas), scroll, 56, left.y + 84)
    for rect, index in rows:
        area = areas[index]
        if index == selected:
            pygame.draw.rect(screen, (64, 71, 88), rect, border_radius=6)
        check = "✓" if area.get("complete") else "□"
        current = " | CURRENT" if area.get("current") else ""
        _text(screen, body, f"{check} {area.get('name')} — {area.get('game')}{current}", rect.x + 10, rect.y + 7)
        _text(screen, small, f"Trainers defeated: {area.get('trainers_defeated', 0)} | caught here: {len(area.get('pokemon_caught', []))}", rect.x + 10, rect.y + 31, (180, 186, 200))

    _text(screen, heading, "Area details", right.x + 16, right.y + 14)
    if areas:
        area = areas[selected]
        caught = ", ".join(area.get("pokemon_caught", [])) or "none yet"
        possible = [item.get("display_name", "Unknown") for item in area.get("possible_catches", [])]
        possible_text = ", ".join(possible) or "none"
        lines = [
            f"Area: {area.get('name')}",
            f"Game: {area.get('game')}",
            f"Visited: {'yes' if area.get('visited') else 'no'} | current: {'yes' if area.get('current') else 'no'}",
            f"Trainers defeated: {area.get('trainers_defeated', 0)}",
            f"Caught here: {caught}",
            f"Possible catches: {possible_text}",
            f"Trainer check: {'done' if area.get('trainer_check_complete') else 'open'}",
            f"Pokémon check: {'done' if area.get('pokemon_check_complete') else 'open'}",
            f"Item check: {'done' if area.get('items_check_complete') else 'open'}",
        ]
        for i, line in enumerate(lines):
            _text(screen, body, line[:72], right.x + 18, right.y + 58 + i * 27)
        for label, rect in edit_buttons.items():
            active = (
                (label == "Visited" and area.get("visited"))
                or (label == "Trainer Check" and area.get("trainer_check_complete"))
                or (label == "Pokemon Check" and area.get("pokemon_check_complete"))
                or (label == "Items Check" and area.get("items_check_complete"))
                or (label == "Area Complete" and area.get("complete"))
            )
            _button(screen, pygame, small, label, rect, active)
        if save_message:
            _text(screen, small, save_message[:72], right.x + 18, right.y + 456, (190, 220, 190))
    return rows, selected, scroll


def _draw_journey(screen, pygame, fonts, left, right):
    heading, body, small = fonts
    logs = load_journey_logs()
    overall = journey_summary()
    _text(screen, heading, "Journey / trainer log", left.x + 18, left.y + 16)
    _text(screen, body, f"Trainer battles: {overall.get('trainer_battles', 0)} | Wins: {overall.get('wins', 0)} | Losses: {overall.get('losses', 0)}", left.x + 18, left.y + 52)
    y = left.y + 94
    for log in logs:
        journey = log.get("journey", {})
        _text(screen, heading, log.get("game", "Unknown Game"), left.x + 18, y)
        y += 34
        phase = str(journey.get("current_phase", "unknown")).replace("_", " ")
        _text(screen, body, f"Phase: {phase}", left.x + 18, y)
        y += 29
        _text(screen, body, f"Dynamax Band received: {'yes' if journey.get('dynamax_band_received') else 'no'}", left.x + 18, y)
        y += 29
        _text(screen, body, f"Current area: {journey.get('current_area') or '-'}", left.x + 18, y)
        y += 42
        for battle in log.get("trainer_battles", []):
            if y + 48 > left.bottom:
                break
            card = pygame.Rect(left.x + 14, y, left.width - 28, 48)
            pygame.draw.rect(screen, (40, 45, 56), card, border_radius=7)
            opponent = battle.get("opponent", "Unknown Trainer")
            result = str(battle.get("result", "unknown")).upper()
            location = f" @ {battle.get('location')}" if battle.get("location") else ""
            _text(screen, body, f"#{battle.get('sequence', '-')}  {opponent}{location} — {result}", card.x + 12, card.y + 7)
            _text(screen, small, str(battle.get("notes", ""))[:76], card.x + 12, card.y + 28, (182, 188, 200))
            y += 56
        y += 18

    sword = journey_summary("Pokemon Sword")
    sword_log = next((log for log in logs if log.get("game") == "Pokemon Sword"), {})
    journey = sword_log.get("journey", {})
    checkpoint = str(journey.get("current_phase", "unknown")).replace("_", " ")
    _text(screen, heading, "Live Sword progress", right.x + 18, right.y + 16)
    lines = [
        f"Trainer wins logged: {sword.get('wins', 0)}",
        f"Trainer losses logged: {sword.get('losses', 0)}",
        "Hop wins logged: 2",
        "Route 2 trainer wins: 1",
        f"Dynamax Band: {'received' if journey.get('dynamax_band_received') else 'not received'}",
        f"Checkpoint: {checkpoint}",
        "Pending trainer identity stays unguessed until confirmed.",
    ]
    for i, line in enumerate(lines):
        _text(screen, body, line, right.x + 18, right.y + 62 + i * 31)


def _battle_button_rects(pygame, left):
    return {
        "Next Turn": pygame.Rect(left.x + 18, left.y + 58, 142, 44),
        "Reset": pygame.Rect(left.x + 170, left.y + 58, 105, 44),
        "Trainer Battle": pygame.Rect(left.x + 285, left.y + 58, 158, 44),
        "Wild Battle": pygame.Rect(left.x + 453, left.y + 58, 142, 44),
    }


def _draw_battle(screen, pygame, fonts, battle, left, right, buttons):
    heading, body, small = fonts
    _text(screen, heading, "Offline battle engine", left.x + 18, left.y + 16)
    for label, rect in buttons.items():
        _button(screen, pygame, small, label, rect)
    if not battle:
        _text(screen, body, "No battle roster is available.", left.x + 18, left.y + 130)
        return
    a, b = battle.active_pair()
    _text(screen, heading, battle.trainer_a.name, left.x + 20, left.y + 130)
    _text(screen, body, f"{a.species_name} Lv.{a.level} | HP {a.hp}/{a.max_hp}", left.x + 20, left.y + 164)
    _text(screen, heading, battle.trainer_b.name, left.x + 20, left.y + 232)
    _text(screen, body, f"{b.species_name} Lv.{b.level} | HP {b.hp}/{b.max_hp}", left.x + 20, left.y + 266)
    _text(screen, body, f"Turn: {battle.turn} | Kind: {battle.battle_kind}", left.x + 20, left.y + 332)
    if battle.winner:
        _text(screen, heading, f"Winner: {battle.winner}", left.x + 20, left.y + 368)
    _text(screen, heading, "Battle log", right.x + 18, right.y + 16)
    lines = battle.log[-18:] if battle.log else ["Battle ready. Tap Next Turn to begin."]
    for i, line in enumerate(lines):
        _text(screen, small, line[:72], right.x + 18, right.y + 56 + i * 26)


def _draw_system(screen, pygame, fonts, left, right):
    heading, body, small = fonts
    status = get_status()
    dex = dex_summary()
    team = team_summary()
    routes = route_summary()
    members = team_members()
    _text(screen, heading, "System / database health", left.x + 18, left.y + 16)
    lines = [
        f"Database version: {status.database_version}",
        f"Canonical profiles: {status.canonical_profiles}",
        f"Personal profile files: {status.personal_profile_files}",
        f"Indexed profile files: {status.indexed_pokemon}",
        f"Indexed art assets: {status.indexed_art_assets}",
        f"Art files on disk: {status.art_files}",
        f"Registered games: {status.games}",
        f"Registered Dexes: {status.dexes}",
        f"Registered forms: {status.forms}",
        "Network/API dependency: none",
        f"GUI engine: Pygame {pygame.version.ver}",
    ]
    for i, line in enumerate(lines):
        _text(screen, body, line, left.x + 20, left.y + 58 + i * 29)
    _text(screen, heading, "Personal/live data health", right.x + 18, right.y + 16)
    personal_lines = [
        f"My Dex unique species: {dex.get('unique_species', 0)}",
        f"My Dex caught records: {dex.get('caught_records', 0)}",
        f"Games represented: {dex.get('games_with_caught_data', 0)}",
        f"Route areas tracked: {routes.get('areas', 0)}",
        f"Route areas complete: {routes.get('complete', 0)}",
        f"Configured team members: {team.get('members', 0)}",
        "Live edits: enabled with automatic backups",
    ]
    for i, line in enumerate(personal_lines):
        _text(screen, body, line, right.x + 18, right.y + 58 + i * 30)
    if not members:
        _text(screen, small, "Current Sword team has not been explicitly configured yet.", right.x + 18, right.y + 292, (180, 186, 200))


def run_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Live Editor")
    screen = pygame.display.set_mode((1280, 840), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 30)
    body = pygame.font.Font(None, 23)
    small = pygame.font.Font(None, 20)
    title = pygame.font.Font(None, 42)

    catalog = _load_catalog()
    active_tab = 0
    selected = 0
    scroll = 0
    search = ""
    game_filter = "All"
    battle = new_demo_battle()
    search_active = False
    save_message = ""

    def refresh_personal():
        personal_records = load_personal_records()
        return personal_records, caught_records(), summarize_games(personal_records)

    personal, mydex, games = refresh_personal()
    areas = all_areas()
    running = True

    while running:
        width, height = screen.get_size()
        tabs = _tab_rects(pygame, width)
        nav = _nav_rects(pygame, width, height)
        left, right = _list_layout(pygame, width, height)
        search_box = pygame.Rect(24, 134, 360, 32)
        clear_button = pygame.Rect(394, 134, 86, 32)
        battle_buttons = _battle_button_rects(pygame, left)
        edit_buttons = _edit_rects(pygame, right)
        route_buttons = _route_edit_rects(pygame, right)

        if active_tab == 0:
            data_for_click = _filtered_catalog(catalog, search)
            row_rects, visible_rows = _row_rects(pygame, left, len(data_for_click), scroll, 34, left.y + 84)
            filter_rects = {}
        elif active_tab == 1:
            data_for_click = _filtered_mydex(mydex, search, game_filter)
            row_rects, visible_rows = _row_rects(pygame, left, len(data_for_click), scroll, 38, left.y + 142)
            filter_rects = _game_filter_rects(pygame, left, list(caught_by_game().keys()))
        elif active_tab == 3:
            data_for_click = areas
            row_rects, visible_rows = _row_rects(pygame, left, len(areas), scroll, 56, left.y + 84)
            filter_rects = {}
        else:
            data_for_click = []
            row_rects = []
            visible_rows = 10
            filter_rects = {}

        def refresh_after_edit(message: str) -> None:
            nonlocal personal, mydex, games, areas, save_message, selected, scroll
            personal, mydex, games = refresh_personal()
            areas = all_areas()
            save_message = message
            selected = max(0, selected)
            scroll = max(0, scroll)

        def edit_current_pokemon(label: str) -> None:
            if not data_for_click or selected >= len(data_for_click):
                return
            record = data_for_click[selected]
            try:
                if label == "Owned -":
                    adjust_field(record, "owned_count", -1)
                elif label == "Owned +":
                    adjust_field(record, "owned_count", 1)
                elif label == "Team":
                    toggle_field(record, "in_team")
                elif label == "Level -":
                    adjust_field(record, "level", -1)
                elif label == "Level +":
                    adjust_field(record, "level", 1)
                elif label == "Complete":
                    toggle_field(record, "complete")
                elif label == "Evolved":
                    toggle_field(record, "evolved")
                elif label == "Battles -":
                    adjust_field(record, "battle_count", -1)
                elif label == "Battles +":
                    adjust_field(record, "battle_count", 1)
                else:
                    return
                refresh_after_edit(f"Saved {record.get('species_name')} locally. Backup created.")
            except ProfileEditError as exc:
                refresh_after_edit(f"Edit error: {exc}")

        def edit_current_route(label: str) -> None:
            if not areas or selected >= len(areas):
                return
            area = areas[selected]
            try:
                if label == "Visited":
                    update_area(area, {"visited": not bool(area.get("visited"))})
                elif label == "Trainers -":
                    update_area(area, {"trainers_defeated": int(area.get("trainers_defeated") or 0) - 1})
                elif label == "Trainers +":
                    update_area(area, {"trainers_defeated": int(area.get("trainers_defeated") or 0) + 1})
                elif label == "Trainer Check":
                    update_area(area, {"trainer_check_complete": not bool(area.get("trainer_check_complete"))})
                elif label == "Pokemon Check":
                    update_area(area, {"pokemon_check_complete": not bool(area.get("pokemon_check_complete"))})
                elif label == "Items Check":
                    update_area(area, {"items_check_complete": not bool(area.get("items_check_complete"))})
                elif label == "Area Complete":
                    update_area(area, {"complete": not bool(area.get("complete"))})
                else:
                    return
                refresh_after_edit(f"Saved {area.get('name')} checklist locally. Backup created.")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                refresh_after_edit(f"Route edit error: {exc}")

        def handle_press(pos) -> None:
            nonlocal active_tab, selected, scroll, search, search_active, game_filter, battle, save_message
            for index, rect in enumerate(tabs):
                if rect.collidepoint(pos):
                    active_tab = index
                    selected = 0
                    scroll = 0
                    search = ""
                    search_active = False
                    save_message = ""
                    return

            if active_tab in {0, 1}:
                if search_box.collidepoint(pos):
                    search_active = True
                    return
                if clear_button.collidepoint(pos) or nav["Clear Search"].collidepoint(pos):
                    search = ""
                    selected = 0
                    scroll = 0
                    search_active = False
                    return
                if nav["Up"].collidepoint(pos):
                    selected = max(0, selected - 1)
                    return
                if nav["Down"].collidepoint(pos):
                    selected = min(max(0, len(data_for_click) - 1), selected + 1)
                    return
                if nav["Page Up"].collidepoint(pos):
                    selected = max(0, selected - visible_rows)
                    scroll = max(0, scroll - visible_rows)
                    return
                if nav["Page Down"].collidepoint(pos):
                    selected = min(max(0, len(data_for_click) - 1), selected + visible_rows)
                    scroll += visible_rows
                    return
                for label, rect in filter_rects.items():
                    if rect.collidepoint(pos):
                        game_filter = label
                        selected = 0
                        scroll = 0
                        return
                for rect, index in row_rects:
                    if rect.collidepoint(pos):
                        selected = index
                        search_active = False
                        save_message = ""
                        return
                if active_tab == 1:
                    for label, rect in edit_buttons.items():
                        if rect.collidepoint(pos):
                            edit_current_pokemon(label)
                            return
            elif active_tab == 3:
                for rect, index in row_rects:
                    if rect.collidepoint(pos):
                        selected = index
                        save_message = ""
                        return
                for label, rect in route_buttons.items():
                    if rect.collidepoint(pos):
                        edit_current_route(label)
                        return
            elif active_tab == 5:
                if battle_buttons["Next Turn"].collidepoint(pos) and battle:
                    perform_turn(battle)
                elif battle_buttons["Reset"].collidepoint(pos):
                    battle = new_demo_battle()
                elif battle_buttons["Trainer Battle"].collidepoint(pos):
                    battle = new_demo_battle()
                elif battle_buttons["Wild Battle"].collidepoint(pos):
                    battle = new_wild_battle()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif search_active and active_tab in {0, 1}:
                    if event.key == pygame.K_BACKSPACE:
                        search = search[:-1]
                        selected = 0
                        scroll = 0
                    elif event.unicode and event.unicode.isprintable():
                        search += event.unicode
                        selected = 0
                        scroll = 0
            elif event.type == pygame.MOUSEWHEEL and active_tab in {0, 1, 3}:
                scroll = max(0, scroll - event.y * 3)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_press(event.pos)
            elif event.type == pygame.FINGERDOWN:
                handle_press((int(event.x * width), int(event.y * height)))

        screen.fill((18, 21, 27))
        _text(screen, title, "Pokemon-DEX", 24, 20, (248, 248, 252))
        _text(screen, small, "Live local edits | touch/mouse-first | automatic backup before changed saves", 26, 58, (175, 182, 197))
        for i, rect in enumerate(tabs):
            _button(screen, pygame, body, TABS[i], rect, i == active_tab)

        if active_tab in {0, 1}:
            pygame.draw.rect(screen, (54, 60, 74) if search_active else (36, 41, 51), search_box, border_radius=7)
            pygame.draw.rect(screen, (95, 103, 125), search_box, width=1, border_radius=7)
            _text(screen, body, search or "Tap to search (optional)", search_box.x + 10, search_box.y + 7, (225, 228, 235) if search else (150, 157, 172))
            _button(screen, pygame, small, "Clear", clear_button)

        pygame.draw.rect(screen, (29, 33, 41), left, border_radius=10)
        pygame.draw.rect(screen, (29, 33, 41), right, border_radius=10)

        if active_tab == 0:
            _, _, selected, scroll = _draw_catalog(screen, pygame, (heading, body, small), catalog, personal, search, selected, scroll, left, right)
        elif active_tab == 1:
            _, _, _, selected, scroll = _draw_mydex(screen, pygame, (heading, body, small), mydex, search, game_filter, selected, scroll, left, right, edit_buttons, save_message)
        elif active_tab == 2:
            _draw_games(screen, pygame, (heading, body, small), games, left, right)
        elif active_tab == 3:
            _, selected, scroll = _draw_routes(screen, pygame, (heading, body, small), areas, selected, scroll, left, right, route_buttons, save_message)
        elif active_tab == 4:
            _draw_journey(screen, pygame, (heading, body, small), left, right)
        elif active_tab == 5:
            _draw_battle(screen, pygame, (heading, body, small), battle, left, right, battle_buttons)
        else:
            _draw_system(screen, pygame, (heading, body, small), left, right)

        if active_tab in {0, 1}:
            for label, rect in nav.items():
                _button(screen, pygame, small, label, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
