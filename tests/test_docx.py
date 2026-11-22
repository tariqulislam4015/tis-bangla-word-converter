import zipfile

import docx
import pytest
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.shared import Pt, RGBColor

from services.docx_service import (RPR_ORDER, W_NS, DocxConverter, DocxError,
                                   convert_docx, extract_text)

NS = {"w": W_NS}


def _w(tag):
    return f"{{{W_NS}}}{tag}"


def _fonts(run):
    rf = run._element.rPr.find(_w("rFonts")) if run._element.rPr is not None else None
    return None if rf is None else (rf.get(_w("ascii")), rf.get(_w("hAnsi")), rf.get(_w("cs")))


@pytest.fixture
def sample(tmp_path):
    d = docx.Document()
    p = d.add_paragraph()
    p.add_run("আমার সোনার বাংলা")      # inherited font (no explicit name)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    b = p.add_run(" বাংলাদেশ")
    b.bold = True
    b.font.size = Pt(16)
    b.font.color.rgb = RGBColor(0x12, 0x34, 0x56)

    d.add_paragraph("Class 8 বাংলা পরীক্ষা 2024")            # mixed run
    split = d.add_paragraph()
    split.add_run("ক")                                      # syllable split: ক | ি
    split.add_run("িছু").italic = True
    d.add_paragraph("")                                     # empty paragraph
    d.add_paragraph("English only paragraph")

    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "প্রশ্ন"
    inner = t.cell(0, 1).add_table(rows=1, cols=1)
    inner.cell(0, 0).text = "উত্তর"

    sec = d.sections[0]
    sec.header.paragraphs[0].text = "শিরোনাম"
    sec.footer.paragraphs[0].text = "পৃষ্ঠা"

    # hyperlink + text box built from raw XML
    hp = d.add_paragraph()
    hp._p.append(parse_xml(
        f'<w:hyperlink xmlns:w="{W_NS}"><w:r><w:t>লিংক</w:t></w:r></w:hyperlink>'))
    tb = d.add_paragraph()
    tb._p.append(parse_xml(
        f'<w:r xmlns:w="{W_NS}" xmlns:v="urn:schemas-microsoft-com:vml"><w:pict><v:shape>'
        f'<v:textbox><w:txbxContent><w:p><w:r><w:t>বাক্স</w:t></w:r></w:p></w:txbxContent>'
        f'</v:textbox></v:shape></w:pict></w:r>'))
    src = tmp_path / "Class_8_Bangla_Unicode.docx"
    d.save(src)
    return src


def test_full_conversion(sample, tmp_path):
    out = tmp_path / "out.docx"
    rep = convert_docx(sample, out)
    d = docx.Document(out)
    p0 = d.paragraphs[0]
    assert p0.text == "Avgvi †mvbvi evsjv evsjv‡`k"
    assert all(_fonts(r) == ("SutonnyMJ",) * 3 for r in p0.runs)
    # formatting preserved
    assert p0.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert p0.runs[1].bold and p0.runs[1].font.size == Pt(16)
    assert p0.runs[1].font.color.rgb == RGBColor(0x12, 0x34, 0x56)
    # mixed run split: English keeps original font, Bengali gets SutonnyMJ
    mixed = d.paragraphs[1]
    assert mixed.text == "Class 8 evsjv cix¶v 2024"
    kinds = [(r.text, _fonts(r)) for r in mixed.runs]
    assert kinds[0][1] is None and kinds[-1][1] is None
    assert any(f == ("SutonnyMJ",) * 3 for _, f in kinds)
    # split syllable re-joined and reordered
    assert d.paragraphs[2].text == "wKQz"
    assert d.paragraphs[2].runs[1].italic
    assert rep.syllables_rejoined == 1
    # untouched content
    assert d.paragraphs[3].text == ""
    assert d.paragraphs[4].text == "English only paragraph"
    assert _fonts(d.paragraphs[4].runs[0]) is None
    # tables, nested tables, header, footer
    assert d.tables[0].cell(0, 0).text == "cÖkœ"
    assert d.tables[0].cell(0, 1).tables[0].cell(0, 0).text == "DËi"
    assert d.sections[0].header.paragraphs[0].text == "wk‡ivbvg"
    assert d.sections[0].footer.paragraphs[0].text == "c„ôv"
    # hyperlink and text box
    body = d.element.body
    texts = [t.text for t in body.iter(_w("t"))]
    assert "wjsK" in texts and "evb" not in texts and "evª" not in texts
    assert "ev·" in texts
    assert rep.paragraphs_converted >= 8


def test_rpr_children_in_schema_order(sample, tmp_path):
    out = tmp_path / "out.docx"
    convert_docx(sample, out, highlight=True)
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml")
    from lxml import etree
    root = etree.fromstring(xml)
    order = {t: i for i, t in enumerate(RPR_ORDER)}
    for rpr in root.iter(_w("rPr")):
        idx = [order.get(c.tag, 999) for c in rpr]
        assert idx == sorted(idx), [c.tag for c in rpr]


