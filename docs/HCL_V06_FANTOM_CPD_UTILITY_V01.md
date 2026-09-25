# HCL v0.6 FANToM C/P/D Development Utility Check v0.1

Status: **DESIGN FROZEN / PROVIDER-FREE PREFLIGHT NEXT / OWNER AUTHORIZED BOUNDED DEVELOPMENT RUN**

## Purpose

This is the first small external utility check after the actual v0.6 capability
implementation.

It asks one narrow question:

> On previously unconsumed FANToM information-asymmetry conversations, does the
> minimal v0.6 perspective runtime add useful accuracy beyond both a strong
> direct model and a thin perspective scaffold?

This is a **development utility check**, not a fresh efficacy claim and not a
leaderboard submission.

## Frozen evidence

Source:
- repository: `skywalker023/fantom`
- commit: `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

CQ-00 already froze eight complete, historically disjoint development
conversations:
`119, 197, 240, 7, 220, 189, 208, 36`.

All historical FANToM v0.1/v0.2 conversations remain excluded.

Before any provider call, provider-free code deterministically freezes exactly
one perspective-relevant question per conversation using:
- the CQ-00 capability stratum;
- a fixed SHA-256 selection salt;
- no model outcome.

For binary information/answerability strata, the selected question must be a
real inaccessible `no` case, not a `no:long` outsider.

Question text and gold text are not committed to the public repository.

## Base model

All answer arms and the D conversation-access adapter use:
- provider: DeepSeek API
- model name: `deepseek-flash`
- provider profile: `deepseek_flash`
- temperature: 0
- DeepSeek thinking: disabled by the existing provider profile.

As of 2026-09-25, the official DeepSeek API maps `deepseek-flash` to
DeepSeek-V4.1-Flash.

This pilot intentionally uses one model family. Cross-model transfer remains a
later question.

## Arms

### C — strong direct control

Input:
- official full conversation;
- exact selected benchmark task.

Instruction:
- answer directly;
- exact output format only.

### P — thin perspective scaffold

Input:
- same full conversation;
- same exact selected task;
- same answer model and output budget.

Additional instruction only:
- internally track who was present for each utterance;
- do not give missed content to absent/not-yet-joined participants;
- for second-order questions, track what the outer character can know about the
  inner character's access.

P has no persistent state and no explicit event graph.

### D — HCL v0.6 perspective runtime

Before the question is released, an access adapter sees only the full
conversation and deterministically parsed turn speaker/text pairs.

The adapter returns, for every turn, which *other named participants* could hear
that utterance. It is not shown:
- question text;
- answer options;
- gold answer;
- selected task family;
- benchmark outcome.

The adapter:
- may track only explicit leave/absence/rejoin/arrival evidence;
- may not invent participants;
- may not infer beliefs or benchmark answers;
- gets one bounded repair if its JSON/access map is structurally invalid.

The resulting immutable `EventRecord` sequence enters
`HCLV06Runtime.ingest_prestructured_event`.

D then constructs, before seeing the question:
- every character's first-order evidence-bounded view;
- the bounded pairwise second-order access matrix;
- any already available system-level belief estimates.

Only after that state is frozen is the selected task released to the D answer
model.

The D answer model does **not** receive the omniscient raw conversation as a
single shared transcript. It receives the separated HCL perspective state plus
the task.

## Budget

This run is deliberately small.

Operational hard caps:

| component | max calls | max input chars | max output chars |
|---|---:|---:|---:|
| C | 8 | 300,000 | 10,000 |
| P | 8 | 320,000 | 10,000 |
| D access adapter | 16 | 320,000 | 150,000 |
| D answer | 8 | 700,000 | 10,000 |

Maximum calls: **40**.

The repository records a conservative planning calculation using the official
DeepSeek Flash **peak** no-cache input rate of USD 0.30 / 1M tokens and output
rate of USD 1.20 / 1M tokens. For the hard character caps, treating one
character as one token gives a planning ceiling below **USD 1.00**.

This is deliberately conservative and is **not** a billing-token guarantee or
actual invoice. The run also records measured provider input/output characters
and wall time.

Owner instruction to continue this stage authorizes this bounded existing-
credential DeepSeek development run up to the frozen USD 1.00 planning cap.
It does not authorize new provider accounts, new credentials, LongMemEval, or
any broader paid experiment.

## One-shot / consumption rule

The provider-backed workflow:
- runs only on an exact-parent trigger-file commit;
- is first-attempt only;
- verifies the committed deterministic selection and pinned dataset digest;
- makes no provider call until provider-free tests/preflight pass.

When provider execution begins, all eight development conversations are
provider-consumed for HCL v0.6 development. They can never become fresh efficacy
evidence.

A partial run is preserved as partial consumed evidence. It is not silently
rerun as a fresh sample.

## Stored evidence

Workflow artifact may contain:
- selected IDs / set IDs;
- response strings and response hashes;
- normalized predictions and correctness;
- adapter event counts / repair counts;
- access-state hashes;
- provider call / character / wall-time metrics;
- aggregate C/P/D paired results.

Do not commit raw FANToM conversation/question/gold text to the public repo.

## Development interpretation

This n=8 run is directional.

A useful specialized-D signal requires at minimum:
- at least **2** P-wrong / D-correct conversations; and
- no more than **1** P-correct / D-wrong conversation; and
- manual audit confirms the D-only improvements come from a correct perspective
  boundary rather than parser/output-format luck.

If P matches or exceeds D without meaningful D-only saves, do not expand the
specialized perspective architecture. Prefer the simpler scaffold or revise the
runtime.

If D shows a useful signal, the next stage may add a competent generic
structured G and a fresh, larger efficacy design.

No result here proves broad Theory of Mind, psychology, literary, moral,
philosophical or general human-cognition superiority.

## LongMemEval

Unchanged:
- paid trigger absent;
- sealed 32 rows unconsumed;
- not a prerequisite for this run.

**Current gate: HCL_V06_FANTOM_CPD_V01_PROVIDER_FREE_PREFLIGHT_NEXT**
