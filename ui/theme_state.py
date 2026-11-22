"""Process-wide current theme (kept tiny so widgets can query it)."""
from __future__ import annotations

from .theme import LIGHT, Palette, palette

_current: Palette = LIGHT


def current_palette() -> Palette:
    return _current


def set_theme(name: str) -> Palette:
    global _current
    _current = palette(name)
    return _current
