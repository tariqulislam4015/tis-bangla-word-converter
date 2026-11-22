"""Conversion history and recent files."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QListWidget,
                               QListWidgetItem, QMessageBox, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .components import Card, label, push_button
from .context import AppContext
from .document_page import reveal_in_folder

MODE_NAMES = {"text": "Text", "txt": "TXT file", "docx": "Word document", "batch": "Batch"}
DIR_NAMES = {"U2B": "Unicode → Bijoy", "B2U": "Bijoy → Unicode"}


class HistoryPage(QWidget):
    restore_text = Signal(str, str)     # input text, direction
    open_file = Signal(str)
    status = Signal(str, str)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(14)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("History", "PageTitle"))
        self.stats = label("", "PageSubtitle")
        titles.addWidget(self.stats)
        head.addLayout(titles, 1)
        b_refresh = push_button("Refresh", "restore")
        b_clear = push_button("Clear history", "trash", object_name="Danger")
        b_refresh.clicked.connect(self.refresh)
        b_clear.clicked.connect(self.clear)
        head.addWidget(b_refresh)
        head.addWidget(b_clear)
        root.addLayout(head)

        card = Card()
        card.lay.addWidget(label("Recent conversions", "CardTitle"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Time", "Type", "Direction", "Source", "Output", "Status"])
        hh = self.table.horizontalHeader()
        for c in (0, 1, 2, 5):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(lambda _i: self.restore_selected())
        card.lay.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.b_restore = push_button("Restore to editor", "restore")
        self.b_open = push_button("Open output", "open_external")
        self.b_reveal = push_button("Show in folder", "folder")
        self.b_restore.clicked.connect(self.restore_selected)
        self.b_open.clicked.connect(self.open_selected)
        self.b_reveal.clicked.connect(self.reveal_selected)
        for b in (self.b_restore, self.b_open, self.b_reveal):
            row.addWidget(b)
        row.addStretch(1)
        card.lay.addLayout(row)
        root.addWidget(card, 3)

        rc = Card()
        rc.lay.addWidget(label("Recent files", "CardTitle"))
        self.recent = QListWidget()
        self.recent.setMaximumHeight(170)
        self.recent.itemDoubleClicked.connect(self._open_recent)
        rc.lay.addWidget(self.recent)
        rc.lay.addWidget(label("Double-click a file to open it.", "Muted"))
        root.addWidget(rc, 1)
        self._entries = []
        self.table.itemSelectionChanged.connect(self._update_buttons)
        self.refresh()

    def refresh(self) -> None:
        self._entries = self.ctx.history.list(300)
        st = self.ctx.history.stats()
        self.stats.setText(f"{st['conversions']:,} successful conversions  ·  "
                           f"{st['characters']:,} characters converted")
        self.table.setRowCount(len(self._entries))
        for r, e in enumerate(self._entries):
            vals = [e.timestamp.replace("T", "  "), MODE_NAMES.get(e.mode, e.mode),
                    DIR_NAMES.get(e.direction, e.direction), e.source, e.output,
                    {"ok": "✓ OK", "error": "✗ Error", "cancelled": "Cancelled"}.get(e.status, e.status)]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v))
                it.setToolTip(e.detail or str(v))
                self.table.setItem(r, c, it)
        self.recent.clear()
        for p in self.ctx.settings.recent_files:
            it = QListWidgetItem(Path(p).name + "    —    " + str(Path(p).parent))
            it.setData(Qt.ItemDataRole.UserRole, p)
            it.setToolTip(p)
            self.recent.addItem(it)
        self._update_buttons()

    def _selected(self):
        rows = {i.row() for i in self.table.selectedIndexes()}
        if not rows:
            return None
        r = rows.pop()
        return self._entries[r] if r < len(self._entries) else None

    def _update_buttons(self) -> None:
        e = self._selected()
        self.b_restore.setEnabled(bool(e and e.mode == "text" and e.input_text))
        has_file = bool(e and e.output and Path(e.output).exists())
        self.b_open.setEnabled(has_file)
        self.b_reveal.setEnabled(has_file)

    def restore_selected(self) -> None:
        e = self._selected()
        if e is None:
            return
        if e.mode == "text" and e.input_text:
            self.restore_text.emit(e.input_text, e.direction)
        elif e.output and Path(e.output).exists():
            self.open_selected()

    def open_selected(self) -> None:
        e = self._selected()
        if e and e.output and Path(e.output).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(e.output))

    def reveal_selected(self) -> None:
        e = self._selected()
        if e and e.output and Path(e.output).exists():
            reveal_in_folder(Path(e.output))

    def _open_recent(self, item: QListWidgetItem) -> None:
        p = item.data(Qt.ItemDataRole.UserRole)
        if p and Path(p).exists():
            self.open_file.emit(p)
        else:
            self.status.emit("error", f"File not found: {p}")

    def clear(self) -> None:
        if QMessageBox.question(self, "Clear history",
                                "Delete all conversion history? Converted files are not deleted.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.ctx.history.clear()
        self.ctx.settings.recent_files = []
        self.refresh()
        self.status.emit("ready", "History cleared")
