"""Generation orchestration and robust LLM-output parsing."""

from __future__ import annotations

import json
import re
from typing import Sequence

from .models import DataSpec, SyntheticSample
from .provider import BaseProvider

SYSTEM_PROMPT = (
    "You are a data engineer generating high-quality test inputs for software "
    "testing. Given a specification, produce diverse, realistic samples as a "
    "JSON object {\"samples\": [ {<fields>} , ... ]}. Each sample must have every "
    "requested field. Spread samples across all provided categories. Avoid "
    "duplicates and avoid real personally identifiable information (PII). "
    "Respond with JSON only, no markdown fences."
)


def build_prompt(spec: DataSpec) -> tuple[str, str]:
    field_desc = ", ".join(spec.fields) if spec.fields else "text"
    cat_desc = ", ".join(spec.categories) if spec.categories else "(none specified)"
    user = (
        f"Generate test data according to this spec.\n\n"
        f"Name: {spec.name}\n"
        f"Instruction: {spec.instruction}\n"
        f"Fields (each sample must include all): {field_desc}\n"
        f"Categories (distribute samples across these): {cat_desc}\n"
    )
    if spec.language:
        user += f"Language: {spec.language}\n"
    if spec.constraints:
        user += f"Constraints: {spec.constraints}\n"
    if spec.target_per_category:
        user += f"Aim for about {spec.target_per_category} samples per category.\n"
    user += (
        "\nReturn the JSON now.\n"
        f"<<SPEC_JSON>>{json.dumps(spec.to_dict(), ensure_ascii=False)}<</SPEC_JSON>>"
    )
    return SYSTEM_PROMPT, user


def parse_llm_output(text: str, spec_name: str = "unknown") -> list[SyntheticSample]:
    """Extract a ``{"samples": [...]}`` list from an LLM reply (robust)."""
    if not text:
        return []
    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", candidate, re.S)
    if fence:
        candidate = fence.group(1)
    if not candidate.lstrip().startswith("{"):
        m = re.search(r"\{.*\}", candidate, re.S)
        candidate = m.group(0) if m else candidate
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        m = re.search(r'"samples"\s*:\s*(\[.*?\])\s*}', candidate, re.S)
        if not m:
            return []
        try:
            data = {"samples": json.loads(m.group(1))}
        except json.JSONDecodeError:
            return []
    raw = data.get("samples", []) if isinstance(data, dict) else []
    out: list[SyntheticSample] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(SyntheticSample.from_dict({"spec": spec_name, "data": item}))
        elif item is not None:
            out.append(SyntheticSample.from_dict({"spec": spec_name, "data": {"value": item}}))
    return out


def synthesize(
    spec: DataSpec,
    provider: BaseProvider,
    *,
    n: int = 10,
    temperature: float = 0.9,
    max_tokens: int = 2048,
    provider_name: str | None = None,
    samples_per_call: int = 10,
) -> list[SyntheticSample]:
    """Synthesize ``n`` samples for *spec* by calling *provider* as needed."""
    pname = provider_name or getattr(provider, "name", "unknown")
    system, user = build_prompt(spec)
    collected: list[SyntheticSample] = []
    calls = max(1, -(-n // samples_per_call))  # ceil
    for _ in range(calls):
        if len(collected) >= n:
            break
        text = provider.synthesize(spec, system, user, temperature=temperature, max_tokens=max_tokens)
        for s in parse_llm_output(text, spec_name=spec.name):
            s.provider = pname
            s.raw = text
            collected.append(s)
            if len(collected) >= n:
                break
    return collected[:n]
