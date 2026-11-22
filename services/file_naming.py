"""Output file naming that never overwrites user files."""
from __future__ import annotations

import re
from pathlib import Path

# "Unicode" or "Bijoy" in a file name is replaced by the target tag.
_UNICODE_TAG = re.compile(r"(?i)(?<![A-Za-z])(unicode|bijoy)(?![A-Za-z])")


def suggest_output_name(src: Path, suffix: str = "Bijoy", ext: str | None = None) -> str:
    """Class_8_Bangla_Unicode.docx -> Class_8_Bangla_Bijoy.docx; a.docx -> a_Bijoy.docx.

    Works both ways: Exam_Bijoy.docx with suffix "Unicode" -> Exam_Unicode.docx.
    """
    src = Path(src)
    stem = src.stem
    ext = ext or src.suffix
    if _UNICODE_TAG.search(stem):
        new = _UNICODE_TAG.sub(suffix, stem)
    else:
        new = f"{stem}_{suffix}"
    return new + ext


def unique_path(path: Path) -> Path:
    """Return *path*, or 'name (2).ext', 'name (3).ext' ... if it exists."""
    path = Path(path)
    if not path.exists():
        return path
    i = 2
    while True:
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def same_file(a: Path, b: Path) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return str(a) == str(b)
