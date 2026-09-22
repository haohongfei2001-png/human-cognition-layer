# HCL Runtime State-Prompt Conformance Repair v0.1

Status: **PREDECLARED / IMPLEMENTATION OF ALREADY-FROZEN SEMANTICS**

## Trigger

Synthetic full-state audit established that the runtime state path repeatedly
interprets ordinary direct communication too skeptically.

Observed target pattern across 8/8 state builds:
- direct communication was explicit;
- no textual deception, source error, unreliability, or conflicting world truth;
- runtime state still produced EPISTEMIC / medium;
- runtime state invented missing truth / reliability / trust bridges;
- runtime state preserved competing "knows" vs "does not know" hypotheses.

The state was internally coherent under a strict philosophical definition of
knowledge, but this behavior conflicts with already-frozen HCL v0.3 semantics.

## Frozen semantic authority

The following existing rules remain authoritative and unchanged:

1. world truth != agent knowledge;
2. information transfer requires an evidence path;
3. directly communicated information without relevant conflict can be low
   uncertainty;
4. direct communication may be SIMPLE when no asymmetric/nested reasoning is
   needed;
5. explicit misinformation / world-belief divergence is EPISTEMIC;
6. do not manufacture uncertainty or exotic alternatives without textual or
   ordinary-context support;
7. use the minimal sufficient model;
8. uncertainty is calibrated at the actual question granularity.

Exact prompt wording is explicitly evolvable under the v0.3 freeze.

## Repair scope

Change only runtime `STATE_SYSTEM` in `hcl/v03/answer_loop.py`.

Do not change:
- state schema;
- mode enum;
- uncertainty enum;
- build_state control flow;
- retry budgets;
- state max_tokens;
- backends.py;
- repair-v0.2 thinking-disabled state request;
- DRAFT_SYSTEM / CHECK_SYSTEM / REVISION_SYSTEM;
- Decision Policy;
- Action Checker.

## Required runtime clarifications

Add generic communication rules:

1. Direct communication is an evidence path.
2. If an agent directly receives proposition P and the text supplies no relevant
   conflict, deception, source-error, unreliability, or contrary world fact,
   do not invent a separate truth/reliability/trust blocker.
3. At the asked granularity, ordinary direct communication may support
   SIMPLE/low and agent knowledge of P.
4. If the text explicitly supplies misinformation, deception, source
   unreliability, or contrary world truth:
   - preserve the communicated content as the agent's belief/information;
   - preserve world truth separately;
   - use EPISTEMIC where the divergence matters.
5. Do not treat merely logically possible lying/error as decision-relevant
   counterevidence.
6. Direct communication of a proposition and observation of the fact are
   different evidence paths, but neither requires invented skepticism absent
   relevant conflict.

No fixture-specific name, token, source role, or literal may appear in runtime
repair text.

## Fresh communication-boundary validation

Use a new repository-owned 10-case suite frozen before provider calls.

Coverage:
- 4 ordinary direct-communication positive cases;
- 2 explicit negative/no-receipt cases;
- 2 explicit misinformation/world-truth divergence cases;
- 1 explicit source-unreliability case;
- 1 conflicting-sources case.

For each case freeze:
- expected mode;
- allowed uncertainty levels;
- missing-bridge expectation;
- target agent;
- required terms in agent knows/believes;
- forbidden terms in agent knows when world truth conflicts.

Strict pass gate:
- 10/10 schema valid;
- 10/10 mode acceptable;
- 10/10 uncertainty acceptable;
- 10/10 required agent-field semantics;
- 10/10 missing-bridge expectation.

## Post-boundary regressions

Only if the fresh communication state gate passes:

1. rerun the frozen 24-case state-generation reliability suite:
   - 24/24 success;
   - 0 state_json_exhaustion;
   - 0 backend/other exceptions;
2. rerun the 12-case fresh semantic-faithfulness answer suite;
3. rerun original 16-case information-state/output-interface audit;
4. rerun production-path state-fidelity suite;
5. rerun existing answer-checker fresh suite.

Repair closes only if all gates pass in the same frozen behavior.

## No semantic version change

This repair does not alter frozen cognition semantics. It restores runtime
prompt conformance to already-frozen rules.

Any proposal to change the semantic rule itself still requires a new state
semantics version.

## External-evidence boundary

No external benchmark evidence until synthetic closure.

## Claim boundary

A pass establishes runtime conformance to the frozen communication semantics on
fresh synthetic boundaries plus preservation of existing synthetic regressions.

It does not establish external benchmark efficacy or HCL 1.0 certification.
