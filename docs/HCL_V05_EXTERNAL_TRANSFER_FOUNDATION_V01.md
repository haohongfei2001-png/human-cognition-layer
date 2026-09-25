# HCL v0.5 External Validation & Cross-Model Transfer Foundation v0.1

Status: **DESIGN FROZEN / ZERO-PROVIDER QUALIFICATION NEXT**

## Purpose

HCL v0.5 has completed its planned internal synthetic capability loop.

The final fresh internal replication established:
- controlled internal practical module utility (Route B PASS);
- no clean specialized-capability superiority claim against a competent generic
  structured-state baseline.

The next phase therefore moves away from repository-authored synthetic efficacy
tests and toward:
1. independently authored external tasks; and
2. transfer across different base-model/provider families.

This phase must preserve the current v0.5 mechanism rather than modifying HCL
to fit a benchmark after inspecting benchmark errors.

## Current v0.5 claim boundary

The canonical v0.5 mechanism currently provides a narrow capability:

- event-local semantic extraction of explicit self stance;
- subject binding to the event actor;
- revision-relation extraction without model-selected exposure subject;
- deterministic exposure routing from explicit recipients/observers;
- issue-centered current stance with AFFIRM / DENY /
  REVISION_EXPOSURE / UNRESOLVED;
- historical current-stance reconstruction;
- persistent, invalidatable, auditable state.

It is **not** currently a general proposition knowledge graph, arbitrary
third-person mental-state parser, emotion/intention model, complete long-term
memory system, or general Theory-of-Mind solver.

External evaluation must test this mechanism as it exists. Benchmark adaptation
must not silently expand the semantic contract.

## Existing external exposure

The exposure register remains authoritative:
- `docs/HCL_V04_EVALUATION_EXPOSURE_REGISTER.md`.

Already consumed:
- CogToM: historically exposed;
- SOTOPIA-Hard: all environment templates exposed;
- FANToM v0.1: 32 conversations consumed;
- FANToM v0.2: 48 additional conversations consumed;
- Hi-ToM v0.1: 60 selected rows consumed.

The 80 consumed FANToM conversations and 60 Hi-ToM rows cannot become fresh
v0.5 evidence.

Historical FANToM/Hi-ToM runs used the older HCL v0.3 answer loop. They are
background evidence, not v0.5 external validation.

## Benchmark qualification

### 1. MemoryAgentBench / FactConsolidation — first qualification target

Pinned public harness:
- repository: `HUST-AI-HYZ/MemoryAgentBench`
- main snapshot:
  `fe1735de8cf8b9908e1e3d3b5612afc815698062`
- repository license: MIT

Relevant official task family:
- Conflict Resolution;
- `factconsolidation_sh_*`;
- `factconsolidation_mh_*`;
- official metric: substring exact match.

Why it is useful:
- independently authored;
- incremental multi-turn memory setting;
- explicitly tests conflicting/updating facts;
- deterministic automatic scoring avoids an LLM-judge confound;
- directly probes the state-consolidation mechanism implicated by v0.5.

Claim boundary:
- this is **external mechanism validation**, not proof of human cognition or
  Theory of Mind;
- generic facts must not be relabeled as human beliefs in research claims.

First work is **zero-provider qualification only**. No benchmark row is yet
authorized for provider-backed execution.

Qualification must determine whether the official data representation exposes a
stable fact identity/update relation that can be adapted without changing HCL
semantics. If the adapter would need benchmark-specific answer rules or
gold-derived issue identities, this target is rejected.

### 2. DynToM — human dynamic-mental-state candidate, not yet executable

Pinned public source:
- repository: `GAIR-NLP/DynToM`
- main snapshot:
  `9c95b1b8300f3e352626feae51aaeeda111b6d3d`

DynToM is unusually well aligned with the research objective because it evaluates
mental-state evolution across temporally connected social scenarios, including
belief transformation.

However, current v0.5 deliberately binds self stance to the event actor.
DynToM stories express mental states through third-person narrative. Treating a
narrator statement such as "A believes X" as if it were A's explicit
self-stance would loosen HCL's evidence semantics.

Therefore:
- do not execute DynToM as v0.5 efficacy evidence yet;
- do not modify v0.5 merely to make DynToM scoreable;
- a future narrator-supported mental-state evidence bridge requires a separate,
  benchmark-independent correctness hypothesis and contract before any DynToM
  provider run.

