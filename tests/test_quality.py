"""Quality / correctness tests for diversity metrics and sample canonicalization."""

from aigc_synth.diversity import analyze_diversity, _gini
from aigc_synth.models import SyntheticSample


def _sample(cat, text):
    return SyntheticSample.from_dict({"spec": "x", "data": {"category": cat, "text": text}})


def test_gini_balanced_is_zero():
    # perfectly equal distribution -> Gini 0
    assert _gini([5, 5, 5, 5]) == 0.0


def test_gini_empty_and_zero_total():
    assert _gini([]) == 0.0
    assert _gini([0, 0, 0]) == 0.0


def test_evenness_perfectly_balanced():
    samples = [
        _sample("refund", "a"),
        _sample("refund", "b"),
        _sample("shipping", "c"),
        _sample("shipping", "d"),
        _sample("account", "e"),
        _sample("account", "f"),
    ]
    rep = analyze_diversity(samples)
    assert rep.evenness == 1.0  # balanced -> 1 - Gini(0)


def test_evenness_imbalanced_lower():
    samples = [
        _sample("refund", "a"),
        _sample("refund", "b"),
        _sample("refund", "c"),
        _sample("refund", "d"),
        _sample("shipping", "e"),
        _sample("account", "f"),
    ]
    rep = analyze_diversity(samples)
    assert rep.evenness < 1.0  # imbalanced -> Gini > 0 -> evenness < 1


def test_evenness_empty_input_is_zero():
    # No samples and no target categories -> nothing to distribute.
    rep = analyze_diversity([], target_categories=None)
    assert rep.evenness == 0.0
    # Explicit empty target list also yields 0.0 (no categories to spread over).
    rep2 = analyze_diversity([], target_categories=[])
    assert rep2.evenness == 0.0


def test_nan_data_canonicalizes_and_stays_distinct():
    # NaN previously serialized to the literal "NaN" and collapsed distinct
    # samples to the same id. After normalization to None they must differ.
    a = SyntheticSample.from_dict(
        {"spec": "x", "data": {"category": "refund", "score": float("nan"), "text": "a"}}
    )
    b = SyntheticSample.from_dict(
        {"spec": "x", "data": {"category": "refund", "score": float("nan"), "text": "b"}}
    )
    assert a.id != b.id  # distinct content -> distinct id
    # The canonical fingerprint must be valid JSON (no bare NaN literal) and the
    # normalized data must round-trip through json.dumps without error.
    import json

    assert a.data.get("score") is None  # NaN -> None
    json.dumps({"spec": a.spec, "data": a.data}, ensure_ascii=False)
    assert isinstance(a.id, str) and len(a.id) == 12
