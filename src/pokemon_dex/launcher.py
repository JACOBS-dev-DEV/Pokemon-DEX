"""Touch/mouse-first home launcher for Pokemon-DEX."""

from __future__ import annotations

from pokemon_dex.display import PRESETS, apply_display_mode, fit_text, font_size_for_height


def _text(screen, font, value, x, y, color=(225, 228, 235), max_width: int | None = None) -> None:
    rendered = fit_text(font, value, max_width) if max_width is not None else str(value)
    screen.blit(font.render(rendered, True, color), (x, y))


def _button(screen, pygame, font, label: str, rect, *, active: bool = False):
    fill = (70, 78, 96) if active else (43, 48, 60)
    pygame.draw.rect(screen, fill, rect, border_radius=12)
    pygame.draw.rect(screen, (118, 126, 150), rect, width=2 if active else 1, border_radius=12)
    surface = font.render(fit_text(font, label, rect.width - 18), True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _run_child(kind: str) -> int:
    if kind == "dex":
        from pokemon_dex.live_gui import run_gui

        return run_gui()
    if kind == "badges":
        from pokemon_dex.badge_gui import run_badge_gui

        return run_badge_gui()
    if kind == "wallet":
        from pokemon_dex.wallet_gui import run_wallet_gui

        return run_wallet_gui()
    return 0


def run_app() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    preset = "standard"
    fullscreen = False

    while True:
        pygame.init()
        pygame.display.set_caption("Pokemon-DEX Home")
        screen = apply_display_mode(pygame, preset, fullscreen=fullscreen)
        clock = pygame.time.Clock()
        running = True
        next_view: str | None = None

        while running:
            width, height = screen.get_size()
            title = pygame.font.Font(None, font_size_for_height(height, 52, minimum=38, maximum=66))
            heading = pygame.font.Font(None, font_size_for_height(height, 29, minimum=22, maximum=38))
            body = pygame.font.Font(None, font_size_for_height(height, 23, minimum=18, maximum=30))
            small = pygame.font.Font(None, font_size_for_height(height, 18, minimum=15, maximum=24))

            gap = max(12, min(24, width // 48))
            horizontal_margin = max(22, min(48, width // 24))
            usable = width - horizontal_margin * 2 - gap * 2
            card_w = max(185, usable // 3)
            total = card_w * 3 + gap * 2
            x0 = max(14, (width - total) // 2)
            y = max(170, int(height * 0.30))
            card_h = max(135, min(180, int(height * 0.24)))
            dex_rect = pygame.Rect(x0, y, card_w, card_h)
            badge_rect = pygame.Rect(x0 + card_w + gap, y, card_w, card_h)
            wallet_rect = pygame.Rect(x0 + 2 * (card_w + gap), y, card_w, card_h)

            display_y = min(height - 150, y + card_h + 46)
            display_gap = 10
            display_labels = ("Compact", "Standard", "Large", "Fullscreen")
            display_w = max(120, min(170, (width - 80 - display_gap * 3) // 4))
            display_total = display_w * 4 + display_gap * 3
            display_x = max(20, (width - display_total) // 2)
            display_rects = {
                label: pygame.Rect(display_x + index * (display_w + display_gap), display_y, display_w, 42)
                for index, label in enumerate(display_labels)
            }
            exit_rect = pygame.Rect((width - 150) // 2, height - 68, 150, 40)

            def change_display(label: str) -> None:
                nonlocal screen, preset, fullscreen
                lowered = label.lower()
                if lowered == "fullscreen":
                    fullscreen = not fullscreen
                else:
                    preset = lowered
                    fullscreen = False
                screen = apply_display_mode(pygame, preset, fullscreen=fullscreen)

            def handle_press(pos):
                nonlocal running, next_view
                if dex_rect.collidepoint(pos):
                    next_view = "dex"
                    running = False
                elif badge_rect.collidepoint(pos):
                    next_view = "badges"
                    running = False
                elif wallet_rect.collidepoint(pos):
                    next_view = "wallet"
                    running = False
                elif exit_rect.collidepoint(pos):
                    next_view = "exit"
                    running = False
                else:
                    for label, rect in display_rects.items():
                        if rect.collidepoint(pos):
                            change_display(label)
                            break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    next_view = "exit"
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and fullscreen:
                        fullscreen = False
                        screen = apply_display_mode(pygame, preset, fullscreen=False)
                    elif event.key == pygame.K_ESCAPE:
                        next_view = "exit"
                        running = False
                    elif event.key == pygame.K_F11:
                        change_display("Fullscreen")
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_press(event.pos)
                elif event.type == pygame.FINGERDOWN:
                    handle_press((int(event.x * width), int(event.y * height)))

            screen.fill((18, 21, 27))
            safe_width = max(120, width - 72)
            _text(screen, title, "Pokemon-DEX", 34, 28, (248, 248, 252), safe_width)
            _text(screen, heading, "Offline Pokédex companion", 36, 80, max_width=safe_width)
            _text(screen, small, "Touch/mouse-first home | choose what you want to manage", 38, 116, (175, 182, 197), safe_width)

            _button(screen, pygame, heading, "Pokédex / Progress", dex_rect)
            inner_w = max(90, dex_rect.width - 38)
            _text(screen, small, "My Dex • Routes • Journey", dex_rect.x + 18, dex_rect.y + card_h - 52, (180, 186, 200), inner_w)
            _text(screen, small, "Battles • live edits", dex_rect.x + 18, dex_rect.y + card_h - 28, (180, 186, 200), inner_w)

            _button(screen, pygame, heading, "Gym Badges", badge_rect)
            inner_w = max(90, badge_rect.width - 36)
            _text(screen, small, "8 Sword badges • tap to check off", badge_rect.x + 18, badge_rect.y + card_h - 52, (180, 186, 200), inner_w)
            _text(screen, small, "backed up before save", badge_rect.x + 18, badge_rect.y + card_h - 28, (180, 186, 200), inner_w)

            _button(screen, pygame, heading, "Game Wallet", wallet_rect)
            inner_w = max(90, wallet_rect.width - 36)
            _text(screen, small, "Poké Dollars • Watts • BP", wallet_rect.x + 18, wallet_rect.y + card_h - 52, (180, 186, 200), inner_w)
            _text(screen, small, "ledger • exact balances", wallet_rect.x + 18, wallet_rect.y + card_h - 28, (180, 186, 200), inner_w)

            _text(screen, small, "Display size", display_x, display_y - 25, (175, 182, 197), max(120, display_total))
            for label, rect in display_rects.items():
                active = (label.lower() == preset and not fullscreen) or (label == "Fullscreen" and fullscreen)
                _button(screen, pygame, small, label, rect, active=active)

            _button(screen, pygame, body, "Exit", exit_rect)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        if next_view == "exit" or next_view is None:
            return 0
        child_code = _run_child(next_view)
        if child_code not in {0, None}:
            return int(child_code)
