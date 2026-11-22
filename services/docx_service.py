"""Unicode -> Bijoy conversion of Word (.docx) documents.

Strategy
--------
* Every story part is processed: main body, headers, footers, footnotes,
  endnotes and comments.  Traversal is done on the XML, so text inside
  tables (any nesting depth), text boxes, hyperlinks, content controls and
  field results is reached as well.
* A run is converted only if it contains Bengali Unicode characters.  The
  run's font name is *not* used as a filter (most Bengali runs inherit their
  font from a style, which defeats font-name checks).
* A Bengali syllable split across two runs (common after spell-check or
  partial formatting) is moved into the run where it starts, so pre-base
  vowels and reph can be reordered correctly.  Nothing else is merged.
* A run containing only Bengali (plus spaces / punctuation) keeps its
  element and formatting; only its text and fonts change.  A run mixing
  Bengali with English, digits or symbols is split so that only the Bengali
  part is set in SutonnyMJ.
* Complex-script formatting (bold/italic/size given only via w:bCs, w:iCs,
  w:szCs) is carried over to the regular properties, because Bijoy text is
  not complex-script text.
* Equations (OMML) are left exactly as they are by default.  Optionally,
  Bengali text inside equations can be converted too.
* The output file is the original .docx package with ONLY the changed story
  parts replaced (e.g. word/document.xml).  Styles, numbering, settings,
  themes, images, page setup etc. are copied byte-for-byte from the original.
"""
from __future__ import annotations

import os
import tempfile
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from lxml import etree

from config.settings import BIJOY_FONT
from core import conversion_rules as R
from core.text_utils import Kind, contains_bengali
from core.unicode_to_bijoy import ConversionReport, UnicodeToBijoy

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


W_P, W_R, W_T, W_RPR = w("p"), w("r"), w("t"), w("rPr")
M_R, M_T, M_RPR = f"{{{M_NS}}}r", f"{{{M_NS}}}t", f"{{{M_NS}}}rPr"
_TEXT_FOR_RUN = {W_R: W_T, M_R: M_T}

STORY_TYPES = ("document.main+xml", "template.main+xml", "document.macroEnabled.main+xml",
               "template.macroEnabledTemplate.main+xml", "header+xml", "footer+xml",
               "footnotes+xml", "endnotes+xml", "comments+xml")

# Schema order of children inside w:rPr (ECMA-376 CT_RPr).
RPR_ORDER = [w(t) for t in (
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike",
    "dstrike", "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid",
    "vanish", "webHidden", "color", "spacing", "w", "kern", "position", "sz",
    "szCs", "highlight", "u", "effect", "bdr", "shd", "fitText", "vertAlign",
    "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish", "oMath")]
_RPR_INDEX = {t: i for i, t in enumerate(RPR_ORDER)}

# Characters that continue the syllable started before them.
_CONTINUATION = frozenset(R.VOWEL_SIGNS | {R.HASANTA, R.NUKTA, R.CHANDRABINDU, R.ZWJ, R.ZWNJ})


class DocxError(Exception):
    """User-presentable DOCX error."""


class Cancelled(Exception):
    pass


@dataclass
class DocxReport:
    source: str = ""
    output: str = ""
    parts: list[str] = field(default_factory=list)
    paragraphs_total: int = 0
    paragraphs_converted: int = 0
    runs_converted: int = 0
    runs_split: int = 0
    equation_runs_converted: int = 0
    syllables_rejoined: int = 0
    characters_converted: int = 0
    unmapped: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Paragraphs converted: {self.paragraphs_converted} of {self.paragraphs_total}",
            f"Runs converted: {self.runs_converted} (split for mixed text: {self.runs_split})",
            f"Equation runs converted: {self.equation_runs_converted}",
            f"Bengali characters converted: {self.characters_converted:,}",
        ]
        if self.syllables_rejoined:
            lines.append(f"Syllables re-joined across formatting boundaries: {self.syllables_rejoined}")
        if self.unmapped:
            lines.append("Kept unchanged (no Bijoy equivalent): " + " ".join(sorted(self.unmapped)))
        lines.extend(self.warnings)
        return "\n".join(lines)


ProgressFn = Callable[[int, int], None]


# --------------------------------------------------------------------- rPr
def _child(parent, tag):
    return parent.find(tag)


