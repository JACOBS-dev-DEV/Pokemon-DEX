"""Touch/mouse-first Pygame interface for Pokemon-DEX.

Keyboard shortcuts remain available as optional fallbacks, while normal
navigation, Dex browsing, filtering, row selection, and battle controls are
available through mouse and touchscreen controls.
"""

from __future__ import annotations

import json
from pathlib import Path

from pokemon_dex.battle import new_demo_battle, new_wild_battle, perform_turn
from pokemon_dex.database import get_status
from pokemon_dex.journey import load_journey_logs, journey_summary
from pokemon_dex.my_dex import caught_by_game, caught_records, dex_summary
from pokemon_dex.personal import load_personal_records, summarize_games
from pokemon_dex.team import team_members, team_summary

ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "res" / "data" / "catalog" / "kanto_verified.json"
TABS = ("Catalog", "My Dex", "Games", "Journey", "Battles", "System")


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
    gap = 7
    left = 20
    usable = width - left * 2 - gap * (len(TABS) - 1)
    tab_w = max(95, usable // len(TABS))
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


def _row_rects(pygame, panel, count: int, scroll: int, row_h: int, start_y: int):
    rects = []
    visible = max(1, (panel.bottom - start_y - 10) // row_h)
    for offset in range(min(visible, max(0, count - scroll))):
        index = scroll + offset
        rect = pygame.Rect(panel.x + 10, start_y + offset * row_h, panel.width - 20, row_h - 3)
        rects.append((rect, index))
    return rects, visible


def _game_filter_rects(pygame, left, game_names: list[str]):
    labels = ["All"] + game_names
    gap = 6
    available = left.width - 28 - gap * (len(labels) - 1)
    width = max(92, available // max(1, len(labels)))
    width = min(165, width)
    x = left.x + 14
    y = left.y + 72
    return {label: pygame.Rect(x + i * (width + gap), y, width, 36) for i, label in enumerate(labels)}


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
                complete = " | complete" if record.get("complete") else ""
                _text(screen, small, f"{record.get('game')}: {marker}{complete}", right.x + 18, right.y + 242 + i * 25)
    return data, rows, selected, scroll


def _draw_mydex(screen, pygame, fonts, records, search, game_filter, selected, scroll, left, right):
    heading, body, small = fonts
    summary = dex_summary()
    grouped = caught_by_game()
    games = list(grouped.keys())
    data = _filtered_mydex(records, search, game_filter)
    visible = _visible_rows(left, 38, 146)
    selected = min(max(0, selected), max(0, len(data) - 1))
    scroll = min(max(0, scroll), max(0, len(data) - visible))
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + visible:
        scroll = selected - visible + 1

    _text(screen, heading, "My Dex — caught Pokémon", left.x + 16, left.y + 12)
    _text(
        screen,
        small,
        f"Unique species: {summary.get('unique_species', 0)} | caught records: {summary.get('caught_records', 0)} | games: {summary.get('games_with_caught_data', 0)}",
        left.x + 16,
        left.y + 44,
        (180, 186, 200),
    )

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
        _text(screen, body, f"{record.get('species_name', 'Unknown')}{owned_text} — {record.get('game')}{team_text}", rect.x + 10, rect.y + 8)

    _text(screen, heading, "Caught record", right.x + 16, right.y + 14)
    if data:
        record = data[selected]
        types = [value for value in (record.get("type_1"), record.get("type_2")) if value]
        details = [
            f"Pokémon: {record.get('species_name')}",
            f"Game: {record.get('game')}",
            f"Types: {' / '.join(types) if types else '-'}",
            f"Owned / obtained: {record.get('owned_count') if record.get('owned_count') is not None else '-'}",
            f"In team: {'yes' if record.get('in_team') else 'no'}",
            f"Complete: {'yes' if record.get('complete') else 'no'}",
            f"Evolved: {'yes' if record.get('evolved') else 'no'}",
            f"Research: {record.get('research_total') if record.get('research_total') is not None else '-'}",
            f"Battles logged: {record.get('battle_count') if record.get('battle_count') is not None else '-'}",
        ]
        for i, line in enumerate(details):
            _text(screen, body, line, right.x + 18, right.y + 62 + i * 29)

        game_stats = summary.get("by_game", {}).get(record.get("game"), {})
        _text(screen, heading, "Game Dex totals", right.x + 18, right.y + 346)
        totals = [
            f"Caught records: {game_stats.get('caught_records', 0)}",
            f"Unique caught: {game_stats.get('unique_species', 0)}",
            f"Team members recorded: {game_stats.get('team_members', 0)}",
            f"Complete entries: {game_stats.get('complete_entries', 0)}",
        ]
        for i, line in enumerate(totals):
            _text(screen, small, line, right.x + 18, right.y + 382 + i * 25)
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
        "The master Catalog remains separate from your catches.",
        "No online account or API is required.",
    ]
    for i, line in enumerate(lines):
        _text(screen, body, line, right.x + 18, right.y + 62 + i * 31)


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
        _text(screen, body, f"Gym Challenge started: {'yes' if journey.get('gym_challenge_started') else 'no'}", left.x + 18, y)
        y += 42
        for battle in log.get("trainer_battles", []):
            if y + 48 > left.bottom:
                break
            card = pygame.Rect(left.x + 14, y, left.width - 28, 48)
            pygame.draw.rect(screen, (40, 45, 56), card, border_radius=7)
            opponent = battle.get("opponent", "Unknown Trainer")
            result = str(battle.get("result", "unknown")).upper()
            _text(screen, body, f"#{battle.get('sequence', '-')}  {opponent} — {result}", card.x + 12, card.y + 7)
            note = battle.get("notes", "")
            _text(screen, small, note[:76], card.x + 12, card.y + 28, (182, 188, 200))
            y += 56
        y += 18

    _text(screen, heading, "Live Sword progress", right.x + 18, right.y + 16)
    sword = journey_summary("Pokemon Sword")
    lines = [
        f"Trainer wins logged: {sword.get('wins', 0)}",
        f"Trainer losses logged: {sword.get('losses', 0)}",
        "Hop wins logged: 2",
        "Other early trainer wins: 1",
        "Current checkpoint: before Dynamax Band",
        "Journey events are stored separately from Dex catches.",
        "Unnamed opponents stay explicitly unrecorded until known.",
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
    _text(screen, small, f"Types: {' / '.join(a.types)} | Moves: {', '.join(a.moves)}", left.x + 20, left.y + 190, (185, 191, 203))

    _text(screen, heading, battle.trainer_b.name, left.x + 20, left.y + 232)
    _text(screen, body, f"{b.species_name} Lv.{b.level} | HP {b.hp}/{b.max_hp}", left.x + 20, left.y + 266)
    _text(screen, small, f"Types: {' / '.join(b.types)} | Moves: {', '.join(b.moves)}", left.x + 20, left.y + 292, (185, 191, 203))
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

    _text(screen, heading, "Personal data health", right.x + 18, right.y + 16)
    personal_lines = [
        f"My Dex unique species: {dex.get('unique_species', 0)}",
        f"My Dex caught records: {dex.get('caught_records', 0)}",
        f"Games represented: {dex.get('games_with_caught_data', 0)}",
        f"Configured team members: {team.get('members', 0)}",
        f"Fainted team members: {team.get('fainted', 0)}",
        f"Team entries with levels: {team.get('with_level', 0)}",
        f"Team entries with moves: {team.get('with_moves', 0)}",
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
    pygame.display.set_caption("Pokemon-DEX Touch UI")
    screen = pygame.display.set_mode((1240, 820), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 30)
    body = pygame.font.Font(None, 23)
    small = pygame.font.Font(None, 20)
    title = pygame.font.Font(None, 42)

    catalog = _load_catalog()
    personal = load_personal_records()
    mydex = caught_records()
    games = summarize_games(personal)
    active_tab = 0
    selected = 0
    scroll = 0
    search = ""
    game_filter = "All"
    battle = new_demo_battle()
    search_active = False
    running = True

    while running:
        width, height = screen.get_size()
        tabs = _tab_rects(pygame, width)
        nav = _nav_rects(pygame, width, height)
        left, right = _list_layout(pygame, width, height)
        search_box = pygame.Rect(24, 134, 360, 32)
        clear_button = pygame.Rect(394, 134, 86, 32)
        battle_buttons = _battle_button_rects(pygame, left)

        if active_tab == 0:
            data_for_click = _filtered_catalog(catalog, search)
            row_rects, visible_rows = _row_rects(pygame, left, len(data_for_click), scroll, 34, left.y + 84)
            filter_rects = {}
        elif active_tab == 1:
            data_for_click = _filtered_mydex(mydex, search, game_filter)
            row_rects, visible_rows = _row_rects(pygame, left, len(data_for_click), scroll, 38, left.y + 142)
            filter_rects = _game_filter_rects(pygame, left, list(caught_by_game().keys()))
        else:
            data_for_click = []
            row_rects = []
            visible_rows = 10
            filter_rects = {}

        def handle_press(pos) -> None:
            nonlocal active_tab, selected, scroll, search, search_active, game_filter, battle

            for index, rect in enumerate(tabs):
                if rect.collidepoint(pos):
                    active_tab = index
                    selected = 0
                    scroll = 0
                    search = ""
                    search_active = False
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
                        return
            elif active_tab == 4:
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
            elif event.type == pygame.MOUSEWHEEL and active_tab in {0, 1}:
                scroll = max(0, scroll - event.y * 3)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_press(event.pos)
            elif event.type == pygame.FINGERDOWN:
                handle_press((int(event.x * width), int(event.y * height)))

        screen.fill((18, 21, 27))
        _text(screen, title, "Pokemon-DEX", 24, 20, (248, 248, 252))
        _text(screen, small, "Touch/mouse-first Pokédex | keyboard is optional", 26, 58, (175, 182, 197))

        for i, rect in enumerate(tabs):
            _button(screen, pygame, body, TABS[i], rect, i == active_tab)

        if active_tab in {0, 1}:
            pygame.draw.rect(screen, (54, 60, 74) if search_active else (36, 41, 51), search_box, border_radius=7)
            pygame.draw.rect(screen, (95, 103, 125), search_box, width=1, border_radius=7)
            placeholder = "Tap to search (optional)"
            _text(screen, body, search or placeholder, search_box.x + 10, search_box.y + 7, (225, 228, 235) if search else (150, 157, 172))
            _button(screen, pygame, small, "Clear", clear_button)

        pygame.draw.rect(screen, (29, 33, 41), left, border_radius=10)
        pygame.draw.rect(screen, (29, 33, 41), right, border_radius=10)

        if active_tab == 0:
            _, _, selected, scroll = _draw_catalog(screen, pygame, (heading, body, small), catalog, personal, search, selected, scroll, left, right)
        elif active_tab == 1:
            _, _, _, selected, scroll = _draw_mydex(screen, pygame, (heading, body, small), mydex, search, game_filter, selected, scroll, left, right)
        elif active_tab == 2:
            _draw_games(screen, pygame, (heading, body, small), games, left, right)
        elif active_tab == 3:
            _draw_journey(screen, pygame, (heading, body, small), left, right)
        elif active_tab == 4:
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
