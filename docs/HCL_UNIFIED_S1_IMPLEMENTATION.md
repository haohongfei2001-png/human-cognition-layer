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
