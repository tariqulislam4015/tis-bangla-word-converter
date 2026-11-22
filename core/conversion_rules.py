"""Character tables for Unicode Bengali <-> Bijoy (SutonnyMJ) conversion.

Bijoy text is "ANSI" text: each byte (0x20-0xFF) selects a glyph in the
SutonnyMJ font.  In Word documents and in Python strings, such text is stored
as the Unicode characters obtained by decoding those bytes with Windows-1252
(e.g. byte 0x87 -> U+2021 '‡').  All Bijoy strings below use that convention.

Provenance: these tables were written independently from knowledge of the
SutonnyMJ glyph layout (a factual property of the font encoding).  No code or
table text was copied from the reference project; see
docs/REPOSITORY_ANALYSIS.md.
"""
from __future__ import annotations

HASANTA = "্"
NUKTA = "়"
ZWJ = "‍"
ZWNJ = "‌"
CHANDRABINDU = "ঁ"
ANUSVARA = "ং"
VISARGA = "ঃ"
KHANDA_TA = "ৎ"
RA = "র"
YA = "য"
BA = "ব"

# --------------------------------------------------------------------------
# Base consonants
# --------------------------------------------------------------------------
CONSONANTS: dict[str, str] = {
    "ক": "K", "খ": "L", "গ": "M", "ঘ": "N", "ঙ": "O",
    "চ": "P", "ছ": "Q", "জ": "R", "ঝ": "S", "ঞ": "T",
    "ট": "U", "ঠ": "V", "ড": "W", "ঢ": "X", "ণ": "Y",
    "ত": "Z", "থ": "_", "দ": "`", "ধ": "a", "ন": "b",
    "প": "c", "ফ": "d", "ব": "e", "ভ": "f", "ম": "g",
    "য": "h", "র": "i", "ল": "j", "শ": "k", "ষ": "l",
    "স": "m", "হ": "n", "\u09DC": "o", "\u09DD": "p", "\u09DF": "q",  # RRA RHA YYA
}

INDEPENDENT_VOWELS: dict[str, str] = {
    "অ": "A", "আ": "Av", "ই": "B", "ঈ": "C", "উ": "D", "ঊ": "E",
    "ঋ": "F", "এ": "G", "ঐ": "H", "ও": "I", "ঔ": "J",
}

# Independent vowels that may carry a ya-phala (অ্যা, এ্যা).
FOLA_CAPABLE_VOWELS = frozenset("অএ")

DIGITS: dict[str, str] = {chr(0x09E6 + i): str(i) for i in range(10)}

# Stand-alone signs and Bengali punctuation.
SIGNS: dict[str, str] = {
    ANUSVARA: "s",
    VISARGA: "t",
    CHANDRABINDU: "u",
    KHANDA_TA: "r",
    "।": "|",   # ।  dari
    "॥": "||",  # ॥  double dari
    HASANTA: "&",    # visible hasanta
}

# Non-Bengali characters that need a SutonnyMJ equivalent when they appear
# inside Bengali text (their cp1252 byte would otherwise show a Bengali glyph).
NEUTRAL_MAP: dict[str, str] = {
    "‘": "Ô",   # ‘
    "’": "Õ",   # ’
    "“": "Ò",   # “
    "”": "Ó",   # ”
    "—": "Ñ",   # — em dash
    "–": "-",   # – en dash -> hyphen
    "…": "...",  # … ellipsis (0x85 is a ri-kar glyph in SutonnyMJ)
    " ": " ",   # no-break space
}

# --------------------------------------------------------------------------
# Vowel signs (kar)
# --------------------------------------------------------------------------
AA_KAR = "া"
I_KAR = "ি"
II_KAR = "ী"
U_KAR = "ু"
UU_KAR = "ূ"
RI_KAR = "ৃ"
E_KAR = "ে"
OI_KAR = "ৈ"
O_KAR = "\u09CB"
OU_KAR = "\u09CC"
AU_LENGTH = "ৗ"

VOWEL_SIGNS = frozenset(
    [AA_KAR, I_KAR, II_KAR, U_KAR, UU_KAR, RI_KAR, "ৄ",
     E_KAR, OI_KAR, O_KAR, OU_KAR, AU_LENGTH]
)

# pre-base forms: (word-initial glyph, medial glyph)
PRE_KAR_FORMS: dict[str, tuple[str, str]] = {
    I_KAR: ("w", "w"),
    E_KAR: ("†", "‡"),
    OI_KAR: ("ˆ", "‰"),
}

SIMPLE_POST_KARS: dict[str, str] = {
    AA_KAR: "v",
    II_KAR: "x",
    AU_LENGTH: "Š",
}

