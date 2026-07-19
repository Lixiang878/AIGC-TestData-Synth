# Changelog

All notable changes are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-19

### Added
- Spec-driven synthesis (`generator.py`) with robust JSON parsing.
- Offline `MockProvider` and network `OpenAIProvider` (OpenAI-compatible).
- Diversity control: de-duplication + per-category distribution report with gap
  detection and evenness metric (`diversity.py`).
- Quality filtering rule chain: required fields, length bounds, language match,
  PII leakage, lightweight relevance (`filter.py`).
- CLI (`synth`, `diversity`, `filter`, `demo`) and an offline pytest suite.
