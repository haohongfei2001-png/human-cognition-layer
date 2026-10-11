# S1.1 implementation and evidence boundary

This implements the approved first slice, not a replacement plan. The single plan
remains [hcl_design_manifest.json](hcl_design_manifest.json); S1.2 and S1.3 are
still required before S1's offline foundation is complete. All later stages,
mechanisms, domains and acceptance families retain their original requirements.

## Actual computation

`HCL.run`, `HCL.stream` and `HCL.run_sync` delegate to the same engine. The host
supplies the authenticated principal; a request cannot grant itself identity.
The store authorizes the session and every requested source before exposing an
immutable version-bound snapshot. The operator reads one explicit FormalProblem
from that snapshot and calls the existing `quantified_logic.check_countermodel`.
No natural-language translation is claimed for this typed formal fixture.

For premises `∀x(Fx→Gx)` and `Ga`, conclusion `Fa`, domain `[0]`, `a=0`, `G=[0]`:

- `F=[]` computes premise values `[true,true]`, conclusion `false`, and
  `is_countermodel=true`. The answer calls this supplied model a counterexample.
- `F=[0]` computes conclusion `true`, `is_countermodel=false`, and changes the
  answer. Absence of a counterexample in this interpretation never proves
  entailment or real-world/private-mental truth.
- Unrelated source additions preserve those values and the answer.

AnswerClaim records the actual conclusion/premise/counterexample fields and
assumption environment. Mechanical validation checks those exact values and the
bounded formal rendering. This is not certification of open semantic judgments.

A source-report light task goes through the same engine without fabricating
cognition operations. An explicitly requested offline model fixture also uses
the same engine and a no-network gateway. It is labelled unverified simulation.
The gateway accepts only its built-in offline port, has no provider imports or
credential loader, and cannot authorize paid work. Capabilities not implemented
are `None`/unknown, not invented provider guarantees.

## Safety, state and failure scope

Only the engine commits candidate inference deltas. This slice uses an in-memory
single-writer store, with source-version, rule-version and ACL-epoch checks. It
fails closed on revision conflicts; fine-grained rebasing, durable SQLite state,
shared persistent budget and crash/unknown-send recovery remain S1.2.

No unchecked answer text is streamed. Source instructions remain data. Bad
formal syntax, valid evaluation fuel exhaustion, missing evidence, budget
exhaustion, denied access, stale state and simulated unknown send have distinct
safe diagnostics. Invalid Unicode is rejected without rewriting source bytes.
If valid computation commits before a later output-size refusal, the refusal
reports the intermediate revision while withholding answer text. Denials never
export source/result metadata or other principals' call state.

Initial independent review found a denied-request call-state side channel and
invalid identifier/Unicode exception paths. Those failures were retained as
negative regression tests and fixed. Evaluation-fuel exhaustion was separated
from malformed formal input. This does not establish comprehensive safety for
unimplemented S2–S7 mechanisms.

## Reproduction

### Diagnostic identity migration regression

The exact-head v1 run at `12bf1a5bd47b8e45b4af8233346eed03dd72a928`
[failed at the original diagnostic preflight](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/38174369118)
with `CURRENT_RUNTIME_DRIFT`. This was the expected rejection of an October 8
whole-runtime identity by the new tree, not permission to rebase old pins. A
local subsequent diagnostic check also reproduced two live-package identity
failures (`FINAL_DIAGNOSTIC_CONFIGURATION_OR_RUNTIME_DRIFT` and the original
runtime equality assertion). The unchanged historical guards remain active.

`scripts.run_unified_diagnostic_regressions` accounts for all 51 original test
IDs from the preflight/shared-core/live-diagnostic selection:

- 39 existing shared-core, authority-negative and fake-transport behavior tests
  execute on the current checkout without adaptation.
- All 10 original exact-package preflight tests and the two whole-runtime live
  identity methods execute on the fixed `52cccc0a` projection. Positive and
  negative identity mutations are both retained. The original standalone
  package/review verification also runs there.
- Nine additional current tests preserve five original control assertion bodies
  with a newly built, current-bound **offline test fixture**, plus a fresh-process
  no-network/no-SDK control, fixture restoration, and original preflight/live
  rejection checks. The five bodies include all fixed failure responses, receipt
  persistence, original-binding mutations, native-capture failure and no retry.
  Only the test-local `preflight` fixture is substituted; no live gate or old
  manifest is edited. Fake reservations still validate the current runtime.

The projection materializes only the old Python runtime and an explicit list of
29 diagnostic code/test/helper/package/review files. No eval tree, paid grant,
trigger, credentials or provider SDK is used. Every diagnostic file is required
to remain byte-identical to the baseline, and the child rejects network/live
imports. The JSON receipt enumerates both partitions and extra current tests;
skips, missing IDs or changed partition sizes fail the runner. Historical output
is separately labeled and never counts as new unified capability acceptance.

The full downstream witness section (70 commands, including the 11 existing
compatibility wrappers) was also executed locally with every exit code zero;
the workflow still executes those original computations. This inventory avoids
treating an early successful CI step as full-workflow completion.

```
python -B -m scripts.run_unified_diagnostic_regressions --output /tmp/hcl-diagnostic-partition.json
```

Use Python 3.12 and the existing `requirements-conceptual.txt` pin for full legacy
logic regression (the explicit supplied-model path itself needs no Z3).

- `python -B -m unittest -v tests.test_unified_s1 tests.test_unified_plan tests.test_quantified_logic tests.test_argument_readings`
- `python -m scripts.render_hcl_status --check`
- `python -m scripts.witness_unified_s1 --output hcl-unified-s1-witness.json`

The witness records the exact checked commit and individual runtime hashes,
computed values, used fields and ACL refusal. Hosted CI checks the precise PR
head. CI results and independent review disposition are recorded on the PR.
No test count is an overall capability-completion percentage.

Current behavioral regressions and historical identity are different evidence.
The old amendment guards must continue rejecting the expanded runtime: their
whole-tree pins cannot authorize new code. The explicitly partitioned legacy
runner records each original test ID, runs actual behavior on current code,
and checks fixed-runtime identity in an allowlisted old Python-code projection.
Old guard code, pins, reports, grants and experiment outputs remain unchanged.

Provider calls/spend: 0. Real model semantics, LIVE_FUNCTIONAL, EFFECT_CONFIRMED,
S1 completion, full T20/T21/T22/T28, and S2 open semantic compilation are not
established by this slice. No sealed material is needed by its synthetic tests.
