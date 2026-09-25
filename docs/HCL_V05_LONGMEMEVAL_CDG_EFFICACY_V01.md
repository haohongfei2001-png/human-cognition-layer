# HCL v0.5 LongMemEval knowledge-update paired C/D/G efficacy contract v0.1

Status: **DESIGN FROZEN / PROVIDER-FREE IMPLEMENTATION AND CERTIFICATION NEXT / SEALED ROWS UNCONSUMED**

## Research question and claim boundary

On the sealed 32-row LongMemEval cleaned-S knowledge-update selection, does canonical v0.5 state improve answer quality or practical state-maintenance efficiency relative to the same base model with equal external evidence (C) and a competent generic structured memory (G)?

This is an **oracle-evidence-assisted state-augmentation** experiment. It does not measure end-to-end retrieval, general human cognition, or cross-model transfer by itself. An honest negative or null outcome is a valid result. The 2 development rows in the ingest diagnostic are consumed and excluded.

## Immutable sources and selection

- HCL state/adapter anchor: main `1d09c102d248a693f0cb895b4347251009554ecb`; do not alter `hcl/v05/**`, its semantic prompts, or the EQ-02 state adapter for this experiment.
- Selection: `eval/longmemeval/knowledge_update_selection_v01.json`, 32 IDs, including 2 `_abs` IDs. No substitution, outcome-based exclusion, or post-run threshold change.
- Official benchmark code: `xiaowu0162/LongMemEval@9e0b455f4ef0e2ab8f2e582289761153549043fc`.
- Official judge file: `src/evaluation/evaluate_qa.py`, Git blob `4732f3772b04a2b9069121ade304e6320494abc2`.
- Cleaned-S dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`; file SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
- For every selected ID, verify the EQ-02 manifest history hash before any state construction. Reject duplicate/missing IDs and any data digest mismatch.

## Ordered execution and firewall

1. Load only the 32 selected IDs and validate the dataset and per-row history digests. The runner may hold reference metadata in a separate scoring object, but no state-arm process receives it.
2. Build the EQ-02 `state_input_view` for each row using session ID, timestamp, role, and raw turn content. Order sessions by timestamp, with original position as the stable tie-break. Skip blank turns by the frozen adapter rule.
3. Complete D and G state ingestion for the entire history **before** releasing the question or oracle evidence to any answer process. C does not construct state.
4. Only after the ingestion barrier, construct one immutable answer packet per row: question plus the same oracle evidence sessions for C, D, and G. Derive oracle session IDs from the cleaned-S `answer_session_ids` annotation at this stage only. Include both user and assistant turns, timestamp and session ID, in stable chronological order. If an abstention row has no oracle sessions, all arms receive the same empty evidence packet. Never use answer text to choose evidence.
5. Generate one raw answer per arm from the same base model family, model ID, temperature, max output budget, and answer instruction. C sees question + equal oracle packet. D and G see that exact packet plus their respective frozen derived state. No arm sees reference answer, `has_answer`, or judge output. Use identical question and packet hashes across arms.
6. Freeze all raw answers and evidence hashes before any judge call. Only then permit the scoring process to see reference question/answer and the answers. Judge feedback cannot flow into ingestion, prompting, retrieval, compaction, retries, or arm ordering.
7. Persist immutable artifacts: dataset/selection/source digests; full run config; per-arm answer packets and raw answers in a restricted artifact; redacted public aggregate and per-ID outcomes; ingestion/repair/failure telemetry; provider calls, input/output chars and tokens when available, latency and cost when available. Do not commit raw benchmark histories, questions, answers, or owner-private examples to the public repository.

The `_abs` rows use the official abstention branch of the judge. They remain in the paired 32-row denominator and are also reported separately.

## Equal evidence and cost scope

Oracle evidence is a controlled answer-time intervention, identical across all three arms. It is derived from benchmark labels only after state ingestion. This creates a conditional comparison: D or G can contribute state built from full history while all arms receive the same sufficient external answer evidence. State construction calls and answer calls count toward each arm's provider cost. Judge calls are reported separately and excluded from arm cost ratios. Any provider-side context truncation must be identical across arms or the run fails fairness certification. If the full oracle packet cannot fit the common context window, stop before consuming that row; never truncate one arm differently.

No extra question-aware retrieval or hand-picked evidence is allowed. Do not report these scores as official end-to-end LongMemEval retrieval results.

## Arms

### C — equal-evidence control

No persistent derived state. The answer model sees the immutable oracle packet and question.

### D — canonical HCL v0.5

Use the current routed semantic extractor, deterministic subject/exposure routing, issue-centered stance projector, and persistent store exactly as frozen at the anchor. No seeded ontology from questions/gold and no benchmark-specific rule. The answer prompt can serialize only the current canonical state and provenance already available from the runtime; its format and character budget must be frozen in provider-free tests. Missing or sparse stance state is shown as such, never filled from gold.

### G — competent generic structured memory

Use a generic entity/attribute/value record with timestamp, source role, confidence/uncertainty, and short provenance. The model may update its generic records from each raw event. It does not receive HCL's AFFIRM/DENY/REVISION_EXPOSURE/UNRESOLVED types, issue-centered transition algorithm, or deterministic perspective-routing code.

G receives the same history turns and chronology as D. Deterministic code validates schema, orders records, enforces a fixed state budget, and compacts oldest detail before each update. Compaction always preserves each entity/attribute's current value, timestamp, and source reference; it may discard older explanatory notes under the frozen policy. The incoming event must be processed and recorded as successful or as an explicit terminal failure. A state over budget after bounded repair must trigger deterministic compaction and revalidation; ordinary size pressure cannot silently drop an event. No outcome-based repair or change to the budget is permitted. Preflight must demonstrate this invariant with provider-free unrelated stress fixtures. G state and update prompt must be frozen before sealed rows are opened for provider execution.

C/D/G have the same answer-context budget for the common packet; additional D/G state is separately bounded and measured. Provider-free tests must verify that G is not weakened by the avoidable 6000-character rejection seen in the internal replication.

## Official scoring and uncertainty

Use the official `get_anscheck_prompt` from the pinned judge file, including its knowledge-update and abstention branches. Primary judge model: `gpt-4o-2024-08-06`, as mapped by that pinned file; temperature 0, `n=1`, `max_tokens=10`. Preserve the exact judge prompt and raw response for every arm/row. Use the official Boolean parser (`'yes' in response.lower()`) for the primary published-equivalent score and flag malformed or ambiguous judge responses separately. Do not change model ID silently if unavailable: stop and freeze an explicit amendment **before** any sealed answer is scored.

Report all 32 paired C/D/G labels, D-only/G-only and D-only/C-only counts, abstention/non-abstention subtotals, and every discordant raw response. Compute an exact two-sided McNemar p-value for D versus G and a paired bootstrap 95% interval for D-G accuracy difference with a fixed seed specified in the implementation before provider use. These are descriptive with n=32 and an LLM judge; they do not replace semantic review. Independently inspect discordant cases and judge anomalies after freezing results, without changing the primary raw score. Judge variance is a limitation even at temperature 0.

A specialized capability signal requires D-G >= 5/32, exact McNemar p <= 0.05, no severe D semantic failure, and no avoidable G update loss. Otherwise report a descriptive positive, null, or negative result without calling capability superiority established. Practical module utility requires D score >= G score - 1, no severe D state error, D total provider character volume <= 60% of G, and D provider wall time <= 60% of G. If neither route passes, report no established external incremental utility. If G outperforms D by >= 5/32, treat it as evidence against current HCL on this slice. C remains a meaningful secondary comparator; D beating G while losing to C cannot support an answer-quality improvement claim.

## Provider and one-shot gates

Before the sealed provider run:

- all provider-free adapter, selection, fairness, firewall, G budget, prompt-shape, and artifact-redaction tests pass at one exact head;
- the full candidate, prompts, budgets, model IDs, judge implementation, statistical code, and source digests are frozen;
- a second independent base-model-family endpoint, credential and request profile pass provider-free request-shape checks; cross-model transfer uses a separate frozen run, never compares raw scores across families;
- existing DeepSeek and judge access plus a bounded cost estimate are verified. New account, credential or paid commitment requires owner decision;
- one-shot trigger is bound to exact certified main; reruns are rejected.

No sealed efficacy row has yet been provider-backed consumed. A run that fails midway marks attempted rows consumed. Preserve the partial evidence, diagnose the cause, and do not rerun those rows as fresh. If mechanism or protocol changes after exposure, a new disjoint selection is required.

**Gate: HCL_V05_LONGMEMEVAL_CDG_EFFICACY_V01_DESIGN_FROZEN_PROVIDER_FREE_IMPLEMENTATION_NEXT**
