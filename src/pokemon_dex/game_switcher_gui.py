"""Touch/mouse-first personal Pokemon game switcher."""

from __future__ import annotations

from pokemon_dex.display import apply_display_mode, fit_text, font_size_for_height
from pokemon_dex.game_switcher import GameSwitcherError, active_game, game_rows, set_active_game


def _text(screen, font, value, x, y, color=(225, 228, 235), max_width: int | None = None) -> None:
    rendered = fit_text(font, value, max_width) if max_width is not None else str(value)
    screen.blit(font.render(rendered, True, color), (x, y))


def _button(screen, pygame, font, label: str, rect, *, active: bool = False, enabled: bool = True):
    if not enabled:
        fill = (34, 37, 45)
        text_color = (125, 130, 142)
    else:
        fill = (70, 78, 96) if active else (43, 48, 60)
        text_color = (245, 246, 250)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, (118, 126, 150), rect, width=2 if active else 1, border_radius=10)
    surface = font.render(fit_text(font, label, rect.width - 16), True, text_color)
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _summary_line(row: dict) -> str:
    if not row.get("personal_data"):
        return "Supported content • no personal save imported"
    summary = row.get("summary", {})
    status = summary.get("sync_status")
    if status == "awaiting_live_sync":
        return "Existing save slot • awaiting live sync"
    if row.get("game") == "Pokemon Shield" and summary.get("galar_caught") is not None:
        return (
            f"Galar {summary.get('galar_caught')}/{summary.get('galar_seen')} • "
            f"Armor {summary.get('armor_caught')}/{summary.get('armor_seen')} • "
            f"Tundra {summary.get('tundra_caught')}/{summary.get('tundra_seen')}"
        )
    parts = []
    if summary.get("recorded_species") is not None:
        parts.append(f"{summary.get('recorded_species')} recorded")
    if summary.get("caught_species_records") is not None:
        parts.append(f"{summary.get('caught_species_records')} caught")
    if summary.get("obtained_total") is not None:
        parts.append(f"{summary.get('obtained_total')} obtained")
    if summary.get("complete_entries") is not None:
        parts.append(f"{summary.get('complete_entries')} complete")
    return " • ".join(parts) if parts else "Personal save data available"


def run_game_switcher_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    preset = "standard"
    fullscreen = False
    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Game Switcher")
    screen = apply_display_mode(pygame, preset, fullscreen=fullscreen)
    clock = pygame.time.Clock()
    selected = 0
    message = "Select a personal save and tap Make Active."
    running = True

    while running:
        width, height = screen.get_size()
        rows = game_rows()
        if rows:
            selected = max(0, min(selected, len(rows) - 1))

        title = pygame.font.Font(None, font_size_for_height(height, 44, minimum=32, maximum=58))
        heading = pygame.font.Font(None, font_size_for_height(height, 27, minimum=20, maximum=35))
        body = pygame.font.Font(None, font_size_for_height(height, 21, minimum=16, maximum=28))
        small = pygame.font.Font(None, font_size_for_height(height, 17, minimum=14, maximum=22))

        margin = max(18, min(34, width // 36))
        back_rect = pygame.Rect(width - 112 - margin, 22, 112, 38)
        list_top = 112
        list_bottom = height - 112
        row_gap = 8
        row_h = max(58, min(78, (list_bottom - list_top - row_gap * max(0, len(rows) - 1)) // max(1, len(rows))))
        row_rects = []
        for index, row in enumerate(rows):
            rect = pygame.Rect(margin, list_top + index * (row_h + row_gap), width - margin * 2, row_h)
            row_rects.append((rect, index, row))

        make_active_rect = pygame.Rect(margin, height - 72, 176, 42)
        display_labels = ("Compact", "Standard", "Large", "Fullscreen")
        display_w = max(90, min(122, (width - 430) // 4))
        display_rects = {
            label: pygame.Rect(220 + i * (display_w + 8), height - 72, display_w, 42)
            for i, label in enumerate(display_labels)
        }

        def set_display(label: str) -> None:
            nonlocal screen, preset, fullscreen
            lowered = label.lower()
            if lowered == "fullscreen":
                fullscreen = not fullscreen
            else:
                preset = lowered
                fullscreen = False
            screen = apply_display_mode(pygame, preset, fullscreen=fullscreen)

        def handle_press(pos) -> None:
            nonlocal selected, running, message
            if back_rect.collidepoint(pos):
                running = False
                return
            for label, rect in display_rects.items():
                if rect.collidepoint(pos):
                    set_display(label)
                    return
            for rect, index, _row in row_rects:
                if rect.collidepoint(pos):
                    selected = index
                    message = f"Selected {rows[index].get('game')}."
                    return
            if make_active_rect.collidepoint(pos) and rows:
                row = rows[selected]
                if not row.get("personal_data"):
                    message = "That game is supported, but no personal save is imported yet."
                    return
                try:
                    set_active_game(str(row.get("game")))
                    message = f"Active game: {row.get('game')}"
                except GameSwitcherError as exc:
                    message = str(exc)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and fullscreen:
                    fullscreen = False
                    screen = apply_display_mode(pygame, preset, fullscreen=False)
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    set_display("Fullscreen")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_press(event.pos)
            elif event.type == pygame.FINGERDOWN:
                handle_press((int(event.x * width), int(event.y * height)))

        screen.fill((18, 21, 27))
        _text(screen, title, "Game Switcher", margin, 22, (248, 248, 252), max(200, width - 180))
        _text(screen, small, f"Current focus: {active_game()}", margin + 2, 68, (175, 182, 197), max(200, width - 180))
        _button(screen, pygame, small, "Back", back_rect)

        for rect, index, row in row_rects:
            selected_row = index == selected
            pygame.draw.rect(screen, (62, 70, 88) if selected_row else (35, 40, 50), rect, border_radius=10)
            pygame.draw.rect(screen, (118, 126, 150), rect, width=2 if selected_row else 1, border_radius=10)
            game = str(row.get("game"))
            active = row.get("active")
            label = f"{game}{'  [ACTIVE]' if active else ''}"
            _text(screen, heading, label, rect.x + 14, rect.y + 10, max_width=rect.width - 28)
            _text(screen, small, _summary_line(row), rect.x + 16, rect.y + row_h - 27, (180, 186, 200), rect.width - 32)

        selected_row = rows[selected] if rows else {}
        _button(screen, pygame, body, "Make Active", make_active_rect, enabled=bool(selected_row.get("personal_data")))
        for label, rect in display_rects.items():
            active = (label.lower() == preset and not fullscreen) or (label == "Fullscreen" and fullscreen)
            _button(screen, pygame, small, label, rect, active=active)
        _text(screen, small, message, margin, height - 98, (190, 220, 190), max(200, width - 2 * margin))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
