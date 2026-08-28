"""Touch-first UI for uneven/custom Pokemon battle simulations."""

from __future__ import annotations

from pokemon_dex.custom_battle import MultiBattleState, new_custom_battle, perform_multi_round
from pokemon_dex.display import fit_text, font_size_for_height


def _text(screen, font, value, x, y, color=(225, 228, 235), max_width: int | None = None) -> None:
    rendered = fit_text(font, value, max_width) if max_width is not None else str(value)
    screen.blit(font.render(rendered, True, color), (x, y))


def _button(screen, pygame, font, label: str, rect, active: bool = False):
    fill = (70, 78, 96) if active else (43, 48, 60)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, (112, 120, 145), rect, width=2 if active else 1, border_radius=10)
    surface = font.render(fit_text(font, label, rect.width - 16), True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _format_counts(label: str) -> tuple[int, int]:
    left, right = label.lower().split("v", 1)
    return int(left), int(right)


def _draw_side(screen, pygame, font, small, rect, title: str, members) -> None:
    pygame.draw.rect(screen, (29, 33, 41), rect, border_radius=10)
    _text(screen, font, title, rect.x + 14, rect.y + 12, max_width=rect.width - 28)
    y = rect.y + 52
    for _, pokemon in members:
        status = "FAINTED" if pokemon.fainted else f"HP {pokemon.hp}/{pokemon.max_hp}"
        _text(screen, small, f"{pokemon.species_name} Lv.{pokemon.level} — {status}", rect.x + 16, y, max_width=rect.width - 32)
        y += 30


def run_custom_battle_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Custom Battles")
    screen = pygame.display.set_mode((1120, 760), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    formats = ("1v1", "2v2", "1v2", "1v3")
    selected_format = "1v3"
    battle: MultiBattleState | None = new_custom_battle(1, 3)
    running = True

    while running:
        width, height = screen.get_size()
        title = pygame.font.Font(None, font_size_for_height(height, 42, minimum=32, maximum=54))
        heading = pygame.font.Font(None, font_size_for_height(height, 28, minimum=22, maximum=36))
        body = pygame.font.Font(None, font_size_for_height(height, 22, minimum=18, maximum=29))
        small = pygame.font.Font(None, font_size_for_height(height, 18, minimum=15, maximum=24))

        margin = max(18, width // 48)
        gap = 10
        button_w = max(90, min(140, (width - margin * 2 - gap * 5) // 6))
        top_y = 92
        format_rects = {
            label: pygame.Rect(margin + i * (button_w + gap), top_y, button_w, 42)
            for i, label in enumerate(formats)
        }
        next_rect = pygame.Rect(margin + 4 * (button_w + gap), top_y, button_w, 42)
        reset_rect = pygame.Rect(margin + 5 * (button_w + gap), top_y, button_w, 42)
        back_rect = pygame.Rect(width - 130, 24, 110, 38)

        panel_y = 160
        panel_h = max(180, int(height * 0.38))
        panel_gap = 16
        panel_w = (width - margin * 2 - panel_gap) // 2
        left = pygame.Rect(margin, panel_y, panel_w, panel_h)
        right = pygame.Rect(margin + panel_w + panel_gap, panel_y, panel_w, panel_h)
        log_rect = pygame.Rect(margin, panel_y + panel_h + 18, width - margin * 2, height - (panel_y + panel_h + 36))

        def reset_battle(label: str) -> None:
            nonlocal battle, selected_format
            selected_format = label
            player_count, enemy_count = _format_counts(label)
            battle = new_custom_battle(player_count, enemy_count)

        def handle_press(pos) -> None:
            nonlocal running
            if back_rect.collidepoint(pos):
                running = False
                return
            for label, rect in format_rects.items():
                if rect.collidepoint(pos):
                    reset_battle(label)
                    return
            if next_rect.collidepoint(pos) and battle:
                perform_multi_round(battle)
            elif reset_rect.collidepoint(pos):
                reset_battle(selected_format)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_press(event.pos)
            elif event.type == pygame.FINGERDOWN:
                handle_press((int(event.x * width), int(event.y * height)))

        screen.fill((18, 21, 27))
        _text(screen, title, "Custom Battle Sandbox", margin, 24, (248, 248, 252), width - margin * 2 - 150)
        _button(screen, pygame, small, "Back", back_rect)

        for label, rect in format_rects.items():
            _button(screen, pygame, body, label, rect, active=(label == selected_format))
        _button(screen, pygame, body, "Next Round", next_rect)
        _button(screen, pygame, body, "Reset", reset_rect)

        if battle:
            _draw_side(screen, pygame, heading, body, left, f"Your side — {selected_format}", battle.active_players())
            _draw_side(screen, pygame, heading, body, right, "Opponent side", battle.active_enemies())
            pygame.draw.rect(screen, (29, 33, 41), log_rect, border_radius=10)
            winner = f" | Winner: {battle.winner}" if battle.winner else ""
            _text(screen, heading, f"Round {battle.round_number}{winner}", log_rect.x + 14, log_rect.y + 12, max_width=log_rect.width - 28)
            lines = battle.log[-10:] if battle.log else ["Tap Next Round to begin."]
            y = log_rect.y + 52
            for line in lines:
                if y + 24 > log_rect.bottom:
                    break
                _text(screen, small, line, log_rect.x + 16, y, (190, 196, 210), log_rect.width - 32)
                y += 24
        else:
            _text(screen, body, "No configured battle roster is available yet.", margin, panel_y + 20)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
