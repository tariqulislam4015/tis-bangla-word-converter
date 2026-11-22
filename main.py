"""TIS (Bangla Word Converter) — application entry point."""
from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

if sys.version_info < (3, 10):  # pragma: no cover
    sys.stderr.write("TIS (Bangla Word Converter) requires Python 3.10 or newer.\n")
    sys.exit(1)

from config import settings as S  # noqa: E402


def setup_logging() -> None:
    handlers: list[logging.Handler] = []
    try:
        handlers.append(RotatingFileHandler(S.log_file(), maxBytes=1_000_000, backupCount=2,
                                            encoding="utf-8"))
    except OSError:
        pass
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def set_windows_app_id() -> None:
    """Give the process its own taskbar identity (correct icon grouping)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(S.APP_ID)
        except Exception:
            pass


def main() -> int:
    setup_logging()
    log = logging.getLogger("tis")
    log.info("Starting %s %s", S.APP_NAME, S.APP_VERSION)
    set_windows_app_id()

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QIcon, QPixmap
    from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

    app = QApplication(sys.argv)
    app.setApplicationName(S.APP_NAME)
    app.setApplicationDisplayName(S.APP_NAME)
    app.setApplicationVersion(S.APP_VERSION)
    app.setOrganizationName(S.APP_SHORT)
    app.setWindowIcon(QIcon(str(S.resource_path("assets/icons/tis.ico"))))
    from PySide6.QtGui import QFontDatabase
    families = set(QFontDatabase.families())
    ui_family = next((f for f in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans")
                      if f in families), app.font().family())
    app.setFont(QFont(ui_family, 10))

    self_testing = "--self-test" in sys.argv
    settings = S.Settings.load()

    # Developer welcome screen (animated, ~2 s; stays while hovered so links can be clicked)
    welcome = None
    splash = None
    if not self_testing and settings.show_welcome:
        from ui.welcome import WelcomeScreen
        bn_font = next((f for f in S.UNICODE_FONTS_PREFERRED if f in families), ui_family)
        welcome = WelcomeScreen(bn_font, voice=settings.welcome_voice)
        welcome.show_centered()
        app.processEvents()
    elif not self_testing:
        pm = QPixmap(str(S.resource_path("assets/images/splash.png")))
        if not pm.isNull():
            splash = QSplashScreen(pm, Qt.WindowType.WindowStaysOnTopHint)
            splash.show()
            app.processEvents()

    def excepthook(exc_type, exc, tb):
        log.error("Unhandled exception", exc_info=(exc_type, exc, tb))
        msg = "".join(traceback.format_exception_only(exc_type, exc)).strip()
        try:
            QMessageBox.critical(None, S.APP_NAME,
                                 f"An unexpected error occurred:\n\n{msg}\n\n"
                                 f"Your text has not been lost. Details are in the log file:\n{S.log_file()}")
        except Exception:
            pass

    if "--self-test" not in sys.argv:
        sys.excepthook = excepthook

    from core.correction_rules import CorrectionSet
    from core.unicode_to_bijoy import UnicodeToBijoy
    from services.history_service import HistoryService
    from ui.context import AppContext
    from ui.main_window import MainWindow
    from ui.workers import TaskRunner

    corrections = CorrectionSet.load(S.corrections_file())
    ctx = AppContext(settings=settings, corrections=corrections,
                     converter=UnicodeToBijoy(corrections),
                     history=HistoryService(S.history_db()), runner=TaskRunner())
    window = MainWindow(ctx)
    if "--self-test" in sys.argv:
        return self_test(app, window)
    if welcome is not None:
        def reveal():
            window.show()
            window.raise_()
            window.activateWindow()
        welcome.finished.connect(reveal)
        QTimer.singleShot(0, welcome.start)      # animate once the event loop is running
    else:
        window.show()
        if splash is not None:
            splash.finish(window)

    # files passed on the command line / "Open with"
    from pathlib import Path
    args = [Path(a) for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        window.handle_files([a for a in args if a.exists()])
    return app.exec()


def self_test(app, window) -> int:
    """Start-up check used by CI on the built executable (exit code 0 = OK)."""
    log = logging.getLogger("tis.selftest")
    try:
        tp = window.text_page
        tp.set_input_text("আমার সোনার বাংলা")
        tp.convert(record=False)
        assert tp.output_plain == "Avgvi †mvbvi evsjv", tp.output_plain
        for i in range(4):
            window.go(i)
        window.toggle_theme()
        window.toggle_theme()
        app.processEvents()
    except Exception:
        log.exception("self-test failed")
        return 1
    log.info("self-test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
