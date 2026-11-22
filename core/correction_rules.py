"""Structured correction rules.

Two layers, both literal (no broad regular expressions):

1. ``NORMALIZATION_RULES`` run on the *Unicode* side before conversion.  They
   canonicalise equivalent encodings (decomposed nukta letters, split o-kar)
   and fix common typing-order mistakes that would otherwise convert wrongly.
2. ``CorrectionSet`` holds user-defined replacements applied to the *Bijoy*
   output of Bengali segments only.  Users can add exceptions without touching
   code (Settings -> Correction rules); rules are stored as JSON.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import conversion_rules as R


@dataclass(frozen=True)
class Rule:
    find: str
    replace: str
    note: str = ""


NORMALIZATION_RULES: tuple[Rule, ...] = (
    Rule("﻿", "", "strip byte-order mark"),
    Rule("ড" + R.NUKTA, "\u09DC", "decomposed RRA"),
    Rule("ঢ" + R.NUKTA, "\u09DD", "decomposed RHA"),
    Rule("য" + R.NUKTA, "\u09DF", "decomposed YYA"),
    Rule(R.E_KAR + R.AA_KAR, R.O_KAR, "split o-kar"),
    Rule(R.E_KAR + R.AU_LENGTH, R.OU_KAR, "split ou-kar"),
    Rule("অ" + R.AA_KAR, "আ", "অ + া typed for আ"),
    Rule(R.AA_KAR + R.AA_KAR, R.AA_KAR, "doubled aa-kar"),
    Rule(R.I_KAR + R.I_KAR, R.I_KAR, "doubled i-kar"),
    Rule(R.U_KAR + R.U_KAR, R.U_KAR, "doubled u-kar"),
    Rule(R.HASANTA + R.HASANTA, R.HASANTA, "doubled hasanta"),
    # chandrabindu typed before the vowel sign it belongs to
    *(Rule(R.CHANDRABINDU + k, k + R.CHANDRABINDU, "chandrabindu after kar")
      for k in (R.AA_KAR, R.II_KAR, R.U_KAR, R.UU_KAR, R.I_KAR, R.E_KAR,
                R.OI_KAR, R.O_KAR, R.OU_KAR)),
)


def _compile(rules) -> tuple[re.Pattern | None, dict[str, str]]:
    table = {r.find: r.replace for r in rules if r.find}
    if not table:
        return None, {}
    keys = sorted(table, key=len, reverse=True)
    return re.compile("|".join(re.escape(k) for k in keys)), table


_NORM_RE, _NORM_TABLE = _compile(NORMALIZATION_RULES)


def normalize_unicode(text: str) -> str:
    """Apply normalisation rules until stable (at most a few passes)."""
    if _NORM_RE is None:
        return text
    for _ in range(3):
        new = _NORM_RE.sub(lambda m: _NORM_TABLE[m.group(0)], text)
        if new == text:
            break
        text = new
    return text


@dataclass
class UserRule:
    find: str
    replace: str
    enabled: bool = True
    note: str = ""


@dataclass
class CorrectionSet:
    """User-defined literal replacements applied to Bijoy output."""

    rules: list[UserRule] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._compiled = None

    def _ensure(self):
        if self._compiled is None:
            active = [Rule(r.find, r.replace) for r in self.rules if r.enabled and r.find]
            self._compiled = _compile(active)
        return self._compiled

    def invalidate(self) -> None:
        self._compiled = None

    def apply(self, bijoy: str) -> str:
        pattern, table = self._ensure()
        if pattern is None:
            return bijoy
        return pattern.sub(lambda m: table[m.group(0)], bijoy)

    # persistence -----------------------------------------------------
    def to_json(self) -> str:
        return json.dumps([asdict(r) for r in self.rules], ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "CorrectionSet":
        items = json.loads(data) if data.strip() else []
        rules = []
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("find"), str):
                rules.append(UserRule(
                    find=it["find"], replace=str(it.get("replace", "")),
                    enabled=bool(it.get("enabled", True)), note=str(it.get("note", ""))))
        return cls(rules)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CorrectionSet":
        try:
            return cls.from_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
