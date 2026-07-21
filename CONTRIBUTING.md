# Contributing

Thanks for improving `aigc-testdata-synth`.

## Development setup

```bash
git clone https://github.com/Lixiang878/AIGC-TestData-Synth.git
cd AIGC-TestData-Synth
pip install -e ".[dev]"
pytest -q
```

## Guidelines

- The **core** must stay dependency-free (Python standard library only).
  Network providers are isolated and lazily imported.
- Add/extend `tests/` for behavioral changes; the suite runs fully offline.
- Keep quality rules in `filter.py` composable via `QualityRule`.
- Format with `ruff` (or `black`) and lint before opening a PR.
- Open an issue first for large design changes.

## Commit messages

Short, imperative: `feat: add LLM-as-judge quality hook`.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
