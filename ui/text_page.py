"""Mode A — interactive text converter."""
from __future__ import annotations

import html
import logging
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QHBoxLayout, QMessageBox,
                               QVBoxLayout, QWidget)

from config import settings as S
from core.bijoy_to_unicode import bijoy_to_unicode
from core.text_utils import Kind, contains_bengali, text_stats
from services.docx_service import DocxError, extract_text
from services.export_service import export_docx, pieces_from_report
from services.file_naming import same_file, suggest_output_name
from services.txt_service import TextFileError, read_text_file, write_text_file

from .components import Banner, EditorPanel, Segmented, flat_button, label, push_button
from .context import AppContext
from .dialogs import FindReplaceDialog
from .workers import Worker

log = logging.getLogger(__name__)

U2B, B2U = "U2B", "B2U"
BACKGROUND_THRESHOLD = 60_000        # characters; larger inputs convert off the UI thread
LIVE_LIMIT = 150_000                 # live conversion is paused above this size
RICH_SEGMENT_LIMIT = 6_000           # above this many segments render as plain text


class TextPage(QWidget):
    status = Signal(str, str)          # state, message
    busy = Signal(bool)
    history_entry = Signal(dict)
    font_help = Signal()
    files_dropped = Signal(list)
    file_info = Signal(str)
    direction_changed = Signal(str)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.direction = U2B
        self.source_path: Path | None = None
        self.output_path: Path | None = None
        self.output_plain = ""
        self.last_report = None
        self._job: Worker | None = None
        self._pending_reconvert = False
        self._find: FindReplaceDialog | None = None
        self._job_text = ""
        self._job_record = False

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)

        # ---- title row
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(label("Text Converter", "PageTitle"))
        self.subtitle = label("Type or paste Unicode Bengali to get SutonnyMJ-ready Bijoy text.",
                              "PageSubtitle")
        titles.addWidget(self.subtitle)
        top.addLayout(titles, 1)
        self.dir_switch = Segmented(["Unicode → Bijoy", "Bijoy → Unicode"])
        self.dir_switch.changed.connect(lambda i: self.set_direction(U2B if i == 0 else B2U))
        top.addWidget(self.dir_switch, 0, Qt.AlignmentFlag.AlignVCenter)
        self.live = QCheckBox("Live")
        self.live.setToolTip("Convert automatically while you type")
        self.live.setChecked(ctx.settings.live_convert)
        self.live.toggled.connect(self._live_toggled)
        top.addSpacing(10)
        top.addWidget(self.live, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addSpacing(10)
        self.zoom_out_btn = flat_button("zoom_out", "Smaller text (Ctrl+-)")
        self.zoom_label = label("", "Muted")
        self.zoom_in_btn = flat_button("zoom_in", "Larger text (Ctrl+=)")
        self.zoom_out_btn.clicked.connect(lambda: self.zoom(-1))
        self.zoom_in_btn.clicked.connect(lambda: self.zoom(+1))
        for wdg in (self.zoom_out_btn, self.zoom_label, self.zoom_in_btn):
            top.addWidget(wdg, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(top)

        # ---- workspace
        ws = QHBoxLayout()
        ws.setSpacing(14)
        self.inp = EditorPanel("Unicode Bengali", "SolaimanLipi / Unicode")
        self.out = EditorPanel("Bijoy ANSI — SutonnyMJ", "Output", rich=True, read_only=True)
        self.inp.editor.setPlaceholderText("এখানে ইউনিকোড বাংলা লিখুন বা পেস্ট করুন…\n\n"
                                           "Type or paste Unicode Bengali text here.")
        # no placeholder on the output: it would be drawn in SutonnyMJ glyphs

        b_paste = flat_button("paste", "Paste from clipboard", "Paste")
        b_import = flat_button("import", "Import a .txt or .docx file (Ctrl+O)", "Import")
        b_find = flat_button("search", "Find and replace (Ctrl+F)", "Find")
        b_clear = flat_button("trash", "Clear input (Ctrl+Z restores)", "Clear")
        b_paste.clicked.connect(self.paste)
        b_import.clicked.connect(self.import_dialog)
        b_find.clicked.connect(self.show_find)
        b_clear.clicked.connect(self.clear_input)
        for b in (b_paste, b_import, b_find, b_clear):
            self.inp.add_tool(b)
        self.inp.toolbar.addStretch(1)

        self.b_copy = flat_button("copy", "Copy output (Ctrl+Shift+C)", "Copy")
        self.b_save = flat_button("save", "Save output as .txt (Ctrl+S)", "Save")
        self.b_export = flat_button("export", "Export to a Word document (.docx)", "Export")
        self.b_copy.clicked.connect(self.copy_output)
        self.b_save.clicked.connect(lambda: self.save_output(save_as=False))
        self.b_export.clicked.connect(self.export_docx)
        for b in (self.b_copy, self.b_save, self.b_export):
            self.out.add_tool(b)
        self.out.toolbar.addStretch(1)

        self.font_banner = Banner("warning")
        self.font_banner.hide()
        self.font_banner.action_clicked.connect(self.font_help)
        self.out.banner_area.addWidget(self.font_banner)

        center = QVBoxLayout()
        center.setSpacing(8)
        center.addStretch(1)
        self.convert_btn = push_button("Convert to\nBijoy →", "arrow_right", object_name="ConvertBig")
        self.convert_btn.setToolTip("Convert (Ctrl+Enter)")
        self.convert_btn.setMinimumWidth(138)
        self.convert_btn.clicked.connect(lambda: self.convert(record=True))
        center.addWidget(self.convert_btn)
        center.addSpacing(6)
        self.swap_btn = push_button("Swap", "swap")
        self.swap_btn.setToolTip("Use the output as new input and reverse the direction")
        self.swap_btn.clicked.connect(self.swap)
        self.undo_btn = push_button("Undo", "undo")
        self.redo_btn = push_button("Redo", "redo")
        self.undo_btn.clicked.connect(self.inp.editor.undo)
        self.redo_btn.clicked.connect(self.inp.editor.redo)
        self.undo_btn.setEnabled(False)
        self.redo_btn.setEnabled(False)
        self.inp.editor.undoAvailable.connect(self.undo_btn.setEnabled)
        self.inp.editor.redoAvailable.connect(self.redo_btn.setEnabled)
        clear_all = push_button("Clear all", "trash", object_name="Danger")
        clear_all.clicked.connect(lambda: self.clear_all(confirm=True))
        for b in (self.swap_btn, self.undo_btn, self.redo_btn, clear_all):
            center.addWidget(b)
        center.addStretch(2)

        ws.addWidget(self.inp, 1)
        ws.addLayout(center)
        ws.addWidget(self.out, 1)
        root.addLayout(ws, 1)

        # ---- timers
        self._live_timer = QTimer(self, singleShot=True, interval=260)
        self._live_timer.timeout.connect(lambda: self.convert(record=False))
        self._stats_timer = QTimer(self, singleShot=True, interval=120)
        self._stats_timer.timeout.connect(self._update_input_stats)
        self._autosave_timer = QTimer(self, singleShot=True, interval=1500)
        self._autosave_timer.timeout.connect(self.autosave_now)
        self.inp.editor.textChanged.connect(self._input_changed)
        self.inp.editor.files_dropped.connect(self.files_dropped)
        self.out.editor.files_dropped.connect(self.files_dropped)

        self.apply_fonts()
        self._update_actions()

    # ---------------------------------------------------------------- fonts
    def apply_fonts(self) -> None:
        size = self.ctx.settings.editor_font_size
        uni = QFont(self.ctx.unicode_font, size)
        bij = QFont(S.BIJOY_FONT, size)
        if self.direction == U2B:
            self.inp.editor.setFont(uni)
            self.out.editor.setFont(bij)
            self.out.editor.document().setDefaultFont(bij)
        else:
            self.inp.editor.setFont(bij)
            self.out.editor.setFont(uni)
            self.out.editor.document().setDefaultFont(uni)
        self.zoom_label.setText(f"{size} pt")
        if self.output_plain:
            self._render_last()

    def set_font_status(self, installed: bool) -> None:
        if installed:
            self.font_banner.hide()
        else:
            self.font_banner.show_message(
                "SutonnyMJ isn't installed, so Bijoy text shows as Latin letters. "
                "The text is still correct, and you can copy and save it.", "How to install")

    def zoom(self, step: int) -> None:
        s = self.ctx.settings
        s.editor_font_size = 14 if step == 0 else max(8, min(48, s.editor_font_size + step))
        self.apply_fonts()

    # ------------------------------------------------------------ direction
    def set_direction(self, direction: str) -> None:
        if direction == self.direction:
            return
        self.direction = direction
        self.dir_switch.set_index(0 if direction == U2B else 1)
        self.inp.editor.setPlaceholderText(
            "এখানে ইউনিকোড বাংলা লিখুন বা পেস্ট করুন…\n\nType or paste Unicode Bengali text here."
            if direction == U2B else "")
        if direction == U2B:
            self.inp.title.setText("Unicode Bengali")
            self.inp.chip.setText("SolaimanLipi / Unicode")
            self.out.title.setText("Bijoy ANSI — SutonnyMJ")
            self.convert_btn.setText("Convert to\nBijoy →")
            self.subtitle.setText("Type or paste Unicode Bengali to get SutonnyMJ-ready Bijoy text.")
        else:
            self.inp.title.setText("Bijoy ANSI — SutonnyMJ")
            self.inp.chip.setText("Bijoy / SutonnyMJ")
            self.out.title.setText("Unicode Bengali")
            self.convert_btn.setText("Convert to\nUnicode →")
            self.subtitle.setText("Paste Bijoy (SutonnyMJ) text to get standard Unicode Bengali.")
        self.output_plain = ""
        self.last_report = None
        self.out.editor.clear()
        self.apply_fonts()
        self.direction_changed.emit(direction)
        if self.inp.editor.toPlainText().strip():
            self.convert(record=False)
        self._update_actions()

    # --------------------------------------------------------------- inputs
    def _input_changed(self) -> None:
        self._stats_timer.start()
        if self.ctx.settings.autosave_input:
            self._autosave_timer.start()
        n = self.inp.editor.document().characterCount()
        if self.live.isChecked() and n <= LIVE_LIMIT:
            self._live_timer.start()
        self._update_actions()

    def _live_toggled(self, on: bool) -> None:
        self.ctx.settings.live_convert = on
        if on and self.inp.editor.toPlainText().strip():
            self.convert(record=False)

    def _update_input_stats(self) -> None:
        st = text_stats(self.inp.editor.toPlainText())
        self.inp.set_stats(st.characters, st.words, st.lines)

    def _update_actions(self) -> None:
        has_out = bool(self.output_plain)
        for b in (self.b_copy, self.b_save, self.b_export, self.swap_btn):
            b.setEnabled(has_out)

    def paste(self) -> None:
        self.inp.editor.setFocus()
        self.inp.editor.paste()

    def set_input_text(self, text: str) -> None:
        """Replace input as one undoable edit."""
        cur = QTextCursor(self.inp.editor.document())
        cur.beginEditBlock()
        cur.select(QTextCursor.SelectionType.Document)
        cur.insertText(text)
        cur.endEditBlock()

    def clear_input(self) -> None:
        if self.inp.editor.toPlainText():
            self.set_input_text("")
        self.status.emit("ready", "Input cleared. Press Ctrl+Z to restore it.")

    def clear_all(self, confirm: bool = True) -> bool:
        if confirm and self.inp.editor.toPlainText().strip():
            r = QMessageBox.question(self, "Clear all", "Clear both the input and the output?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return False
        self.set_input_text("")
        self.out.editor.clear()
        self.output_plain = ""
        self.last_report = None
        self.out.set_stats(0, 0, 0)
        self.out.extra.setText("")
        self._update_actions()
        self.status.emit("ready", "Ready")
        return True

    def new_document(self) -> None:
        if self.clear_all(confirm=True):
            self.source_path = None
            self.output_path = None
            self.file_info.emit("")

    def show_find(self) -> None:
        if self._find is None:
            self._find = FindReplaceDialog(self.inp.editor, self)
        sel = self.inp.editor.textCursor().selectedText()
        if sel and " " not in sel:
            self._find.find_edit.setText(sel)
        self._find.show()
        self._find.raise_()
        self._find.find_edit.setFocus()
        self._find.find_edit.selectAll()

    # ------------------------------------------------------------ conversion
    def convert(self, record: bool = True) -> None:
        text = self.inp.editor.toPlainText()
        if not text.strip():
            self.out.editor.clear()
            self.output_plain = ""
            self.last_report = None
            self.out.set_stats(0, 0, 0)
            self.out.extra.setText("")
            self._update_actions()
            if record:
                self.status.emit("ready", "Nothing to convert. The input is empty.")
            return
        if self._job is not None:
            self._pending_reconvert = True
            return
        direction = self.direction
        if len(text) < BACKGROUND_THRESHOLD:
            try:
                result = self._do_convert(None, text, direction)
            except Exception as e:  # pragma: no cover - defensive
                log.exception("conversion failed")
                self.status.emit("error", f"Conversion failed: {e}")
                return
            self._finish(result, text, record)
            return
        self.status.emit("busy", f"Converting {len(text):,} characters…")
        self.busy.emit(True)
        self.convert_btn.setEnabled(False)
        job = Worker(self._do_convert, text, direction)
        self._job_text, self._job_record = text, record
        # bound methods of this widget => queued onto the UI thread
        job.signals.result.connect(self._job_result)
        job.signals.error.connect(self._job_error)
        job.signals.finished.connect(self._job_done)
        self._job = job
        self.ctx.runner.start(job)

    def _job_result(self, res) -> None:
        self._finish(res, self._job_text, self._job_record)

    def _job_error(self, msg: str) -> None:
        self.status.emit("error", f"Conversion failed: {msg}")

    def _job_done(self) -> None:
        self._job = None
        self.busy.emit(False)
        self.convert_btn.setEnabled(True)
        if self._pending_reconvert:
            self._pending_reconvert = False
            self.convert(record=False)

    def _do_convert(self, _worker, text: str, direction: str):
        if direction == U2B:
            return (U2B, self.ctx.converter.convert_with_report(text))
        return (B2U, bijoy_to_unicode(text))

    def _finish(self, result, source_text: str, record: bool) -> None:
        direction, payload = result
        if direction != self.direction:
            return  # direction changed while converting
        if direction == U2B:
            self.last_report = payload
            self.output_plain = payload.output
        else:
            self.last_report = None
            self.output_plain = payload
        self._render_last()
        st = text_stats(self.output_plain)
        self.out.set_stats(st.characters, st.words, st.lines)
        note = ""
        if self.last_report is not None:
            if self.last_report.unmapped:
                note = f"{len(self.last_report.unmapped)} character type(s) kept unchanged"
                self.out.extra.setToolTip("No Bijoy equivalent: " + " ".join(sorted(self.last_report.unmapped)))
            elif self.last_report.fallback_conjuncts:
                note = "Rare conjunct shown with hasanta (&)"
                self.out.extra.setToolTip("Conjuncts without a SutonnyMJ ligature: "
                                          + " ".join(sorted(self.last_report.fallback_conjuncts)))
            else:
                self.out.extra.setToolTip("")
        self.out.extra.setText(note)
        self._update_actions()
        if direction == U2B and not self.last_report.changed and record:
            self.status.emit("ready", "No Unicode Bengali found in the input. "
                                      "To convert Bijoy text, switch to Bijoy → Unicode.")
        else:
            self.status.emit("ok", "Converted" if record else "Converted (live)")
        if record:
            self.history_entry.emit(dict(
                mode="text", direction=direction, source=source_text[:120].replace("\n", " "),
                output=self.output_plain[:120].replace("\n", " "), chars=len(source_text),
                input_text=source_text, output_text=self.output_plain))

    def _render_last(self) -> None:
        ed = self.out.editor
        ed.setUpdatesEnabled(False)
        try:
            ed.clear()
            rep = self.last_report
            if rep is None or len(rep.segments) > RICH_SEGMENT_LIMIT:
                ed.setPlainText(self.output_plain)
            else:
                cursor = QTextCursor(ed.document())
                cursor.beginEditBlock()
                bij = QTextCharFormat()
                bij.setFontFamilies([S.BIJOY_FONT])
                other = QTextCharFormat()
                other.setFontFamilies([self.ctx.ui_font])
                for seg, out in rep.segments:
                    cursor.insertText(out, bij if seg.kind == Kind.BENGALI else other)
                cursor.endEditBlock()
            ed.moveCursor(QTextCursor.MoveOperation.Start)
        finally:
            ed.setUpdatesEnabled(True)

    # ------------------------------------------------------------ clipboard
    def _html_output(self) -> str:
        parts = []
        if self.last_report is not None:
            for seg, out in self.last_report.segments:
                esc = html.escape(out).replace("\n", "<br>")
                if seg.kind == Kind.BENGALI:
                    parts.append(f"<span style=\"font-family:'{S.BIJOY_FONT}'\">{esc}</span>")
                else:
                    parts.append(f"<span>{esc}</span>")
        else:
            esc = html.escape(self.output_plain).replace("\n", "<br>")
            parts.append(f"<span style=\"font-family:'{self.ctx.unicode_font}'\">{esc}</span>")
        return "<html><body>" + "".join(parts) + "</body></html>"

    def copy_output(self) -> None:
        if not self.output_plain:
            self.status.emit("ready", "Nothing to copy yet.")
            return
        sel = self.out.editor.textCursor().selectedText()
        mime = QMimeData()
        if sel:
            mime.setText(sel.replace(" ", "\n"))
        else:
            mime.setText(self.output_plain)
            mime.setHtml(self._html_output())
        QApplication.clipboard().setMimeData(mime)
        self.status.emit("ok", "Copied selection" if sel else
                         "Output copied. Paste into Word to keep SutonnyMJ formatting.")

    # ------------------------------------------------------------ files
    def _confirm_replace_input(self) -> bool:
        if not self.inp.editor.toPlainText().strip():
            return True
        r = QMessageBox.question(self, "Replace input", "Replace the current input text with the file's contents?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.Yes)
        return r == QMessageBox.StandardButton.Yes

    def import_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import text", self.ctx.settings.last_open_dir,
            "Text or Word files (*.txt *.docx);;Text files (*.txt);;Word documents (*.docx)")
        if path:
            self.open_text_file(Path(path))

    def open_text_file(self, path: Path) -> bool:
        path = Path(path)
        try:
            if path.suffix.lower() == ".docx":
                text, enc = extract_text(path), "docx"
            else:
                tf = read_text_file(path)
                text, enc = tf.text, tf.encoding
        except (TextFileError, DocxError) as e:
            QMessageBox.warning(self, "Cannot open file", str(e))
            self.status.emit("error", str(e))
            return False
        if not self._confirm_replace_input():
            return False
        self.ctx.settings.last_open_dir = str(path.parent)
        self.ctx.settings.add_recent(str(path))
        self.source_path = path
        self.output_path = None
        self.set_input_text(text)
        self.file_info.emit(f"{path.name}  ·  {enc}  ·  {len(text):,} chars")
        if self.direction == U2B and text.strip() and not contains_bengali(text):
            r = QMessageBox.question(
                self, "Bijoy text?", "This file has no Unicode Bengali. It may already be Bijoy "
                "text.\n\nSwitch to Bijoy → Unicode?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self.set_direction(B2U)
        self.convert(record=True)
        return True

    def _default_output_name(self, ext: str) -> str:
        tag = self.ctx.settings.output_suffix if self.direction == U2B else "Unicode"
        if self.source_path:
            return suggest_output_name(self.source_path, tag, ext)
        return f"{tag}_output{ext}"

    def _ask_save_path(self, ext: str, filt: str) -> Path | None:
        start = self.ctx.settings.last_output_dir or (str(self.source_path.parent) if self.source_path else "")
        default = str(Path(start) / self._default_output_name(ext)) if start else self._default_output_name(ext)
        path, _ = QFileDialog.getSaveFileName(self, "Save output", default, filt)
        if not path:
            return None
        p = Path(path)
        if not p.suffix:
            p = p.with_suffix(ext)
        if self.source_path and same_file(p, self.source_path):
            QMessageBox.warning(self, "Save output", "Choose a different file name. "
                                "The original file is never overwritten.")
            return None
        self.ctx.settings.last_output_dir = str(p.parent)
        return p

    def save_output(self, save_as: bool = False) -> None:
        if not self.output_plain:
            self.status.emit("ready", "Nothing to save yet. Convert some text first.")
            return
        path = self.output_path if (self.output_path and not save_as) else None
        if path is None:
            path = self._ask_save_path(".txt", "Text files (*.txt)")
            if path is None:
                return
        enc = self.ctx.settings.txt_output_encoding if self.direction == U2B else "utf-8"
        try:
            used = write_text_file(path, self.output_plain, enc)
        except TextFileError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            self.status.emit("error", str(e))
            return
        self.output_path = path
        self.ctx.settings.add_recent(str(path))
        note = "" if used == ("cp1252" if enc == "ansi" else enc) else \
            " (saved as UTF-8 because some characters are not ANSI)"
        self.status.emit("ok", f"Saved {path.name}{note}")
        self.file_info.emit(f"Saved: {path}")
        self.history_entry.emit(dict(mode="txt", direction=self.direction,
                                     source=str(self.source_path or "Text editor"), output=str(path),
                                     chars=len(self.output_plain), detail=f"encoding {used}"))

    def export_docx(self) -> None:
        if not self.output_plain:
            return
        path = self._ask_save_path(".docx", "Word documents (*.docx)")
        if path is None:
            return
        if self.last_report is not None:
            pieces = pieces_from_report(self.last_report)
        else:
            pieces = [(self.output_plain, self.ctx.unicode_font)]
        try:
            export_docx(path, pieces, font_size_pt=max(10, min(28, self.ctx.settings.editor_font_size)))
        except DocxError as e:
            QMessageBox.critical(self, "Export failed", str(e))
            self.status.emit("error", str(e))
            return
        self.ctx.settings.add_recent(str(path))
        self.status.emit("ok", f"Exported {path.name}")
        self.history_entry.emit(dict(mode="docx", direction=self.direction, source="Text editor",
                                     output=str(path), chars=len(self.output_plain),
                                     detail="exported from text editor"))

    def swap(self) -> None:
        if not self.output_plain:
            return
        new_input = self.output_plain
        target = B2U if self.direction == U2B else U2B
        self.set_direction(target)
        self.set_input_text(new_input)
        self.convert(record=False)
        self.status.emit("ok", "Swapped. The output is now the input.")

    # ------------------------------------------------------------ autosave
    def autosave_now(self) -> None:
        if not self.ctx.settings.autosave_input:
            return
        try:
            text = self.inp.editor.toPlainText()
            S.autosave_file().write_text(text[:5_000_000], encoding="utf-8")
        except OSError:
            log.warning("autosave failed", exc_info=True)

    def restore_autosave(self) -> None:
        if not self.ctx.settings.autosave_input:
            return
        try:
            text = S.autosave_file().read_text(encoding="utf-8")
        except OSError:
            return
        if text:
            self.inp.editor.setPlainText(text)
            self.convert(record=False)
            self.status.emit("ready", "Restored your last input")

    def restore_history(self, input_text: str, direction: str) -> None:
        if not self._confirm_replace_input():
            return
        self.set_direction(direction if direction in (U2B, B2U) else U2B)
        self.set_input_text(input_text)
        self.convert(record=False)
