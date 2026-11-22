"""Reusable widgets."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QPlainTextEdit,
                               QPushButton, QSizePolicy, QTextEdit, QToolButton, QVBoxLayout,
                               QWidget)

from .icons import set_icon

SUPPORTED_DROP = {".txt", ".docx"}


def local_paths(mime) -> list[Path]:
    if not mime.hasUrls():
        return []
    return [Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile()]


def flat_button(icon_name: str, tooltip: str, text: str = "", parent=None) -> QToolButton:
    b = QToolButton(parent)
    b.setObjectName("Flat")
    b.setToolTip(tooltip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setIconSize(QSize(18, 18))
    if text:
        b.setText(text)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    set_icon(b, icon_name)
    return b


def push_button(text: str, icon_name: str | None = None, primary: bool = False,
                object_name: str | None = None, parent=None) -> QPushButton:
    b = QPushButton(text, parent)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        b.setObjectName("Primary")
    if object_name:
        b.setObjectName(object_name)
    if icon_name:
        b.setIconSize(QSize(18, 18))
        set_icon(b, icon_name, "white" if primary or object_name == "ConvertBig" else "text")
    return b


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(16, 14, 16, 14)
        self.lay.setSpacing(10)


def label(text: str, object_name: str | None = None, wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if object_name:
        lab.setObjectName(object_name)
    lab.setWordWrap(wrap)
    return lab


class Banner(QFrame):
    """Inline message bar (warning / success / error) with optional action."""

    action_clicked = Signal()

    def __init__(self, kind: str = "warning", parent=None):
        super().__init__(parent)
        self.setObjectName({"warning": "BannerWarning", "success": "BannerSuccess",
                            "error": "BannerError"}[kind])
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 8, 8)
        self.icon_btn = QToolButton(self)
        self.icon_btn.setObjectName("Flat")
        self.icon_btn.setEnabled(False)
        set_icon(self.icon_btn, {"warning": "alert", "success": "check", "error": "alert"}[kind],
                 {"warning": "warning", "success": "success", "error": "danger"}[kind])
        self.text = QLabel(self)
        self.text.setWordWrap(True)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.action = QPushButton(self)
        self.action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action.hide()
        self.action.clicked.connect(self.action_clicked)
        self.close_btn = flat_button("close", "Dismiss", parent=self)
        self.close_btn.clicked.connect(self.hide)
        lay.addWidget(self.icon_btn)
        lay.addWidget(self.text, 1)
        lay.addWidget(self.action)
        lay.addWidget(self.close_btn)

    def show_message(self, text: str, action: str = "") -> None:
        self.text.setText(text)
        self.action.setVisible(bool(action))
        self.action.setText(action)
        self.show()


def _make_drop_editor(base):
    """Subclass of a Qt text editor that also accepts dropped files.

    Dropped files emit ``files_dropped``; ordinary dropped text still works.
    Built with plain single inheritance (safest with PySide).
    """

    class _DropEditor(base):
        files_dropped = Signal(list)

        def dragEnterEvent(self, e: QDragEnterEvent):  # noqa: N802
            if local_paths(e.mimeData()):
                e.acceptProposedAction()
            else:
                base.dragEnterEvent(self, e)

        def dragMoveEvent(self, e):  # noqa: N802
            if local_paths(e.mimeData()):
                e.acceptProposedAction()
            else:
                base.dragMoveEvent(self, e)

        def dropEvent(self, e: QDropEvent):  # noqa: N802
            paths = local_paths(e.mimeData())
            if paths:
                e.acceptProposedAction()
                self.files_dropped.emit(paths)
            else:
                base.dropEvent(self, e)

    return _DropEditor


DropPlainTextEdit = _make_drop_editor(QPlainTextEdit)
DropTextEdit = _make_drop_editor(QTextEdit)


class EditorPanel(Card):
    """Header + toolbar + editor + stats footer."""

    def __init__(self, title: str, chip: str, rich: bool = False, read_only: bool = False,
                 parent=None):
        super().__init__(parent)
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title = label(title, "CardTitle")
        self.chip = label(chip, "ChipAccent")
        head.addWidget(self.title)
        head.addWidget(self.chip)
        head.addStretch(1)
        self.lay.addLayout(head)
        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(4)
        self.toolbar.setContentsMargins(0, 0, 0, 0)
        self.lay.addLayout(self.toolbar)

        self.banner_area = QVBoxLayout()
        self.banner_area.setSpacing(6)
        self.lay.addLayout(self.banner_area)

        self.editor = DropTextEdit() if rich else DropPlainTextEdit()
        if rich:
            self.editor.setAcceptRichText(False)
        self.editor.setReadOnly(read_only)
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.editor.setMinimumHeight(200)
        self.lay.addWidget(self.editor, 1)

        foot = QHBoxLayout()
        self.stats = label("Characters: 0   ·   Words: 0   ·   Lines: 0", "StatsLabel")
        foot.addWidget(self.stats)
        foot.addStretch(1)
        self.extra = label("", "StatsLabel")
        foot.addWidget(self.extra)
        self.lay.addLayout(foot)

    def add_tool(self, button) -> None:
        self.toolbar.addWidget(button)

    def set_stats(self, chars: int, words: int, lines: int) -> None:
        self.stats.setText(f"Characters: {chars:,}   ·   Words: {words:,}   ·   Lines: {lines:,}")


class Segmented(QFrame):
    """Two-or-more option segmented control."""

    changed = Signal(int)

    def __init__(self, options: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("SegmentBox")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: list[QToolButton] = []
        for i, text in enumerate(options):
            b = QToolButton(self)
            b.setObjectName("Segment")
            b.setText(text)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b)
            self.buttons.append(b)
        self.buttons[0].setChecked(True)
        self.group.idClicked.connect(self.changed)

    def index(self) -> int:
        return self.group.checkedId()

    def set_index(self, i: int) -> None:
        self.buttons[i].setChecked(True)


class DropZone(QFrame):
    """Dashed area that accepts dropped files and opens a picker on click."""

    files_dropped = Signal(list)
    clicked = Signal()

    def __init__(self, title: str, hint: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(150)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QToolButton(self)
        self.icon.setObjectName("Flat")
        self.icon.setIconSize(QSize(40, 40))
        self.icon.setEnabled(False)
        set_icon(self.icon, "document", "accent")
        self.title = label(title, "DropTitle")
        self.hint = label(hint, "Muted")
        for wdg in (self.icon, self.title, self.hint):
            lay.addWidget(wdg, 0, Qt.AlignmentFlag.AlignHCenter)

    def _set_active(self, on: bool) -> None:
        self.setProperty("active", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, e):  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def dragEnterEvent(self, e):  # noqa: N802
        if local_paths(e.mimeData()):
            self._set_active(True)
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):  # noqa: N802
        self._set_active(False)

    def dropEvent(self, e):  # noqa: N802
        self._set_active(False)
        paths = local_paths(e.mimeData())
        if paths:
            e.acceptProposedAction()
            self.files_dropped.emit(paths)


class StatusPill(QLabel):
    def __init__(self, parent=None):
        super().__init__("Ready", parent)
        self.setObjectName("StatusPill")
        self.set_state("ready", "Ready")

    def set_state(self, state: str, text: str) -> None:
        self.setText(text)
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


def h_line() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: rgba(127,127,127,0.25);")
    return f


def spacer_widget() -> QWidget:
    w = QWidget()
    w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return w
