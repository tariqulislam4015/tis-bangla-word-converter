"""Mode C — batch converter for TXT and DOCX files."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from services.batch_service import SUPPORTED, BatchConverter

from .components import Card, Segmented, flat_button, label, push_button
from .context import AppContext
from .document_page import _fmt_size
from .theme_state import current_palette
from .workers import Worker

MAX_FOLDER_FILES = 5000


class BatchPage(QWidget):
    status = Signal(str, str)
    busy = Signal(bool)
    history_entry = Signal(dict)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.files: list[Path] = []
        self._job: Worker | None = None
        self._ok = 0
        self._fail = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)
        root.addWidget(label("Batch Converter", "PageTitle"))
        root.addWidget(label("Convert many .txt and .docx files in one go. Each file gets a new "
                             "converted copy, and the originals stay untouched.", "PageSubtitle", wrap=True))

        files_card = Card()
        bar = QHBoxLayout()
        bar.addWidget(label("Files", "CardTitle"))
        self.count_chip = label("0 files", "Chip")
        bar.addWidget(self.count_chip)
        bar.addStretch(1)
        self.b_add = flat_button("plus", "Add files", "Add files")
        self.b_folder = flat_button("folder", "Add all .txt/.docx files in a folder", "Add folder")
        self.sub = QCheckBox("Include subfolders")
        self.b_remove = flat_button("minus", "Remove selected files", "Remove")
        self.b_clear = flat_button("trash", "Clear the list", "Clear")
        self.b_add.clicked.connect(self.add_files_dialog)
        self.b_folder.clicked.connect(self.add_folder_dialog)
        self.b_remove.clicked.connect(self.remove_selected)
        self.b_clear.clicked.connect(self.clear_list)
        for wdg in (self.b_add, self.b_folder, self.sub, self.b_remove, self.b_clear):
            bar.addWidget(wdg)
        files_card.lay.addLayout(bar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["File", "Type", "Size", "Status"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(170)
        self.table.setAcceptDrops(False)
        files_card.lay.addWidget(self.table, 1)

        dir_row = QHBoxLayout()
        dir_row.addWidget(label("Conversion type", "Muted"))
        self.dir_switch = Segmented(["Unicode → Bijoy", "Bijoy → Unicode"])
        self.dir_switch.changed.connect(self._direction_changed)
        dir_row.addWidget(self.dir_switch)
        dir_row.addStretch(1)
        files_card.lay.addLayout(dir_row)
        self.next_to_src = QCheckBox("Save each converted file in the same folder as its original")
        self.next_to_src.setChecked(ctx.settings.batch_next_to_source)
        self.next_to_src.toggled.connect(self._next_toggled)
        files_card.lay.addWidget(self.next_to_src)
        out_row = QHBoxLayout()
        out_row.addWidget(label("Output folder", "Muted"))
        self.out_edit = QLineEdit(ctx.settings.last_output_dir)
        self.out_edit.setPlaceholderText("Choose a folder for the converted files")
        out_row.addWidget(self.out_edit, 1)
        b_out = push_button("Browse…", "folder")
        b_out.clicked.connect(self.browse_output)
        out_row.addWidget(b_out)
        files_card.lay.addLayout(out_row)
        self._out_widgets = [out_row.itemAt(i).widget() for i in range(out_row.count())]

        act = QHBoxLayout()
        self.start_btn = push_button("Start batch", "play", primary=True)
        self.start_btn.clicked.connect(self.start)
        self.cancel_btn = push_button("Cancel", "stop")
        self.cancel_btn.clicked.connect(self.cancel)
        self.cancel_btn.hide()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.counts = label("Succeeded: 0   ·   Failed: 0", "Muted")
        self.b_open_out = push_button("Open output folder", "open_external")
        self.b_open_out.clicked.connect(self.open_output_folder)
        act.addWidget(self.start_btn)
        act.addWidget(self.cancel_btn)
        act.addWidget(self.progress, 1)
        act.addWidget(self.counts)
        act.addWidget(self.b_open_out)
        files_card.lay.addLayout(act)
        root.addWidget(files_card, 3)

        log_card = Card()
        log_card.lay.addWidget(label("Conversion log", "CardTitle"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setMinimumHeight(100)
        log_card.lay.addWidget(self.log)
        root.addWidget(log_card, 2)
        self._update_state()
        self._next_toggled(self.next_to_src.isChecked())
        self.sync_direction()

    def _direction_changed(self, index: int) -> None:
        self.ctx.settings.doc_direction = "B2U" if index == 1 else "U2B"

    def sync_direction(self) -> None:
        self.dir_switch.set_index(1 if self.ctx.settings.doc_direction == "B2U" else 0)

    def _next_toggled(self, on: bool) -> None:
        self.ctx.settings.batch_next_to_source = on
        for w in self._out_widgets:
            if w is not None:
                w.setEnabled(not on)

    # ------------------------------------------------------------ list
    def _update_state(self) -> None:
        running = self._job is not None
        self.count_chip.setText(f"{len(self.files)} file{'s' if len(self.files) != 1 else ''}")
        self.start_btn.setEnabled(bool(self.files) and not running)
        self.cancel_btn.setVisible(running)
        for b in (self.b_add, self.b_folder, self.b_remove, self.b_clear):
            b.setEnabled(not running)

    def add_files(self, paths: list[Path]) -> int:
        if self._job is not None:
            return 0
        existing = {p.resolve() for p in self.files}
        added = 0
        skipped = []
        for p in paths:
            p = Path(p)
            if p.is_dir():
                added += self.add_folder(p)
                continue
            if p.suffix.lower() not in SUPPORTED or p.name.startswith("~$"):
                skipped.append(p.name)
                continue
            rp = p.resolve()
            if rp in existing:
                continue
            existing.add(rp)
            self.files.append(p)
            r = self.table.rowCount()
            self.table.insertRow(r)
            item = QTableWidgetItem(p.name)
            item.setToolTip(str(p))
            self.table.setItem(r, 0, item)
            self.table.setItem(r, 1, QTableWidgetItem(p.suffix.lower().lstrip(".").upper()))
            try:
                size = _fmt_size(p.stat().st_size)
            except OSError:
                size = "?"
            self.table.setItem(r, 2, QTableWidgetItem(size))
            self.table.setItem(r, 3, QTableWidgetItem("Waiting"))
            added += 1
        if not self.out_edit.text() and self.files:
            self.out_edit.setText(str(self.files[0].parent / "Converted (Bijoy)"))
        if skipped:
            self._log(f"Skipped {len(skipped)} unsupported file(s): {', '.join(skipped[:8])}"
                      + (" …" if len(skipped) > 8 else ""))
        self._update_state()
        return added

    def add_folder(self, folder: Path) -> int:
        it = folder.rglob("*") if self.sub.isChecked() else folder.iterdir()
        found = []
        try:
            for p in it:
                if p.is_file() and p.suffix.lower() in SUPPORTED and not p.name.startswith("~$"):
                    found.append(p)
                    if len(found) >= MAX_FOLDER_FILES:
                        self._log(f"Stopped after {MAX_FOLDER_FILES} files.")
                        break
        except OSError as e:
            QMessageBox.warning(self, "Folder", f"Could not read folder: {e}")
        return self.add_files(sorted(found))

    def add_files_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Add files", self.ctx.settings.last_open_dir,
                                                "Text and Word files (*.txt *.docx)")
        if paths:
            self.ctx.settings.last_open_dir = str(Path(paths[0]).parent)
            self.add_files([Path(p) for p in paths])

    def add_folder_dialog(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Add folder", self.ctx.settings.last_open_dir)
        if d:
            self.ctx.settings.last_open_dir = d
            n = self.add_folder(Path(d))
            self.status.emit("ready", f"Added {n} file(s)")

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
            del self.files[r]
        self._update_state()

    def clear_list(self) -> None:
        if self.files and QMessageBox.question(
                self, "Clear list", "Remove all files from the list?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.files.clear()
        self.table.setRowCount(0)
        self._update_state()

    def browse_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Output folder", self.out_edit.text())
        if d:
            self.out_edit.setText(d)

    def open_output_folder(self) -> None:
        d = Path(self.files[0].parent) if (self.next_to_src.isChecked() and self.files) \
            else Path(self.out_edit.text())
        if d.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _log(self, msg: str) -> None:
        self.log.appendPlainText(f"[{datetime.now():%H:%M:%S}] {msg}")

    def _set_row_status(self, row: int, text: str, ok: bool | None) -> None:
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        p = current_palette()
        if ok is True:
            item.setForeground(QColor(p.success))
        elif ok is False:
            item.setForeground(QColor(p.danger))
        self.table.setItem(row, 3, item)

    # ------------------------------------------------------------ run
    def start(self) -> None:
        if not self.files or self._job is not None:
            return
        s = self.ctx.settings
        if self.next_to_src.isChecked():
            out_dir = None
        else:
            out = self.out_edit.text().strip()
            if not out:
                QMessageBox.warning(self, "Output folder", "Choose an output folder first.")
                return
            out_dir = Path(out)
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                QMessageBox.critical(self, "Output folder", f"Cannot create the output folder:\n{e}")
                return
            s.last_output_dir = str(out_dir)
        self._ok = self._fail = 0
        for r in range(self.table.rowCount()):
            self._set_row_status(r, "Waiting", None)
        self.progress.setValue(0)
        files = list(self.files)
        self._index = {str(f): i for i, f in enumerate(files)}
        b2u = s.doc_direction == "B2U"
        bc = BatchConverter(self.ctx.converter, highlight=s.highlight_converted,
                            txt_encoding=s.txt_output_encoding,
                            suffix="Unicode" if b2u else s.output_suffix,
                            convert_equations=not s.keep_equations,
                            direction=s.doc_direction, unicode_font=s.unicode_output_font)

        def task(worker: Worker):
            return bc.run(files, out_dir,
                          progress=lambda i, t, p: worker.signals.progress.emit(i, t, str(p)),
                          on_result=worker.signals.item.emit, cancel=worker.cancel_event)

        job = Worker(task)
        job.signals.progress.connect(self._on_progress)
        job.signals.item.connect(self._on_item)
        job.signals.result.connect(self._on_result)
        job.signals.error.connect(self._on_error)
        job.signals.finished.connect(self._on_finished)
        self._job = job
        self._log(f"Started: {len(files)} file(s) → "
                  + ("same folder as each original" if out_dir is None else str(out_dir)))
        self.busy.emit(True)
        self.status.emit("busy", "Batch conversion running…")
        self._update_state()
        self.ctx.runner.start(job)

    def cancel(self) -> None:
        if self._job is not None:
            self._job.cancel()
            self._log("Cancelling after the current file…")

    def _on_progress(self, i: int, total: int, path: str) -> None:
        self.progress.setValue(int(i * 100 / total) if total else 100)
        row = self._index.get(path)
        if row is not None and i < total:
            self._set_row_status(row, "Converting…", None)

    def _on_item(self, fr) -> None:
        row = self._index.get(str(fr.source))
        if fr.ok:
            self._ok += 1
            msg = f"✓ {fr.source.name} → {fr.output.name}"
            if row is not None:
                self._set_row_status(row, f"Done → {fr.output.name}", True)
        else:
            self._fail += 1
            msg = f"✗ {fr.source.name}: {fr.message}"
            if row is not None:
                self._set_row_status(row, f"Failed: {fr.message}", False)
        self._log(msg)
        self.counts.setText(f"Succeeded: {self._ok}   ·   Failed: {self._fail}")

    def _on_result(self, result) -> None:
        state = "cancelled" if result.cancelled else ("ok" if result.failed == 0 else "error")
        summary = (f"Batch {'cancelled' if result.cancelled else 'finished'}: "
                   f"{result.succeeded} succeeded, {result.failed} failed")
        self._log(summary)
        self.status.emit("ok" if state == "ok" else ("ready" if result.cancelled else "error"), summary)
        self.history_entry.emit(dict(mode="batch", direction=self.ctx.settings.doc_direction, source=f"{len(result.results)} files",
                                     output="" if self.next_to_src.isChecked() else self.out_edit.text(),
                                     chars=0, status=state, detail=summary))

    def _on_error(self, msg: str) -> None:
        self._log(f"Batch stopped: {msg}")
        self.status.emit("error", f"Batch stopped: {msg}")

    def _on_finished(self) -> None:
        self._job = None
        self.busy.emit(False)
        self._update_state()
