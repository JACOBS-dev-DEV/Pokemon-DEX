"""Touch/mouse-first badge tracker for Pokemon-DEX."""

from __future__ import annotations

from pokemon_dex.badges import BadgeError, badge_summary, load_badges, toggle_badge


def _text(screen, font, value, x, y, color=(225, 228, 235)) -> None:
    screen.blit(font.render(str(value), True, color), (x, y))


def _button(screen, pygame, font, label: str, rect, active: bool = False):
    fill = (72, 79, 98) if active else (43, 48, 60)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, (93, 100, 120), rect, width=1, border_radius=10)
    surface = font.render(label, True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def run_badge_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Badge Tracker")
    screen = pygame.display.set_mode((980, 720), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    title = pygame.font.Font(None, 44)
    heading = pygame.font.Font(None, 30)
    body = pygame.font.Font(None, 23)
    small = pygame.font.Font(None, 19)
    message = "Tap a badge to toggle it when you actually earn it."
    running = True

    while running:
        width, height = screen.get_size()
        data = load_badges()
        badges = data.get("badges", [])
        summary = badge_summary()
        card_gap = 12
        card_h = 58
        left = 40
        top = 150
        card_w = min(560, max(430, int(width * 0.60)))
        back_rect = pygame.Rect(width - 150, 28, 112, 40)
        badge_rects = []
        for index, badge in enumerate(badges):
            badge_rects.append((pygame.Rect(left, top + index * (card_h + card_gap), card_w, card_h), badge))

        def handle_press(pos) -> None:
            nonlocal running, message
            if back_rect.collidepoint(pos):
                running = False
                return
            for rect, badge in badge_rects:
                if rect.collidepoint(pos):
                    try:
                        updated = toggle_badge(str(badge.get("badge_id")))
                        state = "obtained" if updated.get("obtained") else "not obtained"
                        message = f"{updated.get('badge_name')} marked {state}. Backup created."
                    except BadgeError as exc:
                        message = f"Badge edit error: {exc}"
                    return

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
        _text(screen, title, "Pokemon Sword — Gym Badges", 34, 28, (248, 248, 252))
        _text(screen, body, f"Obtained {summary.get('obtained', 0)} / {summary.get('total', 0)}", 38, 82)
        next_badge = summary.get("next_badge")
        if next_badge:
            _text(screen, small, f"Next tracked badge: {next_badge.get('badge_name')} — {next_badge.get('location')}", 38, 112, (180, 186, 200))
        else:
            _text(screen, small, "All tracked badges obtained.", 38, 112, (180, 186, 200))
        _button(screen, pygame, body, "Back", back_rect)

        for rect, badge in badge_rects:
            obtained = bool(badge.get("obtained"))
            pygame.draw.rect(screen, (64, 71, 88) if obtained else (36, 41, 51), rect, border_radius=9)
            pygame.draw.rect(screen, (93, 100, 120), rect, width=1, border_radius=9)
            marker = "✓" if obtained else "□"
            _text(screen, heading, f"{marker} {badge.get('order')}. {badge.get('badge_name')}", rect.x + 14, rect.y + 8)
            _text(screen, small, f"{badge.get('gym_leader')} • {badge.get('location')}", rect.x + 315, rect.y + 20, (180, 186, 200))

        _text(screen, small, message[:100], 38, height - 42, (190, 220, 190))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
