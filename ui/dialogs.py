"""Settings, Find/Replace, Font help, About and Help dialogs."""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap, QTextCursor, QTextDocument
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
                               QTextBrowser, QVBoxLayout, QWidget)

from config import settings as S
from core.correction_rules import CorrectionSet, UserRule

from .components import label, push_button


def _logo_label(size: int = 64) -> QLabel:
    lab = QLabel()
    pm = QPixmap(str(S.resource_path("assets/icons/tis_logo_256.png")))
    if not pm.isNull():
        lab.setPixmap(pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation))
    return lab


# ----------------------------------------------------------------- settings
class SettingsDialog(QDialog):
    def __init__(self, settings: S.Settings, corrections: CorrectionSet, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{S.APP_SHORT} — Settings")
        self.setMinimumSize(620, 520)
        self.settings = settings
        self.corrections = corrections
        lay = QVBoxLayout(self)
        tabs = QTabWidget(self)
        lay.addWidget(tabs, 1)

        # General
        gen = QWidget()
        f = QFormLayout(gen)
        f.setContentsMargins(18, 18, 18, 18)
        f.setSpacing(12)
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark"])
        self.theme.setCurrentIndex(1 if settings.theme == "dark" else 0)
        self.live = QCheckBox("Convert while typing (text mode)")
        self.live.setChecked(settings.live_convert)
        self.autosave = QCheckBox("Auto-save input text and restore it on next start")
        self.autosave.setChecked(settings.autosave_input)
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 48)
        self.font_size.setValue(settings.editor_font_size)
        self.font_size.setSuffix(" pt")
        f.addRow("Theme", self.theme)
        f.addRow("", self.live)
        f.addRow("", self.autosave)
        f.addRow("Editor text size", self.font_size)
        self.welcome = QCheckBox("Show the developer welcome screen at start-up")
        self.welcome.setChecked(settings.show_welcome)
        f.addRow("", self.welcome)
        self.voice = QCheckBox("Play the welcome voice")
        self.voice.setChecked(settings.welcome_voice)
        f.addRow("", self.voice)
        tabs.addTab(gen, "General")

        # Documents
        docs = QWidget()
        f2 = QFormLayout(docs)
        f2.setContentsMargins(18, 18, 18, 18)
        f2.setSpacing(12)
        self.highlight = QCheckBox("Highlight converted text in Word documents (for proofreading)")
        self.highlight.setChecked(settings.highlight_converted)
        self.equations = QCheckBox("Keep equations exactly as they are (recommended)")
        self.equations.setChecked(settings.keep_equations)
        self.open_after = QCheckBox("Open the converted document when finished")
        self.open_after.setChecked(settings.open_after_convert)
        self.auto_conv = QCheckBox("Convert a Word file immediately when it is added (no extra click)")
        self.auto_conv.setChecked(settings.auto_convert_docs)
        self.show_folder = QCheckBox("Show the converted file in its folder when finished")
        self.show_folder.setChecked(settings.show_in_folder)
        self.start_doc = QCheckBox("Start on the Document page")
        self.start_doc.setChecked(settings.start_page == "document")
        self.encoding = QComboBox()
        self.encoding.addItems(["ANSI (Windows-1252) — classic Bijoy", "UTF-8"])
        self.encoding.setCurrentIndex(0 if settings.txt_output_encoding == "ansi" else 1)
        self.suffix = QLineEdit(settings.output_suffix)
        self.suffix.setMaxLength(30)
        f2.addRow("", self.highlight)
        f2.addRow("", self.equations)
        f2.addRow("", self.open_after)
        f2.addRow("", self.auto_conv)
        f2.addRow("", self.show_folder)
        f2.addRow("", self.start_doc)
        f2.addRow("Bijoy .txt encoding", self.encoding)
        f2.addRow("Output name tag", self.suffix)
        self.uni_font = QLineEdit(settings.unicode_output_font)
        self.uni_font.setPlaceholderText("SolaimanLipi")
        f2.addRow("Font for Bijoy → Unicode", self.uni_font)
        f2.addRow("", label("Example: Class_8_Unicode.docx → Class_8_<tag>.docx. "
                            "Originals are never overwritten.", "Muted", wrap=True))
        tabs.addTab(docs, "Documents")

        # Corrections
        cor = QWidget()
        cl = QVBoxLayout(cor)
        cl.setContentsMargins(14, 14, 14, 14)
        cl.addWidget(label("Exact replacements applied to the Bijoy output of Bengali text "
                           "(English text is never affected). Use them for house-style "
                           "spellings or rare glyph exceptions.", "Muted", wrap=True))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Find (Bijoy)", "Replace with", "On", "Note"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for r in corrections.rules:
            self._add_row(r.find, r.replace, r.enabled, r.note)
        cl.addWidget(self.table, 1)
        row = QHBoxLayout()
        add = push_button("Add rule", "plus")
        rem = push_button("Remove selected", "trash")
        add.clicked.connect(lambda: self._add_row("", "", True, ""))
        rem.clicked.connect(self._remove_rows)
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        cl.addLayout(row)
        tabs.addTab(cor, "Correction rules")

        # Developer / About info
        dev = QWidget()
        f3 = QFormLayout(dev)
        f3.setContentsMargins(18, 18, 18, 18)
        self.dev_name = QLineEdit(settings.developer)
        self.dev_contact = QLineEdit(settings.developer_contact)
        self.dev_url = QLineEdit(settings.developer_url)
        f3.addRow("Developer / organisation", self.dev_name)
        f3.addRow("Contact", self.dev_contact)
        f3.addRow("Website", self.dev_url)
        f3.addRow("", label("Shown in the About dialog.", "Muted"))
        tabs.addTab(dev, "Developer info")

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _add_row(self, find: str, repl: str, enabled: bool, note: str) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(find))
        self.table.setItem(r, 1, QTableWidgetItem(repl))
        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        chk.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
        self.table.setItem(r, 2, chk)
        self.table.setItem(r, 3, QTableWidgetItem(note))

    def _remove_rows(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def apply(self) -> None:
        s = self.settings
        s.theme = "dark" if self.theme.currentIndex() == 1 else "light"
        s.live_convert = self.live.isChecked()
        s.autosave_input = self.autosave.isChecked()
        s.editor_font_size = self.font_size.value()
        s.show_welcome = self.welcome.isChecked()
        s.welcome_voice = self.voice.isChecked()
        s.highlight_converted = self.highlight.isChecked()
        s.keep_equations = self.equations.isChecked()
        s.open_after_convert = self.open_after.isChecked()
        s.auto_convert_docs = self.auto_conv.isChecked()
        s.show_in_folder = self.show_folder.isChecked()
        s.start_page = "document" if self.start_doc.isChecked() else "text"
        s.txt_output_encoding = "ansi" if self.encoding.currentIndex() == 0 else "utf-8"
        s.output_suffix = self.suffix.text().strip() or "Bijoy"
        s.unicode_output_font = self.uni_font.text().strip() or "SolaimanLipi"
        s.developer = self.dev_name.text().strip()
        s.developer_contact = self.dev_contact.text().strip()
        s.developer_url = self.dev_url.text().strip()
        rules = []
        for r in range(self.table.rowCount()):
            def txt(c, r=r):
                it = self.table.item(r, c)
                return it.text() if it else ""
            find = txt(0)
            if not find:
                continue
            chk = self.table.item(r, 2)
            rules.append(UserRule(find, txt(1),
                                  chk is None or chk.checkState() == Qt.CheckState.Checked, txt(3)))
        self.corrections.rules = rules
        self.corrections.invalidate()


# ------------------------------------------------------------ find/replace
class FindReplaceDialog(QDialog):
    message = Signal(str)

    def __init__(self, editor: QPlainTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find and Replace")
        self.setModal(False)
        g = QGridLayout(self)
        g.setContentsMargins(16, 16, 16, 16)
        g.setSpacing(10)
        self.find_edit = QLineEdit()
        self.repl_edit = QLineEdit()
        self.case = QCheckBox("Match case")
        self.status = label("", "Muted")
        g.addWidget(QLabel("Find"), 0, 0)
        g.addWidget(self.find_edit, 0, 1, 1, 3)
        g.addWidget(QLabel("Replace"), 1, 0)
        g.addWidget(self.repl_edit, 1, 1, 1, 3)
        g.addWidget(self.case, 2, 1)
        b_prev = QPushButton("Previous")
        b_next = push_button("Find next", primary=True)
        b_rep = QPushButton("Replace")
        b_all = QPushButton("Replace all")
        row = QHBoxLayout()
        for b in (b_prev, b_next, b_rep, b_all):
            row.addWidget(b)
        g.addLayout(row, 3, 0, 1, 4)
        g.addWidget(self.status, 4, 0, 1, 4)
        b_next.clicked.connect(lambda: self.find(False))
        b_prev.clicked.connect(lambda: self.find(True))
        b_rep.clicked.connect(self.replace_one)
        b_all.clicked.connect(self.replace_all)
        self.find_edit.returnPressed.connect(lambda: self.find(False))

    def _flags(self, backward: bool = False):
        flags = QTextDocument.FindFlag(0)
        if self.case.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if backward:
            flags |= QTextDocument.FindFlag.FindBackward
        return flags

    def find(self, backward: bool = False) -> bool:
        text = self.find_edit.text()
        if not text:
            return False
        if self.editor.find(text, self._flags(backward)):
            self.status.setText("")
            return True
        # wrap around
        cur = self.editor.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cur)
        ok = self.editor.find(text, self._flags(backward))
        self.status.setText("" if ok else f"“{text}” not found.")
        return ok

    def _selection_matches(self) -> bool:
        sel = self.editor.textCursor().selectedText()
        t = self.find_edit.text()
        return bool(t) and (sel == t if self.case.isChecked() else sel.lower() == t.lower())

    def replace_one(self) -> None:
        if self._selection_matches():
            self.editor.textCursor().insertText(self.repl_edit.text())
        self.find(False)

    def replace_all(self) -> None:
        text = self.find_edit.text()
        if not text:
            return
        import re
        flags = 0 if self.case.isChecked() else re.IGNORECASE
        repl = self.repl_edit.text()
        old = self.editor.toPlainText()
        new, count = re.subn(re.escape(text), lambda _m: repl, old, flags=flags)
        if count:
            cur = QTextCursor(self.editor.document())
            cur.beginEditBlock()           # a single undo step
            cur.select(QTextCursor.SelectionType.Document)
            cur.insertText(new)
            cur.endEditBlock()
        self.status.setText(f"Replaced {count} occurrence(s).")


# ------------------------------------------------------------ font help
class FontHelpDialog(QDialog):
    recheck_requested = Signal()

    def __init__(self, installed: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SutonnyMJ font")
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 18)
        lay.setSpacing(12)
        title = "SutonnyMJ is installed" if installed else "SutonnyMJ is not installed"
        lay.addWidget(label(title, "PageTitle"))
        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setMinimumHeight(260)
        body.setHtml(f"""
<p>Bijoy text is <b>ANSI text</b>: each character is a code that the
<b>SutonnyMJ</b> font draws as a Bengali glyph. Without the font, the converted text
looks like Latin letters (for example <code>Avgvi †mvbvi evsjv</code>). The text is still
correct, and you can copy, save and send it.</p>
<p><b>To install SutonnyMJ on Windows</b></p>
<ol>
<li>Get the font file (<code>SutonnyMJ.ttf</code>) from your licensed Bijoy Bayanno
installation, or from your institution's IT department. {S.APP_SHORT} does not bundle the font
because it is commercially licensed.</li>
<li>Right-click the <code>.ttf</code> file and choose <b>Install for all users</b>.</li>
<li>Click <b>Check again</b> below, or restart {S.APP_SHORT}.</li>
</ol>
<p>In Microsoft Word, select the converted text and choose the <b>SutonnyMJ</b> font.
Documents converted by {S.APP_SHORT} already have SutonnyMJ applied.</p>""")
        lay.addWidget(body)
        row = QHBoxLayout()
        fonts_btn = push_button("Open Fonts folder", "folder")
        web_btn = push_button("Search online", "open_external")
        again = push_button("Check again", "restore")
        close = push_button("Close", primary=True)
        fonts_btn.clicked.connect(self._open_fonts)
        web_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(S.FONT_HELP_URL)))
        again.clicked.connect(self.recheck_requested)
        close.clicked.connect(self.accept)
        for b in (fonts_btn, web_btn, again):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
        if sys.platform != "win32":
            fonts_btn.hide()

    @staticmethod
    def _open_fonts() -> None:
        if sys.platform == "win32":
            try:
                subprocess.Popen(["explorer.exe", "shell:fonts"])
            except OSError:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.join(
                    os.environ.get("WINDIR", r"C:\Windows"), "Fonts")))


