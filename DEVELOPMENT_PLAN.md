# HCL Development Plan

Status: **CANONICAL CAPABILITY-GROWTH PLAN; CG-02 ACTIVE**

This file defines the live development direction for HCL. `STATUS.md` records
current execution state; this file records the development strategy and the next
work package. Remote `main` is the code fact. Historical reports remain evidence,
not active plans.

## 1. Objective and priority

HCL exists to add a genuinely useful human-cognition layer to a replaceable base
model. The target is improved understanding and reasoning about people,
perspective, belief, intention, relationships, social interaction, narrative,
moral responsibility, values and higher-order concepts.

Development priority is fixed:

> **real capability growth > external validation > leaderboard**

External evaluation is used to falsify a capability claim and to decide
**RETAIN / SIMPLIFY / DEACTIVATE**. It must not choose the capability architecture
for us.

Leaderboard work is deferred until the HCL capability system reaches the maturity
gate in section 8. Leaderboard placement is a later outcome/reward, not the
current research objective.

## 2. Current evidence disposition

### Retain as core

- evidence / provenance / actor / source / time boundaries;
- v0.5 stance / explicit revision / auditable persistent state;
- v0.6 evidence-constrained character information boundaries and bounded
  perspective reasoning;
- system uncertainty separated from character uncertainty;
- narrator/reader information separated from character information.

The strongest specialized external signal remains the frozen v0.6 FANToM fresh
pilot: C/P/G/D = 11/19/22/30 of 32 and D-only/G-only = 8/0. This is one-model,
one-task-family evidence and must not be inflated into broad Theory-of-Mind proof.

### Simplify / keep optional

- v0.7 typed intention/goal;
- v0.8 typed affect/appraisal.

These remain useful evidence/audit structures, but are not default specialized
reasoning paths unless a new capability mechanism demonstrates incremental value.

### Generic exact tools

- v0.9 causal/counterfactual computation;
- v0.10 argumentation computation;
- quantified-logic, witness/countermodel and alternative-reading tools.

These are conditional computation tools. Their outputs are not automatically
world truth, moral truth or private psychological truth. Expanding them is not a
human-cognition capability-growth objective.

### Frozen/inactive research

Consumed or inconclusive Circa, CLASH, TORQUE, FOLIO and similar development
families remain closed under their recorded dispositions. Do not reopen them just
to search for a positive result.

LongMemEval remains **SEALED / DEPRIORITIZED**. Its 32 rows must not be inspected,
consumed, reinterpreted, deleted or triggered without a new owner authorization.

## 3. Capability-first development loop

Every active capability package follows:

```
real failure or falsifiable hypothesis
    -> minimal capability mechanism
    -> provider-free correctness
    -> bounded external development comparison
    -> RETAIN / SIMPLIFY / DEACTIVATE
    -> next capability
```

Implementation is the main line. Full leaderboard selection, large holdouts,
cross-model significance and integrated benchmark qualification are not
prerequisites for implementing a small falsifiable capability prototype.

Every work package must state one user-observable **capability delta**. New tests,
manifests, protocols, CI jobs or schemas do not count by themselves.

If two consecutive complete work packages contain only source audit, protocol,
testing or documentation, the next package must implement, simplify or close a
capability rather than begin a third validation-only package.

At most two implemented-but-unvalidated capability candidates may remain active.

Measurement failure and mechanism failure are separate. Ambiguous source labels,
broken output contracts or unscorable references are **INCONCLUSIVE**, not
evidence for or against cognition.

## 4. Completed main work package

# HCL-CG-01 — Perspective- and Choice-Constrained Character Explanation

### Capability delta

Before CG-01, HCL can preserve who had access to what information and can model
bounded belief/perspective evidence.

After CG-01, HCL should additionally be able to assess a candidate explanation of
a person's action by checking whether that explanation depends on knowledge,
explicit goals or actual opportunities the person had at the action time, and to
revise only the affected explanation when later evidence changes one of those
conditions.

The capability does **not** determine a single true motive.

Example:

- A does not attend B's meeting.
- B interprets the absence as deliberate opposition.
- Reliable later narration says A first learned that the meeting existed only
  after it had ended.

CG-01 should weaken or invalidate the explanation "A intentionally used absence
to express opposition" because its required prior-knowledge condition is
contradicted. It must not infer that A supports B, lacks opposition, or changed
belief.

