"""Brand colour tokens for light and dark themes."""
from __future__ import annotations

from dataclasses import dataclass

# Brand constants
MIDNIGHT_NAVY = "#14243A"
SLATE_BLUE = "#253B55"
ELECTRIC_BLUE = "#3B82F6"
TEAL = "#14B8A6"
LIGHT_BG = "#F5F7FA"
DARK_BG = "#101827"
WHITE = "#FFFFFF"


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    border_strong: str
    text: str
    muted: str
    header_bg: str
    header_text: str
    header_muted: str
    accent: str
    accent_hover: str
    accent_pressed: str
    accent_soft: str
    success: str
    success_soft: str
    warning: str
    warning_soft: str
    danger: str
    danger_soft: str
    selection: str
    editor_bg: str


LIGHT = Palette(
    name="light",
    bg=LIGHT_BG, surface=WHITE, surface_alt="#EEF2F7",
    border="#E2E8F0", border_strong="#CBD5E1",
    text="#182230", muted="#718096",
    header_bg=MIDNIGHT_NAVY, header_text=WHITE, header_muted="#A9B8CC",
    accent=ELECTRIC_BLUE, accent_hover="#2563EB", accent_pressed="#1D4ED8", accent_soft="#E8F0FE",
    success=TEAL, success_soft="#E6F8F6",
    warning="#D97706", warning_soft="#FEF3E2",
    danger="#DC2626", danger_soft="#FDECEC",
    selection="#CFE0FD", editor_bg=WHITE,
)

DARK = Palette(
    name="dark",
    bg=DARK_BG, surface="#162133", surface_alt="#1C2A40",
    border="#26344A", border_strong="#33445E",
    text="#E6EBF2", muted="#8A99AD",
    header_bg="#0C1524", header_text=WHITE, header_muted="#8FA3BD",
    accent=ELECTRIC_BLUE, accent_hover="#60A5FA", accent_pressed="#2563EB", accent_soft="#1B2E4D",
    success="#2DD4BF", success_soft="#12302F",
    warning="#F59E0B", warning_soft="#33280F",
    danger="#F87171", danger_soft="#3A1D20",
    selection="#1E3A5F", editor_bg="#111B2B",
)


def palette(name: str) -> Palette:
    return DARK if name == "dark" else LIGHT
