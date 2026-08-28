"""Touch/mouse-first manager for the active Pokemon Sword party."""

from __future__ import annotations

from pokemon_dex.display import apply_display_mode, draw_wrapped_text, fit_text, font_size_for_height
from pokemon_dex.team import load_team
from pokemon_dex.team_items import TeamItemError, load_team_items, set_held_item, swap_held_items


def _button(screen, pygame, font, label: str, rect, *, active: bool = False):
    fill = (72, 80, 100) if active else (43, 48, 60)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, (112, 121, 145), rect, width=2 if active else 1, border_radius=10)
    surface = font.render(fit_text(font, label, rect.width - 16), True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _text(screen, font, value, x, y, color=(225, 228, 235), max_width: int | None = None) -> None:
    rendered = fit_text(font, value, max_width) if max_width is not None else str(value)
    screen.blit(font.render(rendered, True, color), (x, y))


def _item_for_slot(item_data: dict, slot: int) -> dict:
    return next(
        (row for row in item_data.get("team_items", []) if int(row.get("slot", 0)) == int(slot)),
        {"slot": slot, "held_item": None, "history": []},
    )


def run_team_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    preset = "standard"
    fullscreen = False
    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Team Manager")
    screen = apply_display_mode(pygame, preset, fullscreen=fullscreen)
    clock = pygame.time.Clock()
    selected = 0
    message = "Tap a party slot to inspect it."
    running = True

    def reload_data():
        return load_team(), load_team_items()

    team_data, item_data = reload_data()

    while running:
        width, height = screen.get_size()
        team = list(team_data.get("team", []))
        if team:
            selected = max(0, min(selected, len(team) - 1))

        title = pygame.font.Font(None, font_size_for_height(height, 42, minimum=32, maximum=54))
        heading = pygame.font.Font(None, font_size_for_height(height, 29, minimum=22, maximum=38))
        body = pygame.font.Font(None, font_size_for_height(height, 22, minimum=17, maximum=29))
        small = pygame.font.Font(None, font_size_for_height(height, 18, minimum=14, maximum=24))

        margin = max(18, min(34, width // 36))
        header_h = 126
        footer_h = 104
        left_w = max(300, min(430, int(width * 0.34)))
        gap = 16
        panel_top = header_h
        panel_bottom = height - footer_h
        left = pygame.Rect(margin, panel_top, left_w, max(220, panel_bottom - panel_top))
        right = pygame.Rect(left.right + gap, panel_top, max(340, width - left.right - gap - margin), left.height)

        back_rect = pygame.Rect(width - 112 - margin, 24, 112, 38)
        display_labels = ("Compact", "Standard", "Large", "Fullscreen")
        display_w = max(92, min(126, (width - 2 * margin - 18 * 3) // 4))
        display_y = 72
        display_rects = {
            label: pygame.Rect(margin + index * (display_w + 8), display_y, display_w, 36)
            for index, label in enumerate(display_labels)
        }

        row_gap = 8
        row_h = max(48, min(68, (left.height - 24 - row_gap * 5) // 6))
        slot_rects: list[tuple[object, int]] = []
        for index in range(min(6, len(team))):
            rect = pygame.Rect(left.x + 12, left.y + 12 + index * (row_h + row_gap), left.width - 24, row_h)
            slot_rects.append((rect, index))

        action_y = height - 78
        action_gap = 8
        labels = ("Prev", "Next", "Clear Item", "Swap Up", "Swap Down")
        action_w = max(110, min(150, (width - 2 * margin - action_gap * (len(labels) - 1)) // len(labels)))
        action_total = action_w * len(labels) + action_gap * (len(labels) - 1)
        action_x = max(margin, (width - action_total) // 2)
        action_rects = {
            label: pygame.Rect(action_x + i * (action_w + action_gap), action_y, action_w, 42)
            for i, label in enumerate(labels)
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

        def refresh(msg: str) -> None:
            nonlocal team_data, item_data, message
            team_data, item_data = reload_data()
            message = msg

        def handle_press(pos) -> None:
            nonlocal selected, running, message
            if back_rect.collidepoint(pos):
                running = False
                return
            for label, rect in display_rects.items():
                if rect.collidepoint(pos):
                    set_display(label)
                    return
            for rect, index in slot_rects:
                if rect.collidepoint(pos):
                    selected = index
                    message = f"Selected team slot {index + 1}."
                    return
            if not team:
                return
            slot = int(team[selected].get("slot", selected + 1))
            try:
                if action_rects["Prev"].collidepoint(pos):
                    selected = (selected - 1) % len(team)
                    return
                if action_rects["Next"].collidepoint(pos):
                    selected = (selected + 1) % len(team)
                    return
                if action_rects["Clear Item"].collidepoint(pos):
                    set_held_item(slot, None, reason="cleared from Team Manager")
                    refresh(f"Cleared held item for slot {slot}. Backup created.")
                    return
                if action_rects["Swap Up"].collidepoint(pos):
                    target = slot - 1
                    if target < 1:
                        message = "Slot 1 has no slot above it."
                        return
                    swap_held_items(slot, target, reason="Team Manager swap up")
                    refresh(f"Swapped held items between slots {slot} and {target}.")
                    return
                if action_rects["Swap Down"].collidepoint(pos):
                    target = slot + 1
                    if target > 6:
                        message = "Slot 6 has no slot below it."
                        return
                    swap_held_items(slot, target, reason="Team Manager swap down")
                    refresh(f"Swapped held items between slots {slot} and {target}.")
            except TeamItemError as exc:
                message = f"Item edit error: {exc}"

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
        _text(screen, title, "Team Manager", margin, 20, (248, 248, 252), max(160, width - 190))
        trainer_name = team_data.get("trainer_name", "Trainer")
        trainer_id = team_data.get("trainer_id", "-")
        _text(screen, small, f"{trainer_name} • Trainer ID {trainer_id} • active party snapshot", margin + 2, 54, (175, 182, 197), max(160, width - 190))
        _button(screen, pygame, small, "Back", back_rect)

        for label, rect in display_rects.items():
            active = (label.lower() == preset and not fullscreen) or (label == "Fullscreen" and fullscreen)
            _button(screen, pygame, small, label, rect, active=active)

        pygame.draw.rect(screen, (29, 33, 41), left, border_radius=10)
        pygame.draw.rect(screen, (29, 33, 41), right, border_radius=10)

        _text(screen, heading, "Current party", left.x + 14, left.y + 10, max_width=left.width - 28)
        if not team:
            _text(screen, body, "No active party is configured.", left.x + 16, left.y + 54, max_width=left.width - 32)
        else:
            for rect, index in slot_rects:
                member = team[index]
                active = index == selected
                pygame.draw.rect(screen, (64, 72, 91) if active else (39, 44, 55), rect, border_radius=8)
                pygame.draw.rect(screen, (118, 126, 150), rect, width=2 if active else 1, border_radius=8)
                species = member.get("species_name", "Unknown")
                level = member.get("level", "-")
                hp = f"{member.get('current_hp', '-')}/{member.get('max_hp', '-')}"
                sex = member.get("sex") or "?"
                _text(screen, body, f"{index + 1}. {species}  Lv.{level}", rect.x + 10, rect.y + 8, max_width=rect.width - 20)
                _text(screen, small, f"HP {hp} • {sex} • {member.get('status', 'unknown')}", rect.x + 10, rect.y + row_h - 25, (180, 186, 200), rect.width - 20)

        _text(screen, heading, "Pokemon details", right.x + 16, right.y + 12, max_width=right.width - 32)
        if team:
            member = team[selected]
            slot = int(member.get("slot", selected + 1))
            item_row = _item_for_slot(item_data, slot)
            held_item = item_row.get("held_item") or "None"
            species = member.get("species_name", "Unknown")
            y = right.y + 54
            detail_lines = [
                f"Slot {slot}: {species}",
                f"Level {member.get('level', '-')} • HP {member.get('current_hp', '-')}/{member.get('max_hp', '-')} • {member.get('status', 'unknown')}",
                f"Sex: {member.get('sex') or 'unknown'} • Type: {member.get('type_1') or 'unknown'}{(' / ' + str(member.get('type_2'))) if member.get('type_2') else ''}",
                f"Held item: {held_item}",
            ]
            for line in detail_lines:
                _text(screen, body, line, right.x + 18, y, max_width=right.width - 36)
                y += body.get_linesize() + 5

            stats = member.get("stats") or {}
            if stats:
                y += 5
                _text(screen, heading, "Stats", right.x + 18, y, max_width=right.width - 36)
                y += heading.get_linesize() + 3
                stat_text = " • ".join(
                    f"{name.replace('_', ' ').title()} {value}"
                    for name, value in stats.items()
                )
                stat_rect = pygame.Rect(right.x + 18, y, right.width - 36, max(44, right.height // 7))
                y = draw_wrapped_text(screen, small, stat_text, stat_rect, (190, 196, 208), line_gap=3, max_lines=3) + 4

            ability = member.get("ability")
            if ability:
                _text(screen, body, f"Ability: {ability}", right.x + 18, y, max_width=right.width - 36)
                y += body.get_linesize() + 3
                desc = member.get("ability_description")
                if desc:
                    desc_rect = pygame.Rect(right.x + 18, y, right.width - 36, max(42, right.height // 8))
                    y = draw_wrapped_text(screen, small, desc, desc_rect, (180, 186, 200), line_gap=2, max_lines=3) + 6

            moves = member.get("moves") or []
            _text(screen, heading, "Moves", right.x + 18, y, max_width=right.width - 36)
            y += heading.get_linesize() + 2
            if moves:
                for move in moves[:4]:
                    if isinstance(move, dict):
                        move_name = move.get("name", "Unknown Move")
                        pp = f"{move.get('pp', '-')}/{move.get('max_pp', '-')} PP"
                        move_type = move.get("type", "-")
                        line = f"{move_name} • {move_type} • {pp}"
                    else:
                        line = str(move)
                    if y + small.get_linesize() > right.bottom - 118:
                        break
                    _text(screen, small, line, right.x + 20, y, (205, 209, 220), right.width - 40)
                    y += small.get_linesize() + 4
            else:
                _text(screen, small, "Move details not captured for this party slot yet.", right.x + 20, y, (175, 182, 197), right.width - 40)
                y += small.get_linesize() + 4

            history = item_row.get("history", [])
            history_y = max(y + 8, right.bottom - 104)
            _text(screen, small, f"Held-item changes logged: {len(history)}", right.x + 18, history_y, (175, 182, 197), right.width - 36)
            if history:
                latest = history[-1]
                latest_text = f"Latest: {latest.get('from') or 'None'} → {latest.get('to') or 'None'}"
                _text(screen, small, latest_text, right.x + 18, history_y + 23, (175, 182, 197), right.width - 36)

        _text(screen, small, message, margin, height - 101, (190, 220, 190), max(200, width - 2 * margin))
        for label, rect in action_rects.items():
            _button(screen, pygame, small, label, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
