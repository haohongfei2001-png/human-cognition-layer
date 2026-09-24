# HCL v0.4 Long-Horizon Bounded-Context v0.1 — Execution Closure

Verdict: **EXECUTION FAILED / NO CAPABILITY VERDICT / V0.1 CONSUMED / NO RERUN**

## Frozen execution

- Trigger/main commit: `0f430da6dea90508b9a324b71bd43e8793a71182`
- Frozen candidate anchor: `ff69ff260e214fdeb1a470f003c1c6068418786b`
- Workflow run: `35980385848`
- Job: `107570605207`
- Model: `deepseek-flash`
- Fixture SHA-256:
  `a79b675cf484292a07916141d54d3022862c39851a3fc4b91c73cb13f1a75cfe`
- Gold SHA-256:
  `376fb695eada3b52f7e8fadd395be479f9cbbf47c944c9d3b0c4a56d5f90c988`

Before any provider call, the run passed:

- immutable one-shot trigger guard;
- frozen candidate diff check;
- fixture/gold digest checks;
- validate-only fixture/gold separation;
- eight provider-free fairness/evidence guards.

The run was not manually rerun.

## What was consumed

Provider execution began and ran for roughly 81 seconds before the process
failed.

The runner order is fixed per stream:

```text
C full-history diagnostic
→ D persistent HCL
→ E ordinary persistent memory
→ next stream
```

The traceback occurred inside D on stream s1. Therefore the following can be
established from control flow without guessing:

- all six C queries for s1 completed provider calls;
- D then began ingesting s1 and consumed provider calls for a prefix of its event
  stream;
- E had not begun s1;
- s2 and s3 had not begun.

The exact failing D event cannot be recovered from the workflow evidence because
the runner did not emit per-event progress and the final result artifact had not
yet been written. The artifact upload found no files.

Do not infer a more precise consumption boundary from elapsed time.

For research hygiene, the **entire v0.1 frozen fixture is retired as fresh
evidence**. It must not be rerun after a mechanism repair and presented as an
independent capability result.

## Failure mechanism

The execution did not reach scoring. There is no C/D/E capability verdict.

The failure was:

```text
SchemaValidationError:
BELIEF_ESTIMATE support_level must support the stated belief stance;
use LATENT_HYPOTHESIS for unresolved/counterevidence-only state
```

Call path:

```text
run_d_stream
→ HCLV04Runtime.ingest_event
→ propose_patch
→ patch_from_mapping
→ validate_patch_structure
→ validate_assertion
```

The semantic backend emitted a schema-invalid `BELIEF_ESTIMATE` whose
`support_level` was `COUNTEREVIDENCE` or `INSUFFICIENT`. The bounded
semantic repair call returned a proposal that still violated that rule.

This exposed a runtime boundary defect: schema-invalid cognition generated
inside `propose_patch` could exhaust its one model repair and raise before the
store-level invariant-repair path in `ingest_event` had a valid
`SemanticPatch` to work with.

This is an execution/reliability defect. It is not evidence that HCL improved or
worsened the long-horizon task.

## Repair doctrine

The repair must be mechanism-level and provider-free on v0.1 evidence.

Required behavior:

1. make the BELIEF_ESTIMATE support rule explicit in the semantic repair
   contract;
2. preserve the existing one-model-repair bound;
3. if the repaired output still contains a locally invalid BELIEF_ESTIMATE,
   fail closed by dropping that unsupported belief assertion rather than
   inventing a stance, silently converting counterevidence into belief, or
   crashing the whole event ingestion;
4. preserve raw evidence and any other legal semantic records;
5. expose the semantic repair count/reason in `IngestResult`;
6. retain strict failure for unrelated schema corruption rather than turning
   the runtime into a permissive parser.

The consumed v0.1 rows must not be used to tune a new answer rule.

## Next research boundary

After the general repair passes deterministic regression and exact-main CI:

- do not rerun v0.1;
- if long-horizon evaluation is still justified, freeze a new independently
  generated v0.2 fixture/gold package;
- preserve the same D/E fairness principle and diagnostic evidence capture;
- run v0.2 only once after its own preflight and gold audit.

No external benchmark, owner-private material, cross-model run, training, or
leaderboard action is authorized by this closure.
