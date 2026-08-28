"""Touch/mouse-first Pygame interface for Pokemon-DEX.

Keyboard shortcuts remain available as fallbacks, but normal navigation and
battle controls are exposed as clickable/tappable on-screen controls.
"""

from __future__ import annotations

import json
from pathlib import Path

from pokemon_dex.battle import new_demo_battle, new_wild_battle, perform_turn
from pokemon_dex.database import get_status
from pokemon_dex.personal import load_personal_records, summarize_games

ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "res" / "data" / "catalog" / "kanto_verified.json"
TABS = ("Catalog", "My Pokemon", "Games", "Battles", "System")


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
    gap = 8
    left = 24
    usable = width - left * 2 - gap * (len(TABS) - 1)
    tab_w = max(105, usable // len(TABS))
    return [pygame.Rect(left + i * (tab_w + gap), 82, tab_w, 44) for i in range(len(TABS))]


def _nav_rects(pygame, width: int, height: int):
    labels = ("Up", "Down", "Page Up", "Page Down", "Clear Search")
    button_w = 126
    gap = 8
    total = len(labels) * button_w + (len(labels) - 1) * gap
    start_x = max(20, (width - total) // 2)
    y = height - 58
    return {label: pygame.Rect(start_x + i * (button_w + gap), y, button_w, 40) for i, label in enumerate(labels)}


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


def _filtered_personal(records: list[dict], search: str) -> list[dict]:
    needle = search.lower().strip()
    if not needle:
        return records
    return [
        record for record in records
        if needle in record.get("species_name", "").lower()
        or needle in record.get("game", "").lower()
    ]


def _list_layout(pygame, width: int, height: int):
    top = 150
    bottom = height - 76
    left_panel = pygame.Rect(24, top, max(430, int(width * 0.52)), bottom - top)
    right_x = left_panel.right + 18
    right_panel = pygame.Rect(right_x, top, width - right_x - 24, bottom - top)
    return left_panel, right_panel


def _visible_rows(panel, row_h: int, header_h: int = 92) -> int:
    return max(1, (panel.height - header_h) // row_h)


def _draw_catalog(screen, pygame, fonts, catalog, personal, search, selected, scroll, left, right):
    heading, body, small = fonts
    data = _filtered_catalog(catalog, search)
    selected = min(max(0, selected), max(0, len(data) - 1))
    visible = _visible_rows(left, 34)
    scroll = min(max(0, scroll), max(0, len(data) - visible))
    if selected < scroll:
        scroll = selected
    if selected >= scroll + visible:
        scroll = selected - visible + 1

    _text(screen, heading, f"Catalog ({len(data)})", left.x + 16, left.y + 14)
    _text(screen, body, f"Search: {search or '(all Pokemon)'}", left.x + 16, left.y + 48, (180, 186, 200))

    row_rects = []
    y0 = left.y + 84
    for offset, entry in enumerate(data[scroll:scroll + visible]):
        index = scroll + offset
        rect = pygame.Rect(left.x + 10, y0 + offset * 34, left.width - 20, 31)
        if index == selected:
            pygame.draw.rect(screen, (64, 71, 88), rect, border_radius=6)
        label = f"#{entry.get('national_dex', '---')}  {entry.get('name', 'Unknown')}"
        if entry.get("form", "base") != "base":
            label += f" [{entry.get('form')}]"
        _text(screen, body, label, rect.x + 10, rect.y + 6)
        row_rects.append((rect, index))

    _text(screen, heading, "Pokemon details", right.x + 16, right.y + 14)
    if data:
        entry = data[selected]
        lines = [
            f"National Dex: {entry.get('national_dex', '---')}",
            f"Name: {entry.get('name', 'Unknown')}",
            f"Form: {entry.get('form', 'base')}",
            "Source: local imported data",
        ]
        for i, line in enumerate(lines):
            _text(screen, body, line, right.x + 18, right.y + 62 + i * 30)
        matches = [r for r in personal if r.get("species_name", "").lower() == entry.get("name", "").lower()]
        if matches:
            _text(screen, heading, "Your records", right.x + 18, right.y + 206)
            for i, record in enumerate(matches[:8]):
                marker = "caught" if record.get("caught") else "not caught"
                complete = " | complete" if record.get("complete") else ""
                _text(screen, small, f"{record.get('game')}: {marker}{complete}", right.x + 18, right.y + 242 + i * 26)
    return data, row_rects, selected, scroll


def _draw_personal(screen, pygame, fonts, personal, search, selected, scroll, left, right):
    heading, body, _ = fonts
    data = _filtered_personal(personal, search)
    selected = min(max(0, selected), max(0, len(data) - 1))
    visible = _visible_rows(left, 36)
    scroll = min(max(0, scroll), max(0, len(data) - visible))
    if selected < scroll:
        scroll = selected
    if selected >= scroll + visible:
        scroll = selected - visible + 1

    _text(screen, heading, f"My Pokemon ({len(data)})", left.x + 16, left.y + 14)
    _text(screen, body, f"Search: {search or '(all games)'}", left.x + 16, left.y + 48, (180, 186, 200))

    row_rects = []
    y0 = left.y + 84
    for offset, record in enumerate(data[scroll:scroll + visible]):
        index = scroll + offset
        rect = pygame.Rect(left.x + 10, y0 + offset * 36, left.width - 20, 33)
        if index == selected:
            pygame.draw.rect(screen, (64, 71, 88), rect, border_radius=6)
        flags = []
        if record.get("caught"):
            flags.append("CAUGHT")
        if record.get("complete"):
            flags.append("COMPLETE")
        suffix = f" [{' | '.join(flags)}]" if flags else ""
        _text(screen, body, f"{record.get('species_name')} — {record.get('game')}{suffix}", rect.x + 10, rect.y + 7)
        row_rects.append((rect, index))

    _text(screen, heading, "Personal record", right.x + 16, right.y + 14)
    if data:
        record = data[selected]
        lines = [
            f"Pokemon: {record.get('species_name')}",
            f"Game: {record.get('game')}",
            f"Caught: {'yes' if record.get('caught') else 'no'}",
            f"Complete: {'yes' if record.get('complete') else 'no'}",
            f"Evolved: {'yes' if record.get('evolved') else 'no'}",
            f"In team: {'yes' if record.get('in_team') else 'no'}",
            f"Owned/obtained: {record.get('owned_count') if record.get('owned_count') is not None else '-'}",
            f"Research: {record.get('research_total') if record.get('research_total') is not None else '-'}",
            f"Battles: {record.get('battle_count') if record.get('battle_count') is not None else '-'}",
        ]
        for i, line in enumerate(lines):
            _text(screen, body, line, right.x + 18, right.y + 62 + i * 30)
    return data, row_rects, selected, scroll


def run_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Touch UI")
    screen = pygame.display.set_mode((1240, 800), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    heading = pygame.font.Font(None, 30)
    body = pygame.font.Font(None, 23)
    small = pygame.font.Font(None, 20)
    title = pygame.font.Font(None, 42)

    catalog = _load_catalog()
    personal = load_personal_records()
    games = summarize_games(personal)
    active_tab = 0
    selected = 0
    scroll = 0
    search = ""
    battle = new_demo_battle()
    search_active = False
    running = True

    while running:
        width, height = screen.get_size()
        tabs = _tab_rects(pygame, width)
        nav = _nav_rects(pygame, width, height)
        left, right = _list_layout(pygame, width, height)
        battle_buttons = {
            "Next Turn": pygame.Rect(left.x + 20, left.y + 62, 150, 44),
            "Reset": pygame.Rect(left.x + 180, left.y + 62, 120, 44),
            "Trainer Battle": pygame.Rect(left.x + 310, left.y + 62, 155, 44),
            "Wild Battle": pygame.Rect(left.x + 475, left.y + 62, 145, 44),
        }
        search_box = pygame.Rect(24, 132, 360, 34)
        clear_button = pygame.Rect(394, 132, 86, 34)

        current_rows = []
        current_data = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_BACKSPACE and active_tab in {0, 1}:
                    search = search[:-1]
                    scroll = 0
                elif active_tab in {0, 1} and event.unicode and event.unicode.isprintable():
                    search += event.unicode
                    scroll = 0
            elif event.type == pygame.MOUSEWHEEL and active_tab in {0, 1}:
                scroll = max(0, scroll - event.y * 3)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                for index, rect in enumerate(tabs):
                    if rect.collidepoint(pos):
                        active_tab, selected, scroll, search = index, 0, 0, ""
                        search_active = False
                if active_tab in {0, 1}:
                    search_active = search_box.collidepoint(pos)
                    if clear_button.collidepoint(pos):
                        search, selected, scroll = "", 0, 0
                    if nav["Up"].collidepoint(pos):
                        selected = max(0, selected - 1)
                    elif nav["Down"].collidepoint(pos):
                        selected += 1
                    elif nav["Page Up"].collidepoint(pos):
                        selected, scroll = max(0, selected - 10), max(0, scroll - 10)
                    elif nav["Page Down"].collidepoint(pos):
                        selected += 10
                        scroll += 10
                    elif nav["Clear Search"].collidepoint(pos):
                        search, selected, scroll = "", 0, 0
                elif active_tab == 3:
                    if battle_buttons["Next Turn"].collidepoint(pos) and battle:
                        perform_turn(battle)
                    elif battle_buttons["Reset"].collidepoint(pos):
                        battle = new_demo_battle()
                    elif battle_buttons["Trainer Battle"].collidepoint(pos):
                        battle = new_demo_battle()
                    elif battle_buttons["Wild Battle"].collidepoint(pos):
                        battle = new_wild_battle()

        screen.fill((18, 21, 27))
        _text(screen, title, "Pokemon-DEX", 24, 20, (248, 248, 252))
        _text(screen, small, "Touch/mouse-first controls | keyboard is optional", 26, 58, (175, 182, 197))

        for i, rect in enumerate(tabs):
            _button(screen, pygame, body, TABS[i], rect, i == active_tab)

        if active_tab in {0, 1}:
            pygame.draw.rect(screen, (54, 60, 74) if search_active else (36, 41, 51), search_box, border_radius=7)
            pygame.draw.rect(screen, (95, 103, 125), search_box, width=1, border_radius=7)
            _text(screen, body, search or "Tap here, then type to search", search_box.x + 10, search_box.y + 8, (225, 228, 235) if search else (150, 157, 172))
            _button(screen, pygame, small, "Clear", clear_button)

        pygame.draw.rect(screen, (29, 33, 41), left, border_radius=10)
        pygame.draw.rect(screen, (29, 33, 41), right, border_radius=10)

        if active_tab == 0:
            current_data, current_rows, selected, scroll = _draw_catalog(screen, pygame, (heading, body, small), catalog, personal, search, selected, scroll, left, right)
        elif active_tab == 1:
            current_data, current_rows, selected, scroll = _draw_personal(screen, pygame, (heading, body, small), personal, search, selected, scroll, left, right)
        elif active_tab == 2:
            _text(screen, heading, "Game profiles", left.x + 18, left.y + 16)
            y = left.y + 60
            for game in games:
                card = pygame.Rect(left.x + 14, y, left.width - 28, 112)
                pygame.draw.rect(screen, (40, 45, 56), card, border_radius=8)
                _text(screen, heading, game.get("game"), card.x + 14, card.y + 12)
                _text(screen, body, f"Records {game.get('records')} | Caught {game.get('caught')} | Complete {game.get('complete')}", card.x + 14, card.y + 48)
                _text(screen, body, f"Owned {game.get('owned_total')} | Research {game.get('research_total')}", card.x + 14, card.y + 76)
                y += 124
            _text(screen, heading, "Connected games", right.x + 18, right.y + 16)
            for i, line in enumerate(("Pokemon Sword", "Pokemon Brilliant Diamond", "Pokemon Legends: Arceus", "More games use the same local profile format")):
                _text(screen, body, line, right.x + 18, right.y + 62 + i * 32)
        elif active_tab == 3:
            _text(screen, heading, "Battle controls", left.x + 18, left.y + 16)
            for label, rect in battle_buttons.items():
                _button(screen, pygame, small, label, rect)
            if battle:
                a, b = battle.active_pair()
                y = left.y + 140
                _text(screen, heading, battle.trainer_a.name, left.x + 20, y)
                _text(screen, body, f"{a.species_name} Lv.{a.level} | HP {a.hp}/{a.max_hp} | {'/'.join(a.types)}", left.x + 20, y + 34)
                _text(screen, heading, battle.trainer_b.name, left.x + 20, y + 88)
                _text(screen, body, f"{b.species_name} Lv.{b.level} | HP {b.hp}/{b.max_hp} | {'/'.join(b.types)}", left.x + 20, y + 122)
                _text(screen, body, f"Battle: {battle.battle_kind} | Turn {battle.turn}", left.x + 20, y + 172)
                if battle.winner:
                    _text(screen, heading, f"Winner: {battle.winner}", left.x + 20, y + 214)
                _text(screen, heading, "Battle log", right.x + 18, right.y + 16)
                for i, line in enumerate((battle.log[-17:] or ["Tap Next Turn to begin."])):
                    _text(screen, small, line, right.x + 18, right.y + 58 + i * 27)
        else:
            status = get_status()
            _text(screen, heading, "System health", left.x + 18, left.y + 16)
            lines = (
                f"Database version: {status.database_version}",
                f"Canonical profiles: {status.canonical_profiles}",
                f"Personal files: {status.personal_profile_files}",
                f"Indexed Pokemon: {status.indexed_pokemon}",
                f"Art assets: {status.indexed_art_assets}",
                f"Registered games: {status.games}",
                f"Registered Dexes: {status.dexes}",
                f"Registered forms: {status.forms}",
                "Network/API dependency: none",
            )
            for i, line in enumerate(lines):
                _text(screen, body, line, left.x + 20, left.y + 62 + i * 31)
            _text(screen, heading, "Input modes", right.x + 18, right.y + 16)
            for i, line in enumerate(("Mouse/touch tabs", "Tap Pokemon rows", "On-screen navigation buttons", "On-screen battle buttons", "Mouse wheel optional", "Keyboard shortcuts optional")):
                _text(screen, body, line, right.x + 18, right.y + 62 + i * 32)

        if active_tab in {0, 1}:
            for label, rect in nav.items():
                _button(screen, pygame, small, label, rect)

            # Re-evaluate visible rows after drawing and make them tappable.
            if active_tab == 0:
                _, current_rows, _, _ = _draw_catalog(screen, pygame, (heading, body, small), catalog, personal, search, selected, scroll, left, right)
            else:
                _, current_rows, _, _ = _draw_personal(screen, pygame, (heading, body, small), personal, search, selected, scroll, left, right)

            mouse_down = pygame.mouse.get_pressed(num_buttons=3)[0]
            if mouse_down:
                pos = pygame.mouse.get_pos()
                for rect, index in current_rows:
                    if rect.collidepoint(pos):
                        selected = index
                        break

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
