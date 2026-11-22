"""Mode B — single Word document converter."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QProgressBar, QVBoxLayout, QWidget)

from services.docx_service import DocxConverter
from services.file_naming import same_file, suggest_output_name, unique_path

from .components import Banner, Card, DropZone, Segmented, label, push_button
from .context import AppContext
from .workers import Worker


def _fmt_size(n: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def reveal_in_folder(path: Path) -> None:
    import subprocess
    import sys
    path = Path(path)
    if sys.platform == "win32" and path.exists():
        try:
            subprocess.Popen(["explorer.exe", "/select,", str(path)])
            return
        except OSError:
            pass
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent if path.is_file() else path)))


class DocumentPage(QWidget):
    many_files = Signal(list)          # several files dropped -> batch, saved next to originals
    status = Signal(str, str)
    busy = Signal(bool)
    history_entry = Signal(dict)
    file_info = Signal(str)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.src: Path | None = None
        self.last_output: Path | None = None
        self._job: Worker | None = None
        self._job_dst: Path | None = None
        self._job_direction = "U2B"

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)
        root.addWidget(label("Document Converter", "PageTitle"))
        root.addWidget(label("Convert a Word document (.docx) between Unicode and Bijoy. Only the Bengali "
                             "text changes. Formatting, tables, images, English text and equations stay exactly "
                             "as they are, and the original file is never changed.", "PageSubtitle", wrap=True))

        self.drop = DropZone("Drop a Word document here",
                             "or click to choose. Each converted copy is saved automatically "
                             "in the same folder as its original.")
        self.drop.clicked.connect(self.browse_source)
        self.drop.files_dropped.connect(self._dropped)
        root.addWidget(self.drop)

        # ---- conversion type (separate option below the drop area)
        dir_row = QHBoxLayout()
        dir_row.addWidget(label("Conversion type", "CardTitle"))
        dir_row.addSpacing(8)
        self.dir_switch = Segmented(["Unicode → Bijoy   (SolaimanLipi → SutonnyMJ)",
                                     "Bijoy → Unicode   (SutonnyMJ → SolaimanLipi)"])
        self.dir_switch.changed.connect(self._direction_changed)
        dir_row.addWidget(self.dir_switch)
        dir_row.addStretch(1)
        root.addLayout(dir_row)

        card = Card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.addWidget(label("Source", "Muted"), 0, 0)
        self.src_label = QLabel("No document selected")
        self.src_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.src_label.setWordWrap(True)
        grid.addWidget(self.src_label, 0, 1, 1, 2)
        grid.addWidget(label("Save as", "Muted"), 1, 0)
        self.dst_edit = QLineEdit()
        self.dst_edit.setPlaceholderText("Output file name is suggested automatically")
        grid.addWidget(self.dst_edit, 1, 1)
        b_dst = push_button("Change…", "folder")
        b_dst.clicked.connect(self.browse_output)
        grid.addWidget(b_dst, 1, 2)
        grid.setColumnStretch(1, 1)
        card.lay.addLayout(grid)

        opts = QHBoxLayout()
        self.opt_highlight = QCheckBox("Highlight converted text")
        self.opt_highlight.setToolTip("Marks converted runs in cyan so you can proofread them")
        self.opt_eq = QCheckBox("Keep equations exactly as they are")
        self.opt_eq.setToolTip("Equations are not touched at all (recommended)")
        self.opt_open = QCheckBox("Open when finished")
        self.opt_auto = QCheckBox("Convert immediately when a file is added")
        self.opt_auto.setToolTip("No extra click: choose or drop a .docx and the converted file is saved right away")
        for cb in (self.opt_auto, self.opt_highlight, self.opt_eq, self.opt_open):
            opts.addWidget(cb)
            cb.toggled.connect(self._store_options)
        opts.addStretch(1)
        card.lay.addLayout(opts)

        act = QHBoxLayout()
        self.convert_btn = push_button("Convert document", "play", primary=True)
        self.convert_btn.clicked.connect(self.convert)
        self.cancel_btn = push_button("Cancel", "stop")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.hide()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.hide()
        self.progress_label = label("", "Muted")
        act.addWidget(self.convert_btn)
        act.addWidget(self.cancel_btn)
        act.addWidget(self.progress, 1)
        act.addWidget(self.progress_label)
        act.addStretch(0)
        card.lay.addLayout(act)
        root.addWidget(card)

        self.result_banner = Banner("success")
        self.result_banner.hide()
        self.error_banner = Banner("error")
        self.error_banner.hide()
        self.result_banner.action_clicked.connect(self.open_output)
        root.addWidget(self.result_banner)
        root.addWidget(self.error_banner)

        self.report_card = Card()
        self.report_card.lay.addWidget(label("Conversion report", "CardTitle"))
        self.report_text = QLabel("")
        self.report_text.setWordWrap(True)
        self.report_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.report_card.lay.addWidget(self.report_text)
        row = QHBoxLayout()
        self.b_open = push_button("Open document", "open_external")
        self.b_reveal = push_button("Show in folder", "folder")
        self.b_open.clicked.connect(self.open_output)
        self.b_reveal.clicked.connect(lambda: self.last_output and reveal_in_folder(self.last_output))
        row.addWidget(self.b_open)
        row.addWidget(self.b_reveal)
        row.addStretch(1)
        self.report_card.lay.addLayout(row)
        self.report_card.hide()
        root.addWidget(self.report_card)
        root.addStretch(1)
        self.load_options()
        self._apply_direction()
        self._update_state()

    # ------------------------------------------------------------ options
    # ------------------------------------------------------------ direction
    @property
    def direction(self) -> str:
        return self.ctx.settings.doc_direction

    def _direction_changed(self, index: int) -> None:
        self.ctx.settings.doc_direction = "B2U" if index == 1 else "U2B"
        self._apply_direction()
        if self.src is not None and self._job is None:
            self.dst_edit.setText(str(self._suggest_output(self.src)))
        self.status.emit("ready", "Bijoy → Unicode selected" if self.direction == "B2U"
                         else "Unicode → Bijoy selected")

    def _apply_direction(self) -> None:
        b2u = self.direction == "B2U"
        self.dir_switch.set_index(1 if b2u else 0)
        # equations are never touched in Bijoy -> Unicode
        self.opt_eq.setEnabled(not b2u)
        self.drop.title.setText(self.drop.title.text() if self.src else
                                ("Drop a Bijoy (SutonnyMJ) Word document here" if b2u
                                 else "Drop a Unicode Word document here"))

    def _suggest_output(self, path: Path) -> Path:
        tag = "Unicode" if self.direction == "B2U" else self.ctx.settings.output_suffix
        return unique_path(path.parent / suggest_output_name(path, tag))

    def load_options(self) -> None:
        s = self.ctx.settings
        for cb, val in ((self.opt_auto, s.auto_convert_docs),
                        (self.opt_highlight, s.highlight_converted), (self.opt_eq, s.keep_equations),
                        (self.opt_open, s.open_after_convert)):
            cb.blockSignals(True)
            cb.setChecked(val)
            cb.blockSignals(False)

    def _store_options(self) -> None:
        s = self.ctx.settings
        s.auto_convert_docs = self.opt_auto.isChecked()
        s.highlight_converted = self.opt_highlight.isChecked()
        s.keep_equations = self.opt_eq.isChecked()
        s.open_after_convert = self.opt_open.isChecked()

    def _update_state(self) -> None:
        running = self._job is not None
        self.convert_btn.setEnabled(self.src is not None and not running)
        self.cancel_btn.setVisible(running)
        self.progress.setVisible(running)
        self.drop.setEnabled(not running)

    # ------------------------------------------------------------ files
    def _dropped(self, paths: list) -> None:
        paths = [Path(p) for p in paths]
        if len(paths) == 1 and paths[0].is_file():
            self.select_file(paths[0])
        else:
            self.many_files.emit(paths)

    def browse_source(self) -> None:
        if self._job is not None:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose Word documents",
                                                self.ctx.settings.last_open_dir,
                                                "Word documents (*.docx)")
        if paths:
            self._dropped([Path(p) for p in paths])

    def select_file(self, path: Path) -> None:
        path = Path(path)
        ext = path.suffix.lower()
        if ext == ".doc":
            QMessageBox.information(self, "Old Word format",
                                    "This is an old .doc file. Open it in Word and use "
                                    "File → Save As → Word Document (*.docx), then convert the .docx.")
            return
        if ext != ".docx":
            QMessageBox.warning(self, "Unsupported file", f"'{path.name}' is not a .docx document.")
            return
        if path.name.startswith("~$"):
            QMessageBox.warning(self, "Temporary file", "This is a Word lock file, not a document.")
            return
        if not path.exists():
            QMessageBox.warning(self, "File not found", str(path))
            return
        self.src = path
        self.ctx.settings.last_open_dir = str(path.parent)
        self.ctx.settings.add_recent(str(path))
        size = path.stat().st_size
        self.src_label.setText(f"<b>{path.name}</b><br><span style='color:gray'>{path.parent}  ·  "
                               f"{_fmt_size(size)}</span>")
        # the converted copy goes into the same folder the file came from
        dst = self._suggest_output(path)
        self.dst_edit.setText(str(dst))
        self.result_banner.hide()
        self.error_banner.hide()
        self.report_card.hide()
        self.drop.title.setText(path.name)
        self.drop.hint.setText("Drop another document to replace it")
        self.file_info.emit(f"{path.name}  ·  {_fmt_size(size)}")
        self.status.emit("ready", "Document ready to convert")
        self._update_state()
        if self.ctx.settings.auto_convert_docs:
            self.convert()

    def browse_output(self) -> None:
        start = self.dst_edit.text() or (str(self.src.parent) if self.src else "")
        path, _ = QFileDialog.getSaveFileName(self, "Save converted document as", start,
                                              "Word documents (*.docx)")
        if path:
            p = Path(path)
            if p.suffix.lower() != ".docx":
                p = p.with_suffix(".docx")
            self.dst_edit.setText(str(p))

    # ------------------------------------------------------------ convert
    def convert(self) -> None:
        if self.src is None or self._job is not None:
            return
        text = self.dst_edit.text().strip()
        if not text:
            QMessageBox.warning(self, "Output file", "Choose where to save the converted document.")
            return
        dst = Path(text)
        if dst.suffix.lower() != ".docx":
            dst = dst.with_suffix(".docx")
        if same_file(dst, self.src):
            QMessageBox.warning(self, "Output file", "The output must be a different file. "
                                "The original document is never overwritten.")
            return
        if dst.exists():
            r = QMessageBox.question(self, "Replace file?", f"'{dst.name}' already exists.\n\n"
                                     "Replace it with the new conversion?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return
        self._store_options()
        self.ctx.settings.last_output_dir = str(dst.parent)
        self.result_banner.hide()
        self.error_banner.hide()
        self.report_card.hide()
        self.progress.setValue(0)
        self.progress_label.setText("Reading document…")
        s = self.ctx.settings
        if self.direction == "B2U":
            from services.docx_b2u import BijoyToUnicodeDocxConverter
            conv = BijoyToUnicodeDocxConverter(s.unicode_output_font, s.highlight_converted)
        else:
            conv = DocxConverter(self.ctx.converter, s.highlight_converted, not s.keep_equations)
        self._job_direction = self.direction
        src = self.src

        def task(worker: Worker):
            return conv.convert_file(
                src, dst, progress=lambda d, t: worker.signals.progress.emit(d, t, ""),
                cancel=worker.cancel_event)

        job = Worker(task)
        job.signals.progress.connect(self._on_progress)
        job.signals.result.connect(self._on_result)
        job.signals.error.connect(self._on_error)
        job.signals.cancelled.connect(self._on_cancelled)
        job.signals.finished.connect(self._on_finished)
        self._job, self._job_dst = job, dst
        self.busy.emit(True)
        self.status.emit("busy", f"Converting {src.name}…")
        self._update_state()
        self.ctx.runner.start(job)

    def cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()
            self.progress_label.setText("Cancelling…")

    def _on_progress(self, done: int, total: int, _msg: str) -> None:
        self.progress.setValue(int(done * 100 / total) if total else 100)
        self.progress_label.setText(f"{done:,} / {total:,} paragraphs")

    def _on_result(self, report) -> None:
        self.last_output = Path(report.output)
        self.result_banner.show_message(f"Converted successfully and saved as {self.last_output.name}.",
                                        "Open document")
        self.report_text.setText(report.summary().replace("\n", "<br>"))
        self.report_card.show()
        self.status.emit("ok", f"Converted {Path(report.source).name}")
        self.file_info.emit(f"Saved: {self.last_output}")
        self.ctx.settings.add_recent(str(self.last_output))
        if report.runs_converted == 0:
            other = "Unicode → Bijoy" if self._job_direction == "B2U" else "Bijoy → Unicode"
            what = "Bijoy (SutonnyMJ)" if self._job_direction == "B2U" else "Unicode Bengali"
            self.error_banner.show_message(
                f"No {what} text was found in this document, so nothing was changed. "
                f"If it is the other type, choose “{other}” under Conversion type and add the file again.")
        self.history_entry.emit(dict(mode="docx", direction=self._job_direction, source=report.source,
                                     output=report.output, chars=report.characters_converted,
                                     detail=report.summary()))
        if self.ctx.settings.open_after_convert:
            self.open_output()
        elif self.ctx.settings.show_in_folder:
            reveal_in_folder(self.last_output)

    def _on_error(self, msg: str) -> None:
        self.error_banner.show_message(msg)
        self.status.emit("error", "Document conversion failed")
        if self.src:
            self.history_entry.emit(dict(mode="docx", direction=self._job_direction, source=str(self.src),
                                         output=str(self._job_dst or ""), chars=0, status="error",
                                         detail=msg))

    def _on_cancelled(self) -> None:
        self.error_banner.show_message("Conversion cancelled. No file was written.")
        self.status.emit("ready", "Cancelled")

    def _on_finished(self) -> None:
        self._job = None
        self.progress_label.setText("")
        self.busy.emit(False)
        self._update_state()

    def open_output(self) -> None:
        if self.last_output and self.last_output.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))
