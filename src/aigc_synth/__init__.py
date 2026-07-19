"""aigc-testdata-synth — LLM-based test-data synthesis with diversity & filtering.

A lightweight, dependency-free pipeline that uses an LLM to mass-produce test
inputs (records, utterances, documents, ...), then controls their *diversity*
(de-duplication + per-category distribution) and *quality* (rule-based and
optional LLM-as-judge filtering).

The core runs on the Python standard library alone; network-backed providers
are imported lazily so the package installs and tests run fully offline.
"""

from .models import DataSpec, SyntheticSample
from .provider import BaseProvider, MockProvider, OpenAIProvider, get_provider
from .generator import synthesize, parse_llm_output
from .diversity import dedupe, DiversityReport, analyze_diversity, resample_targets
from .filter import filter_samples, QualityRule

__version__ = "0.1.0"

__all__ = [
    "DataSpec",
    "SyntheticSample",
    "BaseProvider",
    "MockProvider",
    "OpenAIProvider",
    "get_provider",
    "synthesize",
    "parse_llm_output",
    "dedupe",
    "DiversityReport",
    "analyze_diversity",
    "resample_targets",
    "filter_samples",
    "QualityRule",
    "__version__",
]
