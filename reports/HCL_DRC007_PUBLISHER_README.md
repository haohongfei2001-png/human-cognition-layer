# 🧠 Theory of Mind Benchmark Suite

A benchmark for evaluating Large Language Models on **Theory of Mind (ToM)** tasks — the cognitive ability to attribute mental states (beliefs, intentions, emotions, knowledge) to others and predict their behavior accordingly.

The suite is organized around **6 cognitive categories** scored through a **3-layer evaluation pipeline** that combines fast deterministic matching with LLM-based semantic judging and structured output analysis.

> **Status:** This repository ships with a **seed dataset** of hand-crafted scenarios (currently 5 per category — 30 total). The schema, scoring pipeline, CLI, dashboard, and tests are all production-ready; the dataset is designed to grow toward a full 150-scenario benchmark over time. See [Categories & Scenarios](#categories--scenarios) for the current count.

> **Live demo:** _Coming soon at `https://tom-benchmark.streamlit.app`_ — once deployed, paste your own Anthropic or OpenAI key in the sidebar to run benchmarks, or browse the dataset without any keys.

![Browse Scenarios tab](docs/screenshots/01-browse.png)

---

## Table of Contents

- [Why Theory of Mind?](#why-theory-of-mind)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Categories & Scenarios](#categories--scenarios)
- [Difficulty Tiers](#difficulty-tiers)
- [Scoring Pipeline](#scoring-pipeline)
- [Architecture](#architecture)
- [CLI Reference](#cli-reference)
- [Streamlit Dashboard](#streamlit-dashboard)
- [Deploying the Web App](#deploying-the-web-app)
- [API Keys](#api-keys)
- [Scenario Schema](#scenario-schema)
- [Export Formats](#export-formats)
- [Development](#development)
- [Research Background](#research-background)
- [License](#license)

---

## Why Theory of Mind?

Theory of Mind is a foundational capability for social intelligence. LLMs increasingly operate in contexts that require understanding **what other agents believe, know, feel, and intend** — from dialogue systems to autonomous agents to safety evaluations. This benchmark provides a structured, reproducible way to measure how well models handle these cognitive tasks, with fine-grained breakdowns across difficulty levels and reasoning types.

---

## Features

- **Hand-crafted scenarios** across 6 ToM categories with explicit difficulty tiers (easy → expert)
- **3-layer scoring pipeline**: fast string match → LLM-as-Judge → structured output analysis
- **CLI toolkit**: run benchmarks, filter by category/tier, export datasets, view results
- **Pluggable model adapters**: built-in support for Claude (Anthropic) and GPT (OpenAI) models with an extensible adapter interface, deterministic scoring (temperature 0 by default), automatic retry with exponential backoff on transient API errors, and optional parallel execution
- **Honest accuracy**: API failures are recorded as *unscored* rather than counted as wrong, so a rate-limited run never silently deflates a model's score
- **Multiple export formats**: JSONL, CSV, and HuggingFace Datasets for research workflows
- **Streamlit dashboard**: interactive web UI (styled with [Material Design 3](https://m3.material.io/)) for running benchmarks and comparing model performance
- **Comprehensive test suite**: pytest-based tests covering models, scoring, loading, adapters, CLI, and schema validation

---

## Installation

Install from source:

```bash
git clone https://github.com/jessholbrook/tom-benchmark.git
cd tom-benchmark
pip install -e ".[dev]"
```

To include the Streamlit dashboard dependencies:

```bash
pip install -e ".[dashboard]"
```

**Requirements:** Python 3.11+

---

## Quick Start

```bash
# List all categories and scenario counts
tom-benchmark list-categories

# List scenarios with optional filters
tom-benchmark list-scenarios
tom-benchmark list-scenarios --category false_belief --tier hard

# Run benchmark against a model
tom-benchmark run --models claude-sonnet-4-6 --output results.json

# Run with LLM-as-Judge scoring (Layer 2)
tom-benchmark run --models claude-sonnet-4-6 --judge claude-haiku-4-5-20251001

# Run with structured output analysis (Layer 3)
tom-benchmark run --models claude-sonnet-4-6 --structured

# Run with all layers enabled
tom-benchmark run --models claude-sonnet-4-6 --judge claude-haiku-4-5-20251001 --structured --output results.json

# Run multiple models in a single benchmark
tom-benchmark run --models claude-sonnet-4-6 --models gpt-4o --output comparison.json

# Export dataset
tom-benchmark export --format jsonl --output tom_benchmark.jsonl
tom-benchmark export --format huggingface --output tom_benchmark_hf/

# View results from a previous run
tom-benchmark results results.json
```

---

## Categories & Scenarios

Each of the 6 categories targets a distinct aspect of social cognition. Run `tom-benchmark list-categories` for the live count.

| Category | Description |
|---|---|
| **False Belief** | Sally-Anne style perspective-taking — can the model understand that characters hold beliefs that differ from reality? Tests whether models track belief/reality divergence when agents lack information about state changes. |
| **Indirect Request** | Pragmatic interpretation — understanding meaning beyond literal words. E.g., "It's cold in here" implies a request to close the window. Tests conversational implicature and speech act recognition. |
| **Knowledge Attribution** | Tracking who knows what based on observation, inference, and information flow. Tests whether models correctly reason about epistemic states across multiple agents. |
| **Deception & Manipulation** | Detecting lies, bluffs, omissions, and manipulative intent across social contexts. Tests whether models can identify when agents are being strategically dishonest. |
| **Emotional Inference** | Inferring emotional states from context, expectation violations, and social dynamics. Tests whether models can predict how agents will feel based on situational cues. |
| **Higher-Order Beliefs** | Recursive belief reasoning — "Alice thinks Bob thinks Carol knows..." Tests 2nd through 5th order belief attribution, the most cognitively demanding ToM task. |

Scenarios are stored as JSON files in `tom_benchmark/scenarios/`, one file per category (e.g., `false_belief.json`, `deception.json`).

---

## Difficulty Tiers

Each scenario is tagged with a difficulty tier reflecting the cognitive complexity required:

| Tier | Description |
|---|---|
| **Easy** | Single-step reasoning, familiar patterns, 1–2 agents |
| **Medium** | Multi-agent tracking, mild ambiguity, requires chaining 2–3 inferences |
| **Hard** | Nested beliefs, competing cues, cultural context, 3+ agents |
| **Expert** | 4th/5th-order beliefs, layered deception, strategic ambiguity, unreliable narrators |

Filter by tier in the CLI with `--tier easy`, `--tier hard`, etc.

---

## Scoring Pipeline

The benchmark uses a **3-layer scoring pipeline** that balances speed, accuracy, and depth of analysis:

```
Model Response
     │
     ▼
┌─────────────────────────────────┐
│  Layer 1 — String Match         │  Always active
│  Regex-based answer extraction  │  Returns: correct / incorrect / ambiguous
└──────────────┬──────────────────┘
               │ (if ambiguous, or --judge-always)
               ▼
┌─────────────────────────────────┐
│  Layer 2 — LLM-as-Judge         │  Opt-in (--judge <model>)
│  Evaluates response vs rubric   │  Returns: score (0–1), verdict, rationale
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Layer 3 — Structured Output    │  Opt-in (--structured)
│  Model responds in JSON format  │  Returns: answer, reasoning, confidence
└─────────────────────────────────┘
```

### Layer 1 — String Match (always on)

Fast regex-based matching against `expected_answer` and `answer_aliases`. The scorer normalizes text (lowercasing, stripping punctuation), extracts the core answer from verbose responses using pattern matching (e.g., "the answer is…", "will look in…"), and checks for negation to avoid false positives. Returns `correct`, `incorrect`, or `ambiguous`.

### Layer 2 — LLM-as-Judge (opt-in)

A separate LLM evaluates the model's response against the scenario's rubric. The judge receives the full scenario context, expected answer, rubric, and model response, then returns a structured JSON verdict with a score (0.0–1.0), verdict string, and rationale. Triggered automatically on `ambiguous` Layer 1 results, or forced on all responses with `--judge-always`. Can also be scoped to specific categories.

### Layer 3 — Structured Output (opt-in)

Instead of free-form text, the model is prompted to respond in JSON format with `answer`, `reasoning`, and `confidence` (0.0–1.0) fields. This enables reasoning quality analysis, confidence calibration studies, and more deterministic evaluation. When Layer 3 is active, its structured response is used as the input for Layer 1 scoring.

---

## Architecture

### Module Overview

```
tom-benchmark/
├── tom_benchmark/
│   ├── __init__.py          # Package version (1.0.0)
│   ├── models.py            # Pydantic data models (Scenario, TestResult, BenchmarkRun, etc.)
│   ├── loader.py            # Scenario loading from JSON with category/tier filtering
│   ├── scorer.py            # Layer 1: regex-based answer extraction & string matching
│   ├── judge.py             # Layer 2: LLM-as-Judge evaluation with rubric grading
│   ├── structured.py        # Layer 3: structured JSON output prompting & parsing
│   ├── runner.py            # Benchmark orchestration engine (BenchmarkRunner)
│   ├── exporter.py          # Dataset export (JSONL, CSV, HuggingFace)
│   ├── cli.py               # Click-based CLI with 5 commands
│   ├── scenarios/           # 6 JSON files containing the bundled scenarios
│   │   ├── false_belief.json
│   │   ├── indirect_request.json
│   │   ├── knowledge_attr.json
│   │   ├── deception.json
│   │   ├── emotional_inference.json
│   │   └── higher_order_beliefs.json
│   └── adapters/            # Pluggable LLM provider adapters
│       ├── __init__.py      # Factory function (get_adapter) & model registry
│       ├── base.py          # Abstract base class (LLMAdapter) & LLMResponse dataclass
│       ├── claude.py        # Anthropic Claude adapter (lazy client initialization)
│       └── openai.py        # OpenAI GPT adapter (lazy client initialization)
├── tests/                   # pytest suite
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_loader.py
│   ├── test_scorer.py
│   ├── test_judge.py
│   ├── test_structured.py
│   ├── test_runner.py
│   ├── test_adapters.py
│   ├── test_cli.py
│   └── test_scenario_schema.py
├── app.py                   # Streamlit dashboard (interactive web UI)
└── pyproject.toml           # Build configuration & dependencies
```

### Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  Scenarios   │────▶│   Loader     │────▶│   BenchmarkRunner    │
│  (JSON)      │     │  (loader.py) │     │   (runner.py)        │
└──────────────┘     └──────────────┘     │                      │
                                          │  ┌────────────────┐  │
                                          │  │ LLM Adapter    │  │
                     ┌──────────────┐     │  │ (Claude/OpenAI)│  │
                     │   Scorer     │◀───▶│  └────────────────┘  │
                     │  (scorer.py) │     │                      │
                     └──────────────┘     │  ┌────────────────┐  │
                                          │  │ JudgeScorer    │  │
                     ┌──────────────┐     │  │ (judge.py)     │  │
                     │  Structured  │◀───▶│  └────────────────┘  │
                     │(structured.py)│    │                      │
                     └──────────────┘     └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │   TestResult /       │
                                          │   BenchmarkRun       │
                                          │   (models.py)        │
                                          └──────────┬───────────┘
                                                     │
                                          ┌──────────▼───────────┐
                                          │  CLI Output / JSON   │
                                          │  Exporter / Dashboard│
                                          └──────────────────────┘
```

### Key Data Models (Pydantic)

| Model | Purpose |
|---|---|
| `Scenario` | A single ToM test: id, category, name, scenario text, question, expected answer, aliases, rubric, explanation, tier, complexity metadata |
| `TestResult` | Result of running one scenario: response, extracted answer, correctness, timing, optional Layer 2/3 results |
| `BenchmarkRun` | Aggregated run: model name, timestamp, list of TestResults, with computed accuracy properties |
| `Layer2Result` | LLM judge output: score (0–1), verdict, rationale |
| `Layer3Result` | Structured model output: answer, reasoning, confidence (0–1) |

### Adapter System

The adapter layer uses the **Strategy pattern** to abstract LLM provider differences behind a unified interface:

- **`LLMAdapter`** (abstract base): defines `query(prompt, system_prompt?) → LLMResponse` and `is_available() → bool`
- **`ClaudeAdapter`**: wraps the Anthropic Python SDK with lazy client initialization
- **`OpenAIAdapter`**: wraps the OpenAI Python SDK with lazy client initialization
- **`get_adapter(model_name)`**: factory function that routes model names to the correct adapter

Both adapters use lazy initialization — API clients are only created when first needed, avoiding import errors if API keys aren't set for unused providers.

**Supported models:**

| Provider | Models |
|---|---|
| Anthropic | claude-sonnet-4-6, claude-3-5-sonnet-20241022, claude-haiku-4-5-20251001 |
| OpenAI | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |

Adding a new provider requires implementing the `LLMAdapter` interface and registering it in `adapters/__init__.py`.

---

## CLI Reference

The CLI is built with [Click](https://click.palletsprojects.com/) and exposes 5 commands:

### `tom-benchmark list-categories`

Lists all 6 ToM categories with their scenario counts.

### `tom-benchmark list-scenarios`

Lists individual scenarios with optional filtering.

| Flag | Description |
|---|---|
| `--category` | Filter by category (e.g., `false_belief`, `deception`) |
| `--tier` | Filter by difficulty tier (e.g., `easy`, `expert`) |

### `tom-benchmark run`

Runs the benchmark against one or more models.

| Flag | Description |
|---|---|
| `--models` | Model name(s) to evaluate (repeatable) |
| `--category` | Filter scenarios by category |
| `--tier` | Filter scenarios by difficulty tier |
| `--output` | Save results to JSON file |
| `--judge` | Enable Layer 2 with specified judge model |
| `--judge-always` | Run judge on all responses, not just ambiguous ones |
| `--judge-categories` | Only judge these categories (repeatable); default all |
| `--structured` | Enable Layer 3 structured output |
| `--limit` | Run at most N scenarios (useful for smoke tests) |
| `--workers` | Run scenarios in parallel with N threads (default 1) |

### `tom-benchmark results`

Displays results from a previous run file.

| Flag | Description |
|---|---|
| `--format` | Output format: `table` (default) or `json` |

### `tom-benchmark export`

Exports the scenario dataset to various formats.

| Flag | Description |
|---|---|
| `--format` | Export format: `jsonl`, `csv`, or `huggingface` |
| `--output` | Output file or directory path |
| `--category` | Filter by category |
| `--tier` | Filter by tier |

---

## Streamlit Dashboard

An interactive web dashboard (`app.py`) provides a visual interface for running benchmarks and analyzing results. It is styled with [Material Design 3](https://m3.material.io/) — Roboto typography, the M3 color system (primary/secondary/tertiary containers), elevated surface cards, pill-shaped filled buttons, Material tabs with bottom indicators, Material chips for difficulty/category badges, banner-style alerts, and Material Symbols icons. The styling is injected via CSS on top of native Streamlit widgets, so no extra component library is required. Install the dashboard dependencies and launch:

```bash
pip install -e ".[dashboard]"
streamlit run app.py
```

The dashboard has four tabs:

#### Browse Scenarios

Filter and inspect every scenario in the dataset — scenario text, question, expected answer, aliases, rubric, and the reasoning behind the answer. Works without any API keys.

![Browse Scenarios tab](docs/screenshots/01-browse.png)

#### Run Benchmark

Pick the model(s) to evaluate, optionally narrow by category or tier, and choose whether to enable Layer 2 (LLM-as-Judge) and Layer 3 (structured output). Progress streams live as scenarios run.

![Run Benchmark tab](docs/screenshots/02-run.png)

#### Results

Browse past runs, see overall accuracy, per-category accuracy as a Plotly chart, and drill into individual scenario responses.

![Results tab](docs/screenshots/03-results.png)

#### Compare Models

Side-by-side accuracy by category across multiple saved runs. Useful for tracking regressions across model versions.

![Compare Models tab](docs/screenshots/04-compare.png)

The sidebar shows API key status (Anthropic/OpenAI), accepts session-only key inputs, and shows the live dataset counts. The Browse Scenarios tab works without any API keys, so the app stays useful as a read-only dataset viewer for visitors who don't bring credentials.

---

## Deploying the Web App

`app.py` is designed to deploy as-is to any Streamlit-friendly host. The sidebar accepts session-only API keys, so you can ship a public demo without exposing your own credentials — visitors paste their own keys to run benchmarks, and anyone can use the Browse Scenarios tab without keys.

### Streamlit Community Cloud (recommended, free)

1. Push this repo to GitHub (already done if you cloned this from a fork).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app** → pick `tom-benchmark` → set the main file to `app.py` → deploy.

Streamlit Cloud reads `requirements.txt` automatically. No secrets are required for a BYO-key demo.

### Hugging Face Spaces (free)

Create a new Space, choose the **Docker** SDK, point it at this repo. The included `Dockerfile` + `app.py` are all you need. Optionally add `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` as Space secrets if you want a key pre-loaded.

### Fly.io (paid; container, very flexible)

```bash
brew install flyctl
fly auth signup        # or `fly auth login`
fly launch --copy-config --no-deploy --name <your-app-name>
fly deploy
```

The included `Dockerfile` and `fly.toml` configure a small shared-CPU instance that scales to zero when idle.

### Anywhere with Docker (Render, Railway, Cloud Run, your own box)

```bash
docker build -t tom-benchmark .
docker run -p 8501:8501 tom-benchmark
```

The container honors `$PORT`, so it works on any platform that injects one.

---

## API Keys

Set your API keys in a `.env` file in the project root or as environment variables:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Only the keys for providers you intend to use are required. The adapters check for key availability and will report an error if a key is missing when a model is requested.

---

## Scenario Schema

Each scenario JSON file contains a `scenarios` array. Individual scenarios follow this schema:

```json
{
  "id": "fb_001",
  "category": "false_belief",
  "name": "Sally-Anne Classic",
  "tier": "easy",
  "complexity": {
    "belief_depth": 1,
    "num_agents": 2,
    "information_gap_type": "absence"
  },
  "scenario": "Sally puts her marble in the basket. She leaves the room. While Sally is away, Anne moves the marble from the basket to the box. Sally returns to the room.",
  "question": "Where will Sally look for her marble first?",
  "expected_answer": "basket",
  "answer_aliases": ["the basket", "in the basket"],
  "rubric": "A correct answer must indicate Sally will look in the basket, where she originally placed the marble, because she did not witness Anne moving it.",
  "explanation": "Sally did not see Anne move the marble. She still believes it is in the basket, so she will look there first."
}
```

**Complexity metadata** varies by category and may include:

- `belief_depth` — order of belief reasoning (1 = first-order, up to 5)
- `num_agents` — number of agents involved in the scenario
- `information_gap_type` — how the information asymmetry is created (`absence`, `deception`, `false_information`)

---

## Export Formats

The `export` command supports three output formats for research use:

| Format | Description |
|---|---|
| **JSONL** | One JSON object per line — compatible with most ML training pipelines |
| **CSV** | Flat tabular format with nested fields JSON-serialized — for spreadsheet analysis |
| **HuggingFace** | Directory with JSONL data file and `dataset_info.json` metadata — ready for `datasets.load_dataset()` |

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run the full test suite
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=tom_benchmark

# Build distribution
python -m build
```

The test suite covers:

- **Schema validation** for every bundled scenario (`test_scenario_schema.py`)
- **Pydantic model** creation and computed properties (`test_models.py`)
- **Scenario loading** and category filtering (`test_loader.py`)
- **String-match scoring** including negation detection and edge cases (`test_scorer.py`)
- **LLM-as-Judge** prompt construction and JSON parsing (`test_judge.py`)
- **Structured output** parsing and confidence clamping (`test_structured.py`)
- **Benchmark runner** orchestration and multi-layer integration (`test_runner.py`)
- **Adapter** interface compliance and factory routing (`test_adapters.py`)
- **CLI** command invocation and output formatting (`test_cli.py`)

---

## Research Background

This benchmark builds on research in Theory of Mind evaluation for AI systems, including:

- **Sally-Anne false belief tests** from developmental psychology (Baron-Cohen, Leslie & Frith, 1985)
- **Pragmatic inference** and indirect speech act studies (Grice, Searle)
- **LLM ToM benchmarks**: ToMBench, BigToM, Hi-ToM, FANToM, and OpenToM
- **LLM-as-Judge evaluation**: using language models as scalable, rubric-grounded evaluators

Scenarios are hand-crafted (not template-generated) to cover realistic social reasoning situations with carefully controlled complexity variables.

---

## License

MIT