A missing record that A heard something is not proof that A did not know it.
Negative knowledge requires explicit source evidence, a reliable first-learning
statement, a declared complete information channel, or another justified
closed-world boundary. Otherwise the condition remains **UNKNOWN**.

### First-round engineering bounds

- at most 4 actors;
- at most 24 events;
- at most 3 named explanation candidates plus an open unknown candidate;
- at most 2 update points.

These are complexity limits, not psychological assumptions.

Do not add a new database, global personality profile, trust score, relationship
graph, emotion ontology or rational-choice optimizer. v0.9/v0.10 tools are not
required by CG-01.

## 5. CG-01 execution phases

### Phase A — Correct the v1 entry semantics

Modify the smallest coherent set around:

- `hcl/v1/router.py`
- `hcl/v1/layer.py`
- `hcl/v1/context.py`

Required behavior:

1. A generic `why` / `为什么` question must not by itself trigger an intention
   or person-cognition path.
2. Explicitly distinguish:
   - **READER_ANALYSIS**: external reader may use authorized narrative evidence;
   - **CHARACTER_PERSPECTIVE**: answer only from the target character's evidence at
     the requested time;
   - **OBSERVER_ABOUT_TARGET**: reason about a target using only what the observer
     can know about the target and target access.
3. Reader-visible narrator evidence must not be copied into character knowledge.
4. If an LLM semantic-preparation step is needed, it must be explicit and its
   calls/input/output/cost/failure recorded.
5. Ordinary non-person tasks remain on the direct path with no unnecessary HCL
   extraction.

Provider-free tests must include both English and Chinese routing cases and all
three perspective modes.

When Phase A is correct and CI is green, continue directly to Phase B.

### Phase B — Implement explanation-condition reasoning

Implement a lightweight CG-01 module. Reuse v0.6 evidence/perspective assets;
do not rename the old hypothesis tracker and call it a new capability.

Each candidate explanation binds:

- target actor;
- action;
- action time;
- source/provenance;
- optional explicit goal/intention evidence;
- knowledge/access conditions;
- opportunity/choice conditions;
- support, challenge, contradiction and unknown conditions.

The deterministic mechanism must actually perform:

- source-scope validation;
- temporal validation;
- perspective availability checks;
- explicit contradiction checks;
- unresolved-condition preservation;
- local invalidation/revision when new evidence changes a required condition.

Action does not imply motive. Third-party attribution does not imply private truth.
Later evidence does not retroactively become information available at the action
time.

Tests must include both useful positive reasoning and refusal cases.

When Phase B is runnable and provider-free correct, continue directly to Phase C.

### Phase C — End-to-end v1 integration

Provide an ordinary-text path:

```
authorized narrative
 -> v1 router
 -> answer perspective mode
 -> evidence/perspective preparation
 -> finite candidate explanations
 -> knowledge/goal/opportunity condition checks
 -> bounded explanation context
 -> base-model final answer
```

The implementation must not require a human to pre-enter the correct mental state
or gold explanation.

Research/debug receipts must preserve the **actual content** sent to the final
answer model:

- source evidence;
- perspective state;
- explanation candidates;
- condition states;
- support/challenge/conflict;
- uncertainty;
- final cognition context;
- provider/extraction call counts and cost when applicable.

Hashes/counts alone are insufficient for causal audit.

Ordinary user output remains natural language; internal enums/state are exposed
only in research/debug mode.

After Phase C and full provider-free regressions, label the capability
**IMPLEMENTED_UNVALIDATED**. That is a valid milestone. Do not claim external
model improvement yet.

### Phase D — Minimal external development package

Only after A+B+C is complete, qualify a small external development task and
freeze a fair comparison:

- **C** — current qualified strong model direct reasoning;
- **P** — strongest simple cognition prompt/process;
- **G** — competent generic structured/multi-hypothesis method;
- **H** — integrated HCL + CG-01 from ordinary text;
- **H-new** — identical to H except the new knowledge/choice condition mechanism
  is removed.

The decisive attribution question is whether H's gain disappears in H-new.
If not, CG-01 cannot claim the improvement.

The package may be prepared provider-free: source/license audit, deterministic
selection, exposure ledger, scorer, audit rubric, call/input/output/cost caps,
runner and CI. Do not execute paid calls without explicit authorization.

If paid execution is the only remaining step, stop at:

