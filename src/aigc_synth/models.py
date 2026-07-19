"""Data models: data specification and synthesized samples."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class DataSpec:
    """Specification of what test data to synthesize."""

    name: str
    instruction: str
    fields: list[str] = field(default_factory=lambda: ["text"])
    categories: list[str] = field(default_factory=list)
    constraints: str = ""
    target_per_category: int | None = None
    language: str = ""  # e.g. "en", "zh", "" = any

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DataSpec":
        return cls(
            name=d["name"],
            instruction=d.get("instruction", ""),
            fields=list(d.get("fields", ["text"])),
            categories=list(d.get("categories", [])),
            constraints=d.get("constraints", ""),
            target_per_category=d.get("target_per_category"),
            language=d.get("language", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SyntheticSample:
    """A single synthesized test input."""

    id: str
    spec: str
    data: dict[str, Any]
    provider: str = "unknown"
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SyntheticSample":
        d = dict(d)
        d.pop("id", None)
        spec = d.get("spec", "unknown")
        data = d.get("data", d.get("sample", {})) or {}
        if not isinstance(data, dict):
            data = {"value": data}
        fingerprint = json.dumps(
            {"spec": spec, "data": _norm(data)}, sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        _id = hashlib.sha1(fingerprint).hexdigest()[:12]
        return cls(
            id=_id,
            spec=spec,
            data=data,
            provider=d.get("provider", "unknown"),
            raw=d.get("raw", ""),
        )

    def canonical_key(self) -> str:
        return self.id

    def category(self) -> str:
        """Best-effort extraction of the sample's category for diversity."""
        for key in ("category", "type", "label", "class"):
            if key in self.data and isinstance(self.data[key], str):
                return self.data[key]
        return ""


def _norm(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _norm(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, float):
        return round(v, 9)
    return v
