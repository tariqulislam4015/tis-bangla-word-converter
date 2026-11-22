"""Export converted text to a new Word document with correct fonts."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from config.settings import BIJOY_FONT
from core.text_utils import Kind
from core.unicode_to_bijoy import ConversionReport

from .docx_service import DocxError, apply_bijoy_font


def export_docx(path: Path, pieces: list[tuple[str, str | None]], font_size_pt: int = 12) -> None:
    """Write *pieces* ``[(text, font_or_None), ...]`` to a new .docx.

    Newlines start new paragraphs.  ``font`` "SutonnyMJ" gets all three font
    slots (ascii / hAnsi / cs) set; other fonts are set on the run normally.
    """
    import docx
    from docx.shared import Pt

    doc = docx.Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(font_size_pt)
    para = doc.add_paragraph()
    for text, font in pieces:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        for k, line in enumerate(lines):
            if k > 0:
                para = doc.add_paragraph()
            if not line:
                continue
            run = para.add_run(line)
            if font == BIJOY_FONT:
                apply_bijoy_font(run._element)
            elif font:
                run.font.name = font
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tis_", suffix=".docx", dir=str(path.parent))
        os.close(fd)
        try:
            doc.save(tmp)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except PermissionError as e:
        raise DocxError(f"Permission denied while saving '{path.name}'. "
                        "The file may be open in Word.") from e
    except OSError as e:
        raise DocxError(f"Could not save '{path.name}': {e.strerror or e}") from e


def pieces_from_report(report: ConversionReport) -> list[tuple[str, str | None]]:
    return [(out, BIJOY_FONT if seg.kind == Kind.BENGALI else None)
            for seg, out in report.segments]