**HCL_CG01_EXTERNAL_VALIDATION_OWNER_AUTHORIZATION**

and report exact source, license, sample/family count, exposure state,
provider/model, arms, calls, input/output caps, USD hard cap, scorer and expected
evidence value.

### Phase E — Single decision closure

After valid external development evidence, make one decision:

- **RETAIN** — meaningful semantic increment over qualified P/G, H-new ablation
  supports the mechanism, reverse harm acceptable, cost justified;
- **SIMPLIFY** — P or G provides equivalent useful behavior more simply;
- **DEACTIVATE** — no substantive increment, systematic harm, case-specific rules
  required, or end-to-end value disappears without hand-prepared mental state.

Historical code/results remain preserved even when deactivated.

Do not keep switching datasets to seek a positive answer on the same mechanism.

## 6. Work autonomy and owner gates

The development manager should resolve without stopping:

- ordinary bugs;
- failed tests/CI;
- import/type/schema issues;
- stale docs/status;
- branch/merge conflicts;
- receipt/harness errors;
- provider-free fixtures and regressions.

Use one active writer. Re-read remote `main` at the start of each coherent
package. Prefer a coherent PR rather than one PR per field.

Owner approval is required only for:

- new provider-backed spending;
- new account/credential/training/deployment cost;
- private owner material or changed data-sharing scope;
- unresolved licensing/privacy boundary;
- expansion into a large ontology or product-engineering program;
- relaxing frozen evidence/privacy/budget rules.

Historical unused budgets do not transfer.

## 7. Explicit prohibitions for the current phase

Do not:

- make leaderboard search or optimization the development main line;
- reopen sealed LongMemEval;
- rerun consumed FANToM/SAGA/CAREBench/Circa/CLASH/TORQUE/FOLIO families as fresh;
- insert benchmark IDs, gold labels, answer distribution or task-specific rules
  into the mechanism;
- infer a unique motive from an action;
- infer emotion truth from expression alone;
- infer private belief from third-party attribution;
- turn conditional exact-tool output into psychological/world/moral truth;
- activate all cognition modules by default;
- count tests, protocols or schemas as capability growth;
- create a v0.11/v1.1 shell merely to continue version numbering.

## 8. Candidate pool after CG-01

Do not freeze these as mandatory versions. Re-evaluate after each capability package.

The first candidate is now **selected as CG-02** and removed from the unfrozen pool:

1. **CG-02 ACTIVE — Social commitment and misunderstanding explanation** — proposals, requests,
   acceptance, commitments, conditions, who received/understood what; avoid trust
   scores and large relationship graphs.
2. **Responsibility-structure explanation** — distinguish causal contribution,
   knowledge, foreseeability, control, intention and responsibility basis under
   explicit normative premises.
3. **Contextual value conflict and preference** — conditional preferences,
   role/context changes and unresolved value conflict; no global fixed weights.
4. **Concept interpretation in person/social context** — local definitions,
   speaker-relative usage, applicability, counterexamples and multiple readings.

Narrative/social integration should emerge across these capabilities rather than
be introduced as an empty large "literature engine".

Affect or identity can move upward only if a different, concrete capability
failure justifies it.

## 9. Leaderboard maturity gate

Do not select a leaderboard yet.

Only begin **Authoritative Leaderboard Target Audit** after all of the following
are substantially met:

1. At least four substantively different human-cognition capability families have
   external task utility evidence.
2. At least two families show attributable specialized HCL increment beyond
   qualified simple P and generic G methods; otherwise describe HCL honestly as
   a useful cognition workflow rather than a rich specialized architecture.
3. Evidence spans at least three independent source systems, including at least
   one multi-event character narrative/social-interaction task requiring two
   substantive cognition operations.
4. Integrated HCL from ordinary input through routing/preparation/context/tools to
   final answer shows a predeclared meaningful gain over C/P/G. As a maturity
   reference, predeclare either at least +5 percentage points task success or at
   least 20% relative reduction in substantive errors before evaluation.
5. Transfer is demonstrated within at least two independent model families, with
   at least one then-representative strong reasoning configuration.
6. Reliability is high: valid final output target >=99%; no observed severe
   predeclared actor/time/access-boundary errors in the audited sample; ordinary
   non-target tasks remain within a roughly 2 percentage-point non-inferiority
   margin; gains are not produced simply by abstaining more.
