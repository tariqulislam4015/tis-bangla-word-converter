import threading
from pathlib import Path

import docx

from services.batch_service import BatchConverter
from services.file_naming import suggest_output_name, unique_path
from services.history_service import HistoryService
from services.txt_service import read_text_file, write_text_file


def _make_inputs(d: Path):
    (d / "a_Unicode.txt").write_text("আমার সোনার বাংলা", encoding="utf-8")
    (d / "b.txt").write_bytes("﻿বাংলাদেশ".encode("utf-8"))
    doc = docx.Document()
    doc.add_paragraph("প্রশ্ন")
    doc.save(d / "c.docx")
    (d / "broken.docx").write_bytes(b"garbage")
    (d / "image.png").write_bytes(b"\x89PNG")
    return [d / "a_Unicode.txt", d / "b.txt", d / "c.docx", d / "broken.docx", d / "image.png"]


def test_batch_counts_and_outputs(tmp_path):
    src = tmp_path / "in"
    out = tmp_path / "out"
    src.mkdir()
    files = _make_inputs(src)
    seen = []
    res = BatchConverter().run(files, out, on_result=seen.append)
    assert res.succeeded == 3 and res.failed == 2
    assert len(seen) == 5
    a = read_text_file(out / "a_Bijoy.txt")
    assert a.text == "Avgvi †mvbvi evsjv" and a.encoding == "cp1252"
    assert read_text_file(out / "b_Bijoy.txt").text == "evsjv‡`k"
    assert docx.Document(out / "c_Bijoy.docx").paragraphs[0].text == "cÖkœ"
    # running again never overwrites
    res2 = BatchConverter().run(files[:1], out)
    assert res2.results[0].output.name == "a_Bijoy (2).txt"


def test_batch_cancel(tmp_path):
    files = _make_inputs(tmp_path)
    ev = threading.Event()
    ev.set()
    res = BatchConverter().run(files, tmp_path / "o", cancel=ev)
    assert res.cancelled and res.results == []


def test_naming():
    assert suggest_output_name(Path("Class_8_Bangla_Unicode.docx")) == "Class_8_Bangla_Bijoy.docx"
    assert suggest_output_name(Path("notes.txt")) == "notes_Bijoy.txt"
    assert suggest_output_name(Path("unicode-file.txt")) == "Bijoy-file.txt"


def test_unique_path(tmp_path):
    p = tmp_path / "x.txt"
    assert unique_path(p) == p
    p.write_text("1")
    assert unique_path(p).name == "x (2).txt"


def test_txt_encodings(tmp_path):
    p = tmp_path / "u16.txt"
    p.write_bytes("বাংলা".encode("utf-16"))
    assert read_text_file(p).text == "বাংলা"
    # ANSI falls back to UTF-8 when characters are not representable
    used = write_text_file(tmp_path / "o.txt", "evsjv ৳", "ansi")
    assert used == "utf-8-sig"
    assert read_text_file(tmp_path / "o.txt").text == "evsjv ৳"
    # ANSI Bijoy text read back
    write_text_file(tmp_path / "b.txt", "†mvbvi", "ansi")
    assert read_text_file(tmp_path / "b.txt").text == "†mvbvi"


def test_history(tmp_path):
    h = HistoryService(tmp_path / "h.sqlite3")
    i = h.add("text", "U2B", "আমি", "Avwg", 3, input_text="আমি", output_text="Avwg")
    assert h.get(i).output_text == "Avwg"
    assert h.stats()["conversions"] == 1
    h.clear()
    assert h.list() == []
    h.close()
    bad = tmp_path / "bad.sqlite3"
    bad.write_bytes(b"not a database" * 100)
    h2 = HistoryService(bad)
    h2.add("text", "U2B", "a", "b", 1)
    assert len(h2.list()) == 1


def test_export_docx_fonts(tmp_path):
    import docx as _docx
    from core.unicode_to_bijoy import UnicodeToBijoy
    from services.export_service import export_docx, pieces_from_report
    rep = UnicodeToBijoy().convert_with_report("Class 8 বাংলা\nদ্বিতীয় লাইন")
    out = tmp_path / "e.docx"
    export_docx(out, pieces_from_report(rep))
    runs = [(r.text, r.font.name) for p in _docx.Document(out).paragraphs for r in p.runs]
    assert runs == [("Class 8 ", None), ("evsjv", "SutonnyMJ"), ("wØZxq jvBb", "SutonnyMJ")]


def test_batch_saves_next_to_each_original(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    a = tmp_path / "x" / "a.txt"
    b = tmp_path / "y" / "b.txt"
    a.write_text("আমি", encoding="utf-8")
    b.write_text("তুমি", encoding="utf-8")
    res = BatchConverter().run([a, b], None)
    assert res.succeeded == 2
    assert (tmp_path / "x" / "a_Bijoy.txt").exists()
    assert (tmp_path / "y" / "b_Bijoy.txt").exists()


def test_naming_both_directions():
    assert suggest_output_name(Path("Exam_Bijoy.docx"), "Unicode") == "Exam_Unicode.docx"
    assert suggest_output_name(Path("Exam.docx"), "Unicode") == "Exam_Unicode.docx"


def test_batch_bijoy_to_unicode(tmp_path):
    a = tmp_path / "old_Bijoy.txt"
    a.write_bytes("Avgvi †mvbvi evsjv".encode("cp1252"))
    res = BatchConverter(direction="B2U").run([a], None)
    assert res.succeeded == 1
    assert read_text_file(tmp_path / "old_Unicode.txt").text == "আমার সোনার বাংলা"
