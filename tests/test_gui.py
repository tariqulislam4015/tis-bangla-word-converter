"""Headless GUI tests (run wherever PySide6 is installed; skipped otherwise).

Uses Qt's offscreen platform, so no display is needed (CI-friendly).
"""
import os
import sys

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThreadPool  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from config import settings as S
    from core.correction_rules import CorrectionSet
    from core.unicode_to_bijoy import UnicodeToBijoy
    from services.history_service import HistoryService
    from ui.context import AppContext
    from ui.main_window import MainWindow
    from ui.workers import TaskRunner

    settings = S.Settings(show_in_folder=False)
    cs = CorrectionSet()
    ctx = AppContext(settings=settings, corrections=cs, converter=UnicodeToBijoy(cs),
                     history=HistoryService(tmp_path / "h.sqlite3"), runner=TaskRunner())
    w = MainWindow(ctx)
    w.show()
    yield w
    w.close()


def _wait(app):
    QThreadPool.globalInstance().waitForDone(20000)
    for _ in range(20):
        app.processEvents()


def test_text_conversion_flow(window, app):
    tp = window.text_page
    tp.set_input_text("আমার সোনার বাংলা")
    tp.convert(record=True)
    assert tp.output_plain == "Avgvi †mvbvi evsjv"
    assert tp.out.editor.toPlainText() == "Avgvi †mvbvi evsjv"
    assert "Characters: 18" in tp.out.stats.text()
    assert window.ctx.history.list()[0].output_text == "Avgvi †mvbvi evsjv"
    # undo restores the cleared input
    tp.clear_input()
    assert tp.inp.editor.toPlainText() == ""
    tp.inp.editor.undo()
    assert tp.inp.editor.toPlainText() == "আমার সোনার বাংলা"


def test_mixed_output_html_and_swap(window, app):
    tp = window.text_page
    tp.set_input_text("Class 8 বাংলা")
    tp.convert(record=False)
    html = tp._html_output()
    assert "SutonnyMJ" in html and "Class 8" in html
    tp.swap()
    assert tp.direction == "B2U"
    assert tp.inp.editor.toPlainText() == "Class 8 evsjv"
    assert tp.output_plain.endswith("বাংলা")
    tp.set_direction("U2B")


def test_large_text_runs_in_background(window, app):
    tp = window.text_page
    tp.live.setChecked(False)
    tp.set_input_text("বাংলাদেশ " * 12000)
    tp.convert(record=True)
    _wait(app)
    assert tp.output_plain.startswith("evsjv‡`k evsjv‡`k")


def test_document_page(window, app, tmp_path):
    import docx
    src = tmp_path / "Exam_Unicode.docx"
    d = docx.Document()
    d.add_paragraph("প্রশ্ন")
    d.save(src)
    window.handle_files([src])            # auto-converts immediately (default)
    dp = window.doc_page
    assert dp.src == src
    assert dp.dst_edit.text().endswith("Exam_Bijoy.docx")
    _wait(app)
    out = tmp_path / "Exam_Bijoy.docx"
    assert out.exists()
    assert docx.Document(out).paragraphs[0].text == "cÖkœ"


def test_batch_page(window, app, tmp_path):
    (tmp_path / "a.txt").write_text("আমি", encoding="utf-8")
    bp = window.batch_page
    bp.add_files([tmp_path / "a.txt", tmp_path / "a.txt"])
    assert len(bp.files) == 1
    bp.next_to_src.setChecked(False)          # use an explicit output folder
    bp.out_edit.setText(str(tmp_path / "out"))
    bp.start()
    _wait(app)
    assert (tmp_path / "out" / "a_Bijoy.txt").exists()
    assert "Succeeded: 1" in bp.counts.text()


def test_theme_pages_and_dialogs(window, app):
    window.toggle_theme()
    window.toggle_theme()
    for i in range(4):
        window.go(i)
    from ui.dialogs import AboutDialog, FontHelpDialog, HelpDialog, SettingsDialog
    for dlg in (AboutDialog(window.ctx.settings, window), HelpDialog(window),
                FontHelpDialog(False, window),
                SettingsDialog(window.ctx.settings, window.ctx.corrections, window)):
        dlg.show()
        app.processEvents()
        dlg.close()
    window.text_page.show_find()
    window.text_page._find.close()


def test_welcome_screen(app):
    from ui.welcome import WelcomeScreen
    w = WelcomeScreen("Nirmala UI", seconds=0.3, voice=False)
    done = []
    w.finished.connect(lambda: done.append(True))
    w.show_centered()
    w.start()
    import time
    t0 = time.time()
    while not done and time.time() - t0 < 5:
        app.processEvents()
        time.sleep(0.02)
    assert done, "welcome screen did not close by itself"


def test_multiple_docs_saved_next_to_originals(window, app, tmp_path):
    import docx
    paths = []
    for name in ("a", "b"):
        d = docx.Document()
        d.add_paragraph("বাংলা")
        p = tmp_path / f"{name}.docx"
        d.save(p)
        paths.append(p)
    window.doc_page.many_files.emit(paths)
    _wait(app)
    for name in ("a", "b"):
        assert (tmp_path / f"{name}_Bijoy.docx").exists()


def test_welcome_voice_asset():
    from config import settings as S
    from ui.welcome import WelcomeVoice
    v = WelcomeVoice(str(S.resource_path(S.WELCOME_VOICE)))
    assert 2.5 < v.duration < 4.0