# Glyph variants for the "below" vowel signs, chosen by the preceding glyph.
U_KAR_DEFAULT = "y"
U_KAR_NARROW = "z"     # consonants whose foot curls right (কু তু ...)
U_KAR_RA = "æ"         # after র / r-fola  (রু, প্রু)
UU_KAR_DEFAULT = "~"
UU_KAR_NARROW = "‚"
UU_KAR_RA = "ƒ"
RI_KAR_DEFAULT = "„"
RI_KAR_NARROW = "…"

# Glyphs (last character of a rendered consonant token) that take the
# narrow u-kar / uu-kar / ri-kar forms.
NARROW_FOOT = frozenset("KPQSUVWXZdf¼Ü")
NARROW_FOOT_RI = NARROW_FOOT | frozenset("‹")
# Glyphs that already contain an r-fola, or are র itself.
RA_FOOT = frozenset("iÖª«µÎå¿Œ£")

# Combined consonant + vowel-sign ligatures.  Key: (rendered token, kar).
KAR_LIGATURES: dict[tuple[str, str], str] = {
    ("M", U_KAR): "¸",     # গু
    ("k", U_KAR): "ï",     # শু
    ("n", U_KAR): "û",     # হু
    ("n", RI_KAR): "ü",    # হৃ
    ("šÍ", U_KAR): "š‘",   # ন্তু
    ("¯Í", U_KAR): "¯‘",   # স্তু
    ("¶", U_KAR): "ÿz",    # ক্ষু
    ("o", U_KAR): "o–",    # ড়-u
}

REPH = "©"

# --------------------------------------------------------------------------
# Phala (subjoined) forms used when no ligature exists
# --------------------------------------------------------------------------
YA_PHALA = "¨"
R_PHALA_DEFAULT = "Ö"
R_PHALA_NARROW = "ª"
R_PHALA_WIDE = "«"
# preceding glyph (last char of the previous token) -> r-phala variant
R_PHALA_BY_PREV: dict[str, str] = {
    **{g: R_PHALA_NARROW for g in "`UVWXNaó÷"},
    "d": R_PHALA_WIDE,
    "n": R_PHALA_WIDE,
}
GENERIC_SUBSCRIPT: dict[str, str] = {
    "ব": "¦",
    "ন": "œ",
    "ম": "¥",
    "ল": "ø",
}

# --------------------------------------------------------------------------
# Conjunct ligatures (keys are Unicode sequences joined with hasanta)
# --------------------------------------------------------------------------
_H = HASANTA


def _k(*parts: str) -> str:
    return _H.join(parts)