def _ensure_child(rpr, tag):
    el = rpr.find(tag)
    if el is not None:
        return el
    el = etree.SubElement(rpr, tag)
    rpr.remove(el)
    idx = _RPR_INDEX.get(tag, len(RPR_ORDER))
    pos = len(rpr)
    for k, existing in enumerate(rpr):
        if _RPR_INDEX.get(existing.tag, len(RPR_ORDER)) > idx:
            pos = k
            break
    rpr.insert(pos, el)
    return el


def _ensure_rpr(run):
    rpr = run.find(W_RPR)
    if rpr is None:
        rpr = etree.Element(W_RPR)
        # in an equation run w:rPr must follow m:rPr
        mrpr = run.find(M_RPR) if run.tag == M_R else None
        if run.tag == M_R and mrpr is None:
            # mark as plain text so Word uses the run font, not Cambria Math
            mrpr = etree.Element(M_RPR)
            etree.SubElement(mrpr, f"{{{M_NS}}}sty").set(f"{{{M_NS}}}val", "p")
            run.insert(0, mrpr)
        run.insert(0 if mrpr is None else run.index(mrpr) + 1, rpr)
    return rpr


def apply_bijoy_font(run, font: str = BIJOY_FONT, highlight: bool = False) -> None:
    rpr = _ensure_rpr(run)
    fonts = _ensure_child(rpr, w("rFonts"))
    for attr in ("asciiTheme", "hAnsiTheme", "cstheme", "hint"):
        fonts.attrib.pop(w(attr), None)
    for attr in ("ascii", "hAnsi", "cs"):
        fonts.set(w(attr), font)
    # carry complex-script-only formatting over to regular properties
    for cs_tag, tag in (("bCs", "b"), ("iCs", "i"), ("szCs", "sz")):
        cs_el = rpr.find(w(cs_tag))
        if cs_el is None:
            continue
        if tag == "sz":
            val = cs_el.get(w("val"))
            if val:
                _ensure_child(rpr, w("sz")).set(w("val"), val)
        elif rpr.find(w(tag)) is None:
            el = _ensure_child(rpr, w(tag))
            if cs_el.get(w("val")) is not None:
                el.set(w("val"), cs_el.get(w("val")))
    cs_flag = rpr.find(w("cs"))
    if cs_flag is not None:
        rpr.remove(cs_flag)
    if highlight:
        _ensure_child(rpr, w("highlight")).set(w("val"), "cyan")


def _set_text(t_el, text: str) -> None:
    t_el.text = text
    t_el.set(f"{{{XML_NS}}}space", "preserve")


# --------------------------------------------------------------- traversal
def _owner_paragraph(el):
    p = el.getparent()
    while p is not None and p.tag != W_P:
        p = p.getparent()
    return p


def _paragraph_atoms(p, include_math: bool = True) -> list:
    """Text elements that belong to *p* itself (not to nested text boxes).

    Returns w:t (in w:r) and, if *include_math*, m:t (in m:r) in document order.
    """
    tags = (W_T, M_T) if include_math else (W_T,)
    atoms = []
    for t in p.iter(*tags):
        parent = t.getparent()
        if parent is None or parent.tag not in _TEXT_FOR_RUN or _TEXT_FOR_RUN[parent.tag] != t.tag:
            continue
        if _owner_paragraph(t) is p:
            atoms.append(t)
    return atoms


def _rejoin_split_syllables(atoms) -> int:
    """Move syllable continuations into the atom where the syllable starts."""
    moved = 0
    prev = None
    for t in atoms:
        text = t.text or ""
        if prev is not None and text and prev.tag == t.tag:
            ptext = prev.text or ""
            changed = False
            while text and ptext and R.is_bengali_char(ptext[-1]):
                c = text[0]
                joins_consonant = (ptext.endswith(R.HASANTA)
                                   or ptext.endswith(R.HASANTA + R.ZWJ)) and c in R.CONSONANTS
                if c in _CONTINUATION or joins_consonant:
                    ptext += c
                    text = text[1:]
                    changed = True
                else:
                    break
            if changed:
                _set_text(prev, ptext)
                _set_text(t, text)
                moved += 1
        if text:
            prev = t
    return moved