7. Typical complex-task HCL cost is controlled. Initial engineering target:
   total cost <=2x qualified P and P95 latency <=3x on the representative mixed
   task set, unless a harder tier is declared before evaluation.
8. Code, model/config, license, exposure ledger, actual cognition state, raw
   output, scoring and cost evidence are reproducible and auditable.

After this gate, select one primary and at most a small number of auxiliary
authoritative leaderboards based on authority, HCL alignment, official rules,
public reproducibility, community recognition and reasonable cost.

Leaderboard position is a later **research result and reward**. It must never
become the source of HCL capability design.

## 10. Completed CG-01 execution order

The live work order is:

1. **CG01-A** — repair v1 routing and reader/character/observer semantics;
2. **CG01-B** — implement executable knowledge/choice-constrained explanation;
3. **CG01-C** — integrate ordinary-text end-to-end path and auditable actual
   cognition context;
4. **CG01-CERT** — provider-free CG-01 correctness plus all relevant historical
   regressions;
5. **CG01-D** — qualify/freeze one minimal external C/P/G/H/H-new development
   package without paid execution;
6. stop only if the sole remaining step requires owner-paid authorization.

Owner authorization was received for the frozen USD 0.75 package. The one-time
run completed at Actions 36392929956, and Phase E selected SIMPLIFY for the
ordinary-text task class. The specialized checker's efficacy remains
inconclusive because the H arm's semantic preparation failed in all four cases.
The exact evidence and provider-free repair are recorded in
`reports/HCL_CG01_EXTERNAL_DEVELOPMENT_CLOSURE.md`. No unused authorization
transfers. The next capability package must come from the existing priority
pool in section 8 and state a new user-observable capability delta.

The previous v1 integrated-source audit remains a useful validation backlog, but
it is no longer the development blocker.

The completed CG-01 development question was:

> **What does HCL understand about a person after this package that it could not
> reliably represent and check before?**


## 11. Active work package: HCL-CG-02

# HCL-CG-02 — Social Commitment, Expectation and Misunderstanding

Canonical contract: [docs/HCL_CG02_CAPABILITY_CONTRACT.md](docs/HCL_CG02_CAPABILITY_CONTRACT.md).

### User-observable capability delta

CG-02 should let HCL preserve the difference between what a social act actually
expressed and what different participants had evidence to understand or expect.

For example, if A says "If I finish by Friday, I can go with you" and B later
states "A promised to go Friday", HCL should preserve the source act as
conditional, track whether B had access to the condition, and explain any mismatch
without automatically inferring lying, betrayal, promise-breaking, bad intent,
trust change or relationship status.

### Development principle

CG-02 is deliberately narrower than a general relationship/social-cognition
module. It must not become a trust graph, friend/enemy classifier, personality
model or broad speech-act ontology.

Reuse v0.6 perspective/access boundaries and the v1 reader/character/observer
modes. Build only the minimum new operations needed to ground social acts,
preserve explicit conditions and compare participant expectations.

### Immediate execution order

1. **CG02-A** — add the smallest explicit social-commitment/misunderstanding
   operation to v1 without disturbing direct routing.
2. **CG02-B** — implement source/time/access-scoped proposal/request/
   acceptance/refusal/conditional-commitment/withdrawal checking.
3. **CG02-C** — implement participant expectation comparison and bounded
   misunderstanding explanation.
4. **CG02-D** — add ordinary-text semantic preparation with auditable actual state
   and fail-closed source anchoring.
5. **CG02-CERT** — provider-free correctness and all relevant historical
   regressions.
6. **CG02-E** — freeze a bounded C/P/G/H/H-new external development package, but
   make no paid call without owner authorization.

### Hard treatment-presence gate

The CG-01 external run paid for H and H-new even though failed semantic
preparation made their final inputs identical. CG-02 must not repeat that.

Before any owner budget request, every selected H case must pass a provider-free
preflight proving:

- source-valid semantic preparation;
- at least one grounded CG-02 social act;
- at least one actual CG-02 condition/expectation check;
- checked state present in H;
- that state/mechanism removed as intended in H-new;
- final H and H-new model inputs observably differ because of the treatment.

If the treatment is not present, the external package is not ready for paid
authorization.

The current development question is:

> **Can HCL preserve what was actually proposed, requested, accepted or
> conditionally committed, while explaining why different people formed different
> expectations without inventing private motives or moral blame?**
