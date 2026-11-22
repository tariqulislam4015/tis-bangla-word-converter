"""Small line-icon set drawn as inline SVG and tinted to the current theme."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_S = ('stroke="{c}" stroke-width="1.8" fill="none" stroke-linecap="round" '
      'stroke-linejoin="round"')

_PATHS: dict[str, str] = {
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2" {s}/>'
            '<path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" {s}/>',
    "paste": '<rect x="5" y="4" width="14" height="17" rx="2" {s}/>'
             '<rect x="9" y="2.5" width="6" height="3.5" rx="1" {s}/><path d="M9 11h6M9 15h4" {s}/>',
    "trash": '<path d="M4 7h16M9 7V4.5h6V7M6.5 7l1 13h9l1-13M10 11v6M14 11v6" {s}/>',
    "folder": '<path d="M3.5 7a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z" {s}/>',
    "save": '<path d="M5 4h11l3 3v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z" {s}/>'
            '<path d="M8 4v5h7V4M8 20v-6h8v6" {s}/>',
    "export": '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" {s}/>',
    "import": '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" {s}/>',
    "undo": '<path d="M9 7 4.5 11.5 9 16" {s}/><path d="M5 11.5h9.5a5 5 0 0 1 0 10H11" {s}/>',
    "redo": '<path d="M15 7l4.5 4.5L15 16" {s}/><path d="M19 11.5H9.5a5 5 0 0 0 0 10H13" {s}/>',
    "sun": '<circle cx="12" cy="12" r="4" {s}/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2'
           'M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" {s}/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" {s}/>',
    "settings": '<path d="M4 7h10M18 7h2M4 17h4M12 17h8" {s}/>'
                '<circle cx="16" cy="7" r="2" {s}/><circle cx="10" cy="17" r="2" {s}/>',
    "info": '<circle cx="12" cy="12" r="9" {s}/><path d="M12 11v6M12 7.5v.2" {s}/>',
    "help": '<circle cx="12" cy="12" r="9" {s}/>'
            '<path d="M9.3 9.3a2.8 2.8 0 1 1 3.9 2.6c-.8.4-1.2 1-1.2 1.9v.4M12 17.3v.2" {s}/>',
    "text": '<path d="M5 6h14M5 10h14M5 14h9M5 18h11" {s}/>',
    "document": '<path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" {s}/>'
                '<path d="M14 3v5h5M9 13h6M9 17h6" {s}/>',
    "batch": '<rect x="7" y="7" width="13" height="13" rx="2" {s}/>'
             '<path d="M4 15V5a1 1 0 0 1 1-1h10M11 12h5M11 15.5h5" {s}/>',
    "history": '<path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.5" {s}/><path d="M4 4v4.5h4.5M12 8v4.5l3 2" {s}/>',
    "swap": '<path d="M5 8h13M14.5 4.5 18 8l-3.5 3.5M19 16H6M9.5 12.5 6 16l3.5 3.5" {s}/>',
    "search": '<circle cx="11" cy="11" r="6.5" {s}/><path d="m16 16 4 4" {s}/>',
    "zoom_in": '<circle cx="11" cy="11" r="6.5" {s}/><path d="m16 16 4 4M8.5 11h5M11 8.5v5" {s}/>',
    "zoom_out": '<circle cx="11" cy="11" r="6.5" {s}/><path d="m16 16 4 4M8.5 11h5" {s}/>',
    "plus": '<path d="M12 5v14M5 12h14" {s}/>',
    "minus": '<path d="M5 12h14" {s}/>',
    "close": '<path d="M6 6l12 12M18 6 6 18" {s}/>',
    "check": '<path d="M5 12.5 10 17.5 19 7" {s}/>',
    "alert": '<path d="M12 4 2.8 19.5h18.4z" {s}/><path d="M12 10v4.5M12 17v.2" {s}/>',
    "arrow_right": '<path d="M5 12h14M13 6l6 6-6 6" {s}/>',
    "open_external": '<path d="M14 4h6v6M20 4l-8.5 8.5M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" {s}/>',
    "play": '<path d="M7 5v14l11-7z" {s}/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2" {s}/>',
    "new": '<path d="M7 3h7l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" {s}/>'
           '<path d="M14 3v5h5M12 11v6M9 14h6" {s}/>',
    "font": '<path d="M4 19 10 5h1l6 14M6.5 14h8" {s}/><path d="M17 11h4M19 9v4" {s}/>',
    "restore": '<path d="M4 12a8 8 0 1 1 2.4 5.7" {s}/><path d="M4 18v-4.5h4.5" {s}/>',
}


def svg(name: str, color: str) -> str:
    body = _PATHS[name].replace("{s}", _S.replace("{c}", color))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body}</svg>'


@lru_cache(maxsize=512)
def icon(name: str, color: str, size: int = 48) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg(name, color).encode("utf-8")))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QIcon(pm)


def set_icon(button, name: str, role: str = "text") -> None:
    """Attach a themeable icon to a button; MainWindow re-tints on theme change.

    role: "text" (normal text colour), "muted", "accent", "white", "header".
    """
    button.setProperty("tis_icon", name)
    button.setProperty("tis_icon_role", role)
    from .theme_state import current_palette
    button.setIcon(icon(name, role_color(current_palette(), role)))


def role_color(p, role: str) -> str:
    return {
        "text": p.text, "muted": p.muted, "accent": p.accent,
        "white": "#FFFFFF", "header": p.header_text, "warning": p.warning,
        "success": p.success, "danger": p.danger,
    }.get(role, p.text)
