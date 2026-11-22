"""Bijoy (SutonnyMJ ANSI) -> Unicode Bengali decoder.

Used for the "Bijoy -> Unicode" text direction and for round-trip tests of
the forward engine.  Bijoy text has no way to mark English words (every ASCII
letter is a Bengali glyph in SutonnyMJ), so the whole input is decoded.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import conversion_rules as R

H = R.HASANTA

# token kinds
CONS = "cons"          # starts a cluster; may end with hasanta (half form)
CONS_DONE = "done"     # consonant + vowel ligature (গু, শু ...) - closes a cluster
FOLA = "fola"          # subjoined form, starts with hasanta
PRE = "pre"            # pre-base vowel sign
POST = "post"          # post-base vowel sign
BELOW = "below"        # u / uu / ri kar (may precede ya-phala)
REPH = "reph"
OTHER = "other"


@dataclass(frozen=True)
class Tok:
    kind: str
    text: str


def _build_table() -> dict[str, Tok]:
    t: dict[str, Tok] = {}

    def add(glyph: str, kind: str, uni: str) -> None:
        t.setdefault(glyph, Tok(kind, uni))

    for uni, g in R.CONJUNCTS.items():
        add(g, CONS, uni)
    for (base, kar), g in R.KAR_LIGATURES.items():
        base_uni = next((u for u, gg in {**R.CONSONANTS, **R.CONJUNCTS}.items() if gg == base), None)
        if base_uni:
            add(g, CONS_DONE, base_uni + kar)
    for uni, g in R.CONSONANTS.items():
        add(g, CONS, uni)
    add("r", OTHER, R.KHANDA_TA)
    for uni, g in R.INDEPENDENT_VOWELS.items():
        add(g, CONS if uni in R.FOLA_CAPABLE_VOWELS else OTHER, uni)
    # half forms (consonant + hasanta)
    for g, uni in {"¯": "স", "¤": "ম", "®": "ষ", "š": "ন", "›": "ন",
                   "˜": "দ", "™": "দ", "”": "চ", "•": "ঙ"}.items():
        add(g, CONS, uni + H)
    # extra ANSI variants of existing letters
    for g, uni in {"¹": "জ্ঞ", "ÿ": "ক্ষ", "Ê": "ণ্ড"}.items():
        add(g, CONS, uni)
    # phala / subjoined forms
    folas = {
        "Ö": "্র", "ª": "্র", "«": "্র", "¨": "্য",
        "¦": "্ব", "¡": "্ব", "Ÿ": "্ব", "^": "্ব",
        "œ": "্ন", "è": "্ণ", "¥": "্ম", "§": "্ম",
        "ø": "্ল", "¬": "্ল", "­": "্ল",
        "‹": "্ক", "Œ": "্ক্র", "Í": "্ত", "’": "্থ", "ú": "্প",
        "¢": "্ভ", "£": "্ভ্র", "¿": "্ত্র", "‘": "্তু",
    }
    for g, uni in folas.items():
        add(g, FOLA, uni)
    add("w", PRE, R.I_KAR)
    add("†", PRE, R.E_KAR)
    add("‡", PRE, R.E_KAR)
    add("ˆ", PRE, R.OI_KAR)
    add("‰", PRE, R.OI_KAR)
    add("v", POST, R.AA_KAR)
    add("x", POST, R.II_KAR)
    add("Š", POST, R.AU_LENGTH)
    for g in ("y", "z", "“", "–", "æ"):
        add(g, BELOW, R.U_KAR)
    for g in ("~", "‚", "ƒ"):
        add(g, BELOW, R.UU_KAR)
    for g in ("„", "…"):
        add(g, BELOW, R.RI_KAR)
    add("©", REPH, "")
    add("s", OTHER, R.ANUSVARA)
    add("t", OTHER, R.VISARGA)
    add("u", OTHER, R.CHANDRABINDU)
    add("&", OTHER, H)
    add("||", OTHER, "॥")
    add("|", OTHER, "।")
    for uni, g in R.DIGITS.items():
        add(g, OTHER, uni)
    for g, uni in {"Ô": "‘", "Õ": "’", "Ò": "“", "Ó": "”", "Ñ": "—"}.items():
        add(g, OTHER, uni)
    return t


_TABLE = _build_table()
_MAXLEN = max(len(k) for k in _TABLE)


def _tokenize(s: str) -> list[Tok]:
    toks: list[Tok] = []
    i, n = 0, len(s)
    while i < n:
        for size in range(min(_MAXLEN, n - i), 0, -1):
            tok = _TABLE.get(s[i:i + size])
            if tok is not None:
                toks.append(tok)
                i += size
                break
        else:
            toks.append(Tok(OTHER, s[i]))
            i += 1
    return toks


def bijoy_to_unicode(text: str) -> str:
    toks = _tokenize(text)
    out: list[str] = []
    pending_pre: list[str] = []
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t.kind == PRE:
            pending_pre.append(t.text)
            i += 1
            continue
        if t.kind in (CONS, CONS_DONE):
            cluster = t.text
            deferred: list[str] = []
            j = i + 1
            closed = t.kind == CONS_DONE
            while j < n and not closed:
                u = toks[j]
                if u.kind == FOLA:
                    cluster += u.text
                    j += 1
                elif u.kind in (CONS, CONS_DONE) and cluster.endswith(H):
                    cluster += u.text
                    closed = u.kind == CONS_DONE
                    j += 1
                elif (u.kind == OTHER and u.text == H and j + 1 < n
                      and toks[j + 1].kind in (CONS, CONS_DONE)):
                    cluster += H  # visible hasanta used as conjunct fallback
                    j += 1
                elif (u.kind == BELOW and j + 1 < n and toks[j + 1].kind == FOLA
                      and toks[j + 1].text == "্য"):
                    deferred.append(u.text)    # ত z ¨  -> ত্যু
                    cluster += "্য"
                    j += 2
                else:
                    break
            if cluster == R.RA + "্য":
                cluster = R.RA + R.ZWJ + "্য"   # i¨ is র‍্য, never a reph
            if j < n and toks[j].kind == REPH:
                cluster = R.RA + H + cluster
                j += 1
            elif (j + 1 < n and toks[j].kind == BELOW and toks[j + 1].kind == REPH):
                # some typists put the reph after a below-base kar (KZ„©K)
                cluster = R.RA + H + cluster
                deferred.append(toks[j].text)
                j += 2
            if cluster.startswith(R.RA + H):
                # phala written after the reph (ˆ`N©¨ -> দৈর্ঘ্য)
                while j < n and toks[j].kind == FOLA:
                    cluster += toks[j].text
                    j += 1
            out.append(cluster)
            for p in pending_pre:
                if p == R.E_KAR and j < n and toks[j].kind == POST and toks[j].text == R.AA_KAR:
                    out.append(R.O_KAR)
                    j += 1
                elif p == R.E_KAR and j < n and toks[j].kind == POST and toks[j].text == R.AU_LENGTH:
                    out.append(R.OU_KAR)
                    j += 1
                else:
                    out.append(p)
            pending_pre = []
            out.extend(deferred)
            i = j
            continue
        # anything else: flush orphan pre-kars first
        if pending_pre:
            out.extend(pending_pre)
            pending_pre = []
        if t.kind != REPH:
            out.append(t.text)
        i += 1
    out.extend(pending_pre)
    return "".join(out)
