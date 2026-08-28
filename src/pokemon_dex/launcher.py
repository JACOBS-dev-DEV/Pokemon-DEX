"""Touch/mouse-first home launcher for Pokemon-DEX."""

from __future__ import annotations


def _text(screen, font, value, x, y, color=(225, 228, 235)) -> None:
    screen.blit(font.render(str(value), True, color), (x, y))


def _button(screen, pygame, font, label: str, rect):
    pygame.draw.rect(screen, (43, 48, 60), rect, border_radius=12)
    pygame.draw.rect(screen, (93, 100, 120), rect, width=1, border_radius=12)
    surface = font.render(label, True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _run_child(kind: str) -> int:
    if kind == "dex":
        from pokemon_dex.live_gui import run_gui

        return run_gui()
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

    while True:
        pygame.init()
        pygame.display.set_caption("Pokemon-DEX Home")
        screen = pygame.display.set_mode((900, 620), pygame.RESIZABLE)
        clock = pygame.time.Clock()
        title = pygame.font.Font(None, 52)
        heading = pygame.font.Font(None, 32)
        body = pygame.font.Font(None, 23)
        small = pygame.font.Font(None, 19)
        running = True
        next_view: str | None = None

        while running:
            width, height = screen.get_size()
            card_w = min(330, max(240, (width - 96) // 2))
            gap = 28
            total = card_w * 2 + gap
            x0 = max(24, (width - total) // 2)
            y = 210
            dex_rect = pygame.Rect(x0, y, card_w, 150)
            wallet_rect = pygame.Rect(x0 + card_w + gap, y, card_w, 150)
            exit_rect = pygame.Rect((width - 160) // 2, height - 88, 160, 44)

            def handle_press(pos):
                nonlocal running, next_view
                if dex_rect.collidepoint(pos):
                    next_view = "dex"
                    running = False
                elif wallet_rect.collidepoint(pos):
                    next_view = "wallet"
                    running = False
                elif exit_rect.collidepoint(pos):
                    next_view = "exit"
                    running = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    next_view = "exit"
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    next_view = "exit"
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    handle_press(event.pos)
                elif event.type == pygame.FINGERDOWN:
                    handle_press((int(event.x * width), int(event.y * height)))

            screen.fill((18, 21, 27))
            _text(screen, title, "Pokemon-DEX", 34, 32, (248, 248, 252))
            _text(screen, heading, "Offline Pokédex companion", 36, 84)
            _text(screen, small, "Touch/mouse-first home | choose what you want to manage", 38, 120, (175, 182, 197))

            _button(screen, pygame, heading, "Pokédex / Progress", dex_rect)
            _text(screen, small, "My Dex • Routes • Journey • Battles", dex_rect.x + 26, dex_rect.y + 96, (180, 186, 200))
            _button(screen, pygame, heading, "Game Wallet", wallet_rect)
            _text(screen, small, "Poké Dollars • Watts • BP • ledger", wallet_rect.x + 26, wallet_rect.y + 96, (180, 186, 200))
            _button(screen, pygame, body, "Exit", exit_rect)

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        if next_view == "exit" or next_view is None:
            return 0
        child_code = _run_child(next_view)
        if child_code not in {0, None}:
            return int(child_code)
