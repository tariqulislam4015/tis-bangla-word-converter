"""Shared application state passed to pages."""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import Settings
from core.correction_rules import CorrectionSet
from core.unicode_to_bijoy import UnicodeToBijoy
from services.history_service import HistoryService

from .workers import TaskRunner


@dataclass
class AppContext:
    settings: Settings
    corrections: CorrectionSet
    converter: UnicodeToBijoy
    history: HistoryService
    runner: TaskRunner
    unicode_font: str = "Nirmala UI"
    ui_font: str = "Segoe UI"
    bijoy_installed: bool = False

    def save_settings(self) -> None:
        try:
            self.settings.save()
        except OSError:
            pass
