from core.correction_rules import CorrectionSet, UserRule, normalize_unicode
from core.unicode_to_bijoy import UnicodeToBijoy


def test_normalization_rules():
    assert normalize_unicode("কো") == "কো"
    assert normalize_unicode("চঁা") == "চাঁ"
    assert normalize_unicode("অা") == "আ"
    assert normalize_unicode("﻿ক") == "ক"


def test_user_rules_apply_only_to_bengali_output():
    rules = CorrectionSet([UserRule("Avwg", "AvwgB")])
    conv = UnicodeToBijoy(rules)
    # Bengali segment is corrected, English 'Avwg' typed literally is not.
    assert conv.convert("আমি Avwg") == "AvwgB Avwg"


def test_disabled_rule_and_json_round_trip(tmp_path):
    cs = CorrectionSet([UserRule("a", "b", enabled=False, note="x"), UserRule("Kg", "KM")])
    path = tmp_path / "rules.json"
    cs.save(path)
    loaded = CorrectionSet.load(path)
    assert [r.find for r in loaded.rules] == ["a", "Kg"]
    assert loaded.rules[0].enabled is False
    assert UnicodeToBijoy(loaded).convert("কম") == "KM"


def test_corrupt_rules_file(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text("{not json", encoding="utf-8")
    assert CorrectionSet.load(path).rules == []


def test_longest_rule_wins():
    cs = CorrectionSet([UserRule("K", "1"), UserRule("Kv", "2")])
    assert cs.apply("KvK") == "21"
