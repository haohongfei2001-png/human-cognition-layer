# HCL v0.5 EQ-01 — MemoryAgentBench FactConsolidation Qualification Closure

Verdict: **COMPLETE / PURE-ADAPTER QUALIFICATION FAILED / NO PROVIDER RUN**

## Scope

EQ-01 asked whether MemoryAgentBench FactConsolidation could serve as the first
external v0.5 mechanism evaluation without changing HCL cognition semantics,
using benchmark-independent structure and no gold-derived adapter logic.

Upstream examined:
- repository: `HUST-AI-HYZ/MemoryAgentBench`
- pinned main:
  `fe1735de8cf8b9908e1e3d3b5612afc815698062`
- repository license: MIT
- official task family: Conflict Resolution
- official subdatasets: `factconsolidation_sh_*`, `factconsolidation_mh_*`
- official metric: substring exact match

No provider/model call was made and no scored row was consumed.

## Finding

FactConsolidation is a valid external conflict-resolution benchmark, but its
released task interface does not expose the fact identity/supersession relation
needed by current HCL v0.5 as benchmark-independent structured metadata.

The public dataset/harness presents:
- long natural-language `context`;
- questions / answers;
- generic question/session metadata;
- a task instruction that newer serial-numbered facts supersede older ones.

The benchmark's own ecosystem contains a stronger write-time conflict baseline
(Knowl) that explicitly derives **subject + relation** identity before retiring
older facts with the same identity.

That identity layer is not part of current HCL v0.5.

Current v0.5 models:
- explicit self stance;
- explicit revision relation;
- deterministic recipient/observer exposure;
- issue-centered current stance.

It does not contain a generic factual subject/relation parser or general
knowledge-base supersession layer.

## Why EQ-01 fails

A provider-backed HCL run on FactConsolidation would require at least one of:

1. add a generic subject/relation fact-identity extractor;
2. derive issue identity from benchmark questions/answers;
3. add FactConsolidation-specific serial-number rules into the HCL adapter.

All three change the object being evaluated or risk benchmark-specific leakage.

Therefore FactConsolidation is not a valid **pure adapter** test of the current
v0.5 mechanism.

This is not a judgment that FactConsolidation is a poor benchmark. It is a
boundary result: it tests generic knowledge consolidation, whereas current v0.5
is a narrower human-stance/update layer.

## Disposition

- no provider execution;
- no selected external row consumed;
- no HCL mechanism change;
- do not build a benchmark-specific fact parser merely to obtain a score;
- retain FactConsolidation as a possible future benchmark if HCL independently
  grows a general proposition/fact identity layer for reasons outside this
  benchmark.

## Next

Move to EQ-02:
**LongMemEval knowledge-update zero-provider qualification**.

LongMemEval is a better current candidate because the task is built from
timestamped user/assistant sessions with old and new evidence sessions, allowing
the adapter to preserve externally supplied temporal/session structure without
inventing a benchmark-specific fact graph.

**Gate: HCL_V05_EQ01_COMPLETE_NOT_ADAPTABLE_EQ02_LONGMEMEVAL_NEXT**
