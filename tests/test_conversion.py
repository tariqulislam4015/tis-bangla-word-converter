import time

import pytest

from core.bijoy_to_unicode import bijoy_to_unicode
from core.correction_rules import normalize_unicode
from core.text_utils import Kind, contains_bengali, segment, text_stats
from core.unicode_to_bijoy import UnicodeToBijoy, unicode_to_bijoy

from . import corpus


@pytest.mark.parametrize("src,expected", corpus.ALL, ids=[u for u, _ in corpus.ALL])
def test_corpus(src, expected):
    assert unicode_to_bijoy(src) == expected


@pytest.mark.parametrize("src", corpus.ROUND_TRIP)
def test_round_trip(src):
    assert bijoy_to_unicode(unicode_to_bijoy(src)) == normalize_unicode(src)


def test_empty_and_whitespace():
    assert unicode_to_bijoy("") == ""
    assert unicode_to_bijoy("   \n\t ") == "   \n\t "


def test_non_bengali_untouched():
    text = "The quick brown fox, 123 — “quotes” & symbols ^_~|`"
    assert unicode_to_bijoy(text) == text


def test_idempotent_on_bijoy_output():
    once = unicode_to_bijoy("আমার সোনার বাংলা")
    assert unicode_to_bijoy(once) == once
    assert not contains_bengali(once)


def test_multiple_paragraphs_preserved():
    src = "প্রথম লাইন\nদ্বিতীয় লাইন\r\n\nতৃতীয়"
    out = unicode_to_bijoy(src)
    assert out.count("\n") == src.count("\n")
    assert out.count("\r") == src.count("\r")


def test_word_initial_ekar_after_space_and_context():
    assert unicode_to_bijoy("সে যে") == "†m †h"
    assert unicode_to_bijoy("দেশ") == "†`k"
    # previous-character context (e.g. previous Word run) gives medial form
    assert unicode_to_bijoy("দের", prev_char="মা") == "‡`i"
    assert unicode_to_bijoy("দের", prev_char=" ") == "†`i"


def test_explicit_hasanta_and_zwnj():
    assert unicode_to_bijoy("ক্‌") == "K&"
    assert unicode_to_bijoy("ক্") == "K&"


def test_unknown_conjunct_falls_back_without_loss():
    conv = UnicodeToBijoy()
    rep = conv.convert_with_report("গ্ঘ")
    assert rep.output == "M&N"
    assert rep.fallback_conjuncts


def test_unmapped_bengali_is_kept_and_reported():
    conv = UnicodeToBijoy()
    rep = conv.convert_with_report("দাম ৳৫০")
    assert "৳" in rep.output
    assert "৳" in rep.unmapped


def test_decomposed_input_normalised():
    composed = unicode_to_bijoy("পড়া বোকা")
    decomposed = unicode_to_bijoy("পড়া বোকা")
    assert composed == decomposed == "cov †evKv"


def test_segmentation_kinds():
    segs = segment("Class ৮: বাংলা 2nd")
    kinds = [s.kind for s in segs]
    assert kinds == [Kind.FOREIGN, Kind.BENGALI, Kind.FOREIGN]
    assert "".join(s.text for s in segs) == "Class ৮: বাংলা 2nd"


def test_large_text_is_fast():
    para = "জ্ঞানার্জনের পথটি কষ্টসাধ্য হলেও অবিচ্ছেদ্য সাধনা এবং নিষ্ঠার মাধ্যমে তা সফল হতে পারে। "
    text = para * 5000          # ~450k characters
    t0 = time.perf_counter()
    out = unicode_to_bijoy(text)
    elapsed = time.perf_counter() - t0
    assert out.startswith("ÁvbvR©‡bi")
    assert elapsed < 15, f"too slow: {elapsed:.1f}s"


def test_stats():
    st = text_stats("আমার সোনার\nবাংলা")
    assert (st.words, st.lines) == (3, 2)
    assert text_stats("").characters == 0
