"""Touch/mouse-first home launcher for Pokemon-DEX."""

from __future__ import annotations

from pokemon_dex.display import apply_display_mode, fit_text, font_size_for_height


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
    if kind == "team":
        from pokemon_dex.team_gui import run_team_gui

        return run_team_gui()
    if kind == "badges":
        from pokemon_dex.badge_gui import run_badge_gui

        return run_badge_gui()
    if kind == "wallet":
        from pokemon_dex.wallet_gui import run_wallet_gui

        return run_wallet_gui()
    if kind == "custom":
        from pokemon_dex.custom_battle_gui import run_custom_battle_gui

        return run_custom_battle_gui()
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
            title = pygame.font.Font(None, font_size_for_height(height, 52, minimum=36, maximum=66))
            heading = pygame.font.Font(None, font_size_for_height(height, 26, minimum=20, maximum=34))
            body = pygame.font.Font(None, font_size_for_height(height, 22, minimum=18, maximum=29))
            small = pygame.font.Font(None, font_size_for_height(height, 17, minimum=14, maximum=23))

            margin = max(16, min(38, width // 30))
            gap = max(10, min(18, width // 58))
            grid_top = max(136, int(height * 0.21))
            display_space = 120
            grid_bottom = max(grid_top + 250, height - display_space - 20)
            grid_height = max(250, grid_bottom - grid_top)
            card_w = max(190, (width - margin * 2 - gap * 2) // 3)
            card_h = max(110, (grid_height - gap) // 2)

            positions = {
                "dex": (0, 0),
                "team": (1, 0),
                "badges": (2, 0),
                "wallet": (0, 1),
                "custom": (1, 1),
            }
            cards = {
                key: pygame.Rect(
                    margin + col * (card_w + gap),
                    grid_top + row * (card_h + gap),
                    card_w,
                    card_h,
                )
                for key, (col, row) in positions.items()
            }

            display_y = min(height - 62, grid_top + card_h * 2 + gap + 24)
            display_gap = 8
            display_labels = ("Compact", "Standard", "Large", "Fullscreen")
            display_w = max(98, min(150, (width - 64 - display_gap * 3) // 4))
            display_total = display_w * 4 + display_gap * 3
            display_x = max(14, (width - display_total) // 2)
            display_rects = {
                label: pygame.Rect(display_x + index * (display_w + display_gap), display_y, display_w, 38)
                for index, label in enumerate(display_labels)
            }
            exit_rect = pygame.Rect(width - 116 - margin, 22, 116, 38)

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
                for kind, rect in cards.items():
                    if rect.collidepoint(pos):
                        next_view = kind
                        running = False
                        return
                if exit_rect.collidepoint(pos):
                    next_view = "exit"
                    running = False
                    return
                for label, rect in display_rects.items():
                    if rect.collidepoint(pos):
                        change_display(label)
                        return

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
            safe_width = max(120, width - 180)
            _text(screen, title, "Pokemon-DEX", margin, 22, (248, 248, 252), safe_width)
            _text(screen, heading, "Offline Pokédex companion", margin + 2, 72, max_width=safe_width)
            _text(screen, small, "Touch/mouse-first • live save tracking • team tools • custom battles", margin + 2, 106, (175, 182, 197), safe_width)
            _button(screen, pygame, small, "Exit", exit_rect)

            card_content = {
                "dex": ("Pokédex / Progress", "My Dex • Routes • Journey", "live edits • normal battles"),
                "team": ("Team Manager", "current six • HP • moves", "held items • party details"),
                "badges": ("Gym Badges", "8 Sword badges", "tap to check off safely"),
                "wallet": ("Game Wallet", "Poké Dollars • Watts • BP", "ledger • exact balances"),
                "custom": ("Custom Battles", "1v1 • 2v2 • 1v2 • 1v3", "simultaneous uneven fights"),
            }
            for kind, rect in cards.items():
                label, line1, line2 = card_content[kind]
                _button(screen, pygame, heading, label, rect)
                inner_w = max(80, rect.width - 30)
                _text(screen, small, line1, rect.x + 15, rect.bottom - 48, (180, 186, 200), inner_w)
                _text(screen, small, line2, rect.x + 15, rect.bottom - 25, (180, 186, 200), inner_w)

            _text(screen, small, "Display size", display_x, display_y - 21, (175, 182, 197), max(120, display_total))
            for label, rect in display_rects.items():
                active = (label.lower() == preset and not fullscreen) or (label == "Fullscreen" and fullscreen)
                _button(screen, pygame, small, label, rect, active=active)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        if next_view == "exit" or next_view is None:
            return 0
        child_code = _run_child(next_view)
        if child_code not in {0, None}:
            return int(child_code)
