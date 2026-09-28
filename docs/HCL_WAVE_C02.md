# C02 — Competing conditional action explanations

## CAPABILITY_DELTA

Ordinary source text now supports multiple conditional explanations of one recorded
action or inaction. C01 goal/plan relations before the action can supply two
coexisting goal-directed candidates. Explicit action-time ignorance weakens
knowledge-dependent candidates without proving another motive. Missing knowledge
is not treated as ignorance, and inability to attend is not reinterpreted as an
opportunity deliberately to choose nonattendance.

## Mechanism and reuse

`prepare_explanations` uses A02 anchored speech, C01's source-order prefix goal/plan
projection and the retained CG01 conditional checker. A01 supports connect each
source condition and checked candidate to its actual source. The adapter never
reopens or upgrades CG01's historical SIMPLIFY disposition.

Candidate generation is bounded and explicitly non-exhaustive/non-exclusive: up
to two source-supported goal-directed explanations, otherwise a generic informed
choice hypothesis, plus explicit ignorance/opportunity-constraint alternatives
within a three-candidate cap. They are hypotheses, never facts about motives.
At-action knowledge and opportunity require explicit source reference to that time.
Later/current knowledge without that reference is not backfilled. Earlier C01
source order is a visible conditional assumption, not verified chronology.

Negated requirements use explicit complementary facts only; absence does not
create a negative fact. Original sources and typed fact/event bindings are saved.
Conflicting positive and negative reports remain `CONFLICTING_PREMISES` even when
the retained checker has a stronger native precedence rule. Native results remain
visible beside the conservative new disposition. Every result retains
`actual_motive=NOT_ESTABLISHED` and no unique winner is inferred.

## Verification and limits

Thirteen targeted tests cover positive counterevidence update, two simultaneous
supported goals, actor/source/access/time boundaries, later evidence, missing and
conflicting premises, inaction, hidden input, stale support, ambiguous action and
budgets. Full v1 plus 176 historical regressions run on exact PR head/main; the
artifact includes SHA, runtime hash and `scripts/witness_action_explanations.py`.
The authored replay and actual final inputs are saved in
`reports/HCL_WAVE_C02_WITNESS.json`.

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Explicit bounded
English action/self-report forms, source-local actor identity, 20 source statements,
three conditional candidates and two goal candidates. It is not a general motive
classifier, exhaustive explanation search or verified private-state inference.
A source-provided action-time claim remains a claim. Zero provider calls/spend;
LongMemEval sealed. NEXT_READY: C03 belief-dependent plan feasibility/revision,
separating the character's perspective from a declared world model.
