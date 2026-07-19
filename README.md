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
- **Diversity**: exact de-dup (canonical key) **+ similarity de-dup** (token
  Jaccard) that collapses LLM near-duplicates which only differ in wording,
  plus a category coverage report with gap detection and evenness.
- **Quality**: configurable rule chain (required fields, length, language,
  PII, relevance); every rejection carries a reason.
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

Similarity de-duplication (collapse rephrased near-duplicates) is available in
`synth` via `--similar 0.8` (0 disables, the default), or as a standalone pass:

```bash
aigc-testdata-synth dedupe-similar samples.json --threshold 0.8 -o samples.dedup.json
```

### Design notes (engineering judgment)

- **Two-stage de-duplication.** Exact-hash removal catches byte-identical
  repeats; the Jaccard pass catches the *semantic* repeats LLMs actually
  produce ("I want a refund" vs "please refund my order"). The signature uses
  `category + text tokens` only — not IDs or ordering — so genuinely distinct
  inputs survive.
- **Evenness over raw count.** A category set that is 90% one label is useless
  for testing; the report quantifies balance (1 − normalised Gini spread) so
  you can see *imbalance*, not just *totals*.
- **Filter rejects, never silently drops.** Every removed sample keeps its
  reason (`pii:email`, `missing_fields`, …), which is what lets a test author
  trust the kept set.

### Limitations

- **Relevance is keyword-based**, not semantic. It guards against obviously
  off-topic samples, not subtle off-target phrasing; an embedding or
  LLM-as-judge stage would be the next upgrade.
- **The quality rules are conservative examples.** Calibrate thresholds and add
  domain rules for your own data.
- **MockProvider is a deterministic fixture**, not a model — use a real provider
  for production data.

### Example output

`aigc-testdata-synth demo` (or the equivalent synth command with `--dedup --filter`)
produces 10 unique samples with zero duplicates:

```text
==================================================
  AIGC Test Data Synthesis — Diversity Report
==================================================
  Total samples        : 10
  Unique samples       : 10
  Duplicates removed   : 0
  Categories present   : 4 / 4
  Gaps                 : none
  Evenness             : 0.8500
--------------------------------------------------
  Per category:
    account      : 3
    complaint    : 1
    refund       : 3
    shipping     : 3
==================================================
```

The generated samples are in `examples/samples.json`, and the full report is in
`results/diversity_report.txt`.

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
- **多样性**：精确去重（规范化指纹）**+ 相似度去重**（token Jaccard），合并"只是措辞不同"的近重复；类别覆盖报告含缺口检测与均衡度。
- **质量**：可配置规则链，拒绝均带原因。
- **核心零依赖**，离线测试套件。

### 示例输出

`aigc-testdata-synth demo`（或带 `--dedup --filter` 的 synth 命令）生成 10 条唯一样本，无重复：

```text
==================================================
  AIGC Test Data Synthesis — Diversity Report
==================================================
  Total samples        : 10
  Unique samples       : 10
  Duplicates removed   : 0
  Categories present   : 4 / 4
  Gaps                 : none
  Evenness             : 0.8500
--------------------------------------------------
  Per category:
    account      : 3
    complaint    : 1
    refund       : 3
    shipping     : 3
==================================================
```

生成样本见 `examples/samples.json`，完整报告见 `results/diversity_report.txt`。

### 设计决策（工程判断）

- **两阶段去重**：精确哈希去除字节级重复；Jaccard 阶段捕获 LLM 真正产生的"语义重复"
  （"I want a refund" 与 "please refund my order"）。签名只用 `类别 + 文本 token`，
  不含 ID 与顺序，所以真正不同的输入得以保留。
- **看重均衡而非总量**：某一类占 90% 的样本对测试毫无价值；报告量化均衡度
  （1 − 归一化 Gini  spread），让你看到"失衡"而非仅"总数"。
- **过滤是拒绝而非静默丢弃**：每个被移除样本都保留原因（`pii:email`、
  `missing_fields` 等），测试作者才敢信任保留集。

### 局限

- **相关性为关键词级，非语义级**：它能挡住明显离题样本，挡不住细微偏题表述；下一步可上
   embedding 或 LLM-as-Judge。
- **质量规则是保守示例**：请针对你的数据校准阈值、补充领域规则。
- **MockProvider 是确定性夹具而非模型**：生产数据请用真实提供者。

### 许可证

MIT © 2026 李想 (Lixiang)

---

<div align="center">

**Star ⭐ if useful. Issues and PRs welcome.**

</div>
