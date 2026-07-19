"""Diversity control: de-duplication and per-category distribution analysis."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable

from .models import SyntheticSample

_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[\u4e00-\u9fff]")


def _sample_tokens(s: SyntheticSample) -> set[str]:
    """Token signature of a sample (category + all data values)."""
    text = " ".join(str(v) for v in s.data.values())
    return set(_TOKEN_RE.findall(text.lower())) | {s.category().lower()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(samples: Iterable[SyntheticSample]) -> tuple[list[SyntheticSample], list[SyntheticSample]]:
    """Remove exact duplicates by canonical key. Returns ``(unique, removed)``."""
    samples = list(samples)
    seen: set[str] = set()
    unique: list[SyntheticSample] = []
    removed: list[SyntheticSample] = []
    for s in samples:
        k = s.canonical_key()
        if k in seen:
            removed.append(s)
        else:
            seen.add(k)
            unique.append(s)
    return unique, removed


def dedupe_similar(
    samples: Iterable[SyntheticSample],
    *,
    threshold: float = 0.8,
    keep: str = "first",
) -> tuple[list[SyntheticSample], list[SyntheticSample]]:
    """Collapse near-duplicate samples by token Jaccard similarity.

    LLM-synthesized samples often vary only cosmetically (``"I want a refund"``
    vs ``"Please refund my order"``). Exact-key ``dedupe`` keeps both; this
    pass merges pairs whose normalized token overlap meets *threshold*.

    Returns ``(unique, removed)``.
    """
    samples = list(samples)
    sigs = [_sample_tokens(s) for s in samples]
    kept_idx: list[int] = []
    removed: list[SyntheticSample] = []
    for i, s in enumerate(samples):
        dup_of = -1
        for j in kept_idx:
            if _jaccard(sigs[j], sigs[i]) >= threshold:
                dup_of = j
                break
        if dup_of == -1:
            kept_idx.append(i)
        elif keep == "last":
            removed.append(samples[dup_of])
            kept_idx[kept_idx.index(dup_of)] = i
        else:
            removed.append(s)
    return [samples[i] for i in kept_idx], removed


@dataclass
class DiversityReport:
    total: int = 0
    unique: int = 0
    duplicates: int = 0
    per_category: dict[str, int] = field(default_factory=dict)
    categories_present: int = 0
    target_categories: int = 0
    gaps: list[str] = field(default_factory=list)
    evenness: float = 0.0  # 0..1, 1 = perfectly balanced across categories

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "unique": self.unique,
            "duplicates": self.duplicates,
            "per_category": self.per_category,
            "categories_present": self.categories_present,
            "target_categories": self.target_categories,
            "gaps": self.gaps,
            "evenness": round(self.evenness, 4),
        }


def analyze_diversity(
    samples: Iterable[SyntheticSample],
    *,  # noqa: D401
    target_categories: list[str] | None = None,
) -> DiversityReport:
    """Analyze category distribution and detect gaps / imbalance."""
    samples = list(samples)
    counts: Counter[str] = Counter()
    for s in samples:
        cat = s.category() or "uncategorized"
        counts[cat] += 1
    cats = target_categories or sorted(counts)
    gaps = [c for c in cats if counts.get(c, 0) == 0]
    # Evenness: 1 - normalized Gini-like spread over target categories.
    if cats:
        vals = [counts.get(c, 0) for c in cats]
        total = sum(vals)
        if total > 0:
            mean = total / len(vals)
            spread = sum(abs(v - mean) for v in vals) / (2 * total)
            evenness = 1.0 - spread
        else:
            evenness = 0.0
    else:
        evenness = 1.0
    return DiversityReport(
        total=len(samples),
        unique=len(samples),
        duplicates=0,
        per_category=dict(counts),
        categories_present=len([c for c in counts if counts[c] > 0]),
        target_categories=len(cats),
        gaps=gaps,
        evenness=evenness,
    )


def resample_targets(report: DiversityReport) -> list[str]:
    """Return the list of categories that need more samples (gaps first)."""
    return list(report.gaps)