class _RunBuilder:
    """Rebuilds a mixed run as a sequence of runs with per-segment fonts."""

    def __init__(self, original, highlight: bool):
        self.orig = original
        self.rpr = original.find(W_RPR)
        self.mrpr = original.find(M_RPR)
        self.text_tag = _TEXT_FOR_RUN[original.tag]
        self.highlight = highlight
        self.runs: list = []
        self.kind: str | None = None

    def _new_run(self, kind: str):
        r = etree.Element(self.orig.tag, attrib=dict(self.orig.attrib))
        if self.mrpr is not None:
            r.append(_deepcopy(self.mrpr))
        if self.rpr is not None:
            r.append(_deepcopy(self.rpr))
        if kind == "bijoy":
            apply_bijoy_font(r, highlight=self.highlight)
        self.runs.append(r)
        self.kind = kind
        return r

    def add_element(self, el, kind: str = "orig") -> None:
        run = self.runs[-1] if self.runs and self.kind == kind else self._new_run(kind)
        run.append(el)

    def add_text(self, text: str, kind: str) -> None:
        if not text:
            return
        t = etree.Element(self.text_tag)
        _set_text(t, text)
        self.add_element(t, kind)


def _deepcopy(el):
    import copy
    return copy.deepcopy(el)


class DocxConverter:
    def __init__(self, converter: UnicodeToBijoy | None = None, highlight: bool = False,
                 convert_equations: bool = False):
        self.converter = converter or UnicodeToBijoy()
        self.highlight = highlight
        self.convert_equations = convert_equations

    # public ------------------------------------------------------------
    def convert_file(self, src: Path, dst: Path, progress: ProgressFn | None = None,
                     cancel: threading.Event | None = None) -> DocxReport:
        src, dst = Path(src), Path(dst)
        if src.suffix.lower() == ".doc":
            raise DocxError("Old Word 97-2003 (.doc) files are not supported. "
                            "Open the file in Word and save it as .docx first.")
        if not src.exists():
            raise DocxError(f"File not found: {src}")
        try:
            if src.resolve() == dst.resolve():
                raise DocxError("The output file must be different from the original document.")
        except OSError:
            pass
        doc = self._open(src)
        report = DocxReport(source=str(src), output=str(dst))
        self.convert_document(doc, report, progress, cancel)
        self._save_preserving(src, dst, self._changed_parts)
        return report

    def convert_document(self, doc, report: DocxReport, progress: ProgressFn | None = None,
                         cancel: threading.Event | None = None) -> DocxReport:
        stories = []
        for part in doc.part.package.iter_parts():
            ct = part.content_type or ""
            if "wordprocessingml" in ct and ct.endswith(STORY_TYPES):
                stories.append(part)
        self._changed_parts: dict[str, bytes] = {}
        roots = []
        for part in stories:
            root = getattr(part, "_element", None)
            generic = root is None
            if generic:
                try:
                    root = etree.fromstring(part.blob)
                except etree.XMLSyntaxError:
                    report.warnings.append(f"Skipped unreadable part {part.partname}.")
                    continue
            paragraphs = list(root.iter(W_P))
            roots.append((part, root, generic, paragraphs))
            report.paragraphs_total += len(paragraphs)

        done = 0
        for part, root, generic, paragraphs in roots:
            part_changed = False
            for p in paragraphs:
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                if self._convert_paragraph(p, report):
                    report.paragraphs_converted += 1
                    part_changed = True
                done += 1
                if progress and (done % 25 == 0 or done == report.paragraphs_total):
                    progress(done, report.paragraphs_total)
            if not self.convert_equations and self._math_has_bengali(root):
                report.warnings.append(
                    f"Equations in {part.partname} contain Bengali text; equations are left unchanged.")
            if part_changed:
                report.parts.append(str(part.partname))
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
                if generic:
                    part._blob = data
                self._changed_parts[str(part.partname).lstrip("/")] = data
        if progress:
            progress(report.paragraphs_total, report.paragraphs_total)
        return report

    # internals ---------------------------------------------------------
    @staticmethod
    def _open(src: Path):
        import docx
        from docx.opc.exceptions import PackageNotFoundError
        try:
            return docx.Document(str(src))
        except PermissionError as e:
            raise DocxError(f"Permission denied while opening '{src.name}'. "
                            "Close it in Word and try again.") from e
        except (PackageNotFoundError, zipfile.BadZipFile, KeyError, ValueError,
                etree.XMLSyntaxError) as e:
            raise DocxError(f"'{src.name}' is not a valid Word document or is damaged.") from e

    @staticmethod
    def _save(doc, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tis_", suffix=".docx", dir=str(dst.parent))
        os.close(fd)
        try:
            doc.save(tmp)
            os.replace(tmp, dst)
        except PermissionError as e:
            _silent_unlink(tmp)
            raise DocxError(f"Permission denied while saving '{dst.name}'. "
                            "The file may be open in Word.") from e
        except OSError as e:
            _silent_unlink(tmp)
            raise DocxError(f"Could not save '{dst.name}': {e.strerror or e}") from e

    @staticmethod
    def _save_preserving(src: Path, dst: Path, changed: dict[str, bytes]) -> None:
        """Write *dst* as a copy of the *src* package where only the parts in
        *changed* are replaced.  Every other part is copied byte-for-byte."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tis_", suffix=".docx", dir=str(dst.parent))
        os.close(fd)
        try:
            with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w") as zout:
                for info in zin.infolist():
                    data = changed.get(info.filename)
                    if data is None:
                        data = zin.read(info.filename)
                    zout.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
            os.replace(tmp, dst)
        except PermissionError as e:
            _silent_unlink(tmp)
            raise DocxError(f"Permission denied while saving '{dst.name}'. "
                            "The file may be open in Word.") from e
        except (OSError, zipfile.BadZipFile) as e:
            _silent_unlink(tmp)
            raise DocxError(f"Could not save '{dst.name}': {getattr(e, 'strerror', None) or e}") from e

    @staticmethod
    def _math_has_bengali(root) -> bool:
        for t in root.iter(f"{{{M_NS}}}t"):
            if t.text and contains_bengali(t.text):
                return True
        return False

    def _convert_paragraph(self, p, report: DocxReport) -> bool:
        atoms = _paragraph_atoms(p, self.convert_equations)
        if not atoms or not any(contains_bengali(t.text or "") for t in atoms):
            return False
        report.syllables_rejoined += _rejoin_split_syllables(atoms)

        results: dict[int, ConversionReport] = {}
        prev_char = ""
        for t in atoms:
            text = t.text or ""
            if text and contains_bengali(text):
                rep = self.converter.convert_with_report(text, prev_char)
                results[id(t)] = rep
                report.unmapped |= rep.unmapped
                report.characters_converted += rep.bengali_chars
            if text:
                prev_char = text[-1]

        runs: list = []
        for t in atoms:
            r = t.getparent()
            if id(t) in results and (not runs or runs[-1] is not r):
                runs.append(r)
        for r in runs:
            self._convert_run(r, results, report)
        return True

    def _convert_run(self, r, results: dict[int, ConversionReport], report: DocxReport) -> None:
        text_tag = _TEXT_FOR_RUN[r.tag]
        texts = [c for c in r if c.tag == text_tag]
        mixed = False
        for t in texts:
            rep = results.get(id(t))
            if rep is None:
                if (t.text or "").strip():
                    mixed = True     # other non-Bengali text in the same run
            elif any(seg.kind == Kind.FOREIGN for seg, _ in rep.segments):
                mixed = True
        report.runs_converted += 1
        if r.tag == M_R:
            report.equation_runs_converted += 1
        if not mixed:
            for t in texts:
                rep = results.get(id(t))
                if rep is not None:
                    _set_text(t, rep.output)
            apply_bijoy_font(r, highlight=self.highlight)
            return

        report.runs_split += 1
        builder = _RunBuilder(r, self.highlight)
        for child in list(r):
            if child.tag in (W_RPR, M_RPR):
                continue
            rep = results.get(id(child)) if child.tag == text_tag else None
            if rep is None:
                builder.add_element(child, "orig")      # moves the element (no copy)
                continue
            for seg, out in rep.segments:
                builder.add_text(out, "bijoy" if seg.kind == Kind.BENGALI else "orig")
        parent = r.getparent()
        idx = parent.index(r)
        parent.remove(r)
        for k, nr in enumerate(builder.runs):
            parent.insert(idx + k, nr)


def _silent_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def convert_docx(src: Path, dst: Path, highlight: bool = False,
                 converter: UnicodeToBijoy | None = None,
                 progress: ProgressFn | None = None,
                 cancel: threading.Event | None = None,
                 convert_equations: bool = False) -> DocxReport:
    return DocxConverter(converter, highlight, convert_equations).convert_file(
        src, dst, progress, cancel)


def extract_text(src: Path, limit: int = 2_000_000) -> str:
    """Plain text of the main document body (for previews / importing)."""
    doc = DocxConverter._open(Path(src))
    body = doc.part._element
    lines = []
    total = 0
    for p in body.iter(W_P):
        if _owner_paragraph(p) is not None:
            continue  # nested (text box) paragraph - its text is in the outer one
        line = "".join(t.text or "" for t in p.iter(W_T))
        lines.append(line)
        total += len(line)
        if total > limit:
            break
    return "\n".join(lines)
