"""Reading and writing plain-text files."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


class TextFileError(Exception):
    """User-presentable error about a text file."""


MAX_TXT_BYTES = 200 * 1024 * 1024


@dataclass
class TextFile:
    text: str
    encoding: str


def read_text_file(path: Path) -> TextFile:
    path = Path(path)
    try:
        size = path.stat().st_size
        if size > MAX_TXT_BYTES:
            raise TextFileError(f"'{path.name}' is too large ({size // (1024*1024)} MB).")
        raw = path.read_bytes()
    except PermissionError as e:
        raise TextFileError(f"Permission denied while reading '{path.name}'.") from e
    except FileNotFoundError as e:
        raise TextFileError(f"File not found: {path}") from e
    except OSError as e:
        raise TextFileError(f"Could not read '{path.name}': {e.strerror or e}") from e

    if raw.startswith(b"\xef\xbb\xbf"):
        return TextFile(raw[3:].decode("utf-8", errors="replace"), "utf-8-sig")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return TextFile(raw.decode("utf-16"), "utf-16")
    try:
        return TextFile(raw.decode("utf-8"), "utf-8")
    except UnicodeDecodeError:
        pass
    # Not UTF-8: most likely ANSI (e.g. existing Bijoy text).  cp1252 maps
    # every byte except five, which are kept with replacement markers.
    return TextFile(raw.decode("cp1252", errors="replace"), "cp1252")


def write_text_file(path: Path, text: str, encoding: str = "utf-8") -> str:
    """Write atomically.  Returns the encoding actually used.

    ``encoding="ansi"`` writes Windows-1252 bytes (genuine Bijoy ANSI).  If
    the text contains characters outside Windows-1252 (e.g. untouched
    non-Bengali symbols) it falls back to UTF-8 with BOM so nothing is lost.
    """
    path = Path(path)
    used = encoding
    if encoding == "ansi":
        try:
            data = text.encode("cp1252")
            used = "cp1252"
        except UnicodeEncodeError:
            data = text.encode("utf-8-sig")
            used = "utf-8-sig"
    else:
        data = text.encode("utf-8")
        used = "utf-8"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tis_", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except PermissionError as e:
        raise TextFileError(f"Permission denied while saving '{path.name}'. "
                            "The file may be open in another program.") from e
    except OSError as e:
        raise TextFileError(f"Could not save '{path.name}': {e.strerror or e}") from e
    return used
