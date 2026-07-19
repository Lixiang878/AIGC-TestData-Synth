"""LLM provider abstraction (offline Mock + OpenAI-compatible).

Self-contained copy so this repository is independently installable. Mirrors
the design used across the author's tooling portfolio.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Sequence

from .models import DataSpec


class BaseProvider:
    name = "base"

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float = 0.9,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError

    def synthesize(self, spec: DataSpec, system: str, user: str, **kw: Any) -> str:
        return self.complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **kw,
        )


class MockProvider(BaseProvider):
    """Offline provider producing deterministic, plausible samples.

    It does NOT call any model. It fabricates samples per category (and a few
    generic ones) so the full pipeline runs and is testable without a network.
    Output is clearly pseudo-data and must be reviewed before real use.
    """

    name = "mock"

    def __init__(self, samples_per_category: int = 3, **kwargs: Any) -> None:
        self.samples_per_category = max(1, samples_per_category)

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float = 0.9,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        user = ""
        for m in messages:
            if m.get("role") == "user":
                user = m.get("content", "")
                break
        spec = self._recover_spec(user)
        return self._render(spec)

    def _recover_spec(self, user: str) -> DataSpec:
        m = re.search(r"<<SPEC_JSON>>\s*(\{.*\})\s*<</SPEC_JSON>>", user, re.S)
        if m:
            try:
                return DataSpec.from_dict(json.loads(m.group(1)))
            except Exception:
                pass
        return DataSpec(name="unknown", instruction="")

    def _render(self, spec: DataSpec) -> str:
        fields = spec.fields or ["text"]
        cats = spec.categories or ["general"]
        samples: list[dict[str, Any]] = []
        for cat in cats:
            for i in range(self.samples_per_category):
                item: dict[str, Any] = {}
                for f in fields:
                    if f in ("category", "type", "label", "class"):
                        item[f] = cat
                    elif f in ("language", "lang"):
                        item[f] = spec.language or "en"
                    elif f == "text":
                        item[f] = f"[{cat}] sample {i + 1} for {spec.name}."
                    else:
                        item[f] = f"{cat}_{i}"
                samples.append(item)
        # a couple of generic ones
        for i in range(self.samples_per_category):
            item = {f: (f"generic_{i}" if f not in ("text",) else f"generic sample {i + 1}") for f in fields}
            if "category" in fields and "general" not in cats:
                item["category"] = "general"
            samples.append(item)
        return json.dumps({"samples": samples}, ensure_ascii=False, indent=2)


class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._client_kwargs = client_kwargs
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:  # pragma: no cover - depends on environment
            from openai import OpenAI

            kwargs = dict(self._client_kwargs)
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = ("sdk", OpenAI(**kwargs))
            return self._client
        except Exception:
            pass
        self._client = ("requests", None)
        return self._client

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float = 0.9,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> str:
        kind, client = self._get_client()
        if kind == "sdk":  # pragma: no cover - depends on environment
            resp = client.chat.completions.create(
                model=self.model,
                messages=list(messages),
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return resp.choices[0].message.content or ""
        import requests  # lazy

        url = (self.base_url or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or ""


_PROVIDERS = {"mock": MockProvider, "openai": OpenAIProvider}


def get_provider(name: str = "mock", **kwargs: Any) -> BaseProvider:
    name = (name or "mock").lower()
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown provider {name!r}. Available: {sorted(_PROVIDERS)}")
    return _PROVIDERS[name](**kwargs)