CONJUNCTS: dict[str, str] = {
    # ক
    _k("ক", "ক"): "°", _k("ক", "ট"): "±", _k("ক", "ত"): "³",
    _k("ক", "ম"): "´", _k("ক", "র"): "µ", _k("ক", "ষ"): "¶",
    _k("ক", "স"): "·", _k("ক", "ল"): "K¬", _k("ক", "ব"): "K¡",
    _k("ক", "ষ", "ম"): "²", _k("ক", "ষ", "ণ"): "¶è",
    # গ
    _k("গ", "দ"): "º", _k("গ", "ধ"): "»", _k("গ", "ন"): "Mœ",
    _k("গ", "ম"): "M¥", _k("গ", "ল"): "Mø",
    # ঙ
    _k("ঙ", "ক"): "¼", _k("ঙ", "গ"): "½", _k("ঙ", "খ"): "•L",
    _k("ঙ", "ঘ"): "•N", _k("ঙ", "ক", "ষ"): "•¶", _k("ঙ", "ম"): "•g",
    # চ
    _k("চ", "চ"): "”P", _k("চ", "ছ"): "”Q", _k("চ", "ঞ"): "”T",
    _k("চ", "ছ", "ব"): "”Q¡",
    # জ
    _k("জ", "জ"): "¾", _k("জ", "ঝ"): "À", _k("জ", "ঞ"): "Á",
    _k("জ", "ব"): "R¡", _k("জ", "জ", "ব"): "¾¡",
    # ঞ
    _k("ঞ", "চ"): "Â", _k("ঞ", "ছ"): "Ã", _k("ঞ", "জ"): "Ä",
    _k("ঞ", "ঝ"): "Å",
    # ট ড ণ
    _k("ট", "ট"): "Æ", _k("ট", "ব"): "U¡", _k("ট", "ম"): "U¥",
    _k("ড", "ড"): "Ç",
    _k("ণ", "ট"): "È", _k("ণ", "ঠ"): "É", _k("ণ", "ড"): "Ð",
    _k("ণ", "ব"): "Y¦", _k("ণ", "ণ"): "Yœ",
    # ত থ
    _k("ত", "ত"): "Ë", _k("ত", "থ"): "Ì", _k("ত", "ন"): "Zœ",
    _k("ত", "ম"): "Z¥", _k("ত", "র"): "Î", _k("ত", "ব"): "Z¡",
    _k("ত", "ত", "ব"): "Ë¡",
    _k("থ", "ব"): "_¡",
    # দ
    _k("দ", "গ"): "˜M", _k("দ", "ঘ"): "˜N", _k("দ", "দ"): "Ï",
    _k("দ", "ধ"): "×", _k("দ", "ব"): "Ø", _k("দ", "ভ"): "™¢",
    _k("দ", "ম"): "Ù", _k("দ", "ভ", "র"): "™£",
    # ধ
    _k("ধ", "ব"): "aŸ", _k("ধ", "ম"): "a¥",
    # ন
    _k("ন", "ট"): "›U", _k("ন", "ঠ"): "Ú", _k("ন", "ড"): "Û",
    _k("ন", "ত"): "šÍ", _k("ন", "থ"): "š’", _k("ন", "দ"): "›`",
    _k("ন", "ধ"): "Ü", _k("ন", "ন"): "bœ", _k("ন", "ব"): "š^",
    _k("ন", "ম"): "b¥", _k("ন", "স"): "Ý",
    _k("ন", "ত", "র"): "š¿", _k("ন", "ত", "ব"): "šÍ¡",
    _k("ন", "দ", "ব"): "›Ø",
    # প ফ
    _k("প", "ট"): "Þ", _k("প", "ত"): "ß", _k("প", "ন"): "cœ",
    _k("প", "প"): "à", _k("প", "ল"): "cø", _k("প", "স"): "á",
    _k("ফ", "ল"): "d¬",
    # ব ভ
    _k("ব", "জ"): "â", _k("ব", "দ"): "ã", _k("ব", "ধ"): "ä",
    _k("ব", "ব"): "eŸ", _k("ব", "ল"): "eø",
    _k("ভ", "র"): "å",
    # ম
    _k("ম", "ন"): "gœ", _k("ম", "প"): "¤ú", _k("ম", "ফ"): "ç",
    _k("ম", "ব"): "¤^", _k("ম", "ভ"): "¤¢", _k("ম", "ম"): "¤§",
    _k("ম", "ল"): "¤ø", _k("ম", "র"): "¤ª",
    _k("ম", "প", "র"): "¤úÖ", _k("ম", "ভ", "র"): "¤£",
    # ল
    _k("ল", "ক"): "é", _k("ল", "গ"): "ê", _k("ল", "ট"): "ë",
    _k("ল", "ড"): "ì", _k("ল", "প"): "í", _k("ল", "ফ"): "î",
    _k("ল", "ব"): "j¦", _k("ল", "ম"): "j¥", _k("ল", "ল"): "jø",
    # শ
    _k("শ", "চ"): "ð", _k("শ", "ছ"): "ñ", _k("শ", "ন"): "kœ",
    _k("শ", "ব"): "k¦", _k("শ", "ম"): "k¥", _k("শ", "ল"): "kø",
    # ষ
    _k("ষ", "ক"): "®‹", _k("ষ", "ট"): "ó", _k("ষ", "ঠ"): "ô",
    _k("ষ", "ণ"): "ò", _k("ষ", "প"): "®ú", _k("ষ", "ফ"): "õ",
    _k("ষ", "ম"): "®§", _k("ষ", "ক", "র"): "®Œ",
    # স
    _k("স", "ক"): "¯‹", _k("স", "খ"): "ö", _k("স", "ট"): "÷",
    _k("স", "ত"): "¯Í", _k("স", "থ"): "¯’", _k("স", "ন"): "¯œ",
    _k("স", "প"): "¯ú", _k("স", "ফ"): "ù", _k("স", "ব"): "¯^",
    _k("স", "ম"): "¯§", _k("স", "ল"): "¯ø", _k("স", "র"): "¯ª",
    _k("স", "ক", "র"): "¯Œ", _k("স", "ত", "র"): "¯¿",
    _k("স", "প", "র"): "¯úÖ",
    # হ
    _k("হ", "ণ"): "nè", _k("হ", "ন"): "ý", _k("হ", "ব"): "nŸ",
    _k("হ", "ম"): "þ", _k("হ", "ল"): "n¬",
}

MAX_CONJUNCT_LEN = max(len(k) for k in CONJUNCTS)

# --------------------------------------------------------------------------
# Character classes
# --------------------------------------------------------------------------
BENGALI_BLOCK = (0x0980, 0x09FF)


def is_bengali_char(ch: str) -> bool:
    cp = ord(ch)
    return BENGALI_BLOCK[0] <= cp <= BENGALI_BLOCK[1] or cp in (0x0964, 0x0965)


def is_consonant(ch: str) -> bool:
    return ch in CONSONANTS


# ASCII characters that SutonnyMJ draws as themselves, so they may sit inside a
# SutonnyMJ run.  Letters, digits and the glyph-carrying punctuation
# (& ^ ` _ ~ | \ @ # $ < > { }) are deliberately excluded.
SUTONNY_SAFE_ASCII = frozenset(" \t\r\n,.?!:;()[]-+=/*%'\"")
