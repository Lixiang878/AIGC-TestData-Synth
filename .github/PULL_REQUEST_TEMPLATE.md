## What

<!-- Briefly describe the change. -->

## Why

<!-- Motivation / linked issue. -->

## How to test

```bash
pip install -e ".[dev]"
pytest -q
aigc-testdata-synth demo
```

## Checklist

- [ ] Core remains dependency-free (stdlib only)
- [ ] New behavior covered by `tests/`
- [ ] `ruff check src tests` passes
- [ ] Docs updated if needed
