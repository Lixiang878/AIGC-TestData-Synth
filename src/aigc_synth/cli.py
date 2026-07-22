"""Command-line interface for aigc-testdata-synth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .diversity import analyze_diversity, dedupe, dedupe_similar
from .filter import filter_samples
from .generator import synthesize
from .models import DataSpec, SyntheticSample
from .provider import get_provider


def _load_spec(path: str) -> DataSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return DataSpec.from_dict(data)


def _save(samples: list[SyntheticSample], out: str | None) -> None:
    dumped = json.dumps([s.to_dict() for s in samples], ensure_ascii=False, indent=2)
    if out:
        Path(out).write_text(dumped, encoding="utf-8")
        print(f"[ok] wrote {len(samples)} samples -> {out}")
    else:
        print(dumped)


def cmd_synth(args: argparse.Namespace) -> int:
    spec = _load_spec(args.spec)
    provider = get_provider(args.provider, model=args.model, base_url=args.base_url)
    samples = synthesize(
        spec,
        provider,
        n=args.n,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    if args.dedup:
        samples, removed = dedupe(samples)
        print(f"[info] {len(removed)} duplicates removed")
    if args.filter:
        result = filter_samples(samples, spec, min_len=args.min_len, max_len=args.max_len)
        print(
            f"[info] filter kept {len(result.kept)} / rejected {len(result.rejected)} "
            f"(reasons: {result.to_dict()['reasons']})"
        )
        samples = result.kept
    rep = analyze_diversity(samples, target_categories=spec.categories or None)
    print(f"[info] diversity: {json.dumps(rep.to_dict(), ensure_ascii=False)}")
    _save(samples, args.out)
    return 0


def cmd_diversity(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.infile).read_text(encoding="utf-8"))
    samples = [SyntheticSample.from_dict(d) for d in data]
    rep = analyze_diversity(samples, target_categories=args.categories.split(",") if args.categories else None)
    print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.infile).read_text(encoding="utf-8"))
    spec = _load_spec(args.spec) if args.spec else DataSpec(name="unknown", instruction="")
    samples = [SyntheticSample.from_dict(d) for d in data]
    result = filter_samples(samples, spec, min_len=args.min_len, max_len=args.max_len)
    _save(result.kept, args.out)
    return 0


def cmd_dedupe_similar(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.infile).read_text(encoding="utf-8"))
    samples = [SyntheticSample.from_dict(d) for d in data]
    unique, removed = dedupe_similar(samples, threshold=args.threshold)
    print(f"[info] similarity dedup (threshold={args.threshold}) removed "
          f"{len(removed)} near-duplicate(s); {len(unique)} kept")
    _save(unique, args.out)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    spec_path = Path(__file__).resolve().parents[2] / "examples" / "support_tickets.json"
    if not spec_path.exists():
        sys.exit(f"[error] spec not found: {spec_path}")
    spec = DataSpec.from_dict(json.loads(spec_path.read_text(encoding="utf-8")))
    provider = get_provider("mock")
    samples = synthesize(spec, provider, n=args.n)
    samples, removed = dedupe(samples)
    result = filter_samples(samples, spec)
    rep = analyze_diversity(result.kept, target_categories=spec.categories or None)
    print(f"[demo] generated={len(samples)} dedup_removed={len(removed)} "
          f"kept={len(result.kept)} rejected={len(result.rejected)}")
    print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aigc-testdata-synth",
        description="Synthesize AI-generated test data with diversity & quality control.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("synth", help="synthesize samples from a spec file")
    s.add_argument("--spec", "-s", required=True, help="JSON data spec")
    s.add_argument("--provider", default="mock", help="mock | openai")
    s.add_argument("--model", default="gpt-4o-mini")
    s.add_argument("--base-url", default=None)
    s.add_argument("--n", type=int, default=10)
    s.add_argument("--temperature", type=float, default=0.9)
    s.add_argument("--max-tokens", type=int, default=2048)
    s.add_argument("--dedup", action="store_true")
    s.add_argument("--filter", action="store_true")
    s.add_argument("--min-len", type=int, default=3)
    s.add_argument("--max-len", type=int, default=2000)
    s.add_argument("--out", "-o")
    s.set_defaults(func=cmd_synth)

    d = sub.add_parser("diversity", help="report category diversity of a JSON file")
    d.add_argument("infile")
    d.add_argument("--categories", default=None, help="comma list of target categories")
    d.set_defaults(func=cmd_diversity)

    f = sub.add_parser("filter", help="apply quality filters to a JSON file")
    f.add_argument("infile")
    f.add_argument("--spec", "-s", help="spec for relevance/language rules")
    f.add_argument("--min-len", type=int, default=3)
    f.add_argument("--max-len", type=int, default=2000)
    f.add_argument("--out", "-o", required=True)
    f.set_defaults(func=cmd_filter)

    demo = sub.add_parser("demo", help="offline end-to-end demo (mock provider)")
    demo.add_argument("--n", type=int, default=10, help="number of samples to synthesize")
    demo.set_defaults(func=cmd_demo)

    ds = sub.add_parser("dedupe-similar", help="collapse near-duplicate samples by similarity")
    ds.add_argument("infile")
    ds.add_argument("--threshold", type=float, default=0.8, help="Jaccard threshold 0-1")
    ds.add_argument("--out", "-o", required=True)
    ds.set_defaults(func=cmd_dedupe_similar)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
