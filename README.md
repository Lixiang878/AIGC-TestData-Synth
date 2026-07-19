<div align="center">

# aigc-testdata-synth

**LLM-based test-data synthesis with diversity control & quality filtering**

Define a spec → mass-produce test inputs with an LLM → de-duplicate → control
category diversity → filter by quality.

[English](#english) · [中文](#中文)

</div>

---

<a id="english"></a>
## English

`aigc-testdata-synth` uses a large language model to generate test inputs at
scale — records, utterances, documents, JSON payloads — then applies two
post-processing stages that matter for *testing* specifically:

1. **Diversity control** — de-duplication by canonical key, plus per-category
   distribution analysis that flags gaps (categories with zero coverage) and
   quantifies evenness.
2. **Quality filtering** — rule-based checks (required fields, length bounds,
   language match, PII leakage, lightweight relevance) that reject bad samples
   with reasons. An LLM-as-judge hook point is included for extension.

> Part of 李想's 2027 autumn-recruitment portfolio. The **core** depends only on
> the Python standard library; network providers (`openai`) import lazily, so it
> installs instantly and is fully testable offline.

### Features

- **Spec-driven**: a small JSON spec describes fields, categories, constraints,
  target language, and per-category targets.
- **Pluggable providers**: offline `MockProvider` (deterministic, CI-friendly)
  and `OpenAIProvider` (OpenAI / Wenxin / Qwen / vLLM).
- **Diversity**: de-dup + category coverage report with gap detection.
- **Quality**: configurable rule chain; every rejection carries a reason.
- **Zero core deps**, offline test suite.

### Install

```bash
pip install -e .
pip install -e ".[dev]"
```

### Quick start (offline)

```bash
aigc-testdata-synth demo
aigc-testdata-synth synth -s examples/support_tickets.json --provider mock \
    --dedup --filter -o samples.json
aigc-testdata-synth diversity samples.json --categories refund,shipping,account,complaint
```

### With a real LLM

```bash
export OPENAI_API_KEY=sk-...
aigc-testdata-synth synth -s examples/support_tickets.json --provider openai \
    --model gpt-4o-mini --dedup --filter -o samples.json
```

### Spec schema

```json
{
  "name": "support_tickets",
  "instruction": "Generate customer support ticket texts for an e-commerce chatbot.",
  "fields": ["text", "category", "language"],
  "categories": ["refund", "shipping", "account", "complaint"],
  "constraints": "1-3 sentences, no PII.",
  "target_per_category": 5,
  "language": "en"
}
```

### Project layout

```
aigc-testdata-synth/
├── README.md
├── pyproject.toml
├── src/aigc_synth/
│   ├── models.py        # DataSpec / SyntheticSample
│   ├── provider.py      # MockProvider / OpenAIProvider
│   ├── generator.py     # synthesis + JSON parsing
│   ├── diversity.py     # dedupe + distribution analysis
│   ├── filter.py        # quality rules
│   └── cli.py
├── tests/               # offline pytest suite
├── examples/            # spec + generated samples
├── configs/             # default config
└── .github/
```

### Tests

```bash
pytest -q
```

---

<a id="中文"></a>
## 中文

`aigc-testdata-synth` 借助大模型批量生成测试输入（记录、语料、文档、JSON
载荷等），并针对"测试"场景做两道后处理：

1. **多样性控制**：基于规范化指纹去重，并按类别统计分布，标记覆盖缺口、量化均衡度。
2. **质量过滤**：规则链（必填字段、长度边界、语言匹配、PII 泄露、轻量相关性）逐条过滤，每条拒绝都附带原因。

> 李想 2027 秋招作品集的一部分。**核心零第三方依赖**，联网提供者懒加载，可完全离线测试。

### 特性

- **规格驱动**：一份小 JSON 描述字段、类别、约束、目标语言与每类数量。
- **可插拔提供者**：离线 `MockProvider` 与 `OpenAIProvider`（兼容 OpenAI / 文心 / 通义 / vLLM）。
- **多样性**：去重 + 类别覆盖报告（缺口检测）。
- **质量**：可配置规则链，拒绝均带原因。
- **核心零依赖**，离线测试套件。

### 许可证

MIT © 2026 李想 (Lixiang)

---

<div align="center">

**Star ⭐ if useful. Issues and PRs welcome.**

</div>
