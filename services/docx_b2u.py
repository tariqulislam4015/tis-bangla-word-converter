"""Bijoy (SutonnyMJ ANSI) -> Unicode conversion of Word (.docx) documents.

Bijoy text is made of ordinary Latin-1 characters, so it can only be recognised
by its *font*.  A run is treated as Bijoy when its effective font is a Bijoy
ANSI font (SutonnyMJ, SutonnyOMJ, TonnyMJ ... — names ending in "MJ").  The
effective font is resolved like Word does: run properties, then the run's
character style, then the paragraph style chain, then the document defaults.

Only those runs change: their text is decoded to Unicode Bengali and their
font is set to a Unicode Bengali font (SolaimanLipi by default), including the
complex-script font, size, bold and italic that Word uses for Bengali.
English text, equations, images, tables and all other parts of the file are
left exactly as they are (same byte-for-byte package preservation as the
Unicode -> Bijoy direction).
"""
from __future__ import annotations

import re

from lxml import etree

from core.bijoy_to_unicode import BELOW, FOLA, POST, PRE, REPH, _TABLE, bijoy_to_unicode
from core.text_utils import contains_bengali

from .docx_service import (W_P, W_R, W_RPR, W_T, DocxConverter, DocxReport, _ensure_child,
                           _ensure_rpr, _paragraph_atoms, _set_text, w)

DEFAULT_UNICODE_FONT = "SolaimanLipi"

_BIJOY_NAME = re.compile(r"mj$")
_KNOWN_BIJOY = {"sutonnymj", "sutonnyomj", "sutonnyemj", "tonnymj", "bijoy"}

# glyphs that must stay with the consonant before them / after them
_PRE_GLYPHS = frozenset(g for g, t in _TABLE.items() if t.kind == PRE and len(g) == 1)
_CONT_GLYPHS = frozenset(g for g, t in _TABLE.items()
                         if t.kind in (FOLA, POST, BELOW, REPH) and len(g) == 1) | {"u"}


def is_bijoy_font(name: str | None) -> bool:
    if not name:
        return False
    n = "".join(ch for ch in name.lower() if ch.isalnum())
    return n in _KNOWN_BIJOY or bool(_BIJOY_NAME.search(n))


class StyleFonts:
    """Resolves the effective ASCII font of a run (styles.xml + docDefaults)."""

    def __init__(self, styles_root):
        self.styles: dict[str, tuple[str | None, str | None, str]] = {}
        self.default_para: str | None = None
        self.default_char: str | None = None
        self.doc_default: str | None = None
        if styles_root is None:
            return
        rf = styles_root.find(f"{w('docDefaults')}/{w('rPrDefault')}/{w('rPr')}/{w('rFonts')}")
        self.doc_default = self._font_of(rf)
        for st in styles_root.iter(w("style")):
            sid = st.get(w("styleId"))
            if not sid:
                continue
            stype = st.get(w("type"), "")
            based = st.find(w("basedOn"))
            font = self._font_of(st.find(f"{w('rPr')}/{w('rFonts')}"))
            self.styles[sid] = (font, based.get(w("val")) if based is not None else None, stype)
            if st.get(w("default")) in ("1", "true", "on"):
                if stype == "paragraph":
                    self.default_para = sid
                elif stype == "character":
                    self.default_char = sid

    @staticmethod
    def _font_of(rfonts) -> str | None:
        if rfonts is None:
            return None
        return rfonts.get(w("ascii")) or rfonts.get(w("hAnsi"))

    def _chain(self, sid: str | None) -> str | None:
        seen = set()
        while sid and sid not in seen:
            seen.add(sid)
            font, based, _ = self.styles.get(sid, (None, None, ""))
            if font:
                return font
            sid = based
        return None

    def effective_font(self, run, paragraph) -> str | None:
        rpr = run.find(W_RPR)
        if rpr is not None:
            rf = rpr.find(w("rFonts"))
            if rf is not None:
                f = self._font_of(rf)
                if f:
                    return f
                if rf.get(w("asciiTheme")):
                    return None           # theme font: never a Bijoy font
            rs = rpr.find(w("rStyle"))
            if rs is not None:
                f = self._chain(rs.get(w("val")))
                if f:
                    return f
        pstyle = None
        ppr = paragraph.find(w("pPr")) if paragraph is not None else None
        if ppr is not None:
            ps = ppr.find(w("pStyle"))
            if ps is not None:
                pstyle = ps.get(w("val"))
        f = self._chain(pstyle or self.default_para)
        if f:
            return f
        return self.doc_default


