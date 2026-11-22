"""Main application window."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QAction, QFontDatabase, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup, QFileDialog, QFrame,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar,
                               QStackedWidget, QStatusBar, QToolButton, QVBoxLayout, QWidget)

from config import settings as S
from core.font_detector import find_font

from .batch_page import BatchPage
from .components import StatusPill, label, local_paths
from .context import AppContext
from .dialogs import AboutDialog, FontHelpDialog, HelpDialog, SettingsDialog
from .document_page import DocumentPage
from .history_page import HistoryPage
from .icons import icon, role_color, set_icon
from .styles import stylesheet
from .text_page import TextPage
from .theme_state import current_palette, set_theme

log = logging.getLogger(__name__)

PAGE_TEXT, PAGE_DOC, PAGE_BATCH, PAGE_HISTORY = range(4)


def detect_bijoy_font() -> bool:
    """True if SutonnyMJ is usable by Qt; loads it from disk if registered but unseen."""
    fams = {f.lower() for f in QFontDatabase.families()}
    if S.BIJOY_FONT.lower() in fams:
        return True
    st = find_font(S.BIJOY_FONT)
    if st.installed and st.location:
        loc = Path(st.location)
        if not loc.is_absolute():
            import os
            loc = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / loc
        if loc.exists():
            fid = QFontDatabase.addApplicationFont(str(loc))
            if fid != -1 and any(f.lower() == S.BIJOY_FONT.lower()
                                 for f in QFontDatabase.applicationFontFamilies(fid)):
                return True
    return False


def pick_unicode_font() -> str:
    fams = {f.lower(): f for f in QFontDatabase.families()}
    for name in S.UNICODE_FONTS_PREFERRED:
        if name.lower() in fams:
            return fams[name.lower()]
    return QApplication.font().family()


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(S.APP_NAME)
        self.setWindowIcon(QIcon(str(S.resource_path("assets/icons/tis.ico"))))
        self.setMinimumSize(1040, 680)
        self.setAcceptDrops(True)

        ctx.unicode_font = pick_unicode_font()
        ctx.ui_font = QApplication.font().family()
        ctx.bijoy_installed = detect_bijoy_font()

        central = QWidget()
        central.setObjectName("AppBody")
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._build_header())
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_nav())
        self.stack = QStackedWidget()
        self.text_page = TextPage(ctx)
        self.doc_page = DocumentPage(ctx)
        self.batch_page = BatchPage(ctx)
        self.history_page = HistoryPage(ctx)
        for p in (self.text_page, self.doc_page, self.batch_page, self.history_page):
            self.stack.addWidget(p)
        body.addWidget(self.stack, 1)
        v.addLayout(body, 1)
        self.setCentralWidget(central)
        self._build_status_bar()
        self._wire()
        self._build_actions()

        self.apply_theme(ctx.settings.theme, save=False)
        self._apply_font_status()
        self._restore_geometry()
        self.text_page.restore_autosave()
        self.go(PAGE_DOC if ctx.settings.start_page == "document" else PAGE_TEXT)

    # ------------------------------------------------------------ build
    def _build_header(self) -> QWidget:
        h = QFrame()
        h.setObjectName("Header")
        h.setFixedHeight(68)
        lay = QHBoxLayout(h)
        lay.setContentsMargins(18, 8, 14, 8)
        lay.setSpacing(12)
        logo = QLabel()
        pm = QPixmap(str(S.resource_path("assets/icons/tis_logo_256.png")))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(logo)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(label(S.APP_SHORT, "BrandMark"))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label(S.APP_PRODUCT, "BrandName"))
        names.addWidget(label(S.APP_HEADER_SUBTITLE, "BrandSub"))
        brand.addLayout(names)
        lay.addLayout(brand)
        lay.addStretch(1)
        self.theme_btn = QToolButton()
        self.theme_btn.setToolTip("Switch light / dark theme")
        self.theme_btn.setIconSize(QSize(20, 20))
        self.theme_btn.clicked.connect(self.toggle_theme)
        b_settings = QToolButton()
        b_settings.setText("Settings")
        b_help = QToolButton()
        b_help.setText("Help")
        b_about = QToolButton()
        b_about.setText("About")
        for b, name in ((b_settings, "settings"), (b_help, "help"), (b_about, "info")):
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setIconSize(QSize(18, 18))
            set_icon(b, name, "header")
        b_settings.clicked.connect(self.open_settings)
        b_help.clicked.connect(lambda: HelpDialog(self).exec())
        b_about.clicked.connect(lambda: AboutDialog(self.ctx.settings, self).exec())
        for b in (self.theme_btn, b_settings, b_help, b_about):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            lay.addWidget(b)
        return h

    def _build_nav(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("NavRail")
        nav.setFixedWidth(104)
        lay = QVBoxLayout(nav)
        lay.setContentsMargins(0, 14, 0, 10)
        lay.setSpacing(4)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for i, (text, ic, tip) in enumerate((
                ("Text", "text", "Text converter"),
                ("Document", "document", "Word document converter"),
                ("Batch", "batch", "Convert many files"),
                ("History", "history", "History and recent files"))):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setIconSize(QSize(22, 22))
            b.setMinimumWidth(88)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            set_icon(b, ic, "muted")
            self.nav_group.addButton(b, i)
            lay.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        self.nav_group.idClicked.connect(self.go)
        lay.addStretch(1)
        ver = label(f"v{S.APP_VERSION}", "NavVersion")
        ver.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(ver)
        return nav

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        sb.setSizeGripEnabled(True)
        self.setStatusBar(sb)
        self.pill = StatusPill()
        self.status_msg = QLabel("Ready")
        self.busy_bar = QProgressBar()
        self.busy_bar.setObjectName("Mini")
        self.busy_bar.setRange(0, 0)
        self.busy_bar.setMaximumWidth(110)
        self.busy_bar.hide()
        self.dir_label = QLabel("Unicode → Bijoy")
        self.file_label = QLabel("")
        self.font_btn = QToolButton()
        self.font_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.font_btn.clicked.connect(self.show_font_help)
        sb.addWidget(self.pill)
        sb.addWidget(self.status_msg, 1)
        sb.addPermanentWidget(self.busy_bar)
        sb.addPermanentWidget(self.file_label)
        sb.addPermanentWidget(self.dir_label)
        sb.addPermanentWidget(self.font_btn)

    def _wire(self) -> None:
        for page in (self.text_page, self.doc_page, self.batch_page, self.history_page):
            page.status.connect(self.set_status)
        for page in (self.text_page, self.doc_page, self.batch_page):
            page.history_entry.connect(self.add_history)
            page.busy.connect(self.set_busy)
        self.text_page.font_help.connect(self.show_font_help)
        self.text_page.files_dropped.connect(self.handle_files)
        self.text_page.file_info.connect(self.file_label.setText)
        self.doc_page.file_info.connect(self.file_label.setText)
        self.text_page.direction_changed.connect(
            lambda d: self.dir_label.setText("Unicode → Bijoy" if d == "U2B" else "Bijoy → Unicode"))
        self.history_page.restore_text.connect(self._restore_from_history)
        self.doc_page.many_files.connect(self.handle_files)
        self.history_page.open_file.connect(lambda p: self.handle_files([Path(p)]))

    def _build_actions(self) -> None:
        def act(text, shortcut, fn):
            a = QAction(text, self)
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            a.triggered.connect(fn)
            self.addAction(a)
            return a

        act("New", "Ctrl+N", self.new_document)
        act("Open", "Ctrl+O", self.open_dialog)
        act("Save", "Ctrl+S", lambda: self._text_cmd(lambda: self.text_page.save_output(False)))
        act("Save As", "Ctrl+Shift+S", lambda: self._text_cmd(lambda: self.text_page.save_output(True)))
        act("Find", "Ctrl+F", lambda: self._text_cmd(self.text_page.show_find))
        act("Convert", "Ctrl+Return", self.convert_current)
        act("Convert", "Ctrl+Enter", self.convert_current)
        act("Copy output", "Ctrl+Shift+C", lambda: self._text_cmd(self.text_page.copy_output))
        act("Zoom in", "Ctrl+=", lambda: self.text_page.zoom(+1))
        act("Zoom in", "Ctrl++", lambda: self.text_page.zoom(+1))
        act("Zoom out", "Ctrl+-", lambda: self.text_page.zoom(-1))
        act("Reset zoom", "Ctrl+0", lambda: self.text_page.zoom(0))
        for i in range(4):
            act(f"Page {i + 1}", f"Alt+{i + 1}", lambda _=False, i=i: self.go(i))

    # ------------------------------------------------------------ navigation
    def go(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        btn = self.nav_group.button(index)
        if btn is not None:
            btn.setChecked(True)
        if index == PAGE_HISTORY:
            self.history_page.refresh()
        elif index == PAGE_BATCH:
            self.batch_page.sync_direction()
        elif index == PAGE_DOC:
            self.doc_page._apply_direction()
        self._retint_nav()

    def _text_cmd(self, fn) -> None:
        if self.stack.currentIndex() != PAGE_TEXT:
            self.go(PAGE_TEXT)
        fn()

    def convert_current(self) -> None:
        idx = self.stack.currentIndex()
        if idx == PAGE_TEXT:
            self.text_page.convert(record=True)
        elif idx == PAGE_DOC:
            self.doc_page.convert()
        elif idx == PAGE_BATCH:
            self.batch_page.start()

    # ------------------------------------------------------------ status
    def set_status(self, state: str, msg: str) -> None:
        names = {"ready": "Ready", "busy": "Processing", "ok": "Converted", "error": "Error"}
        if state == "ok" and not msg.lower().startswith("convert"):
            names["ok"] = "Done"
        self.pill.set_state(state, names.get(state, state.title()))
        self.status_msg.setText(msg)
        if state == "error":
            log.warning("UI error status: %s", msg)

    def set_busy(self, on: bool) -> None:
        self.busy_bar.setVisible(on or self.ctx.runner.busy())

    def add_history(self, entry: dict) -> None:
        try:
            self.ctx.history.add(
                mode=entry.get("mode", "text"), direction=entry.get("direction", "U2B"),
                source=str(entry.get("source", "")), output=str(entry.get("output", "")),
                chars=int(entry.get("chars", 0)), status=entry.get("status", "ok"),
                detail=str(entry.get("detail", "")), input_text=entry.get("input_text", ""),
                output_text=entry.get("output_text", ""))
        except Exception:
            log.exception("could not write history")

    # ------------------------------------------------------------ fonts
    def _apply_font_status(self) -> None:
        ok = self.ctx.bijoy_installed
        self.font_btn.setText("SutonnyMJ: Installed" if ok else "SutonnyMJ: Not installed")
        self.font_btn.setObjectName("FontOk" if ok else "FontMissing")
        self.font_btn.setToolTip("SutonnyMJ font is available for previews" if ok else
                                 "Click for font installation help")
        set_icon(self.font_btn, "check" if ok else "alert", "success" if ok else "warning")
        self.font_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.font_btn.style().unpolish(self.font_btn)
        self.font_btn.style().polish(self.font_btn)
        self.text_page.set_font_status(ok)

    def show_font_help(self) -> None:
        dlg = FontHelpDialog(self.ctx.bijoy_installed, self)

        def recheck():
            self.ctx.bijoy_installed = detect_bijoy_font()
            self._apply_font_status()
            self.text_page.apply_fonts()
            QMessageBox.information(dlg, "Font check", "SutonnyMJ found and loaded."
                                    if self.ctx.bijoy_installed else
                                    "SutonnyMJ is still not installed. If you just installed it, "
                                    "restart TIS.")
        dlg.recheck_requested.connect(recheck)
        dlg.exec()

    # ------------------------------------------------------------ theme
    def apply_theme(self, name: str, save: bool = True) -> None:
        p = set_theme(name)
        self.ctx.settings.theme = p.name
        QApplication.instance().setStyleSheet(stylesheet(p))
        for b in self.findChildren(QAbstractButton):
            ic = b.property("tis_icon")
            if ic:
                b.setIcon(icon(ic, role_color(p, b.property("tis_icon_role") or "text")))
        set_icon(self.theme_btn, "sun" if p.name == "dark" else "moon", "header")
        self._retint_nav()
        if save:
            self.ctx.save_settings()

    def _retint_nav(self) -> None:
        p = current_palette()
        for b in self.nav_group.buttons():
            ic = b.property("tis_icon")
            if ic:
                b.setIcon(icon(ic, p.accent if b.isChecked() else p.muted))

    def toggle_theme(self) -> None:
        self.apply_theme("light" if current_palette().name == "dark" else "dark")

    # ------------------------------------------------------------ dialogs
    def open_settings(self) -> None:
        dlg = SettingsDialog(self.ctx.settings, self.ctx.corrections, self)
        if dlg.exec():
            dlg.apply()
            self.ctx.save_settings()
            try:
                self.ctx.corrections.save(S.corrections_file())
            except OSError as e:
                QMessageBox.warning(self, "Settings", f"Could not save correction rules: {e}")
            self.apply_theme(self.ctx.settings.theme)
            self.text_page.live.setChecked(self.ctx.settings.live_convert)
            self.text_page.apply_fonts()
            self.doc_page.load_options()
            if self.text_page.inp.editor.toPlainText().strip():
                self.text_page.convert(record=False)
            self.set_status("ready", "Settings saved")

    # ------------------------------------------------------------ files
    def new_document(self) -> None:
        self.go(PAGE_TEXT)
        self.text_page.new_document()

    def open_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open", self.ctx.settings.last_open_dir,
            "Supported files (*.txt *.docx);;Text files (*.txt);;Word documents (*.docx)")
        if paths:
            self.handle_files([Path(p) for p in paths])

    def handle_files(self, paths: list[Path]) -> None:
        paths = [Path(p) for p in paths]
        if not paths:
            return
        if len(paths) > 1 or paths[0].is_dir():
            self.go(PAGE_BATCH)
            n = self.batch_page.add_files(paths)
            self.set_status("ready", f"Added {n} file(s) to the batch")
            s = self.ctx.settings
            if n and s.auto_convert_docs and s.batch_next_to_source:
                self.batch_page.start()      # converted copies go next to each original
            return
        p = paths[0]
        ext = p.suffix.lower()
        if ext == ".txt":
            self.go(PAGE_TEXT)
            self.text_page.open_text_file(p)
        elif ext in (".docx", ".doc"):
            self.go(PAGE_DOC)
            self.doc_page.select_file(p)
        else:
            QMessageBox.warning(self, "Unsupported file",
                                f"'{p.name}' is not supported. Use .txt or .docx files.")

    def _restore_from_history(self, text: str, direction: str) -> None:
        self.go(PAGE_TEXT)
        self.text_page.restore_history(text, direction)

    def dragEnterEvent(self, e):  # noqa: N802
        if local_paths(e.mimeData()):
            e.acceptProposedAction()

    def dropEvent(self, e):  # noqa: N802
        paths = local_paths(e.mimeData())
        if paths:
            e.acceptProposedAction()
            self.handle_files(paths)

    # ------------------------------------------------------------ lifecycle
    def _restore_geometry(self) -> None:
        g = self.ctx.settings.window_geometry
        if g:
            try:
                self.restoreGeometry(QByteArray.fromBase64(g.encode("ascii")))
                return
            except Exception:
                pass
        self.resize(1280, 800)

    def closeEvent(self, e):  # noqa: N802
        if self.ctx.runner.busy():
            r = QMessageBox.question(self, "Conversion running",
                                     "A conversion is still running. Cancel it and quit?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
            self.ctx.runner.cancel_all()
            self.ctx.runner.wait(5000)
        self.text_page.autosave_now()
        self.ctx.settings.window_geometry = self.saveGeometry().toBase64().data().decode("ascii")
        self.ctx.save_settings()
        try:
            self.ctx.history.close()
        except Exception:
            pass
        e.accept()
