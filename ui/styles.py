"""Qt style sheet generated from the active palette."""
from __future__ import annotations

from config.settings import resource_path

from .theme import Palette


def stylesheet(p: Palette) -> str:
    check = resource_path("assets/icons/check_white.svg").as_posix()
    return f"""
/* No global font-family here: style-sheet fonts would override the SutonnyMJ /
   Unicode fonts that the editors set in code.  The UI font is set on QApplication. */
* {{ color: {p.text}; outline: 0; }}
QMainWindow, QDialog, #AppBody {{ background: {p.bg}; }}
QToolTip {{
    background: {p.surface}; color: {p.text}; border: 1px solid {p.border_strong};
    padding: 5px 8px; border-radius: 6px;
}}

/* ---------- header ---------- */
#Header {{ background: {p.header_bg}; }}
#Header QLabel {{ color: {p.header_text}; background: transparent; }}
#BrandMark {{ font-size: 17pt; font-weight: 800; letter-spacing: 1px; }}
#BrandName {{ font-size: 11pt; font-weight: 600; }}
#BrandSub {{ color: {p.header_muted}; font-size: 9pt; }}
#Header QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 8px;
    padding: 6px 10px; color: {p.header_text};
}}
#Header QToolButton:hover {{ background: rgba(255,255,255,0.10); }}
#Header QToolButton:pressed {{ background: rgba(255,255,255,0.18); }}

/* ---------- navigation rail ---------- */
#NavRail {{ background: {p.surface}; border-right: 1px solid {p.border}; }}
#NavRail QToolButton {{
    background: transparent; border: none; border-radius: 10px;
    padding: 8px 4px; margin: 2px 8px; color: {p.muted}; font-size: 9pt;
}}
#NavRail QToolButton:hover {{ background: {p.surface_alt}; color: {p.text}; }}
#NavRail QToolButton:checked {{ background: {p.accent_soft}; color: {p.accent}; font-weight: 600; }}
#NavVersion {{ color: {p.muted}; font-size: 8pt; }}

/* ---------- cards ---------- */
#Card {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 12px; }}
#CardTitle {{ font-size: 11pt; font-weight: 600; }}
#CardHint, #Muted {{ color: {p.muted}; }}
#PageTitle {{ font-size: 16pt; font-weight: 700; }}
#PageSubtitle {{ color: {p.muted}; }}
#StatsLabel {{ color: {p.muted}; font-size: 9pt; }}
#Chip {{
    background: {p.surface_alt}; color: {p.muted}; border-radius: 9px;
    padding: 2px 8px; font-size: 8pt; font-weight: 600;
}}
#ChipAccent {{
    background: {p.accent_soft}; color: {p.accent}; border-radius: 9px;
    padding: 2px 8px; font-size: 8pt; font-weight: 600;
}}

/* ---------- buttons ---------- */
QPushButton {{
    background: {p.surface}; border: 1px solid {p.border_strong}; border-radius: 8px;
    padding: 7px 14px; min-height: 18px;
}}
QPushButton:hover {{ background: {p.surface_alt}; }}
QPushButton:pressed {{ background: {p.border}; }}
QPushButton:disabled {{ color: {p.muted}; background: {p.surface_alt}; border-color: {p.border}; }}
QPushButton#Primary {{
    background: {p.accent}; color: white; border: 1px solid {p.accent};
    font-weight: 600; padding: 9px 18px;
}}
QPushButton#Primary:hover {{ background: {p.accent_hover}; border-color: {p.accent_hover}; }}
QPushButton#Primary:pressed {{ background: {p.accent_pressed}; }}
QPushButton#Primary:disabled {{ background: {p.border_strong}; border-color: {p.border_strong}; color: {p.surface}; }}
QPushButton#ConvertBig {{
    background: {p.accent}; color: white; border: none; border-radius: 12px;
    font-size: 11pt; font-weight: 700; padding: 14px 10px;
}}
QPushButton#ConvertBig:hover {{ background: {p.accent_hover}; }}
QPushButton#ConvertBig:pressed {{ background: {p.accent_pressed}; }}
QPushButton#Danger {{ color: {p.danger}; }}
QPushButton#Danger:hover {{ background: {p.danger_soft}; border-color: {p.danger}; }}
QToolButton#Flat {{
    background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 5px 8px;
}}
QToolButton#Flat:hover {{ background: {p.surface_alt}; border-color: {p.border}; }}
QToolButton#Flat:pressed {{ background: {p.border}; }}
QToolButton#Flat:disabled {{ color: {p.muted}; }}
QToolButton#Segment {{
    background: transparent; border: none; border-radius: 7px; padding: 6px 12px; color: {p.muted};
    font-weight: 600;
}}
QToolButton#Segment:checked {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; }}
#SegmentBox {{ background: {p.surface_alt}; border-radius: 9px; }}

/* ---------- inputs ---------- */
QPlainTextEdit, QTextEdit, QTextBrowser {{
    background: {p.editor_bg}; border: 1px solid {p.border}; border-radius: 10px;
    padding: 8px; selection-background-color: {p.selection}; selection-color: {p.text};
}}
QPlainTextEdit:focus, QTextEdit:focus {{ border: 1px solid {p.accent}; }}
QLineEdit, QSpinBox, QComboBox {{
    background: {p.editor_bg}; border: 1px solid {p.border_strong}; border-radius: 7px;
    padding: 6px 8px; selection-background-color: {p.selection};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {p.accent}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p.surface}; border: 1px solid {p.border_strong}; selection-background-color: {p.accent_soft};
    selection-color: {p.text};
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid {p.border_strong};
    background: {p.editor_bg};
}}
QCheckBox::indicator:unchecked {{ background: {p.editor_bg}; border: 1px solid {p.border_strong}; image: none; }}
QCheckBox::indicator:checked {{
    background: {p.accent}; border: 1px solid {p.accent}; image: url("{check}");
}}
QCheckBox::indicator:hover {{ border-color: {p.accent}; }}

/* ---------- tables / lists ---------- */
QTableWidget, QListWidget {{
    background: {p.editor_bg}; border: 1px solid {p.border}; border-radius: 10px;
    gridline-color: {p.border}; selection-background-color: {p.accent_soft}; selection-color: {p.text};
    alternate-background-color: {p.surface_alt};
}}
QHeaderView::section {{
    background: {p.surface_alt}; color: {p.muted}; border: none; border-bottom: 1px solid {p.border};
    padding: 6px 8px; font-weight: 600; font-size: 9pt;
}}
QTableCornerButton::section {{ background: {p.surface_alt}; border: none; }}

/* ---------- progress ---------- */
QProgressBar {{
    background: {p.surface_alt}; border: none; border-radius: 5px; min-height: 10px; max-height: 10px;
    text-align: center; color: transparent;
}}
QProgressBar::chunk {{ background: {p.accent}; border-radius: 5px; }}
QProgressBar#Mini {{ min-height: 6px; max-height: 6px; min-width: 90px; }}

/* ---------- tabs (dialogs) ---------- */
QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 10px; background: {p.surface}; top: -1px; }}
QTabBar::tab {{
    background: transparent; padding: 8px 14px; color: {p.muted}; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.accent}; font-weight: 600; }}

/* ---------- scrollbars ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.border_strong}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {p.muted}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p.border_strong}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------- banners ---------- */
#BannerWarning {{ background: {p.warning_soft}; border: 1px solid {p.warning}; border-radius: 9px; }}
#BannerWarning QLabel {{ color: {p.text}; }}
#BannerSuccess {{ background: {p.success_soft}; border: 1px solid {p.success}; border-radius: 9px; }}
#BannerError {{ background: {p.danger_soft}; border: 1px solid {p.danger}; border-radius: 9px; }}

/* ---------- drop zone ---------- */
#DropZone {{
    background: {p.surface_alt}; border: 2px dashed {p.border_strong}; border-radius: 12px;
}}
#DropZone[active="true"] {{ border-color: {p.accent}; background: {p.accent_soft}; }}
#DropTitle {{ font-size: 12pt; font-weight: 600; }}

/* ---------- status bar ---------- */
QStatusBar {{ background: {p.surface}; border-top: 1px solid {p.border}; }}
QStatusBar QLabel {{ color: {p.muted}; font-size: 9pt; padding: 0 6px; }}
QStatusBar::item {{ border: none; }}
#StatusPill {{ border-radius: 9px; padding: 2px 10px; font-weight: 600; font-size: 9pt; }}
#StatusPill[state="ready"] {{ background: {p.surface_alt}; color: {p.muted}; }}
#StatusPill[state="busy"] {{ background: {p.accent_soft}; color: {p.accent}; }}
#StatusPill[state="ok"] {{ background: {p.success_soft}; color: {p.success}; }}
#StatusPill[state="error"] {{ background: {p.danger_soft}; color: {p.danger}; }}
QStatusBar QToolButton {{ border: none; background: transparent; color: {p.muted}; font-size: 9pt; padding: 2px 6px; }}
QStatusBar QToolButton:hover {{ color: {p.accent}; }}
#FontOk {{ color: {p.success}; }}
#FontMissing {{ color: {p.warning}; }}
"""
