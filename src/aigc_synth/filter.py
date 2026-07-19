"""Quality filtering for synthesized samples (rule-based, offline-friendly)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .models import DataSpec, SyntheticSample

# Common PII pattern detectors (conservative; meant to flag obvious leaks).
_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\s-]?){7,13}(?!\d)"),
    "id_card_cn": re.compile(r"\b\d{17}[\dXx]\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass
class QualityRule:
    """A named rule returning ``(passed, reason)`` for a sample."""

    name: str
    fn: Callable[[SyntheticSample, DataSpec], tuple[bool, str]]

    def check(self, sample: SyntheticSample, spec: DataSpec) -> tuple[bool, str]:
        try:
            return self.fn(sample, spec)
        except Exception as exc:  # a rule must never crash the pipeline
            return False, f"rule_error:{exc}"


def _text_of(sample: SyntheticSample) -> str:
    parts = []
    for v in sample.data.values():
        if isinstance(v, str):
            parts.append(v)
        else:
            parts.append(json.dumps(v, ensure_ascii=False))
    return " ".join(parts)


def _required_fields(sample: SyntheticSample, spec: DataSpec) -> tuple[bool, str]:
    missing = [f for f in spec.fields if f not in sample.data]
    if missing:
        return False, f"missing_fields:{missing}"
    return True, ""


def _length_bounds(
    lo: int, hi: int
) -> Callable[[SyntheticSample, DataSpec], tuple[bool, str]]:
    def _fn(sample: SyntheticSample, spec: DataSpec) -> tuple[bool, str]:
        n = len(_text_of(sample))
        if n < lo:
            return False, f"too_short:{n}<{lo}"
        if n > hi:
            return False, f"too_long:{n}>{hi}"
        return True, ""

    return _fn


def _language_match(sample: SyntheticSample, spec: DataSpec) -> tuple[bool, str]:
    if not spec.language:
        return True, ""
    text = _text_of(sample)
    has_cjk = bool(_CJK_RE.search(text))
    if spec.language.lower().startswith("zh") and not has_cjk:
        return False, "language_mismatch:expected_zh"
    if spec.language.lower().startswith("en") and has_cjk:
        return False, "language_mismatch:expected_en"
    return True, ""


def _no_pii(sample: SyntheticSample, spec: DataSpec) -> tuple[bool, str]:
    text = _text_of(sample)
    for name, pat in _PII_PATTERNS.items():
        if pat.search(text):
            return False, f"pii:{name}"
    return True, ""


def _relevance(sample: SyntheticSample, spec: DataSpec) -> tuple[bool, str]:
    """Lightweight relevance: at least one instruction keyword or category appears.

    Matching against both the instruction vocabulary and the declared category
    names avoids over-rejecting realistic short samples (e.g. "I want a refund"
    for a ``refund`` category).
    """
    if not spec.instruction and not spec.categories:
        return True, ""
    text = _text_of(sample).lower()
    keywords = [w for w in re.findall(r"[a-zA-Z\u4e00-\u9fff]{3,}", spec.instruction.lower())]
    keywords += [c.lower() for c in spec.categories]
    keywords = [k for k in keywords if k]
    if not keywords:
        return True, ""
    hits = sum(1 for k in keywords if k in text)
    if hits == 0:
        return False, "low_relevance"
    return True, ""


def default_rules(
    spec: DataSpec, *, min_len: int = 3, max_len: int = 2000
) -> list[QualityRule]:
    rules = [
        QualityRule("required_fields", _required_fields),
        QualityRule("length", _length_bounds(min_len, max_len)),
        QualityRule("no_pii", _no_pii),
    ]
    if spec.language:
        rules.append(QualityRule("language", _language_match))
    if spec.instruction:
        rules.append(QualityRule("relevance", _relevance))
    return rules


@dataclass
class FilterResult:
    kept: list[SyntheticSample] = field(default_factory=list)
    rejected: list[tuple[SyntheticSample, list[str]]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "kept": len(self.kept),
            "rejected": len(self.rejected),
            "reasons": sorted({r for _, rs in self.rejected for r in rs}),
        }


def filter_samples(
    samples: Iterable[SyntheticSample],
    spec: DataSpec,
    *,
    rules: list[QualityRule] | None = None,
    min_len: int = 3,
    max_len: int = 2000,
) -> FilterResult:
    """Apply quality rules; keep samples passing ALL rules."""
    rules = rules or default_rules(spec, min_len=min_len, max_len=max_len)
    result = FilterResult()
    for s in samples:
        failed: list[str] = []
        for rule in rules:
            passed, reason = rule.check(s, spec)
            if not passed:
                failed.append(reason or rule.name)
        if failed:
            result.rejected.append((s, failed))
        else:
            result.kept.append(s)
    return result
