"""Unicode Bengali -> Bijoy (SutonnyMJ ANSI) conversion engine.

Design
------
The input is first split into Bengali and non-Bengali segments
(:func:`core.text_utils.segment`).  Only Bengali segments are converted; English
words, ASCII digits, symbols and maths are passed through untouched.

Each Bengali segment is parsed left-to-right, once, into *syllable clusters*::

    [reph] consonant (hasanta consonant)* [hasanta] vowel-sign* [chandrabindu]

and every cluster is rendered in Bijoy visual order::

    pre-kar  body-glyphs  [u-kar placed before ya-phala]  reph  post-kar  ঁ

Body glyphs come from a greedy longest-match over the conjunct table, then
phala forms, then an explicit-hasanta fallback (so nothing is ever dropped).
Glyph variants (u-kar, uu-kar, ri-kar, r-phala, word-initial e/oi-kar) are
selected from the neighbouring glyph while rendering instead of being patched
afterwards with string replacements.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import conversion_rules as R
from .correction_rules import CorrectionSet, normalize_unicode
from .text_utils import Kind, Segment, segment, unmappable_bengali


@dataclass
class ConversionReport:
    output: str
    segments: list[tuple[Segment, str]] = field(default_factory=list)
    clusters: int = 0
    bengali_chars: int = 0
    unmapped: set[str] = field(default_factory=set)
    fallback_conjuncts: set[str] = field(default_factory=set)

    @property
    def changed(self) -> bool:
        return any(s.kind == Kind.BENGALI for s, _ in self.segments)


class UnicodeToBijoy:
    """Stateless converter (safe to share between threads)."""

    def __init__(self, corrections: CorrectionSet | None = None):
        self.corrections = corrections or CorrectionSet()

    # ------------------------------------------------------------------ API
    def convert(self, text: str, prev_char: str = "") -> str:
        return self.convert_with_report(text, prev_char).output

    def convert_with_report(self, text: str, prev_char: str = "") -> ConversionReport:
        report = ConversionReport(output="")
        if not text:
            return report
        parts: list[str] = []
        prev = prev_char
        for seg in segment(text):
            if seg.kind == Kind.BENGALI:
                out = self._convert_bengali(seg.text, prev, report)
                report.bengali_chars += len(seg.text)
            else:
                out = seg.text
                report.unmapped |= unmappable_bengali(seg.text)
            report.segments.append((seg, out))
            parts.append(out)
            prev = seg.text[-1]
        report.output = "".join(parts)
        return report

    def convert_bengali_segment(self, text: str, prev_char: str = "") -> str:
        """Convert text already known to be a Bengali segment."""
        return self._convert_bengali(text, prev_char, ConversionReport(output=""))

    # ------------------------------------------------------------ internals
    @staticmethod
    def _is_letter_context(ch: str) -> bool:
        """Whether *ch* continues a word (affects word-initial e-kar form)."""
        ch = ch[-1:]
        if not ch:
            return False
        return R.is_bengali_char(ch) and ch not in ("।", "॥")

    def _convert_bengali(self, text: str, prev_char: str, report: ConversionReport) -> str:
        s = normalize_unicode(text)
        n = len(s)
        out: list[str] = []
        i = 0
        in_word = self._is_letter_context(prev_char)
        while i < n:
            ch = s[i]
            if ch in R.CONSONANTS or (
                ch in R.FOLA_CAPABLE_VOWELS and s.startswith(R.HASANTA + R.YA, i + 1)
            ):
                i, glyphs = self._cluster(s, i, in_word, report)
                out.append(glyphs)
                report.clusters += 1
                in_word = True
            elif ch in R.INDEPENDENT_VOWELS:
                out.append(R.INDEPENDENT_VOWELS[ch])
                i += 1
                in_word = True
            elif ch in R.VOWEL_SIGNS:
                # orphan vowel sign (no base consonant) - keep it visible
                out.append(self._orphan_kar(ch, in_word))
                i += 1
                in_word = True
            elif ch in (R.ZWJ, R.ZWNJ, R.NUKTA):
                i += 1
            elif ch in R.DIGITS:
                out.append(R.DIGITS[ch])
                i += 1
                in_word = True
            elif ch in R.SIGNS:
                out.append(R.SIGNS[ch])
                i += 1
                in_word = ch not in ("।", "॥")
            elif ch in R.NEUTRAL_MAP:
                out.append(R.NEUTRAL_MAP[ch])
                i += 1
                in_word = False
            else:
                if R.is_bengali_char(ch):
                    report.unmapped.add(ch)
                out.append(ch)
                i += 1
                in_word = False
        return self.corrections.apply("".join(out))

    @staticmethod
    def _orphan_kar(ch: str, in_word: bool) -> str:
        if ch in R.PRE_KAR_FORMS:
            return R.PRE_KAR_FORMS[ch][1 if in_word else 0]
        if ch in R.SIMPLE_POST_KARS:
            return R.SIMPLE_POST_KARS[ch]
        return {
            R.U_KAR: R.U_KAR_DEFAULT, R.UU_KAR: R.UU_KAR_DEFAULT,
            R.RI_KAR: R.RI_KAR_DEFAULT, R.O_KAR: "‡v", R.OU_KAR: "‡Š",
        }.get(ch, ch)

    def _cluster(self, s: str, i: int, in_word: bool, report: ConversionReport):
        n = len(s)
        H = R.HASANTA
        reph = False
        # Reph: র + ্ + consonant, but not র‍্য (ra + ZWJ + hasanta + ya).
        if (s[i] == R.RA and i + 2 < n and s[i + 1] == H
                and s[i + 2] in R.CONSONANTS):
            reph = True
            i += 2

        cons = s[i]
        i += 1
        explicit_hasanta = False
        while i < n:
            if s[i] == H and i + 1 < n and s[i + 1] in R.CONSONANTS:
                cons += H + s[i + 1]
                i += 2
            elif s[i] == H and i + 2 < n and s[i + 1] == R.ZWJ and s[i + 2] in R.CONSONANTS:
                cons += H + s[i + 2]          # hasanta + ZWJ + consonant
                i += 3
            elif (s[i] == R.ZWJ and cons.endswith(R.RA) and i + 2 < n
                  and s[i + 1] == H and s[i + 2] == R.YA):
                cons += "\x00RA_YA"           # র‍্য marker: র + ya-phala, no reph
                i += 3
            elif s[i] == H:
                explicit_hasanta = True
                i += 1
                while i < n and s[i] in (R.ZWNJ, R.ZWJ):
                    i += 1
                break
            elif s[i] == R.NUKTA:
                i += 1
            else:
                break

        vowels: list[str] = []
        chandra = 0
        while i < n:
            c = s[i]
            if c in R.VOWEL_SIGNS and not explicit_hasanta:
                vowels.append(c)
                i += 1
            elif c == R.CHANDRABINDU:
                chandra += 1
                i += 1
            else:
                break

        body = self._render_body(cons, report)
        if explicit_hasanta:
            body.append("&")
        if reph:
            # Reph follows the consonant body - before a trailing ya-phala
            # (ˆ`N©¨, mvg_©¨) - and precedes every vowel sign (KZ©„K, Kvh©vjq).
            # Placing it in the body makes below-kars after it take their
            # default glyph form.
            if len(body) >= 2 and body[-1] == R.YA_PHALA:
                body.insert(len(body) - 1, R.REPH)
            else:
                body.append(R.REPH)

        pre: list[str] = []
        post: list[str] = []
        for v in vowels:
            if v in R.PRE_KAR_FORMS:
                pre.append(R.PRE_KAR_FORMS[v][1 if in_word else 0])
            elif v == R.O_KAR:
                pre.append(R.PRE_KAR_FORMS[R.E_KAR][1 if in_word else 0])
                post.append("v")
            elif v == R.OU_KAR:
                pre.append(R.PRE_KAR_FORMS[R.E_KAR][1 if in_word else 0])
                post.append("Š")
            elif v in R.SIMPLE_POST_KARS:
                post.append(R.SIMPLE_POST_KARS[v])
            elif v in (R.U_KAR, R.UU_KAR, R.RI_KAR):
                self._attach_below_kar(body, v)
            else:  # ৄ and other rare signs: keep as-is
                report.unmapped.add(v)
                post.append(v)

        return i, "".join(pre) + "".join(body) + "".join(post) + "u" * chandra

    def _render_body(self, cons: str, report: ConversionReport) -> list[str]:
        """Render a consonant sequence (joined by hasanta) to glyph tokens."""
        H = R.HASANTA
        tokens: list[str] = []
        ra_ya = cons.endswith("\x00RA_YA")
        if ra_ya:
            cons = cons[: -len("\x00RA_YA")]
        j = 0
        L = len(cons)
        while j < L:
            ch = cons[j]
            if ch == H:
                nxt = cons[j + 1]
                prev_last = tokens[-1][-1] if tokens else ""
                if nxt == R.RA:
                    tokens.append(R.R_PHALA_BY_PREV.get(prev_last, R.R_PHALA_DEFAULT))
                    j += 2
                    continue
                if nxt == R.YA:
                    tokens.append(R.YA_PHALA)
                    j += 2
                    continue
                if nxt in R.GENERIC_SUBSCRIPT:
                    tokens.append(R.GENERIC_SUBSCRIPT[nxt])
                    j += 2
                    continue
                # No ligature known: show an explicit hasanta, keep going.
                report.fallback_conjuncts.add(cons)
                tokens.append("&")
                j += 1
                continue
            # longest conjunct starting here
            matched = False
            for size in range(min(R.MAX_CONJUNCT_LEN, L - j), 2, -1):
                key = cons[j:j + size]
                if key in R.CONJUNCTS:
                    tokens.append(R.CONJUNCTS[key])
                    j += size
                    matched = True
                    break
            if not matched:
                tokens.append(R.CONSONANTS.get(ch) or R.INDEPENDENT_VOWELS[ch])
                j += 1
        if ra_ya:
            tokens.append(R.YA_PHALA)
        return tokens

    @staticmethod
    def _attach_below_kar(body: list[str], kar: str) -> None:
        """Attach u/uu/ri-kar, choosing the glyph variant from its neighbour.

        In Bijoy order these signs come before a trailing ya-phala (ত্যু -> Zz¨).
        """
        idx = len(body)
        if idx >= 2 and body[-1] == R.YA_PHALA:
            idx -= 1
        if idx == 0:
            body.append({R.U_KAR: R.U_KAR_DEFAULT, R.UU_KAR: R.UU_KAR_DEFAULT}.get(kar, R.RI_KAR_DEFAULT))
            return
        base = body[idx - 1]
        lig = R.KAR_LIGATURES.get((base, kar))
        if lig is not None and idx == len(body):
            body[idx - 1] = lig
            return
        last = base[-1]
        if kar == R.U_KAR:
            g = R.U_KAR_RA if last in R.RA_FOOT else (
                R.U_KAR_NARROW if last in R.NARROW_FOOT else R.U_KAR_DEFAULT)
        elif kar == R.UU_KAR:
            g = R.UU_KAR_RA if last in R.RA_FOOT else (
                R.UU_KAR_NARROW if last in R.NARROW_FOOT else R.UU_KAR_DEFAULT)
        else:
            g = R.RI_KAR_NARROW if last in R.NARROW_FOOT_RI else R.RI_KAR_DEFAULT
        body.insert(idx, g)


_default = UnicodeToBijoy()


def unicode_to_bijoy(text: str, prev_char: str = "") -> str:
    """Convenience wrapper using the default converter."""
    return _default.convert(text, prev_char)
