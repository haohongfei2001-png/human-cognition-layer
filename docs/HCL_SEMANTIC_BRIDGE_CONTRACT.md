# Clarify existing first-plan semantic-input responsibility

The [fixed-16K smoke](HCL_PLANNING_RECOVERY_20261007_RESULTS.md) delivered a good
cited answer but failed its required native-treatment gate. The model selected
D02/B02/B01 using source IDs and questions only. B01 received no structured
`semantic_candidates`, so it admitted no typed premises; B02 produced no checked
access treatment. D02's question and empty bindings were valid, but its native
communication parser rejected the multi-sentence source-line shape. The original
arguments and all results remain unchanged and replay to those same outcomes.

This repair changes **only two passages of the planner policy**, a net 190 UTF-8
bytes. It makes the existing division of work explicit:

- For ordinary prose outside the native literal forms, the model constructs
  faithful, source-anchored `semantic_candidates` in the same first response for
  at most one relevant B01/C01/C02/C03 operation. Source IDs alone are not typed
  semantic preparation.
- Already-supported literal input does not require translation. If no faithful,
  supported translation is possible, the model must leave the gap unresolved;
  nothing inserts candidates, invents an actor or forces an irrelevant module.
- B02 and D02 do not accept this bridge. Native readers are literal checkers,
  not another language model.

The accepted argument schema, actual parsers, adapter catalog and dispatch are
unchanged. So are the original complete source/question, unverified-translation
status, quote/version/scope restrictions, native-result requirement, final
citation and semantic acceptance, 16K/high planning, 8K final and 36KB wire limit.
No readiness-probe layer, additional planning call, automatic extraction, retry,
new adapter or schema framework is added.

## What the provider-free tests establish

Ten controls cover the explicit policy contract, exact actual-argument replay,
independent new-character nested negation, Tuesday-only scope, conditional plans
without invented active goals, explicit goal/selection distinction, no backfilling
later knowledge into C02 action time, already-supported literal input, anonymous
unrepresentable input and rejection of a bridge on unsupported B02. Scripted
faithful arguments reach the existing native operations and retain full sources.
They remain unverified translation hypotheses; this is not source truth or private
mental-state certification. The actual insufficient recorded arguments still
produce insufficient/rejected native results rather than being repaired after output.

The old policy fails the new explicit-contract assertion; the revised policy
passes it. This does **not** demonstrate that a real model will follow the clearer
contract or construct semantically faithful arguments. That proposition needs a
new bounded, predeclared live run and independent source-first review. Both prior
experiments are closed; no unused stage allowance is repurposed.

The existing current-runtime/history discipline preserves all 114 prior artifact
pins, including the 16K package, executor, raw output and failed native review.
Its 106 executor tests now replay at the exact closed historical commit; current
regressions run against this new planner policy. The paired diagnostic comparison
accepts only these two exact code-owned policy substitutions plus previously
reviewed changes, keeping every other parsed planning/final value checked.
