# SOTOPIA Goal-Regression Audit — Abstract Failure Classes

Source:
- fresh holdout / repeat settings: Hard ordinals 10-19
- seed 43/44 repeat run: `35482453412`

This audit uses exact SOTOPIA trajectories only as diagnostics. It does not turn
benchmark instances into training examples.

## 1. Repeated large goal losses separate into different phenomena

### A. Metric conflict: explicit task goal vs interpersonal boundary

Hard setting 11 is the clearest case.

The tested role's private objective is exclusive control of a scarce shared
resource while the other participant is also cold.

Across both repeats:
- Control goal score: 10 / 10
- HCL goal score: 1 / 3
- HCL relationship and social-rules scores improve materially.

Control achieves the literal private goal mainly by repeatedly refusing every
sharing proposal. HCL instead searches for alternatives and eventually accepts
a consensual shared arrangement.

Interpretation:

This is **not a clean capability regression**. The benchmark's goal dimension
rewards literal private-goal completion even where doing so can conflict with
cooperation and explicit consent.

Research consequence:
- do not "repair" this by teaching HCL to ignore consent or social constraints;
- keep goal score separate from constraint-respecting instrumental competence;
- when possible, improve the alternative route to the underlying need without
  chasing raw goal score blindly.

### B. Genuine policy weakness: verification deadlock under option decay

Hard setting 19 repeats the same failure in both seeds.

The tested role has a conjunctive objective:
- obtain an item;
- keep a friend out of trouble.

Control completes the purchase and plans to resolve the ownership issue
afterward.

HCL correctly detects a decision-critical ownership uncertainty, but then:
- probes repeatedly;
- waits for confirmation;
- keeps re-checking the same unresolved fact;
- allows the seller's patience / opportunity to decay;
- never transitions to a bounded fallback decision.

Across repeats:
- goal delta: -5 / -5.

This is the strongest **genuine Decision Policy defect** in the repeat audit.

Abstract failure class:

> **verification deadlock** — a critical uncertainty is identified correctly,
> but the policy treats verification as a prerequisite for all progress even
> when waiting itself destroys option value.

The repair target is not "ignore uncertainty." It is:
1. compare cost-of-waiting with cost-of-acting;
2. distinguish reversible from irreversible commitments;
3. use a finite probe budget / stopping rule;
4. after repeated non-resolution, switch to the best constraint-respecting
   fallback: reversible commitment, alternative path, defer, or exit.

### C. Infeasible bargaining gaps are not meaningful HCL regressions

Several smaller negative goal deltas occur where the buyer ceiling and seller
floor do not overlap.

Examples include settings 10, 12, and 14 in seed 43.

Both control and HCL fail to complete the transaction. Small score differences
come from evaluator credit for negotiation style or partial progress.

Research consequence:
- do not tune HCL to "force" a deal when no mutually acceptable deal exists;
- exiting after confirming an infeasible gap is correct behavior.

### D. Conditional long-term goals can create evaluator sensitivity

Some smaller losses occur where the immediate objective is achieved but the
agent accepts a future contingency or fallback.

This may reduce the evaluator's interpretation of full goal commitment even
when the immediate interaction remains successful.

Research consequence:
- treat these as lower-priority evaluator-sensitivity cases unless the action
  trajectory itself shows a real capability defect.

## 2. Main diagnosis

The repeat run does **not** support a single generic conclusion that HCL is
"too cautious."

The sharper diagnosis is:

1. cognition-state representation is often correct;
2. relationship / social-rule benefits are stable;
3. knowledge loss has been repaired on the repeat slice;
4. remaining large goal losses are dominated by:
   - benchmark metric conflict in some settings; and
   - verification deadlock / no stopping rule in at least one repeated setting.

## 3. Decision Policy v0.2 target

The next policy revision should add general decision-theoretic structure without
weakening HCL:

- **option value**: waiting can have a cost;
- **reversibility**: reversible actions can be rational before full certainty;
- **probe budget**: do not ask the same unresolved question indefinitely;
- **decision threshold**: full certainty is not always required;
- **constraint-respecting fallback**: after the probe budget is exhausted,
  choose the best safe reversible action, alternative path, defer, or exit;
- **hard-boundary protection**: never convert this into permission to cross
  explicit non-consent or clear legal/social constraints.

## 4. Anti-overfitting boundary

No SOTOPIA dialogue text, evaluator answer, or exact scenario is copied into the
new synthetic fixtures.

The next synthetic suite is independently written around:
- expiring options;
- refundable reservations;
- reversible commitments;
- repeated failed probes;
- hard infeasibility;
- explicit-consent boundaries.

Only after that synthetic gate should Decision Policy v0.2 be validated on
previously unused SOTOPIA-Hard settings.
