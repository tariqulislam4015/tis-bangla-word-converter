import zipfile

import docx
from docx.oxml import parse_xml
from docx.shared import Pt
from lxml import etree

from core.correction_rules import normalize_unicode
from services.docx_b2u import convert_docx_to_unicode, is_bijoy_font
from services.docx_service import RPR_ORDER, W_NS, convert_docx

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _w(t):
    return f"{{{W_NS}}}{t}"


def test_bijoy_font_names():
    for n in ("SutonnyMJ", "SutonnyOMJ", "Sutonny OMJ", "TonnyMJ", "NikoshMJ"):
        assert is_bijoy_font(n)
    for n in ("SolaimanLipi", "Times New Roman", "Nirmala UI", None, ""):
        assert not is_bijoy_font(n)


def _bijoy_doc(tmp_path):
    d = docx.Document()
    st = d.styles.add_style("BijoyBody", 1)            # paragraph style with SutonnyMJ
    st.font.name = "SutonnyMJ"
    p = d.add_paragraph()
    r = p.add_run("Avgvi †mvbvi evsjv")                 # explicit font
    r.font.name = "SutonnyMJ"
    r.bold = True
    r.font.size = Pt(14)
    e = p.add_run(" English")                          # English stays
    e.font.name = "Times New Roman"
    p2 = d.add_paragraph(style="BijoyBody")            # font from style
    p2.add_run("cÖkœ 1|")
    p3 = d.add_paragraph()                             # cluster split across runs: w | K
    a = p3.add_run("w")
    a.font.name = "SutonnyMJ"
    b = p3.add_run("Ki")
    b.font.name = "SutonnyMJ"
    b.italic = True
    p3._p.append(parse_xml(f'<m:oMath xmlns:m="{M_NS}"><m:r><m:t>x+y</m:t></m:r></m:oMath>'))
    t = d.add_table(rows=1, cols=1)
    c = t.cell(0, 0).paragraphs[0].add_run("DËi")
    c.font.name = "SutonnyMJ"
    src = tmp_path / "Exam_Bijoy.docx"
    d.save(src)
    return src


def test_bijoy_docx_to_unicode(tmp_path):
    src = _bijoy_doc(tmp_path)
    out = tmp_path / "Exam_Unicode.docx"
    rep = convert_docx_to_unicode(src, out)
    d = docx.Document(out)
    p0 = d.paragraphs[0]
    assert p0.runs[0].text == "আমার সোনার বাংলা"
    assert p0.runs[0].font.name == "SolaimanLipi"
    assert p0.runs[0].bold and p0.runs[0].font.size == Pt(14)
    rpr = p0.runs[0]._element.rPr
    assert rpr.find(_w("bCs")) is not None and rpr.find(_w("szCs")).get(_w("val")) == "28"
    assert p0.runs[1].text == " English" and p0.runs[1].font.name == "Times New Roman"
    assert d.paragraphs[1].text == "প্রশ্ন ১।"
    assert d.paragraphs[2].text == "কির"
    assert d.tables[0].cell(0, 0).text == "উত্তর"
    assert rep.syllables_rejoined == 1
    # equations, styles and every other part untouched
    a, b = zipfile.ZipFile(src), zipfile.ZipFile(out)
    assert {n for n in a.namelist() if a.read(n) != b.read(n)} == {"word/document.xml"}
    ra = etree.fromstring(a.read("word/document.xml"))
    rb = etree.fromstring(b.read("word/document.xml"))
    tag = f"{{{M_NS}}}oMath"
    assert [etree.tostring(x) for x in ra.iter(tag)] == [etree.tostring(x) for x in rb.iter(tag)]
    order = {t: i for i, t in enumerate(RPR_ORDER)}
    for rp in rb.iter(_w("rPr")):
        idx = [order.get(c.tag, 999) for c in rp]
        assert idx == sorted(idx)


def test_unicode_document_left_alone(tmp_path):
    d = docx.Document()
    d.add_paragraph("আমার সোনার বাংলা")
    d.add_paragraph("Plain English")
    src = tmp_path / "u.docx"
    d.save(src)
    rep = convert_docx_to_unicode(src, tmp_path / "o.docx")
    assert rep.runs_converted == 0


def test_round_trip_unicode_bijoy_unicode(tmp_path):
    d = docx.Document()
    lines = ["জ্ঞানার্জনের পথটি কষ্টসাধ্য হলেও অবিচ্ছেদ্য সাধনা এবং নিষ্ঠার মাধ্যমে তা সফল হতে পারে।",
             "প্রশ্ন ১: বিশ্ববিদ্যালয়ের ছাত্র-ছাত্রীরা কর্তৃক রাষ্ট্রের উন্নয়ন", "Class 8 বাংলা 2024"]
    for ln in lines:
        d.add_paragraph(ln)
    src = tmp_path / "a_Unicode.docx"
    d.save(src)
    mid = tmp_path / "a_Bijoy.docx"
    convert_docx(src, mid)
    back = tmp_path / "a_Unicode2.docx"
    convert_docx_to_unicode(mid, back)
    got = [p.text for p in docx.Document(back).paragraphs]
    assert got == [normalize_unicode(x) for x in lines]