# ------------------------------------------------------------ about / help
class AboutDialog(QDialog):
    def __init__(self, settings: S.Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {S.APP_NAME}")
        self.setMinimumWidth(520)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 24, 26, 20)
        lay.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(_logo_label(72))
        names = QVBoxLayout()
        names.addWidget(label(S.APP_NAME, "PageTitle"))
        names.addWidget(label(S.APP_TAGLINE, "PageSubtitle"))
        names.addWidget(label(f"Version {S.APP_VERSION}", "Chip"), 0, Qt.AlignmentFlag.AlignLeft)
        top.addLayout(names, 1)
        lay.addLayout(top)

        # developer card: photo, name, position, channel and clickable links
        from .welcome import Avatar, link_icon_pixmap
        prof = S.DEVELOPER_PROFILE
        card = QHBoxLayout()
        card.setSpacing(16)
        card.addWidget(Avatar(QPixmap(str(S.resource_path(prof["photo"]))), 96), 0, Qt.AlignmentFlag.AlignTop)
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        nm = QLabel(prof["name"])
        nm.setStyleSheet("font-size: 14pt; font-weight: 700;")
        info_col.addWidget(nm)
        info_col.addWidget(label(f"______{prof['position']}______", "Muted"))
        info_col.addWidget(QLabel(f"YouTube Channel: <b>{prof['channel']}</b>"))
        for kind, title, url in prof["links"]:
            row = QHBoxLayout()
            row.setSpacing(8)
            ic = QLabel()
            ic.setPixmap(link_icon_pixmap(kind, 18))
            ln = QLabel(f'<a href="{url}">{url}</a>')
            ln.setOpenExternalLinks(True)
            ln.setToolTip(f"Open {title}")
            row.addWidget(ic)
            row.addWidget(ln, 1)
            info_col.addLayout(row)
        card.addLayout(info_col, 1)
        lay.addLayout(card)
        dev = settings.developer or S.DEFAULT_DEVELOPER
        contact = " · ".join(x for x in (settings.developer_contact, settings.developer_url) if x)
        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setMinimumHeight(250)
        info.setHtml(f"""
<p><b>{S.APP_NAME}</b> converts Bengali Unicode text (SolaimanLipi, Nirmala UI, Kalpurush
and other Unicode fonts) to Bijoy ANSI text for the SutonnyMJ font. It converts typed text,
Word documents and whole folders. Bijoy text can also be converted back to Unicode in
text mode.</p>
<p><b>Developer:</b> {dev}{('<br>' + contact) if contact else ''}</p>
<p><b>Licence:</b> MIT License. See LICENSE.txt in the installation folder.</p>
<p><b>Credits</b><br>
Built with Python, Qt for Python (PySide6, LGPLv3), python-docx (MIT) and lxml (BSD).<br>
The open-source project <i>WordBuddy</i> by Farias Hamid Jim was studied as a reference.
TIS's conversion engine is an independent implementation, and no WordBuddy code is used.<br>
SutonnyMJ and Bijoy are trademarks of their respective owners. The font is not bundled.</p>""")
        lay.addWidget(info)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


