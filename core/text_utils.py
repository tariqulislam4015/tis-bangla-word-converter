"""Text classification, segmentation and statistics helpers."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import conversion_rules as R

# Bengali characters the engine knows how to convert.
_MAPPABLE_BENGALI = frozenset(
    list(R.CONSONANTS)
    + list(R.INDEPENDENT_VOWELS)
    + list(R.DIGITS)
    + list(R.SIGNS)
    + list(R.VOWEL_SIGNS - {"ৄ"})
    + [R.NUKTA]
)


class Kind(str, Enum):
    BENGALI = "bengali"
    FOREIGN = "foreign"
    NEUTRAL = "neutral"


@dataclass
class Segment:
    kind: Kind
    text: str


def char_kind(ch: str) -> Kind:
    if ch in _MAPPABLE_BENGALI:
        return Kind.BENGALI
    if ch in R.SUTONNY_SAFE_ASCII or ch in R.NEUTRAL_MAP or ch in (R.ZWJ, R.ZWNJ):
        return Kind.NEUTRAL
    return Kind.FOREIGN


def contains_bengali(text: str) -> bool:
    """True if *text* contains at least one convertible Bengali character."""
    return any(ch in _MAPPABLE_BENGALI for ch in text)


def unmappable_bengali(text: str) -> set[str]:
    """Bengali-block characters that the engine leaves untouched."""
    return {ch for ch in text if R.is_bengali_char(ch) and ch not in _MAPPABLE_BENGALI}


def segment(text: str) -> list[Segment]:
    """Split text into Bengali / foreign runs.

    Neutral characters (spaces, common punctuation, quotes) join the segment
    before them; leading neutrals join the first real segment.  A string made
    only of neutral characters yields a single NEUTRAL segment.
    """
    if not text:
        return []
    raw: list[Segment] = []
    for ch in text:
        k = char_kind(ch)
        if raw and raw[-1].kind == k:
            raw[-1].text += ch
        else:
            raw.append(Segment(k, ch))

    out: list[Segment] = []
    pending_neutral = ""
    for seg in raw:
        if seg.kind == Kind.NEUTRAL:
            if out:
                out[-1].text += seg.text
            else:
                pending_neutral += seg.text
            continue
        text_ = pending_neutral + seg.text
        pending_neutral = ""
        if out and out[-1].kind == seg.kind:
            out[-1].text += text_
        else:
            out.append(Segment(seg.kind, text_))
    if pending_neutral:
        out.append(Segment(Kind.NEUTRAL, pending_neutral))
    return out


@dataclass
class TextStats:
    characters: int
    words: int
    lines: int


def text_stats(text: str) -> TextStats:
    if not text:
        return TextStats(0, 0, 0)
    chars = len(text) - text.count("\n") - text.count("\r")
    return TextStats(chars, len(text.split()), text.count("\n") + 1)