def test_complex_script_bold_carried_over(tmp_path):
    d = docx.Document()
    r = d.add_paragraph().add_run("বাংলা")
    r._element.get_or_add_rPr().append(parse_xml(f'<w:bCs xmlns:w="{W_NS}"/>'))
    r._element.rPr.append(parse_xml(f'<w:szCs xmlns:w="{W_NS}" w:val="32"/>'))
    src = tmp_path / "a.docx"
    d.save(src)
    convert_docx(src, tmp_path / "b.docx")
    run = docx.Document(tmp_path / "b.docx").paragraphs[0].runs[0]
    assert run.bold is True
    assert run.font.size == Pt(16)


def test_never_overwrites_source(sample):
    with pytest.raises(DocxError):
        convert_docx(sample, sample)


def test_corrupted_and_doc_files(tmp_path):
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"this is not a zip")
    with pytest.raises(DocxError):
        convert_docx(bad, tmp_path / "o.docx")
    with pytest.raises(DocxError):
        convert_docx(tmp_path / "old.doc", tmp_path / "o.docx")
    assert not (tmp_path / "o.docx").exists()


def test_idempotent_second_pass(sample, tmp_path):
    a, b = tmp_path / "a.docx", tmp_path / "b.docx"
    convert_docx(sample, a)
    rep = convert_docx(a, b)
    assert rep.runs_converted == 0


def test_cancel(sample, tmp_path):
    import threading
    from services.docx_service import Cancelled
    ev = threading.Event()
    ev.set()
    with pytest.raises(Cancelled):
        DocxConverter().convert_file(sample, tmp_path / "x.docx", cancel=ev)
    assert not (tmp_path / "x.docx").exists()


def test_extract_text(sample):
    assert "আমার সোনার বাংলা" in extract_text(sample)


M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _math_doc(tmp_path):
    d = docx.Document()
    p = d.add_paragraph("উত্তর: ")
    p._p.append(parse_xml(
        f'<m:oMath xmlns:m="{M_NS}" xmlns:w="{W_NS}">'
        f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><w:rPr><w:rFonts w:ascii="SolaimanLipi" '
        f'w:hAnsi="SolaimanLipi"/></w:rPr><m:t>ছায়ার দৈর্ঘ্য</m:t></m:r>'
        f'<m:r><m:t>x+বাংলা</m:t></m:r></m:oMath>'))
    src = tmp_path / "math.docx"
    d.save(src)
    return src


def test_equation_text_converted(tmp_path):
    src = _math_doc(tmp_path)
    out = tmp_path / "math_out.docx"
    rep = convert_docx(src, out, convert_equations=True)
    from lxml import etree
    root = etree.fromstring(zipfile.ZipFile(out).read("word/document.xml"))
    mruns = list(root.iter(f"{{{M_NS}}}r"))
    texts = ["".join(r.itertext()) for r in mruns]
    assert texts[0] == "Qvqvi ˆ`N©¨"
    assert "x+" in texts and "evsjv" in texts       # mixed equation run split
    for r in mruns:
        kids = [c.tag for c in r]
        if f"{{{W_NS}}}rPr" in kids and f"{{{M_NS}}}rPr" in kids:
            assert kids.index(f"{{{M_NS}}}rPr") < kids.index(f"{{{W_NS}}}rPr")
    bengali_run = mruns[texts.index("evsjv")]
    assert bengali_run.find(f"{{{W_NS}}}rPr/{{{W_NS}}}rFonts").get(f"{{{W_NS}}}ascii") == "SutonnyMJ"
    assert bengali_run.find(f"{{{M_NS}}}rPr/{{{M_NS}}}sty") is not None
    assert rep.equation_runs_converted == 2
    docx.Document(out)   # still opens


def test_equations_untouched_by_default(tmp_path):
    from lxml import etree
    src = _math_doc(tmp_path)
    out = tmp_path / "o.docx"
    rep = convert_docx(src, out)
    assert rep.equation_runs_converted == 0
    assert any("Equations" in w for w in rep.warnings)
    tag = f"{{{M_NS}}}oMath"
    before = [etree.tostring(e) for e in etree.fromstring(zipfile.ZipFile(src).read("word/document.xml")).iter(tag)]
    after = [etree.tostring(e) for e in etree.fromstring(zipfile.ZipFile(out).read("word/document.xml")).iter(tag)]
    assert before == after and before


def test_only_changed_parts_are_rewritten(sample, tmp_path):
    out = tmp_path / "out.docx"
    rep = convert_docx(sample, out)
    a, b = zipfile.ZipFile(sample), zipfile.ZipFile(out)
    assert a.namelist() == b.namelist()
    changed = {n for n in a.namelist() if a.read(n) != b.read(n)}
    assert changed == {p.lstrip("/") for p in rep.parts}
    assert "word/styles.xml" not in changed and "word/numbering.xml" not in changed