HELP_HTML = f"""
<h2>Using {S.APP_SHORT}</h2>
<h3>1. Text converter</h3>
<ol><li>Type or paste Unicode Bengali text in the left panel (<b>Ctrl+V</b>), or import a
.txt / .docx file.</li>
<li>Click <b>Convert to Bijoy →</b> (<b>Ctrl+Enter</b>). With <i>Live</i> switched on,
the text converts as you type.</li>
<li>Click <b>Copy</b> (<b>Ctrl+Shift+C</b>). The clipboard holds formatted text, so pasting
into Word keeps SutonnyMJ on the Bengali parts and the original font on the English
parts.</li>
<li>Save as .txt (<b>Ctrl+S</b>) or export to a Word document.</li></ol>
<p>Use the direction switch to convert <b>Bijoy → Unicode</b> instead. The swap button moves
the result back into the input.</p>
<h3>2. Document converter</h3>
<p>Choose or drop a <b>.docx</b> file, check the output name, and click <b>Convert
document</b>. The original file is never changed. Formatting, tables, headers, footers, text boxes,
hyperlinks and equations are kept exactly. Only Bengali text is converted and set in SutonnyMJ.
English words, digits and symbols keep their own font.</p>
<h3>3. Batch converter</h3>
<p>Add many .txt and .docx files (or a whole folder), choose an output folder and click
<b>Start</b>. Failed files are listed in the log and don't stop the batch.</p>
<h3>How the conversion works</h3>
<p>Unicode stores Bengali in logical order: consonant, then vowel sign. Bijoy stores it in visual
order. For example, the ি in কি comes first (<code>wK</code>), and the reph র্ is placed after its
consonant (<code>Kg©</code> = কর্ম). {S.APP_SHORT} splits the text into syllables, reorders
each one, picks the right conjunct glyph (for example ক্ষ, ন্ত, স্ত্র) and selects the matching
vowel-sign shape (for example <code>Kz</code> কু and <code>cy</code> পু).</p>
<h3>Troubleshooting</h3>
<ul>
<li><b>The output looks like English letters.</b> The SutonnyMJ font isn't installed or selected.
See <i>Font status</i> in the status bar.</li>
<li><b>A rare conjunct shows a visible hasanta (&amp;).</b> SutonnyMJ has no ready glyph for it.
The text is still correct. You can add a correction rule in <i>Settings → Correction rules</i>.</li>
<li><b>Some Bengali in a document wasn't converted.</b> Text in images, WordArt or charts
can't be converted. The conversion report lists anything that was kept unchanged.</li>
<li><b>Old .doc files</b> must be saved as .docx in Word first.</li>
</ul>
<h3>Keyboard shortcuts</h3>
<table cellpadding="3">
<tr><td><b>Ctrl+N</b></td><td>New</td><td><b>Ctrl+O</b></td><td>Open</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save output</td><td><b>Ctrl+Shift+S</b></td><td>Save output as</td></tr>
<tr><td><b>Ctrl+Enter</b></td><td>Convert</td><td><b>Ctrl+Shift+C</b></td><td>Copy output</td></tr>
<tr><td><b>Ctrl+Z / Ctrl+Y</b></td><td>Undo / Redo</td><td><b>Ctrl+F</b></td><td>Find and replace</td></tr>
<tr><td><b>Ctrl+= / Ctrl+-</b></td><td>Zoom</td><td><b>Ctrl+0</b></td><td>Reset zoom</td></tr>
</table>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{S.APP_SHORT} — Help")
        self.resize(720, 640)
        lay = QVBoxLayout(self)
        b = QTextBrowser()
        b.setOpenExternalLinks(True)
        b.setHtml(HELP_HTML)
        lay.addWidget(b)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.setMinimumSize(QSize(520, 420))
