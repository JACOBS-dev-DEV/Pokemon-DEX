"""Pygame desktop interface for Pokemon-DEX."""

from __future__ import annotations

import json
from pathlib import Path

from pokemon_dex.database import get_status

ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "res" / "data" / "catalog" / "kanto_verified.json"


def _load_catalog() -> list[dict[str, str]]:
    if not CATALOG_FILE.exists():
        return []
    with CATALOG_FILE.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return list(data.get("entries", []))


def run_gui() -> int:
    """Launch the local Pokemon-DEX Pygame GUI."""
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        print("Install local dependencies with: python3 -m pip install -r requirements.txt")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX")
    screen = pygame.display.set_mode((1100, 700), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 40)
    heading_font = pygame.font.Font(None, 28)
    body_font = pygame.font.Font(None, 23)

    catalog = _load_catalog()
    search_text = ""
    scroll = 0
    selected = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_BACKSPACE:
                    search_text = search_text[:-1]
                    scroll = 0
                elif event.key == pygame.K_DOWN:
                    selected += 1
                elif event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.unicode and event.unicode.isprintable():
                    search_text += event.unicode
                    scroll = 0
            elif event.type == pygame.MOUSEWHEEL:
                scroll = max(0, scroll - event.y * 3)

        width, height = screen.get_size()
        screen.fill((20, 22, 28))

        filtered = [
            entry
            for entry in catalog
            if search_text.lower() in entry.get("name", "").lower()
            or search_text.lower() in entry.get("national_dex", "").lower()
        ]
        if filtered:
            selected = min(selected, len(filtered) - 1)
        else:
            selected = 0

        header = title_font.render("Pokemon-DEX", True, (240, 240, 245))
        screen.blit(header, (30, 20))
        subtitle = body_font.render(
            "Offline local database | Type to search | Mouse wheel to scroll | Esc to close",
            True,
            (175, 180, 190),
        )
        screen.blit(subtitle, (30, 62))

        search_label = body_font.render(f"Search: {search_text or '(all)'}", True, (220, 220, 225))
        screen.blit(search_label, (30, 98))

        left_x, top_y = 30, 135
        left_w = max(380, int(width * 0.48))
        panel_h = height - top_y - 30
        pygame.draw.rect(screen, (31, 34, 42), (left_x, top_y, left_w, panel_h), border_radius=8)

        heading = heading_font.render(f"Verified catalog ({len(filtered)} shown)", True, (245, 245, 248))
        screen.blit(heading, (left_x + 20, top_y + 16))

        row_y = top_y + 55
        row_h = 30
        visible_rows = max(1, (panel_h - 75) // row_h)
        max_scroll = max(0, len(filtered) - visible_rows)
        scroll = min(scroll, max_scroll)

        for visible_index, entry in enumerate(filtered[scroll : scroll + visible_rows]):
            index = scroll + visible_index
            y = row_y + visible_index * row_h
            if index == selected:
                pygame.draw.rect(screen, (58, 64, 78), (left_x + 12, y - 3, left_w - 24, row_h), border_radius=5)
            form = entry.get("form", "base")
            form_suffix = "" if form == "base" else f" [{form}]"
            label = f"#{entry.get('national_dex', '---')}  {entry.get('name', 'Unknown')}{form_suffix}"
            text = body_font.render(label, True, (225, 228, 235))
            screen.blit(text, (left_x + 22, y))

        right_x = left_x + left_w + 25
        right_w = max(250, width - right_x - 30)
        pygame.draw.rect(screen, (31, 34, 42), (right_x, top_y, right_w, panel_h), border_radius=8)

        status = get_status()
        status_heading = heading_font.render("Local database status", True, (245, 245, 248))
        screen.blit(status_heading, (right_x + 20, top_y + 16))

        status_lines = [
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
        ]
        for i, line in enumerate(status_lines):
            text = body_font.render(line, True, (205, 210, 220))
            screen.blit(text, (right_x + 20, top_y + 58 + i * 30))

        if filtered:
            entry = filtered[selected]
            detail_y = top_y + 390
            detail_heading = heading_font.render("Selected Pokemon", True, (245, 245, 248))
            screen.blit(detail_heading, (right_x + 20, detail_y))
            details = [
                f"National Dex: {entry.get('national_dex', '---')}",
                f"Name: {entry.get('name', 'Unknown')}",
                f"Form: {entry.get('form', 'base')}",
                "Source: local Google Sheet import",
            ]
            for i, line in enumerate(details):
                text = body_font.render(line, True, (205, 210, 220))
                screen.blit(text, (right_x + 20, detail_y + 40 + i * 29))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
