"""Batch conversion of TXT and DOCX files."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from core.unicode_to_bijoy import UnicodeToBijoy

from .docx_service import Cancelled, DocxConverter, DocxError
from .file_naming import same_file, suggest_output_name, unique_path
from .txt_service import TextFileError, read_text_file, write_text_file

log = logging.getLogger(__name__)

SUPPORTED = {".txt", ".docx"}


@dataclass
class FileResult:
    source: Path
    output: Path | None
    ok: bool
    message: str


@dataclass
class BatchResult:
    results: list[FileResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.ok)


class BatchConverter:
    def __init__(self, converter: UnicodeToBijoy | None = None, *, highlight: bool = False,
                 txt_encoding: str = "ansi", suffix: str = "Bijoy",
                 convert_equations: bool = False, direction: str = "U2B",
                 unicode_font: str = "SolaimanLipi"):
        self.convert_equations = convert_equations
        self.direction = "B2U" if direction == "B2U" else "U2B"
        self.unicode_font = unicode_font
        if self.direction == "B2U" and suffix in (None, "", "Bijoy"):
            suffix = "Unicode"
        self.converter = converter or UnicodeToBijoy()
        self.highlight = highlight
        self.txt_encoding = txt_encoding
        self.suffix = suffix or "Bijoy"

    def output_for(self, src: Path, out_dir: Path | None) -> Path:
        """Output path; with out_dir=None the file is saved next to its original."""
        src = Path(src)
        out_dir = src.parent if out_dir is None else Path(out_dir)
        cand = out_dir / suggest_output_name(src, self.suffix)
        if same_file(cand, src):
            cand = out_dir / f"{src.stem}_{self.suffix}{src.suffix}"
        return unique_path(cand)

    def convert_one(self, src: Path, out_dir: Path | None,
                    cancel: threading.Event | None = None) -> FileResult:
        src = Path(src)
        ext = src.suffix.lower()
        if ext not in SUPPORTED:
            return FileResult(src, None, False, f"Unsupported file type '{src.suffix}'.")
        try:
            dst = self.output_for(src, out_dir)
            if ext == ".txt" and self.direction == "B2U":
                tf = read_text_file(src)
                from core.bijoy_to_unicode import bijoy_to_unicode
                out = bijoy_to_unicode(tf.text)
                used = write_text_file(dst, out, "utf-8")
                msg = f"{len(tf.text):,} characters converted to Unicode ({used})."
            elif ext == ".docx" and self.direction == "B2U":
                from .docx_b2u import BijoyToUnicodeDocxConverter
                rep = BijoyToUnicodeDocxConverter(self.unicode_font, self.highlight).convert_file(
                    src, dst, cancel=cancel)
                msg = f"{rep.paragraphs_converted} paragraphs, {rep.runs_converted} Bijoy runs converted."
                if rep.runs_converted == 0:
                    msg += " (No SutonnyMJ/Bijoy text found.)"
            elif ext == ".txt":
                tf = read_text_file(src)
                rep = self.converter.convert_with_report(tf.text)
                used = write_text_file(dst, rep.output, self.txt_encoding)
                msg = f"{rep.bengali_chars:,} Bengali characters converted ({used})."
                if rep.unmapped:
                    msg += " Unchanged: " + " ".join(sorted(rep.unmapped))
            else:
                rep = DocxConverter(self.converter, self.highlight,
                                    self.convert_equations).convert_file(src, dst, cancel=cancel)
                msg = (f"{rep.paragraphs_converted} paragraphs, {rep.runs_converted} runs converted.")
                if rep.warnings:
                    msg += " " + " ".join(rep.warnings)
            return FileResult(src, dst, True, msg)
        except Cancelled:
            raise
        except (TextFileError, DocxError) as e:
            return FileResult(src, None, False, str(e))
        except Exception as e:  # never let one bad file stop the batch
            log.exception("Batch conversion failed for %s", src)
            return FileResult(src, None, False, f"Unexpected error: {e}")

    def run(self, files: list[Path], out_dir: Path | None,
            progress: Callable[[int, int, Path], None] | None = None,
            on_result: Callable[[FileResult], None] | None = None,
            cancel: threading.Event | None = None) -> BatchResult:
        out_dir = None if out_dir is None else Path(out_dir)
        result = BatchResult()
        total = len(files)
        for i, f in enumerate(files):
            if cancel is not None and cancel.is_set():
                result.cancelled = True
                break
            if progress:
                progress(i, total, Path(f))
            try:
                fr = self.convert_one(Path(f), out_dir, cancel)
            except Cancelled:
                result.cancelled = True
                break
            result.results.append(fr)
            if on_result:
                on_result(fr)
        if progress and not result.cancelled:
            progress(total, total, Path(files[-1]) if files else Path())
        return result