def apply_unicode_font(run, font: str = DEFAULT_UNICODE_FONT, highlight: bool = False) -> None:
    """Set a Unicode Bengali font in every slot Word may use for Bengali text,
    and mirror size/bold/italic into the complex-script properties."""
    rpr = _ensure_rpr(run)
    fonts = _ensure_child(rpr, w("rFonts"))
    for attr in ("asciiTheme", "hAnsiTheme", "cstheme"):
        fonts.attrib.pop(w(attr), None)
    for attr in ("ascii", "hAnsi", "cs"):
        fonts.set(w(attr), font)
    fonts.set(w("hint"), "cs")
    for tag, cs_tag in (("b", "bCs"), ("i", "iCs"), ("sz", "szCs")):
        el = rpr.find(w(tag))
        if el is None:
            continue
        cs_el = _ensure_child(rpr, w(cs_tag))
        val = el.get(w("val"))
        if val is not None:
            cs_el.set(w("val"), val)
    if highlight:
        _ensure_child(rpr, w("highlight")).set(w("val"), "cyan")


def _rejoin_bijoy(atoms) -> int:
    """Keep Bijoy clusters inside one run: a pre-base kar at the end of a run
    moves to the start of the next run; reph/phala/post-kar glyphs at the start
    of a run move to the end of the previous one."""
    moved = 0
    for k in range(len(atoms) - 1):
        a, b = atoms[k], atoms[k + 1]
        ta, tb = a.text or "", b.text or ""
        changed = False
        while ta and ta[-1] in _PRE_GLYPHS:
            tb = ta[-1] + tb
            ta = ta[:-1]
            changed = True
        while tb and ta and tb[0] in _CONT_GLYPHS:
            ta += tb[0]
            tb = tb[1:]
            changed = True
        if changed:
            _set_text(a, ta)
            _set_text(b, tb)
            moved += 1
    return moved


class BijoyToUnicodeDocxConverter(DocxConverter):
    direction = "B2U"

    def __init__(self, unicode_font: str = DEFAULT_UNICODE_FONT, highlight: bool = False):
        super().__init__(None, highlight, convert_equations=False)
        self.unicode_font = unicode_font or DEFAULT_UNICODE_FONT
        self.fonts = StyleFonts(None)

    def convert_document(self, doc, report: DocxReport, progress=None, cancel=None) -> DocxReport:
        try:
            self.fonts = StyleFonts(doc.styles.element)
        except Exception:
            self.fonts = StyleFonts(None)
        return super().convert_document(doc, report, progress, cancel)

    @staticmethod
    def _math_has_bengali(root) -> bool:      # not relevant for this direction
        return False

    def _convert_paragraph(self, p, report: DocxReport) -> bool:
        atoms = []
        for t in _paragraph_atoms(p, include_math=False):
            r = t.getparent()
            if r is None or r.tag != W_R:
                continue
            text = t.text or ""
            if not text or contains_bengali(text):
                continue
            if is_bijoy_font(self.fonts.effective_font(r, p)):
                atoms.append(t)
        if not atoms:
            return False
        report.syllables_rejoined += _rejoin_bijoy(atoms)
        runs = []
        for t in atoms:
            src = t.text or ""
            if src:
                _set_text(t, bijoy_to_unicode(src))
                report.characters_converted += len(src)
            r = t.getparent()
            if not runs or runs[-1] is not r:
                runs.append(r)
        for r in runs:
            apply_unicode_font(r, self.unicode_font, self.highlight)
            report.runs_converted += 1
        return True


def convert_docx_to_unicode(src, dst, unicode_font: str = DEFAULT_UNICODE_FONT,
                            highlight: bool = False, progress=None, cancel=None) -> DocxReport:
    return BijoyToUnicodeDocxConverter(unicode_font, highlight).convert_file(src, dst, progress, cancel)


__all__ = ["BijoyToUnicodeDocxConverter", "convert_docx_to_unicode", "is_bijoy_font",
           "StyleFonts", "apply_unicode_font", "DEFAULT_UNICODE_FONT", "W_T", "W_P", "etree"]
