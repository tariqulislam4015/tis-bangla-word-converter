"""Application identity, paths and persisted user settings."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

APP_NAME = "TIS (Bangla Word Converter)"
APP_SHORT = "TIS"
APP_PRODUCT = "Bangla Word Converter"
APP_TAGLINE = "Smart Bengali Text & Document Conversion"
APP_SUBTITLE = "Unicode to Bijoy | SolaimanLipi to SutonnyMJ"
APP_HEADER_SUBTITLE = "Unicode to Bijoy Conversion Tool"
APP_VERSION = "1.5.0"
APP_ID = "TIS.BanglaWordConverter"
APP_DIR_NAME = "TIS Bangla Word Converter"
EXE_NAME = "TIS_Bangla_Word_Converter"

# Developer information shown in About (edit here or in settings.json).
DEFAULT_DEVELOPER = "তারিকুল ইসলাম (সুমন)"
DEFAULT_DEVELOPER_CONTACT = "https://wa.me/8801755489719"
DEFAULT_DEVELOPER_URL = "https://www.youtube.com/@tis.academy24"

# Developer profile shown on the welcome screen and in About.
DEVELOPER_PROFILE = {
    "name": "তারিকুল ইসলাম (সুমন)",
    "position": "Msc Mathematics",
    "channel": "TIS Academy",
    "photo": "assets/images/developer.jpg",
    "links": [
        ("youtube", "YouTube", "https://www.youtube.com/@tis.academy24"),
        ("facebook", "Facebook", "https://www.facebook.com/tariqul.islam.422531/"),
        ("whatsapp", "WhatsApp", "https://wa.me/8801755489719"),
        ("github", "GitHub", "https://github.com/tariqulislam4015"),
        ("linkedin", "LinkedIn", "https://www.linkedin.com/in/tariqul3315/"),
    ],
}
WELCOME_SECONDS = 2.0
WELCOME_VOICE = "assets/audio/welcome.wav"

BIJOY_FONT = "SutonnyMJ"
UNICODE_FONTS_PREFERRED = ["SolaimanLipi", "Nirmala UI", "Kalpurush", "Noto Sans Bengali", "Vrinda"]

FONT_HELP_URL = "https://www.google.com/search?q=SutonnyMJ+font+download"


def resource_path(relative: str) -> Path:
    """Path to a bundled resource, working both from source and PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


def portable_dir() -> Path | None:
    """Portable mode: a 'portable.ini' next to the executable keeps all data
    in a 'TIS_data' folder beside it (nothing written to the user profile)."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "portable.ini").exists():
            return exe_dir / "TIS_data"
    return None


def app_data_dir() -> Path:
    port = portable_dir()
    if port is not None:
        try:
            port.mkdir(parents=True, exist_ok=True)
            return port
        except OSError:
            pass
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = root / APP_DIR_NAME
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = Path.home() / f".{EXE_NAME.lower()}"
        path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return app_data_dir() / "settings.json"


def corrections_file() -> Path:
    return app_data_dir() / "correction_rules.json"


def history_db() -> Path:
    return app_data_dir() / "history.sqlite3"


def autosave_file() -> Path:
    return app_data_dir() / "autosave_input.txt"


def log_file() -> Path:
    return app_data_dir() / "tis.log"


@dataclass
class Settings:
    theme: str = "light"                 # "light" | "dark"
    live_convert: bool = True
    autosave_input: bool = True
    highlight_converted: bool = False    # DOCX: highlight converted runs for review
    keep_equations: bool = True          # DOCX: leave equations exactly as they are
    open_after_convert: bool = False
    auto_convert_docs: bool = True       # convert a Word file as soon as it is chosen/dropped
    show_in_folder: bool = True          # show the converted file in its folder when finished
    start_page: str = "document"         # "document" | "text"
    batch_next_to_source: bool = True    # batch: save each output next to its original
    show_welcome: bool = True            # developer welcome screen at start-up
    welcome_voice: bool = True           # play the welcome voice with the welcome screen
    doc_direction: str = "U2B"           # Document/Batch pages: "U2B" or "B2U"
    unicode_output_font: str = "SolaimanLipi"   # font for Bijoy -> Unicode output
    txt_output_encoding: str = "ansi"    # "ansi" (Windows-1252) | "utf-8"
    output_suffix: str = "Bijoy"
    editor_font_size: int = 14
    last_open_dir: str = ""
    last_output_dir: str = ""
    recent_files: list[str] = field(default_factory=list)
    developer: str = DEFAULT_DEVELOPER
    developer_contact: str = DEFAULT_DEVELOPER_CONTACT
    developer_url: str = DEFAULT_DEVELOPER_URL
    window_geometry: str = ""

    MAX_RECENT = 10

    def add_recent(self, path: str) -> None:
        p = str(path)
        self.recent_files = [p] + [r for r in self.recent_files if r != p]
        del self.recent_files[self.MAX_RECENT:]

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or settings_file()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        s = cls(**{k: v for k, v in data.items() if k in known})
        if s.theme not in ("light", "dark"):
            s.theme = "light"
        if s.txt_output_encoding not in ("ansi", "utf-8"):
            s.txt_output_encoding = "ansi"
        try:
            s.editor_font_size = max(8, min(48, int(s.editor_font_size)))
        except (TypeError, ValueError):
            s.editor_font_size = 14
        s.highlight_converted = False    # proofreading highlight is never carried over
        if s.doc_direction not in ("U2B", "B2U"):
            s.doc_direction = "U2B"
        if not isinstance(s.unicode_output_font, str) or not s.unicode_output_font.strip():
            s.unicode_output_font = "SolaimanLipi"
        if not isinstance(s.recent_files, list):
            s.recent_files = []
        return s

    def save(self, path: Path | None = None) -> None:
        path = path or settings_file()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
