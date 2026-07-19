<div align="center">

# aigc-testdata-synth

**AIGC 测试数据工厂 · 规格驱动、多样性可控、质量可审计。**
**LLM-based test-data synthesis with diversity control & quality filtering.**

Define a spec → mass-produce test inputs with an LLM → de-duplicate → control
category diversity → filter by quality.

[English](#english) · [中文](#中文)

</div>

---

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/dependencies-zero%20core%20(stdlib)-brightgreen.svg" alt="Zero core deps">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="License">
</p>

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

> Part of 李想 (Lixiang)'s 2027 autumn-recruitment portfolio. The **core** depends only
> on the Python standard library; network providers (`openai`) import lazily, so it
> installs instantly and is fully testable offline.

### Why a "factory" rather than a prompt

Naïve "ask the LLM for 100 examples" produces three predictable failure modes:
**(a)** silent duplicates ("refund my order" ×40), **(b)** category collapse (90% one
label), **(c)** contaminated samples (PII, off-topic). Those are exactly the things
that make a test set *worse* than a small hand-written one. This tool treats synthesis
as a **pipeline with acceptance gates**, so the output is auditable, not just voluminous.

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

### Related work

| Approach | Strength | Weakness this tool addresses |
|---|---|---|
| **Faker / Mimesis** (schema faking) | Fast, deterministic, typed | No natural language; can't produce realistic utterances/topics |
| **Raw LLM prompt ("give me 100")** | Flexible, realistic text | Duplicates, category collapse, PII — no gates |
| **Data-augmentation (nlpaug, etc.)** | Cheap perturbations | Stays near seed data; poor *category* coverage |
| **aigc-testdata-synth (this)** | LLM realism **+ acceptance gates** | Needs a real provider for production volume |

The positioning is explicit: keep the LLM's strength (fluent, on-topic text) and add
the engineering that naive prompting lacks (de-dup, balance, filtering with reasons).

### Methodology (engineering judgment)

- **Two-stage de-duplication.** Exact-hash removal catches byte-identical repeats;
  the Jaccard pass catches the *semantic* repeats LLMs actually produce
  ("I want a refund" vs "please refund my order"). The signature uses
  `category + text tokens` only — not IDs or ordering — so genuinely distinct inputs
  survive.
- **Evenness over raw count.** A category set that is 90% one label is useless for
  testing; the report quantifies balance (1 − normalised Gini spread) so you can see
  *imbalance*, not just *totals*.
- **Filter rejects, never silently drops.** Every removed sample keeps its reason
  (`pii:email`, `missing_fields`, …), which is what lets a test author trust the kept set.

### Limitations

- **Relevance is keyword-based**, not semantic. It guards against obviously off-topic
  samples, not subtle off-target phrasing; an embedding or LLM-as-judge stage would be
  the next upgrade.
- **The quality rules are conservative examples.** Calibrate thresholds and add domain
  rules for your own data.
- **MockProvider is a deterministic fixture**, not a model — use a real provider for
  production data.

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

### 为什么是"工厂"而非一句 prompt

朴素地"让 LLM 生成 100 条"会产生三种可预见的失败：**(a)** 静默重复（"我要退款" ×40）、
**(b)** 类别坍缩（90% 集中在一类）、**(c)** 污染样本（PII、离题）。这些恰恰会让测试集
比一小份手写集更糟。本工具把合成当作**带验收闸门的生产线**，使产出可审计，而非只是量大。

### 特性

- **规格驱动**：一份小 JSON 描述字段、类别、约束、目标语言与每类数量。
- **可插拔提供者**：离线 `MockProvider` 与 `OpenAIProvider`（兼容 OpenAI / 文心 / 通义 / vLLM）。
- **多样性**：精确去重（规范化指纹）**+ 相似度去重**（token Jaccard），合并"只是措辞不同"
  的近重复；类别覆盖报告含缺口检测与均衡度。
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

### 相关作品

| 方法 | 强项 | 本工具补强之处 |
|---|---|---|
| **Faker / Mimesis**（模式伪造） | 快、确定、有类型 | 无自然语言，产不出真实语料/主题 |
| **原始 LLM prompt（"给我 100 条"）** | 灵活、文本真实 | 重复、类别坍缩、PII——无闸门 |
| **数据增强（nlpaug 等）** | 廉价扰动 | 围绕种子数据，类别覆盖差 |
| **aigc-testdata-synth（本项）** | LLM 真实感 **+ 验收闸门** | 生产级体量与真实提供者配合 |

定位很明确：保留 LLM 的优势（流畅、切题的文本），补上朴素 prompt 缺的工程环节
（去重、均衡、带原因过滤）。

### 设计决策（工程判断）

- **两阶段去重**：精确哈希去除字节级重复；Jaccard 阶段捕获 LLM 真正产生的"语义重复"
  （"I want a refund" 与 "please refund my order"）。签名只用 `类别 + 文本 token`，
  不含 ID 与顺序，所以真正不同的输入得以保留。
- **看重均衡而非总量**：某一类占 90% 的样本对测试毫无价值；报告量化均衡度
  （1 − 归一化 Gini spread），让你看到"失衡"而非仅"总数"。
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
