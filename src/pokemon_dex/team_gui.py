"""Touch/mouse-first manager for the active Pokemon Sword or Shield party."""

from __future__ import annotations

from pokemon_dex.display import apply_display_mode, draw_wrapped_text, fit_text, font_size_for_height
from pokemon_dex.team import (
    TeamError,
    load_team,
    owned_candidates,
    remove_team_slot,
    replace_team_slot,
    swap_team_slots,
)
from pokemon_dex.team_items import (
    TeamItemError,
    load_team_items,
    set_held_item,
    swap_held_items,
    sync_team_item_species,
)


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
        {"slot": slot, "species_name": None, "held_item": None, "history": []},
    )


def _member_for_slot(team_data: dict, slot: int) -> dict | None:
    return next((row for row in team_data.get("team", []) if int(row.get("slot", 0)) == int(slot)), None)


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

    selected_slot = 1
    candidate_mode = False
    candidate_page = 0
    selected_candidate_id: int | None = None
    message = "Tap a party slot. Choose Pokemon lets you replace or fill it."
    running = True

    def reload_data():
        return load_team(), load_team_items(), owned_candidates()

    team_data, item_data, candidates = reload_data()

    def refresh(msg: str) -> None:
        nonlocal team_data, item_data, candidates, message, candidate_page, selected_candidate_id
        team_data, item_data, candidates = reload_data()
        pages = max(1, (len(candidates) + 5) // 6)
        candidate_page = max(0, min(candidate_page, pages - 1))
        if selected_candidate_id is not None and not any(
            int(row.get("local_id", -1)) == selected_candidate_id for row in candidates
        ):
            selected_candidate_id = None
        message = msg

    while running:
        width, height = screen.get_size()
        title = pygame.font.Font(None, font_size_for_height(height, 42, minimum=32, maximum=54))
        heading = pygame.font.Font(None, font_size_for_height(height, 28, minimum=21, maximum=36))
        body = pygame.font.Font(None, font_size_for_height(height, 21, minimum=16, maximum=28))
        small = pygame.font.Font(None, font_size_for_height(height, 17, minimum=13, maximum=23))

        margin = max(16, min(34, width // 36))
        header_h = 126
        footer_h = 116
        panel_top = header_h
        panel_bottom = height - footer_h
        gap = max(12, min(18, width // 70))
        left_w = max(300, min(430, int(width * 0.36)))
        left = pygame.Rect(margin, panel_top, left_w, max(250, panel_bottom - panel_top))
        right = pygame.Rect(left.right + gap, panel_top, max(320, width - left.right - gap - margin), left.height)

        back_rect = pygame.Rect(width - 112 - margin, 24, 112, 38)
        display_labels = ("Compact", "Standard", "Large", "Fullscreen")
        display_w = max(90, min(126, (width - 2 * margin - 24) // 4))
        display_rects = {
            label: pygame.Rect(margin + index * (display_w + 8), 72, display_w, 36)
            for index, label in enumerate(display_labels)
        }

        row_gap = 7
        row_h = max(48, min(68, (left.height - 40 - row_gap * 5) // 6))
        slot_rects: list[tuple[object, int]] = []
        for slot in range(1, 7):
            rect = pygame.Rect(left.x + 12, left.y + 34 + (slot - 1) * (row_h + row_gap), left.width - 24, row_h)
            slot_rects.append((rect, slot))

        action_y = height - 82
        action_gap = 8
        if candidate_mode:
            action_labels = ("Prev Page", "Next Page", "Put in Slot", "Cancel")
        else:
            action_labels = ("Choose Pokemon", "Remove", "Move Up", "Move Down", "Clear Item")
        action_w = max(105, min(158, (width - 2 * margin - action_gap * (len(action_labels) - 1)) // len(action_labels)))
        action_total = action_w * len(action_labels) + action_gap * (len(action_labels) - 1)
        action_x = max(margin, (width - action_total) // 2)
        action_rects = {
            label: pygame.Rect(action_x + index * (action_w + action_gap), action_y, action_w, 42)
            for index, label in enumerate(action_labels)
        }

        candidate_rects: list[tuple[object, dict]] = []
        if candidate_mode:
            page_rows = candidates[candidate_page * 6 : candidate_page * 6 + 6]
            candidate_row_h = max(48, min(64, (right.height - 78 - row_gap * 5) // 6))
            for index, candidate in enumerate(page_rows):
                rect = pygame.Rect(
                    right.x + 14,
                    right.y + 58 + index * (candidate_row_h + row_gap),
                    right.width - 28,
                    candidate_row_h,
                )
                candidate_rects.append((rect, candidate))

        def set_display(label: str) -> None:
            nonlocal screen, preset, fullscreen
            lowered = label.lower()
            if lowered == "fullscreen":
                fullscreen = not fullscreen
            else:
                preset = lowered
                fullscreen = False
            screen = apply_display_mode(pygame, preset, fullscreen=fullscreen)

        def sync_items_after_membership_change(new_team: dict, *, clear_changed: bool, reason: str) -> None:
            sync_team_item_species(
                list(new_team.get("team", [])),
                clear_changed_items=clear_changed,
                reason=reason,
            )

        def handle_press(pos) -> None:
            nonlocal selected_slot, running, candidate_mode, candidate_page, selected_candidate_id, message
            if back_rect.collidepoint(pos):
                running = False
                return
            for label, rect in display_rects.items():
                if rect.collidepoint(pos):
                    set_display(label)
                    return
            for rect, slot in slot_rects:
                if rect.collidepoint(pos):
                    selected_slot = slot
                    candidate_mode = False
                    selected_candidate_id = None
                    member = _member_for_slot(team_data, slot)
                    message = f"Selected slot {slot}: {member.get('species_name') if member else 'empty'}."
                    return

            if candidate_mode:
                for rect, candidate in candidate_rects:
                    if rect.collidepoint(pos):
                        selected_candidate_id = int(candidate.get("local_id"))
                        message = f"Selected {candidate.get('species_name')} for slot {selected_slot}."
                        return
                pages = max(1, (len(candidates) + 5) // 6)
                if action_rects["Prev Page"].collidepoint(pos):
                    candidate_page = (candidate_page - 1) % pages
                    selected_candidate_id = None
                    return
                if action_rects["Next Page"].collidepoint(pos):
                    candidate_page = (candidate_page + 1) % pages
                    selected_candidate_id = None
                    return
                if action_rects["Cancel"].collidepoint(pos):
                    candidate_mode = False
                    selected_candidate_id = None
                    message = "Team edit cancelled."
                    return
                if action_rects["Put in Slot"].collidepoint(pos):
                    if selected_candidate_id is None:
                        message = "Tap a Pokemon first, then Put in Slot."
                        return
                    try:
                        new_team = replace_team_slot(selected_slot, selected_candidate_id)
                        sync_items_after_membership_change(
                            new_team,
                            clear_changed=True,
                            reason="Team Manager replacement",
                        )
                        chosen = _member_for_slot(new_team, selected_slot)
                        candidate_mode = False
                        selected_candidate_id = None
                        refresh(f"Slot {selected_slot} is now {chosen.get('species_name') if chosen else 'empty'}. Backup created.")
                    except (TeamError, TeamItemError) as exc:
                        message = f"Team edit error: {exc}"
                    return
                return

            member = _member_for_slot(team_data, selected_slot)
            try:
                if action_rects["Choose Pokemon"].collidepoint(pos):
                    candidates[:] = owned_candidates()
                    candidate_page = 0
                    selected_candidate_id = None
                    candidate_mode = True
                    message = (
                        f"Choose an owned Pokemon for slot {selected_slot}."
                        if candidates
                        else "No owned Pokemon are currently available outside the party."
                    )
                    return
                if action_rects["Remove"].collidepoint(pos):
                    if member is None:
                        message = f"Slot {selected_slot} is already empty."
                        return
                    old_species = member.get("species_name", "Pokemon")
                    new_team = remove_team_slot(selected_slot)
                    sync_items_after_membership_change(
                        new_team,
                        clear_changed=True,
                        reason="Team Manager removal",
                    )
                    refresh(f"Removed {old_species} from slot {selected_slot}. It is still owned. Backup created.")
                    return
                if action_rects["Move Up"].collidepoint(pos):
                    if member is None:
                        message = f"Slot {selected_slot} is empty."
                        return
                    target = selected_slot - 1
                    if target < 1:
                        message = "Slot 1 has no slot above it."
                        return
                    new_team = swap_team_slots(selected_slot, target)
                    swap_held_items(selected_slot, target, reason="Team Manager party move up")
                    sync_items_after_membership_change(
                        new_team,
                        clear_changed=False,
                        reason="Team Manager party reorder",
                    )
                    selected_slot = target
                    refresh(f"Moved the Pokemon to slot {target}. Held item moved with it.")
                    return
                if action_rects["Move Down"].collidepoint(pos):
                    if member is None:
                        message = f"Slot {selected_slot} is empty."
                        return
                    target = selected_slot + 1
                    if target > 6:
                        message = "Slot 6 has no slot below it."
                        return
                    new_team = swap_team_slots(selected_slot, target)
                    swap_held_items(selected_slot, target, reason="Team Manager party move down")
                    sync_items_after_membership_change(
                        new_team,
                        clear_changed=False,
                        reason="Team Manager party reorder",
                    )
                    selected_slot = target
                    refresh(f"Moved the Pokemon to slot {target}. Held item moved with it.")
                    return
                if action_rects["Clear Item"].collidepoint(pos):
                    if member is None:
                        message = f"Slot {selected_slot} is empty."
                        return
                    set_held_item(selected_slot, None, reason="cleared from Team Manager")
                    refresh(f"Cleared held item for slot {selected_slot}. Backup created.")
                    return
            except (TeamError, TeamItemError) as exc:
                message = f"Team edit error: {exc}"

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and fullscreen:
                    fullscreen = False
                    screen = apply_display_mode(pygame, preset, fullscreen=False)
                elif event.key == pygame.K_ESCAPE and candidate_mode:
                    candidate_mode = False
                    selected_candidate_id = None
                    message = "Team edit cancelled."
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
        game_name = team_data.get("game", "Pokemon")
        _text(
            screen,
            small,
            f"{game_name} • {trainer_name} • Trainer ID {trainer_id} • tap a slot to manage it",
            margin + 2,
            54,
            (175, 182, 197),
            max(160, width - 190),
        )
        _button(screen, pygame, small, "Back", back_rect)

        for label, rect in display_rects.items():
            active = (label.lower() == preset and not fullscreen) or (label == "Fullscreen" and fullscreen)
            _button(screen, pygame, small, label, rect, active=active)

        pygame.draw.rect(screen, (29, 33, 41), left, border_radius=10)
        pygame.draw.rect(screen, (29, 33, 41), right, border_radius=10)
        _text(screen, heading, "Current party", left.x + 14, left.y + 8, max_width=left.width - 28)

        for rect, slot in slot_rects:
            member = _member_for_slot(team_data, slot)
            active = slot == selected_slot
            pygame.draw.rect(screen, (64, 72, 91) if active else (39, 44, 55), rect, border_radius=8)
            pygame.draw.rect(screen, (118, 126, 150), rect, width=2 if active else 1, border_radius=8)
            if member is None:
                _text(screen, body, f"{slot}. Empty slot", rect.x + 10, rect.y + 9, (190, 196, 208), rect.width - 20)
                _text(screen, small, "Tap Choose Pokemon to fill", rect.x + 10, rect.bottom - 24, (150, 158, 176), rect.width - 20)
                continue
            species = member.get("species_name", "Unknown")
            level = member.get("level", "-")
            hp = f"{member.get('current_hp', '-')}/{member.get('max_hp', '-')}"
            sex = member.get("sex") or "?"
            _text(screen, body, f"{slot}. {species}  Lv.{level}", rect.x + 10, rect.y + 8, max_width=rect.width - 20)
            _text(screen, small, f"HP {hp} • {sex} • {member.get('status', 'unknown')}", rect.x + 10, rect.bottom - 24, (180, 186, 200), rect.width - 20)

        if candidate_mode:
            pages = max(1, (len(candidates) + 5) // 6)
            _text(screen, heading, f"Choose Pokemon for slot {selected_slot}", right.x + 16, right.y + 12, max_width=right.width - 32)
            _text(
                screen,
                small,
                f"Available outside party: {len(candidates)} • page {candidate_page + 1}/{pages}",
                right.x + 18,
                right.y + 39,
                (175, 182, 197),
                right.width - 36,
            )
            if not candidates:
                msg_rect = pygame.Rect(right.x + 18, right.y + 78, right.width - 36, 100)
                draw_wrapped_text(
                    screen,
                    body,
                    "No spare owned Pokemon are available. Remove a party member first or catch/obtain another Pokemon.",
                    msg_rect,
                    (190, 196, 208),
                    line_gap=4,
                    max_lines=4,
                )
            for rect, candidate in candidate_rects:
                local_id = int(candidate.get("local_id"))
                active = local_id == selected_candidate_id
                pygame.draw.rect(screen, (65, 73, 92) if active else (39, 44, 55), rect, border_radius=8)
                pygame.draw.rect(screen, (118, 126, 150), rect, width=2 if active else 1, border_radius=8)
                species = candidate.get("species_name", "Unknown")
                level = candidate.get("level", "-")
                copies = candidate.get("available_copies", 1)
                type_text = str(candidate.get("type_1") or "unknown")
                if candidate.get("type_2"):
                    type_text += f" / {candidate.get('type_2')}"
                _text(screen, body, f"{species}  Lv.{level}", rect.x + 10, rect.y + 7, max_width=rect.width - 20)
                _text(screen, small, f"{type_text} • {copies} available", rect.x + 10, rect.bottom - 23, (180, 186, 200), rect.width - 20)
        else:
            member = _member_for_slot(team_data, selected_slot)
            _text(screen, heading, "Pokemon details", right.x + 16, right.y + 12, max_width=right.width - 32)
            if member is None:
                info_rect = pygame.Rect(right.x + 18, right.y + 56, right.width - 36, 130)
                draw_wrapped_text(
                    screen,
                    body,
                    f"Slot {selected_slot} is empty. Tap Choose Pokemon to select one of your owned Pokemon and put it here.",
                    info_rect,
                    (190, 196, 208),
                    line_gap=4,
                    max_lines=5,
                )
            else:
                item_row = _item_for_slot(item_data, selected_slot)
                held_item = item_row.get("held_item") or "None"
                y = right.y + 54
                detail_lines = [
                    f"Slot {selected_slot}: {member.get('species_name', 'Unknown')}",
                    f"Level {member.get('level', '-')} • HP {member.get('current_hp', '-')}/{member.get('max_hp', '-')} • {member.get('status', 'unknown')}",
                    f"Sex: {member.get('sex') or 'unknown'} • Type: {member.get('type_1') or 'unknown'}{(' / ' + str(member.get('type_2'))) if member.get('type_2') else ''}",
                    f"Held item: {held_item}",
                ]
                for line in detail_lines:
                    _text(screen, body, line, right.x + 18, y, max_width=right.width - 36)
                    y += body.get_linesize() + 5

                ability = member.get("ability")
                if ability:
                    y += 4
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
                        if y + small.get_linesize() > right.bottom - 76:
                            break
                        _text(screen, small, line, right.x + 20, y, (205, 209, 220), right.width - 40)
                        y += small.get_linesize() + 4
                else:
                    _text(screen, small, "Move details not captured for this slot yet.", right.x + 20, y, (175, 182, 197), right.width - 40)

                history = item_row.get("history", [])
                history_y = right.bottom - 54
                _text(screen, small, f"Held-item changes logged: {len(history)}", right.x + 18, history_y, (175, 182, 197), right.width - 36)

        _text(screen, small, message, margin, height - 108, (190, 220, 190), max(200, width - 2 * margin))
        for label, rect in action_rects.items():
            _button(screen, pygame, small, label, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
