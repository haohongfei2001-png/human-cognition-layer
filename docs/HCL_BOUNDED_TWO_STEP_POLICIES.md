# Bounded two-step conditional policies (M05 / M14)

This is an additive offline increment under HCL_SYSTEM_REDESIGN_SPEC.md M05
steps 1–4 and M14 steps 2–5. S3 ∥ S4 remain open. It is not full M14,
general planning, moral truth, or authenticated principle adoption.

## Input and semantics

Existing judgment v1 decisions remain single-step and unchanged. An explicit
optional `policy_horizon: 2` on a source-bound decision requires its referenced
M05 graph to have horizon 2. Supplying horizon 2 without that opt-in, or any
other policy horizon, is invalid. No supplied policy, score or winner is accepted. Combining policy_horizon with
v2–v5 concept/repair/joint-change/weight-domain inputs is explicitly rejected;
those single-step compositions, including MINIMAX_REGRET, remain unchanged.

The host exhaustively enumerates a root action and one continuation action for
each reachable nonterminal observation symbol. As in M05, the observation is
`root.observations[root.transitions[state]]`. States sharing that symbol share
the same continuation. One complete policy is used across all dimensions and
all scenario distributions. It cannot condition on hidden world identity,
scenario labels, dimension identity, or a favorable hindsight outcome.

Each scenario vector is the expected final-state dimensional value minus the
cost of every action actually executed. Intermediate state value is not an
extra reward. Terminal branches stop immediately and pay no second action cost.
No uniform probabilities, weights, preferences or future facts are invented.

Actual feasibility is checked at the root and at every reachable second-step
state, including actual states assigned zero mass by a declared scenario.
Subjective enablement is separately checked at each corresponding belief branch.
Subjective feasibility remains reported separately, as in existing judgments.
Continuation assignments also cover subjective-only observation branches;
behaviorally distinct assignments remain tied when actual scenarios cannot
separate their values.

Norm guards and M13 joint-extension applicability are the existing action-time
facts. Those fixed hard requirements are enforced on every actually reachable
action in a policy. A prohibited or unresolved continuation cannot be paid for
with a high score. This increment does not model changing future commitments,
future normative guards or newly received messages inside the rollout.
Revising source facts, control, principles, observations or feasible actions
recompiles/recomputes the actual judgment and can change the policy.

## Enumeration, ties and budget

There are at most 256 enumerated complete policies per decision; the common
local-work budget meters generation, state checks, scenario evaluation and
comparison. Exhausting either fence raises a judgment work frontier. Enumeration
is lazy and no partially enumerated set is returned as an optimum. The decision
stays UNCOMPUTED with no robust recommendation, including on recovery/replay.
PARETO retains nondominated policies without inventing weights. EXPECTED uses a
single explicit scenario (or one actual state); MAXIMIN scalarizes each complete
scenario first. All tied scalar optima are retained, including dominated policies
with the same worst-case score. Old single-step outputs and certificates retain
their original semantics and bytes.

Policies have host-computed content identities, root/continuation definitions,
per-step feasibility records and scenario paths. HCL.run consumes these records
in the answer. Delivery verifies the entire computation and source binding;
editing a continuation or step certificate cannot create a deliverable result.

## Evidence and boundaries

- `tests/test_unified_bounded_policies.py`: independent finite-vector oracle,
  informative versus aliased observations, dimension/scenario non-splicing,
  terminal costs, all scalar ties, actual feasibility, norm/fact revisions,
  unknown guards, budgets, tampering, run/stream and durable recovery.
- `tests/test_unified_bounded_policy_upgrade.py`: exact shipped PR446 predecessor,
  single-step EXPECTED/MAXIMIN/MINIMAX_REGRET, schema 3/4, five durable seams,
  no resend, unknown holds and governance fences.
- `scripts/witness_unified_bounded_policies.py`: seven real HCL offline cases,
  source-bound conditional policies, revised recommendations, incomplete cases,
  exact replay and checked-runtime hashes. Provider calls/spend are zero.

Open: arbitrary horizons, evolving future normative guards, general policy
compression/search, natural-language extraction fidelity, candidate completeness,
calibrated human preferences, full M05/M14/T17–T19/S3/S4 and live effects.
