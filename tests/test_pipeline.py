"""Offline pipeline tests for aigc-testdata-synth (MockProvider)."""

import json
from pathlib import Path

from aigc_synth.models import DataSpec, SyntheticSample
from aigc_synth.provider import MockProvider, get_provider
from aigc_synth.generator import synthesize, parse_llm_output
from aigc_synth.diversity import analyze_diversity, dedupe, dedupe_similar
from aigc_synth.filter import filter_samples, default_rules


SPEC = DataSpec.from_dict(
    {
        "name": "support_tickets",
        "instruction": "Generate customer support ticket texts for an e-commerce chatbot.",
        "fields": ["text", "category", "language"],
        "categories": ["refund", "shipping", "account", "complaint"],
        "constraints": "1-3 sentences, no PII.",
        "language": "en",
    }
)


def test_get_provider_mock():
    assert get_provider("mock").name == "mock"


def test_synthesize_mock():
    provider = MockProvider(samples_per_category=2)
    samples = synthesize(SPEC, provider, n=8)
    assert len(samples) == 8
    assert all(isinstance(s, SyntheticSample) for s in samples)
    cats = {s.category() for s in samples}
    assert cats  # at least some categories present


def test_dedupe():
    a = SyntheticSample.from_dict({"spec": "x", "data": {"text": "hi"}})
    b = SyntheticSample.from_dict({"spec": "x", "data": {"text": "hi"}})  # dup
    c = SyntheticSample.from_dict({"spec": "x", "data": {"text": "bye"}})
    unique, removed = dedupe([a, b, c])
    assert len(unique) == 2
    assert len(removed) == 1


def test_filter_rejects_pii_and_missing_fields():
    samples = [
        SyntheticSample.from_dict({"spec": "support_tickets", "data": {"text": "I want a refund", "category": "refund", "language": "en"}}),
        SyntheticSample.from_dict({"spec": "support_tickets", "data": {"text": "email me at john@example.com", "category": "account", "language": "en"}}),
        SyntheticSample.from_dict({"spec": "support_tickets", "data": {"text": "short", "language": "en"}}),  # missing category
    ]
    result = filter_samples(samples, SPEC, min_len=3, max_len=2000)
    reasons = result.to_dict()["reasons"]
    assert any(r.startswith("pii:") for r in reasons)
    assert any(r.startswith("missing_fields") for r in reasons)
    assert len(result.kept) == 1


def test_diversity_report_gaps():
    samples = [
        SyntheticSample.from_dict({"spec": "x", "data": {"category": "refund", "text": "a"}}),
        SyntheticSample.from_dict({"spec": "x", "data": {"category": "refund", "text": "b"}}),
    ]
    rep = analyze_diversity(samples, target_categories=["refund", "shipping", "account"])
    assert rep.gaps == ["shipping", "account"]
    assert rep.categories_present == 1


def test_dedupe_similar_collapses_near_duplicates():
    a = SyntheticSample.from_dict(
        {"spec": "x", "data": {"category": "refund", "text": "I want a refund"}})
    b = SyntheticSample.from_dict(
        {"spec": "x", "data": {"category": "refund", "text": "I want a refund please"}})
    c = SyntheticSample.from_dict(
        {"spec": "x", "data": {"category": "shipping", "text": "where is my package"}})
    unique, removed = dedupe_similar([a, b, c], threshold=0.3)
    assert len(unique) == 2
    assert len(removed) == 1


def test_end_to_end_demo_offline():
    samples = synthesize(SPEC, MockProvider(samples_per_category=3), n=12)
    samples, _ = dedupe(samples)
    result = filter_samples(samples, SPEC)
    assert len(result.kept) >= 1
