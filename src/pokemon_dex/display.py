"""Shared responsive-display helpers for Pokemon-DEX Pygame screens."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayPreset:
    name: str
    width: int
    height: int


PRESETS = {
    "compact": DisplayPreset("Compact", 960, 640),
    "standard": DisplayPreset("Standard", 1280, 800),
    "large": DisplayPreset("Large", 1600, 900),
}


def apply_display_mode(pygame, preset: str = "standard", *, fullscreen: bool = False):
    """Create a resizable or fullscreen display using a named preset."""
    if fullscreen:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    chosen = PRESETS.get(preset, PRESETS["standard"])
    return pygame.display.set_mode((chosen.width, chosen.height), pygame.RESIZABLE)


def font_size_for_height(height: int, base: int, *, minimum: int = 16, maximum: int = 56) -> int:
    """Scale fonts gently with window height while keeping them readable."""
    scale = max(0.80, min(1.35, height / 800.0))
    return max(minimum, min(maximum, int(round(base * scale))))


def fit_text(font, text: object, max_width: int, *, suffix: str = "…") -> str:
    """Trim a single line to fit a width without rendering beyond the panel."""
    value = str(text)
    if max_width <= 0 or font.size(value)[0] <= max_width:
        return value
    trimmed = value
    while trimmed and font.size(trimmed + suffix)[0] > max_width:
        trimmed = trimmed[:-1]
    return trimmed + suffix if trimmed else suffix


def wrap_text(font, text: object, max_width: int) -> list[str]:
    """Wrap text using rendered width rather than character count."""
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(fit_text(font, current, max_width))
            current = word
    lines.append(fit_text(font, current, max_width))
    return lines


def draw_wrapped_text(screen, font, text: object, rect, color=(225, 228, 235), *, line_gap: int = 4, max_lines: int | None = None) -> int:
    """Draw wrapped text inside rect and return the next vertical position."""
    lines = wrap_text(font, text, rect.width)
    if max_lines is not None:
        lines = lines[:max_lines]
    line_height = font.get_linesize() + line_gap
    y = rect.y
    for line in lines:
        if y + line_height > rect.bottom:
            break
        screen.blit(font.render(line, True, color), (rect.x, y))
        y += line_height
    return y
