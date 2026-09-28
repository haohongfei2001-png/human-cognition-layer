# Canonical HCL Status

## Current phase

**LONG-HORIZON CAPABILITY GROWTH — WAVE A / A01 CORRECTNESS_VERIFIED / NEXT_READY=A02**

The long-horizon architecture and 41-package roadmap are canonical in
[HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md](HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md).
The live queue is [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md). Remote `main`,
exact-SHA CI and immutable receipts remain the implementation/evidence facts.

## Current wave

**Wave A — Unified Core and Ordinary Input**

A00 is complete through adoption of the canonical master plan and live-policy
migration. It changes development governance only; it does not modify HCL runtime
code or upgrade any historical evidence.

**NEXT_READY: `A02_UNIFIED_ORDINARY_SEMANTIC_PREPARATION`**

A01 now provides shared versioned evidence, scoped source reports and
interpretations, alternative support sets and rooted invalidation. A source
correction changes Alice's actual retained belief/concept comparison while Bob's
independent result remains identical without reexecution. See
[implementation/witness](docs/HCL_WAVE_A01.md) and the executable
[construction registry](hcl/cognition/registry.py).

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.
The entry still uses the bounded v1 grammar; broader semantic entry is A02.
No provider has been called for A01. Historical efficacy dispositions are unchanged.

## Canonical development policy

Current ordering remains:

> **real capability growth > validation > leaderboard**

During Waves A–H, every package requires unit correctness, negative-inference
tests, composition, ordinary-input smoke and historical regression. Passing these
checks means the package may be used by dependent architecture work. It is **not**
an efficacy proof.

The following former blockers are superseded:

- immediate provider-backed C/P/G/H/H-new after every capability;
- immediate independent benchmark search after every capability;
- a maximum of two correctly integrated but efficacy-untested capabilities;
- external validation blocking otherwise dependency-safe capability growth.

Every work package must show a **positive CAPABILITY_DELTA** in addition to
preventing unsupported inference.

Forty-one work packages are not forty-one required PRs. Work merges coherent
stable slices and must not create filler PRs to consume time. Ordinary bugs, CI,
tests and merge conflicts are manager-owned engineering work.

## Current evidence dispositions — preserved exactly in class

| Asset | Current disposition |
|---|---|
| v0.4/v0.5 | foundation correctness / provenance / stance and revision history |
| v0.6 | **bounded RETAIN** for perspective/belief under limited historical evidence |
| CG01 | **SIMPLIFY / CLOSED** ordinary route; typed checker utility inconclusive |
| CG02 | **INCONCLUSIVE / CLOSED** |
| CG03 | **RETAIN_DEVELOPMENT_ONLY / CLOSED** |
| CG04 | **RETAIN_DEVELOPMENT_ONLY / CLOSED** |
| CG05 | **RETAIN_DEVELOPMENT_ONLY / CLOSED** |
| NI10–14 | **provider-free correctness-only integration; external utility unproven** |
| v0.7/v0.8 | optional simplified intention/goal and affect/appraisal evidence structures |
| v0.9/v0.10 + formal tools | conditional generic exact tools |
| LongMemEval | **SEALED / DEPRIORITIZED** |

No development evidence is reclassified as independent/fresh evidence. Historical
negative, inconclusive, simplified and consumed results remain intact.

## POST-CG05 / EG01-A disposition under the new plan

PR #160's POST-CG05 review and zero-provider DREAM native-readiness result remain
valid historical/current diagnostics. They are not rerun and not erased.

The old EG01-A is split by purpose:

- generic native-task/source actor/time/access semantic preparation is absorbed
  into **Wave A, especially A02–A05**;
- independent source qualification, efficacy package freeze and provider-backed
  comparison are deferred to **post-G-ARCH Serious Independent Evaluation**.

Therefore **EG01-A is no longer the unique next task**.

## Early live-adapter exception

One small live adapter smoke may be designed after the ordinary semantic entry
path forms during Waves A–C. Its only purpose is to verify that real provider
input reaches the real mechanism with valid source binding.

It is not efficacy ranking, is not repeated every wave and cannot be labeled
independent utility evidence.

The owner has separately granted default autonomy for necessary, bounded, normal-cost
provider work using existing provider/API/credential/billing infrastructure.
A00 itself granted none. A–C live-entry calls remain limited to concrete engineering
questions; historical consumed grants remain closed and cannot transfer budget.

## Maturity gates

**G-HC** gates entry into Hard Human Cognition Integration.

**G-ARCH** is the mandatory post-H05 gear shift. Once G-ARCH passes, architecture
building cannot continue indefinitely because another module could be imagined.
The main line must switch to Serious Independent Evaluation.

Required post-G-ARCH order:

```text
independent generalization
→ strong-base / P / G / H comparison
→ mechanism and integration attribution
→ cross-model transfer
→ optimization
→ Authoritative Leaderboard Target Audit
→ final leaderboard push
```

Leaderboard selection is not active now.

## Engineering / authorization state

- Runtime code changed by A00: **NO**
- Provider calls authorized by A00: **0**
- Provider spend authorized by A00: **USD 0**
- New credential/account/training authorization: **NO**
- LongMemEval: **SEALED / NOT ACCESSED**
- Benchmark-specific logic authorized: **NO**
- Leaderboard search/optimization: **OFF**
- Current owner-only blocker: **NONE for A02 implementation**

## Historical state and recovery

Existing reports, raw receipts, paid-run closures, frozen packages and git history
remain the authoritative record of historical experiments. The long-horizon policy
supersedes their old execution cadence, not their results.

Before each coherent slice Work must re-read remote `main`, this status and
`DEVELOPMENT_PLAN.md`, use one active writer for the shared runtime boundary,
repair ordinary engineering failures without owner interruption, and advance to
the next dependency-safe package when the current package's engineering exit is
truthfully satisfied.

## Execution verification

A01 is verified by unit/negative-inference/composition/ordinary-input/historical
checks in the existing exact-SHA v1 workflow. Its artifact includes an executable
positive witness and actual prepared final inputs. Merge only after exact-head
CI; continue A02 only after exact-main CI. GitHub run SHAs, rather than a
self-referential commit hash in this file, identify those receipts.