DynToM remains the leading candidate for later **human dynamic cognition**
validation after that semantic question is resolved.

### 3. FANToM — relevant but not first

Pinned historical upstream:
- `skywalker023/fantom@1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`

FANToM strongly tests information asymmetry, belief, answerability and
information access. It remains thematically relevant.

But:
- 80 conversations are already consumed;
- prior runs used v0.3;
- current v0.5 represents revision exposure/current stance, not a general
  information-access knowledge graph.

A new disjoint FANToM selection is therefore not the first v0.5 external run.

### 4. LongMemEval — practical-memory secondary candidate

Knowledge-update, preference and temporal-memory categories are relevant to the
practical module claim. A fair future comparison should keep retrieval evidence
equal between arms and test whether HCL state adds value.

Its common evaluation path uses an LLM judge, so it is less clean than
FactConsolidation for the first external mechanism test.

### 5. ToMATO / ToMBench / interactive social benchmarks

These cover broader mental states or social interaction than v0.5 currently
models. They are useful later for scope expansion or end-to-end behavior, but
must not drive benchmark-specific semantic accretion now.

## Cross-model transport prerequisite

The historical helper called an OpenAI-compatible transport while hard-coding
DeepSeek-specific capabilities. That is not valid cross-model transfer.

The external-transfer foundation introduces explicit provider profiles:

- `deepseek_flash`
  - preserves historical JSON request behavior;
  - seed enabled;
  - DeepSeek non-thinking extra body retained.
- `qwen_openai`
  - JSON-object mode declared;
  - no DeepSeek request body;
  - no assumed seed support.
- `generic_openai`
  - JSON-object mode declared;
  - no provider-specific extra body;
  - no assumed seed support.

Unknown profiles fail closed.

This refactor is transport-only:
- no v0.5 semantic prompt changes;
- no state-machine changes;
- no benchmark prompt changes;
- historical DeepSeek helper default remains `deepseek_flash`.

A provider/model may enter a paid transfer run only after a provider-free
request-shape smoke/contract demonstrates that its declared profile matches the
actual endpoint.

## Cross-model evidence design

The first valid transfer comparison must:
- use the exact same frozen HCL mechanism and adapter;
- compare direct/control and HCL treatment within each base model;
- never compare raw scores across different models as if model strength were an
  HCL effect;
- record paired improvement/worsening per model;
- use at least two base-model families before making a transfer claim;
- preserve provider/model/version/base URL identity;
- keep temperature/output limits aligned where the APIs permit;
- record unsupported transport features rather than emulating them silently.

DeepSeek may remain the continuity anchor.

A second independent family (Qwen is the first engineering candidate) is needed
before any cross-base transfer conclusion.

## External validation stop/tuning rule

Once provider-backed execution begins on a selected external unit:
- that unit is consumed;
- it cannot be tuned and rerun as fresh evidence;
- failures may motivate only abstract, benchmark-independent hypotheses;
- any mechanism change requires a new disjoint external selection.

External benchmark score is evidence, not the definition of correctness.

## Next authorized gate: EQ-01

**EQ-01 — MemoryAgentBench FactConsolidation zero-provider qualification**

Allowed:
- inspect official task schema, metadata, harness and scoring;
- pin exact upstream/harness and dataset revision/fingerprint;
- determine whether SH or MH is the clean first slice;
- define a deterministic, gold-blind selection;
- define control / HCL / competent generic-state arms;
- define state-budgeting that does not reproduce the avoidable G failure from
  the internal replication;
- write provider-free adapter/unit tests;
- validate that no gold answer or test outcome enters HCL state construction.

Not allowed yet:
- provider-backed benchmark execution;
- viewing model outcomes;
- tuning against selected external rows;
- changing v0.5 stance semantics to fit the benchmark;
- publication/leaderboard claims.

If EQ-01 proves that FactConsolidation cannot be adapted without changing the
current mechanism or using gold-derived structure, stop that target and move to
the next independently qualified external task.

**Gate: HCL_V05_EXTERNAL_TRANSFER_FOUNDATION_V01_FROZEN_EQ01_ZERO_PROVIDER_NEXT**
