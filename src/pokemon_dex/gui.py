"""Pygame desktop interface for Pokemon-DEX."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pokemon_dex.battle import new_demo_battle, perform_turn
from pokemon_dex.database import get_status
from pokemon_dex.personal import load_personal_records, summarize_games

ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "res" / "data" / "catalog" / "kanto_verified.json"
ART_ROOT = ROOT / "res" / "art"
TABS = ("Catalog", "My Pokemon", "Games", "Battles", "System")


def _load_catalog() -> list[dict[str, str]]:
    if not CATALOG_FILE.exists():
        return []
    with CATALOG_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return list(data.get("entries", []))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _find_art(species_name: str) -> Path | None:
    if not ART_ROOT.exists():
        return None
    target = _slug(species_name)
    for path in ART_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            if target in _slug(path.stem):
                return path
    return None


def _draw_text(screen, font, text: str, x: int, y: int, color=(220, 224, 232)) -> None:
    screen.blit(font.render(str(text), True, color), (x, y))


def _draw_tabs(screen, pygame, body_font, active_tab: int, width: int) -> list:
    rects = []
    x = 30
    tab_w = max(105, min(165, (width - 100) // len(TABS)))
    for index, label in enumerate(TABS):
        rect = pygame.Rect(x, 88, tab_w, 38)
        fill = (66, 73, 90) if index == active_tab else (37, 41, 51)
        pygame.draw.rect(screen, fill, rect, border_radius=7)
        _draw_text(screen, body_font, f"{index + 1}. {label}", x + 12, 98)
        rects.append(rect)
        x += tab_w + 8
    return rects


def _draw_art_or_placeholder(screen, pygame, body_font, name: str, rect) -> None:
    pygame.draw.rect(screen, (24, 27, 34), rect, border_radius=8)
    path = _find_art(name)
    if path:
        try:
            image = pygame.image.load(str(path)).convert_alpha()
            image = pygame.transform.smoothscale(image, image.get_rect().fit(rect).size)
            screen.blit(image, image.get_rect(center=rect.center))
            return
        except (pygame.error, OSError):
            pass
    _draw_text(screen, body_font, "Artwork slot ready", rect.x + 20, rect.centery - 12, (150, 156, 168))


def _draw_catalog(screen, pygame, heading_font, body_font, small_font, catalog, personal, search_text, selected, scroll, left, right):
    left_x, top_y, left_w, panel_h = left
    right_x, _, right_w, _ = right
    filtered = [
        entry for entry in catalog
        if search_text.lower() in entry.get("name", "").lower()
        or search_text.lower() in entry.get("national_dex", "").lower()
        or search_text.lower() in entry.get("form", "").lower()
    ]
    selected = min(selected, max(0, len(filtered) - 1))
    _draw_text(screen, heading_font, f"Catalog ({len(filtered)} shown)", left_x + 20, top_y + 16, (245, 245, 248))
    _draw_text(screen, body_font, f"Search: {search_text or '(all)'}", left_x + 20, top_y + 49)
    row_y, row_h = top_y + 84, 30
    visible = max(1, (panel_h - 105) // row_h)
    scroll = min(scroll, max(0, len(filtered) - visible))
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + visible:
        scroll = selected - visible + 1
    for visible_index, entry in enumerate(filtered[scroll:scroll + visible]):
        index = scroll + visible_index
        y = row_y + visible_index * row_h
        if index == selected:
            pygame.draw.rect(screen, (58, 64, 78), (left_x + 12, y - 3, left_w - 24, row_h), border_radius=5)
        suffix = "" if entry.get("form", "base") == "base" else f" [{entry['form']}]"
        _draw_text(screen, body_font, f"#{entry.get('national_dex', '---')}  {entry.get('name', 'Unknown')}{suffix}", left_x + 22, y)

    _draw_text(screen, heading_font, "Pokemon details", right_x + 20, top_y + 16, (245, 245, 248))
    if filtered:
        entry = filtered[selected]
        art_rect = pygame.Rect(right_x + 20, top_y + 56, min(220, right_w - 40), 190)
        _draw_art_or_placeholder(screen, pygame, body_font, entry.get("name", "Unknown"), art_rect)
        detail_y = top_y + 270
        for i, line in enumerate([
            f"National Dex: {entry.get('national_dex', '---')}",
            f"Name: {entry.get('name', 'Unknown')}",
            f"Form: {entry.get('form', 'base')}",
            "Catalog source: local spreadsheet import",
        ]):
            _draw_text(screen, body_font, line, right_x + 20, detail_y + i * 30)
        matches = [r for r in personal if r["species_name"].lower() == entry.get("name", "").lower()]
        if matches:
            _draw_text(screen, heading_font, "Your records", right_x + 20, detail_y + 145, (245, 245, 248))
            for i, record in enumerate(matches[:6]):
                marker = "Caught" if record["caught"] else "Not caught"
                extra = " | Complete" if record.get("complete") else ""
                _draw_text(screen, small_font, f"{record['game']}: {marker}{extra}", right_x + 20, detail_y + 180 + i * 25)
    return selected, scroll


def _draw_personal(screen, pygame, heading_font, body_font, personal, search_text, selected, scroll, left, right):
    left_x, top_y, left_w, panel_h = left
    right_x, _, right_w, _ = right
    filtered = [r for r in personal if search_text.lower() in r["species_name"].lower() or search_text.lower() in r["game"].lower()]
    selected = min(selected, max(0, len(filtered) - 1))
    _draw_text(screen, heading_font, f"My Pokemon ({len(filtered)} records)", left_x + 20, top_y + 16, (245, 245, 248))
    _draw_text(screen, body_font, f"Search: {search_text or '(all games)'}", left_x + 20, top_y + 49)
    row_y, row_h = top_y + 84, 34
    visible = max(1, (panel_h - 105) // row_h)
    scroll = min(scroll, max(0, len(filtered) - visible))
    if selected < scroll:
        scroll = selected
    elif selected >= scroll + visible:
        scroll = selected - visible + 1
    for visible_index, record in enumerate(filtered[scroll:scroll + visible]):
        index = scroll + visible_index
        y = row_y + visible_index * row_h
        if index == selected:
            pygame.draw.rect(screen, (58, 64, 78), (left_x + 12, y - 3, left_w - 24, row_h), border_radius=5)
        flags = []
        if record["caught"]:
            flags.append("CAUGHT")
        if record.get("complete"):
            flags.append("COMPLETE")
        if record["in_team"]:
            flags.append(f"TEAM {record.get('team_slot') or ''}".strip())
        flag_text = f"  [{' | '.join(flags)}]" if flags else ""
        _draw_text(screen, body_font, f"{record['species_name']} — {record['game']}{flag_text}", left_x + 22, y)

    _draw_text(screen, heading_font, "Personal record", right_x + 20, top_y + 16, (245, 245, 248))
    if filtered:
        record = filtered[selected]
        art_rect = pygame.Rect(right_x + 20, top_y + 56, min(220, right_w - 40), 190)
        _draw_art_or_placeholder(screen, pygame, body_font, record["species_name"], art_rect)
        lines = [
            f"Pokemon: {record['species_name']}", f"Game: {record['game']}",
            f"Caught: {'yes' if record['caught'] else 'no'}", f"Complete: {'yes' if record.get('complete') else 'no'}",
            f"Evolved: {'yes' if record.get('evolved') else 'no'}", f"In team: {'yes' if record['in_team'] else 'no'}",
            f"Owned/obtained: {record.get('owned_count') if record.get('owned_count') is not None else '-'}",
            f"Research total: {record.get('research_total') if record.get('research_total') is not None else '-'}",
            f"Battle count: {record.get('battle_count') if record.get('battle_count') is not None else '-'}",
        ]
        for i, line in enumerate(lines):
            _draw_text(screen, body_font, line, right_x + 20, top_y + 270 + i * 28)
    return selected, scroll


def run_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        print("Install local dependencies inside your venv with: python -m pip install -r requirements.txt")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX")
    screen = pygame.display.set_mode((1220, 780), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 40)
    heading_font = pygame.font.Font(None, 29)
    body_font = pygame.font.Font(None, 23)
    small_font = pygame.font.Font(None, 20)

    catalog = _load_catalog()
    personal = load_personal_records()
    games = summarize_games(personal)
    battle = new_demo_battle()
    search_text = ""
    scroll = 0
    selected = 0
    active_tab = 0
    running = True

    while running:
        width, height = screen.get_size()
        tab_rects = _draw_tabs(screen, pygame, body_font, active_tab, width)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, rect in enumerate(tab_rects):
                    if rect.collidepoint(event.pos):
                        active_tab, selected, scroll, search_text = index, 0, 0, ""
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif pygame.K_1 <= event.key <= pygame.K_5:
                    active_tab, selected, scroll, search_text = event.key - pygame.K_1, 0, 0, ""
                elif event.key == pygame.K_SPACE and active_tab == 3 and battle:
                    perform_turn(battle)
                elif event.key == pygame.K_r and active_tab == 3:
                    battle = new_demo_battle()
                elif event.key == pygame.K_BACKSPACE and active_tab in {0, 1}:
                    search_text, scroll = search_text[:-1], 0
                elif event.key == pygame.K_DOWN:
                    selected += 1
                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_PAGEUP:
                    scroll = max(0, scroll - 10)
                elif event.key == pygame.K_PAGEDOWN:
                    scroll += 10
                elif active_tab in {0, 1} and event.unicode and event.unicode.isprintable():
                    search_text, scroll = search_text + event.unicode, 0
            elif event.type == pygame.MOUSEWHEEL:
                scroll = max(0, scroll - event.y * 3)

        screen.fill((20, 22, 28))
        screen.blit(title_font.render("Pokemon-DEX", True, (240, 240, 245)), (30, 20))
        _draw_text(screen, small_font, "Complete offline Pokedex | Keys 1-5 switch views | Esc closes", 30, 62, (175, 180, 190))
        _draw_tabs(screen, pygame, body_font, active_tab, width)

        top_y = 142
        panel_h = height - top_y - 28
        left_x = 30
        left_w = max(430, int(width * 0.51))
        right_x = left_x + left_w + 24
        right_w = max(280, width - right_x - 30)
        left = (left_x, top_y, left_w, panel_h)
        right = (right_x, top_y, right_w, panel_h)
        pygame.draw.rect(screen, (31, 34, 42), left, border_radius=8)
        pygame.draw.rect(screen, (31, 34, 42), right, border_radius=8)

        if active_tab == 0:
            selected, scroll = _draw_catalog(screen, pygame, heading_font, body_font, small_font, catalog, personal, search_text, selected, scroll, left, right)
        elif active_tab == 1:
            selected, scroll = _draw_personal(screen, pygame, heading_font, body_font, personal, search_text, selected, scroll, left, right)
        elif active_tab == 2:
            _draw_text(screen, heading_font, "Game profiles", left_x + 20, top_y + 16, (245, 245, 248))
            y = top_y + 62
            for game in games:
                pygame.draw.rect(screen, (40, 44, 55), (left_x + 16, y - 8, left_w - 32, 118), border_radius=7)
                _draw_text(screen, heading_font, game["game"], left_x + 30, y)
                _draw_text(screen, body_font, f"Records: {game['records']} | Caught: {game['caught']} | Complete: {game['complete']}", left_x + 30, y + 34)
                _draw_text(screen, body_font, f"Owned: {game['owned_total']} | Battles: {game['battles']} | Research: {game['research_total']}", left_x + 30, y + 64)
                y += 132
            _draw_text(screen, heading_font, "Different Pokemon games", right_x + 20, top_y + 16, (245, 245, 248))
            for i, line in enumerate(["Sword data connected", "Brilliant Diamond data connected", "Legends: Arceus data connected", "More game profiles can plug into the same format", "Everything stays local/offline"]):
                _draw_text(screen, body_font, line, right_x + 20, top_y + 62 + i * 31)
        elif active_tab == 3:
            _draw_text(screen, heading_font, "Trainer battle engine", left_x + 20, top_y + 16, (245, 245, 248))
            _draw_text(screen, body_font, "SPACE: next turn | R: reset demo battle", left_x + 20, top_y + 50)
            if battle:
                a, b = battle.active_pair()
                _draw_text(screen, heading_font, battle.trainer_a.name, left_x + 24, top_y + 100)
                _draw_text(screen, body_font, f"Active: {a.species_name} Lv.{a.level} | HP {a.hp}/{a.max_hp}", left_x + 24, top_y + 138)
                _draw_text(screen, heading_font, battle.trainer_b.name, left_x + 24, top_y + 190)
                _draw_text(screen, body_font, f"Active: {b.species_name} Lv.{b.level} | HP {b.hp}/{b.max_hp}", left_x + 24, top_y + 228)
                _draw_text(screen, body_font, f"Turn: {battle.turn}", left_x + 24, top_y + 280)
                if battle.winner:
                    _draw_text(screen, heading_font, f"Winner: {battle.winner}", left_x + 24, top_y + 320, (245, 245, 248))
                _draw_text(screen, heading_font, "Battle log", right_x + 20, top_y + 16, (245, 245, 248))
                log_lines = battle.log[-18:] if battle.log else ["Battle ready. Press SPACE to begin."]
                for i, line in enumerate(log_lines):
                    _draw_text(screen, small_font, line, right_x + 20, top_y + 60 + i * 27)
            else:
                _draw_text(screen, body_font, "No trainer roster is available yet.", left_x + 24, top_y + 100)
        else:
            status = get_status()
            _draw_text(screen, heading_font, "System / database health", left_x + 20, top_y + 16, (245, 245, 248))
            lines = [
                f"Database version: {status.database_version}", f"Canonical profiles: {status.canonical_profiles}",
                f"Personal profile files: {status.personal_profile_files}", f"Indexed profile files: {status.indexed_pokemon}",
                f"Indexed art assets: {status.indexed_art_assets}", f"Art files on disk: {status.art_files}",
                f"Registered games: {status.games}", f"Registered Dexes: {status.dexes}", f"Registered forms: {status.forms}",
                "Network/API dependency: none", f"GUI engine: Pygame {pygame.version.ver}", "Battle engine: local/offline",
            ]
            for i, line in enumerate(lines):
                _draw_text(screen, body_font, line, left_x + 24, top_y + 62 + i * 31)
            _draw_text(screen, heading_font, "Complete Pokedex target", right_x + 20, top_y + 16, (245, 245, 248))
            for i, line in enumerate(["All Pokemon species", "All forms and variants", "All supported games", "Personal caught/save records", "Trainer rosters", "Battle engine", "Local artwork and sprites", "Offline-first architecture"]):
                _draw_text(screen, body_font, line, right_x + 20, top_y + 62 + i * 31)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
