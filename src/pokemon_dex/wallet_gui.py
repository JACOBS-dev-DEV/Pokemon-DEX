"""Touch/mouse-first game-wallet screen for Pokemon-DEX."""

from __future__ import annotations

from pokemon_dex.wallet import WalletError, adjust_balance, load_wallet, set_balance, wallet_summary


def _text(screen, font, value, x, y, color=(225, 228, 235)) -> None:
    screen.blit(font.render(str(value), True, color), (x, y))


def _button(screen, pygame, font, label: str, rect, active: bool = False):
    fill = (72, 79, 98) if active else (43, 48, 60)
    pygame.draw.rect(screen, fill, rect, border_radius=9)
    pygame.draw.rect(screen, (93, 100, 120), rect, width=1, border_radius=9)
    surface = font.render(label, True, (245, 246, 250))
    screen.blit(surface, surface.get_rect(center=rect.center))
    return rect


def _currency_buttons(pygame, width: int, currencies: list[str]):
    left = 28
    gap = 10
    button_w = max(160, (width - left * 2 - gap * max(0, len(currencies) - 1)) // max(1, len(currencies)))
    return {
        currency: pygame.Rect(left + i * (button_w + gap), 96, button_w, 46)
        for i, currency in enumerate(currencies)
    }


def _quick_buttons(pygame, left: int, top: int):
    labels = ("-1000", "-100", "+100", "+1000")
    return {
        label: pygame.Rect(left + i * 118, top, 108, 44)
        for i, label in enumerate(labels)
    }


def _keypad_buttons(pygame, left: int, top: int):
    layout = [
        ("1", 0, 0), ("2", 1, 0), ("3", 2, 0),
        ("4", 0, 1), ("5", 1, 1), ("6", 2, 1),
        ("7", 0, 2), ("8", 1, 2), ("9", 2, 2),
        ("Clear", 0, 3), ("0", 1, 3), ("⌫", 2, 3),
    ]
    return {
        label: pygame.Rect(left + col * 92, top + row * 54, 82, 44)
        for label, col, row in layout
    }


def run_wallet_gui() -> int:
    try:
        import pygame
    except ModuleNotFoundError:
        print("Pygame is not installed yet.")
        return 2

    pygame.init()
    pygame.display.set_caption("Pokemon-DEX Wallet")
    screen = pygame.display.set_mode((1040, 760), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 44)
    heading = pygame.font.Font(None, 30)
    body = pygame.font.Font(None, 23)
    small = pygame.font.Font(None, 19)

    try:
        wallet = load_wallet()
    except WalletError as exc:
        print(f"Wallet error: {exc}")
        pygame.quit()
        return 3

    currencies = list(wallet.get("wallet", {}).keys())
    selected_currency = currencies[0] if currencies else "poke_dollars"
    exact_input = ""
    status_message = "Balances stay unknown until you enter or observe them."
    running = True

    def reload_wallet():
        nonlocal wallet
        wallet = load_wallet()

    def apply_quick(amount: int):
        nonlocal status_message
        try:
            before = wallet.get("wallet", {}).get(selected_currency, {}).get("balance")
            adjust_balance(selected_currency, amount, reason="touch wallet quick adjustment")
            reload_wallet()
            if before is None:
                status_message = f"Logged {amount:+d}. Exact balance is still unknown."
            else:
                status_message = f"Saved {amount:+d}. Backup created."
        except WalletError as exc:
            status_message = f"Wallet error: {exc}"

    def apply_exact():
        nonlocal exact_input, status_message
        if not exact_input:
            status_message = "Enter a balance on the number pad first."
            return
        try:
            set_balance(selected_currency, int(exact_input), reason="touch keypad exact balance")
            reload_wallet()
            status_message = f"Exact balance set to {int(exact_input):,}. Backup created."
            exact_input = ""
        except WalletError as exc:
            status_message = f"Wallet error: {exc}"

    while running:
        width, height = screen.get_size()
        currency_rects = _currency_buttons(pygame, width, currencies)
        quick_rects = _quick_buttons(pygame, 38, 246)
        keypad_rects = _keypad_buttons(pygame, 54, 378)
        set_rect = pygame.Rect(350, 540, 178, 48)
        back_rect = pygame.Rect(width - 154, 24, 126, 42)

        def handle_press(pos):
            nonlocal selected_currency, exact_input, status_message, running
            if back_rect.collidepoint(pos):
                running = False
                return
            for currency, rect in currency_rects.items():
                if rect.collidepoint(pos):
                    selected_currency = currency
                    exact_input = ""
                    status_message = f"Selected {wallet['wallet'][currency].get('display_name', currency)}."
                    return
            for label, rect in quick_rects.items():
                if rect.collidepoint(pos):
                    apply_quick(int(label))
                    return
            for label, rect in keypad_rects.items():
                if rect.collidepoint(pos):
                    if label == "Clear":
                        exact_input = ""
                    elif label == "⌫":
                        exact_input = exact_input[:-1]
                    elif len(exact_input) < 9:
                        exact_input += label
                    return
            if set_rect.collidepoint(pos):
                apply_exact()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_BACKSPACE:
                    exact_input = exact_input[:-1]
                elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    apply_exact()
                elif event.unicode and event.unicode.isdigit() and len(exact_input) < 9:
                    exact_input += event.unicode
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_press(event.pos)
            elif event.type == pygame.FINGERDOWN:
                handle_press((int(event.x * width), int(event.y * height)))

        summary = wallet_summary()
        selected = wallet.get("wallet", {}).get(selected_currency, {})
        selected_summary = summary.get("currencies", {}).get(selected_currency, {})
        display_name = selected.get("display_name", selected_currency)
        symbol = selected.get("symbol", "")
        balance = selected.get("balance")
        balance_text = "UNKNOWN" if balance is None else f"{symbol}{int(balance):,}"

        screen.fill((18, 21, 27))
        _text(screen, title_font, "Pokemon-DEX Wallet", 28, 24, (248, 248, 252))
        _text(screen, small, "In-game currency only | local/offline | backups before changed saves", 30, 66, (175, 182, 197))
        _button(screen, pygame, body, "Back", back_rect)

        for currency, rect in currency_rects.items():
            label = wallet.get("wallet", {}).get(currency, {}).get("display_name", currency)
            _button(screen, pygame, body, label, rect, currency == selected_currency)

        _text(screen, heading, display_name, 38, 172)
        _text(screen, title_font, balance_text, 38, 204, (248, 248, 252))
        _text(screen, small, f"Earned logged: {selected_summary.get('earned', 0):,} | Spent logged: {selected_summary.get('spent', 0):,} | Transactions: {selected_summary.get('transactions', 0)}", 38, 294, (185, 191, 203))

        for label, rect in quick_rects.items():
            _button(screen, pygame, body, label, rect)

        pygame.draw.rect(screen, (29, 33, 41), pygame.Rect(32, 332, 504, 348), border_radius=10)
        _text(screen, heading, "Exact balance", 54, 346)
        _text(screen, small, "Use the number pad when you read the exact value from the game screen.", 54, 376, (180, 186, 200))
        input_rect = pygame.Rect(346, 386, 170, 52)
        pygame.draw.rect(screen, (40, 45, 56), input_rect, border_radius=8)
        pygame.draw.rect(screen, (93, 100, 120), input_rect, width=1, border_radius=8)
        _text(screen, heading, exact_input or "—", input_rect.x + 12, input_rect.y + 13)
        for label, rect in keypad_rects.items():
            _button(screen, pygame, body, label, rect)
        _button(screen, pygame, body, "Set Exact Balance", set_rect)

        ledger_x = 566
        _text(screen, heading, "Recent wallet activity", ledger_x, 172)
        transactions = [tx for tx in wallet.get("transactions", []) if tx.get("currency") == selected_currency][-12:]
        if not transactions:
            _text(screen, body, "No transactions logged yet.", ledger_x, 212, (180, 186, 200))
        else:
            y = 212
            for tx in reversed(transactions):
                amount = tx.get("amount")
                amount_text = "balance read" if amount is None else f"{int(amount):+d}"
                reason = str(tx.get("reason", tx.get("kind", "transaction")))
                after = tx.get("balance_after")
                after_text = "?" if after is None else f"{symbol}{int(after):,}"
                _text(screen, body, f"{amount_text}  →  {after_text}", ledger_x, y)
                _text(screen, small, reason[:52], ledger_x, y + 23, (180, 186, 200))
                y += 50

        status_rect = pygame.Rect(566, height - 92, max(300, width - 594), 54)
        pygame.draw.rect(screen, (29, 33, 41), status_rect, border_radius=8)
        _text(screen, small, status_message[:82], status_rect.x + 12, status_rect.y + 18, (190, 220, 190))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0
