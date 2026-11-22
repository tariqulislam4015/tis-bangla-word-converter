"""Detect installed fonts (SutonnyMJ / Unicode Bengali fonts) without Qt."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

FONT_EXTS = (".ttf", ".otf", ".ttc", ".fon")


@dataclass
class FontStatus:
    name: str
    installed: bool
    location: str = ""


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _windows_registry_fonts() -> dict[str, str]:
    fonts: dict[str, str] = {}
    try:
        import winreg  # type: ignore
    except ImportError:
        return fonts
    key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, key_path) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                    except OSError:
                        break
                    fonts[str(name)] = str(value)
                    i += 1
        except OSError:
            continue
    return fonts


def _font_dirs() -> list[Path]:
    dirs: list[Path] = []
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(Path(windir) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs += [Path("/Library/Fonts"), Path.home() / "Library" / "Fonts"]
    else:
        dirs += [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
                 Path.home() / ".fonts", Path.home() / ".local" / "share" / "fonts"]
    return [d for d in dirs if d.is_dir()]


def find_font(name: str) -> FontStatus:
    """Look for a font by family name in the registry and font folders."""
    target = _norm(name)
    for reg_name, value in _windows_registry_fonts().items():
        if _norm(reg_name).startswith(target):
            return FontStatus(name, True, value)
    for d in _font_dirs():
        try:
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(FONT_EXTS) and _norm(Path(f).stem).startswith(target):
                        return FontStatus(name, True, str(Path(root) / f))
        except OSError:
            continue
    return FontStatus(name, False)
