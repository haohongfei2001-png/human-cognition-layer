# HCL Development Plan

Status: **CANONICAL CAPABILITY-GROWTH PLAN; CG-03 DEVELOPMENT-ONLY RETAIN / CLOSED; CG-04 DEFERRED; CG-05 DEFERRED; NIGHT INTEGRATION ACTIVE**

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

The first candidate was **selected as CG-02** and is now closed as
INCONCLUSIVE for this development package. CG-03 has now closed with a bounded synthetic development RETAIN signal.
The next listed candidate is selected as CG-04; remaining entries stay an
unfrozen priority pool:

1. **CG-02 CLOSED / INCONCLUSIVE — Social commitment and misunderstanding explanation** — proposals, requests,
   acceptance, commitments, conditions, who received/understood what; avoid trust
   scores and large relationship graphs.
2. **CG-03 CLOSED / DEVELOPMENT-ONLY RETAIN — Responsibility-structure explanation** — distinguish causal contribution,
   knowledge, foreseeability, control, intention and responsibility basis under
   explicit normative premises.
3. **CG-04 IMPLEMENTED_UNVALIDATED / DEFERRED — Contextual value conflict and preference** — conditional preferences,
   role/context changes and unresolved value conflict; no global fixed weights.
4. **CG-05 IMPLEMENTED_UNVALIDATED / DEFERRED — Concept interpretation in person/social context** — local definitions,
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


## 11. Completed work package: HCL-CG-02

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

Execution state: A-D and CERT completed on exact-head and merged-main
provider-free CI; E froze the four-case five-arm package. Owner-authorized
DeepSeek run 36413088075 executed once and the source-first closure selected
**INCONCLUSIVE** because the frozen strict scorer was biased by uneven enum
label exposure. The treatment was present and no source/case was replaced.
The grant and trigger are closed; no rerun is authorized. See `STATUS.md` and
`reports/HCL_CG02_EXTERNAL_DEVELOPMENT_CLOSURE.md` for exact evidence.

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

## 12. Completed work package: HCL-CG-03

**Responsibility-structure explanation** is the next candidate from section 8.
The user-observable delta is to explain how an actor's causal contribution,
knowledge, foreseeability, control and stated intention bear on a particular
responsibility basis **under an explicit normative premise**. A causal link or
bad outcome alone must not become intent, blame or a universal moral verdict.

The bounded [CG-03 capability contract](docs/HCL_CG03_CAPABILITY_CONTRACT.md)
sets the A → B → C → D → CERT → E implementation order. **CG03-A–D** now have
the bounded typed operation, source/time/access factor checks, conditional
caller-premise evaluation and a conservative exact-line ordinary-text path.
**CG03-CERT** passed on exact PR head `086fdbd819174505eb862e466177a5b90669b358`
([run 36421176120](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36421176120))
and merged main `2aeda0188eb64728735e3cd6c0b049f9ed329e6e`
([run 36421279622](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36421279622)):
111 v1 + 176 historical tests passed on both, with identical runtime digest,
zero provider calls/spend and LongMemEval sealed. The other five main workflow
groups passed too. This certifies provider-free correctness, not external utility.

**CG03-E** executed the owner-authorized frozen comparison once at
[run 36427668859](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36427668859).
The source-first [closure](reports/HCL_CG03_EXTERNAL_DEVELOPMENT_CLOSURE.md)
selects **RETAIN, development evidence only**: H 28/28, P 21/28, G 20/28,
H-new 23/28. All treatment gates passed; H avoided substantive source/time/
attribution/premise promotions, with H-new supporting attribution. This is four
HCL-authored synthetic cases, not independent/fresh evidence or broad moral
competence. H cost 4.34x P; keep it explicit and optional. The 20-call,
zero-retry run rated USD 0.03700620 under the USD 0.30 cap. Budget and trigger
are closed; no rerun or historical budget transfer is authorized.

## 13. Active work package: HCL-CG-04

**Contextual value conflict and preference** is the next candidate from section 8.
Its [canonical bounded contract](docs/HCL_CG04_CAPABILITY_CONTRACT.md) specifies
one visible delta: explain which explicit preferences apply in an actor's chosen
role/context, what depends on unresolved conditions, and what remains conflicted,
without constructing global fixed value weights or inferring lasting values from
a choice. Explicit local revision must preserve unaffected roles and contexts.

Execution order is **CG04-A → CG04-B → CG04-C → CG04-D → CG04-CERT → CG04-E**.
Begin with the minimal real operation, then source/time/access checks, conditional
applicability, local revision/conflict and a conservative ordinary-text path.
Certify provider-free on exact head and main, then freeze one fair treatment-
presence package. No benchmark/source hunt, ontology expansion or new paid
experiment is part of implementation. During the authorized night, defer a new owner grant when
paid validation is the sole remaining action; all previous grants remain closed.

CG04-A–D and CERT are complete: exact head `ca6f36434275b97b9ed15aaba3f1423f33ed8aa2`
and merged main `88b5cfbefaae51793998a9e2685e11f30a22a241` each passed 142 v1
and 176 frozen historical tests with identical runtime digest and zero provider
calls. See [certification](reports/HCL_CG04_PROVIDER_FREE_CERTIFICATION.json) and
[bounded implementation](docs/HCL_CG04_IMPLEMENTATION.md).

CG04-E freezes four synthetic development cases, all five inputs, a fair shared
output contract, strict typed field scorer and treatment-presence receipts at
zero provider calls. The [protocol](docs/HCL_CG04_EXTERNAL_DEVELOPMENT_PROTOCOL.md)
predeclares source-first RETAIN / SIMPLIFY / DEACTIVATE / INCONCLUSIVE closure.
The dormant runner/workflow reuse the existing DeepSeek client/cap ledger and
propose a new USD 0.30 hard cap for at most 20 calls, zero retries. The conservative
reservation is USD 0.29543184; historical budgets do not transfer. No trigger
exists and the grant is zero. Only paid validation remains, so the live milestone
is **READY / DEFERRED_OWNER_AUTHORIZATION** during the night. Do not execute without
a new explicit owner grant. Any outcome remains synthetic development evidence,
not independent/fresh evidence or a broad value-cognition claim.


## 14. Authorized night continuation / CG-05

The owner authorized NO-BLOCKING-OWNER-GATE unattended development on 2026-09-28.
This overrides historical stop-at-paid wording for the night without authorizing
any spending. CG-04 is READY / DEFERRED_OWNER_AUTHORIZATION with its existing
package and budget proposal unchanged; grant 0, trigger absent. Frozen runtime
replay stays pinned to main 018afbc; current-runtime tests separately prove exact
case/input compatibility. No automatic migration of a future paid grant.

The next section-8 candidate is selected as CG-05. Execute A → B → C → D → CERT → E
under [the minimal contract](docs/HCL_CG05_CAPABILITY_CONTRACT.md). CAPABILITY_DELTA:
check local concept usage by speaker/context, explicit criteria/counterexamples,
multiple readings and local revision without universal/shared/private truth.
A–D are implemented; certify exact head/main, freeze fair ordinary-text five-arm
inputs if needed, then defer paid execution. No source hunt or leaderboard work.

At most two implemented-but-unvalidated candidates: CG-04 and CG-05. Once both
freezes are ready, do not open a third large module. The unique next implementation
package is integration of retained source/perspective/responsibility safeguards,
source-grounded semantic preparation and less duplicated answer context, with
provider-free integrated cases. Record an actual CAPABILITY_DELTA in each package.
Do not change consumed evidence, paid grants or frozen messages to optimize cost.
Continue until the night end conditions supplied by the owner hold; paid owner
authorization alone is never a development stop reason. Preserve canonical main,
PRs, exact-main CI, deltas, dispositions, frozen proposals and unique next task.


CG05-CERT is complete on PR #137 exact head and c7593bc exact main: 347 provider-
free tests, same runtime digest, all six workflow groups PASS. CG05-E is READY /
DEFERRED_OWNER_AUTHORIZATION (20 calls/0 retries/USD 0.30 proposal, reservation
USD 0.29537640). No paid execution/grant/trigger. CG-04/CG-05 are the two pending
candidates. The unique next implementation is NIGHT-INTEGRATION-01: explicit
lossless context compaction for retained cognition and bounded ordinary input;
then cross-capability composition. Preserve every frozen default input and
historical evidence; do not open a third new candidate or ask for paid approval.


NIGHT-INTEGRATION-01 is implemented: explicit lossless source/case references and
shared provenance columns let complete checked cognition fit a previously
insufficient answer-context budget. Twelve existing development inputs are
round-trip identical; total serialized input bytes shrink 8.33% including policy.
No token/cost/utility extrapolation or frozen-input changes. Certify exact
head/main, then immediately implement source-projected cross-capability
composition from ordinary input. Keep CG04/05 as the two deferred candidates;
CG02 is INCONCLUSIVE_CLOSED, CG03 development-only RETAIN. No new paid gate.


NIGHT-INTEGRATION-01 certified: PR139 head/main359 tests, all six groups PASS.
NIGHT-INTEGRATION-02 implements actual same-source composition of existing
preference/concept/responsibility operations into one final answer, without
semantic bridges or added candidate. Ordinary paths execute all checks; private
views require identical typed source/time/access, and per-operation failure stays
unresolved. Fix complete foreign-domain grammar collisions generically while
preserving exact frozen default inputs. Certify head/main, then continue bounded
source-grounded semantic preparation/access integration for existing operations.
No third candidate, new paid call, source hunt or owner gate.


NIGHT-INTEGRATION-02 certified on PR140 head/main: 369 tests, all six groups PASS.
NIGHT-INTEGRATION-03 adds optional exact-source narrated exposure preparation to
existing operations and ordinary private composition. No exposure-to-belief or
narrator-world-to-character promotion. Earlier event/record views cannot consume
later delivery receipts; default freezes remain identical. Certify head/main,
then implement lossless shared source-record pooling in composed final context,
with explicit per-operation access links and no inferred semantic bridge.
CG04/05 remain the only two implemented-unvalidated candidates. CG01/02 closed
registry metadata now matches their historical source-first dispositions.


NIGHT-INTEGRATION-03 certified on PR141 head/main381 tests, all six groups PASS.
NIGHT-INTEGRATION-04 implements lossless composed source-record pooling so every
checked operation fits a tighter total context budget without selective evidence
or shared-access inference. Actual input round trip, privacy, actor/event/record,
reference integrity and whole-budget refusal are tested; direct frozen inputs
stay identical. Certify head/main, preserve deferred frozen-runtime execution
reproducibility, then integrate source-validated preparation for retained v0.6
belief/perspective with existing operations. No third candidate, extra paid call,
private data, ontology, source hunt or owner gate.


NIGHT-INTEGRATION-04 certified on PR142 head/main388 tests; all six groups PASS.
Repair dormant CG04 execution to separate current control/authorization SHA from
its immutable certified execution SHA; cap stays0, no trigger/call, package and
helpers untouched. This is one preservation-only package. The immediate next
package must implement source-validated ordinary belief preparation/composition
for RETAIN v0.6, with actor/source/time/access and uncertainty boundaries and no
new capability candidate, new provider API or paid call. Do not add another
validation-only package before that implementation.


NIGHT-FREEZE-COMPATIBILITY certified on PR143:390 tests, both applicable groups
PASS, grant0/no trigger. NIGHT-INTEGRATION-05 implements source-bound ordinary
preparation into RETAIN v0.6 and real belief/concept/preference composition. New
source/actor/time/access/revision checks preserve uncertainty and block exposure-
to-acceptance, indirect-to-private and belief-to-truth promotion; all frozen default
inputs stay identical. Certify exact head/main, then implement source-scoped
comparison of expressed belief and existing local concept criteria. Explain a
bounded mismatch without automatically concluding the belief is false, the local
meaning is shared, or any moral premise is true. Keep only CG04/05 pending; zero
new paid run or third module, no benchmark/source search or owner gate.


NIGHT-INTEGRATION-05 certified on PR144 head/main402 tests, all six groups PASS.
NIGHT-INTEGRATION-06 implements explicit source-scoped comparison of retained
belief with existing concept readings, preserving actual source timestamp and
all unresolved/indirect/access boundaries. Certify head/main; then add a bounded
ordinary-question entrypoint selecting these existing preparations/composition
from explicit actor/context/item/term semantics. No supplied correct mental state,
extra extraction, synonym/ontology inference or third candidate. Ambiguous tasks
keep authorized reader source with structured analysis unresolved. CG04/05
freezes stay unchanged/deferred; continue provider-free implementation, no owner
paid gate or leaderboard/source hunting.


NIGHT-INTEGRATION-06 certified on PR145 head/main413 tests, both applicable groups
PASS. NIGHT-INTEGRATION-07 implements a bounded ordinary-question entrypoint into
existing belief/concept/comparison preparation, with no caller mental gold or
extra extraction. Ambiguous private questions refuse reader-source transfer.
Certify exact head/main, then implement source-order snapshots so later belief/
meaning revisions or narrated exposure cannot change what an earlier view was
supported to contain. Explicit source statement order only, no calendar-time or
verified receipt claim. Preserve default freezes and historical evidence; only
CG04/05 pending, no new paid calls or third candidate, no owner blocking gate.


NIGHT-INTEGRATION-07 certified on PR146 final head/main425 tests, all six groups
PASS. NIGHT-INTEGRATION-08 implements explicit earlier source-order snapshots of
ordinary person/context questions. No future revision/exposure/invalid semantic
line enters an earlier preparation; scope metadata is budgeted, invalid scopes
refuse whole-source fallback. Certify head/main, then reduce repeated shared
policy/preparation metadata in composed final input losslessly, keeping all
source/actor/time/access/uncertainty decisions and historical/default frozen inputs.
CG04/05 are the two pending candidates; no third module, new paid call, owner
blocking gate, source hunt or leaderboard.


NIGHT-INTEGRATION-08 certified on PR147 head/main435 tests, both applicable groups
PASS. NIGHT-INTEGRATION-09 implements lossless per-stage provider-free preparation
default encoding and shared access policy, with strict backward decoding and
budget/byte checks; no cognition/access selection. Certify head/main, then add
ordinary explicit belief/conditional-responsibility composition using existing
RETAIN v0.6 and development-only RETAIN CG03 with explicit caller normative
premises. Belief/received information/outcome must not establish action-time
knowledge, foreseeability, control, intention or moral truth. Existing source/
time/access checks and default freezes stay unchanged. No third candidate, new
paid call, ontology, benchmark/source hunt or blocking owner gate; CG04/05 deferred.


## 15. Authorized continuous night queue after NIGHT-INTEGRATION-09

This queue extends the existing provider-free integration line without opening a
third implemented-but-unvalidated capability candidate. It exists to prevent the
manager from stopping merely because one bounded integration PR completed while
there is still a concrete dependency-safe capability delta available.

The fixed continuation order is:

### NIGHT-INTEGRATION-10 — belief + conditional-responsibility composition

CAPABILITY_DELTA: an ordinary explicit question can combine retained source-scoped
belief/perspective with the existing CG-03 responsibility-structure checker under
explicit caller normative premises, while keeping belief, received information,
action-time knowledge, foreseeability, control, intention, causal contribution
and normative premise distinct.

Requirements:
- reuse existing v0.6 retained belief/perspective and CG-03 checker/runtime;
- ordinary input must not require caller-entered hidden mental-state gold;
- responsibility conclusions remain conditional on explicit premises;
- belief, outcome or later evidence must not silently establish knowledge,
  foreseeability, control, intention, blame or moral truth;
- preserve source/time/access/revision boundaries and current refusal behavior;
- one final answer call, zero new extraction/provider calls by default;
- no new capability candidate, ontology, benchmark/source hunt or paid grant.

After exact-head/main correctness certification, continue immediately to
NIGHT-INTEGRATION-11.

### NIGHT-INTEGRATION-11 — multi-source local revision composition

CAPABILITY_DELTA: one ordinary question can combine multiple explicitly authorized
source records for the same actor/context and preserve which belief, meaning,
access or conditional-responsibility state was supported before and after a local
revision.

Requirements:
- source identity and ordering remain explicit; source order is not silently
  promoted to calendar time or verified receipt time;
- later source content cannot backfill earlier actor knowledge/access;
- contradictory or incomparable sources remain unresolved rather than averaged;
- revision changes only the scoped actor/context/item/term/factor it actually
  addresses;
- complete provenance for every retained state survives final-input compaction;
- invalid/missing source authority fails closed without whole-library fallback.

After exact-head/main correctness certification, continue immediately to
NIGHT-INTEGRATION-12.

### NIGHT-INTEGRATION-12 — source-bounded perspective contrast

CAPABILITY_DELTA: an ordinary question can compare two explicitly named
participants' supported views of the same event/claim while preserving separate
public evidence, private exposure, belief, uncertainty and unknown state.

Requirements:
- A's evidence/access/belief is never copied to B without an explicit shared
  source/access basis;
- narrator knowledge is not character knowledge;
- reported belief is not world truth;
- disagreement does not imply deception, irrationality, relationship state or
  moral blame;
- the final answer exposes the evidence boundary needed to understand the
  contrast without leaking unauthorized private reader material.

After exact-head/main correctness certification, continue immediately to
NIGHT-INTEGRATION-13.

### NIGHT-INTEGRATION-13 — bounded multi-event narrative integration

CAPABILITY_DELTA: HCL can answer an ordinary question over a short multi-event
narrative requiring at least two existing cognition operations together, while
preserving actor, event, source, access, revision and uncertainty boundaries.

Use only already-retained/implemented mechanisms where applicable: perspective /
belief, social commitment/expectation, responsibility structure, local concept,
preference/value conflict and generic exact tools. This is integration, not a new
large module.

Requirements:
- bounded provider-free development fixtures first;
- no automatic activation of every operation;
- select the minimum operation set justified by the question and source;
- later events cannot rewrite earlier views except through explicit scoped
  revision;
- no action-to-motive/emotion, exposure-to-belief, computation-to-world-truth or
  conditional-premise-to-moral-truth promotion;
- context compaction must remain lossless for all selected cognition decisions.

After exact-head/main correctness certification, continue immediately to
NIGHT-INTEGRATION-14.

### NIGHT-INTEGRATION-14 — ordinary-question robustness and integrated closure

CAPABILITY_DELTA: the integrated HCL path remains usable from ordinary Chinese and
English questions across the supported person/context/narrative forms without
caller knowledge of internal operation names.

Audit and improve only demonstrated integration failures involving:
- explicit actor/context/item/term/event selection;
- negation and local revision;
- source-order scopes;
- two-participant perspective contrast;
- multi-source conflict/uncertainty;
- bounded multi-event composition;
- refusal/fallback privacy;
- total context budget and exact state decoding.

Do not count more tests, schemas or compression alone as the capability delta.
Any code change must repair a reproduced correctness/usability failure or enable a
user-observable integrated behavior. Finish with one provider-free integrated
closure receipt covering the complete NI-10..14 line and the frozen historical
regressions.

### Continuous-execution rules for NI-10..14

1. Remote `main`, this plan, `STATUS.md`, exact-SHA CI and immutable receipts
   are the source of truth.
2. Keep one writer for the active integration boundary. Merge/certify a stable
   slice before moving its writer to the next slice.
3. Ordinary bugs, test failures, review findings, CI failures and harness defects
   are manager-owned. Diagnose, repair and continue without owner interruption.
4. External/provider/paid/device/private-data gates do not block dependency-safe
   provider-free engineering. Record them truthfully as deferred and continue.
5. No new paid call, credential, permission, provider account, benchmark hunt,
   leaderboard target, LongMemEval access or third unvalidated capability
   candidate is authorized by this queue.
6. Do not change consumed evidence, frozen CG04/CG05 messages, scorers or grants
   to manufacture a positive result.
7. Do not weaken/delete tests, hide failures, truncate evidence, or create
   validation-only/filler PRs merely to keep the manager busy.
8. If one numbered item is already satisfied by current `main`, record the
   evidence and advance; do not reimplement it.
9. The night may stop before an arbitrary wall-clock duration only when NI-10..14
   are truthfully complete or every remaining item depends on an owner-only,
   external or prohibited action. Otherwise continue to the unique next item.
10. Capability growth remains the ordering principle:
   **real human-cognition capability growth > external validation > leaderboard**.


NIGHT-INTEGRATION-09 certified on PR148 head/main442 tests, both applicable groups
PASS; four actual inputs53,143→52,328 bytes (-1.5336%), exact decoded cognition,
not token/cost/utility evidence. NIGHT-INTEGRATION-10 implements ordinary retained
belief/conditional-responsibility integration and general foreign-source factor/
episode guards. Explicit caller episode scope retains every required factor source
and existing time/access checks; default consumed cases remain identical. Certify
head/main, then immediately continue section15 NIGHT-INTEGRATION-11 multi-source
local revision composition. Preserve source authority/identity/order, before/after
scoped state, conflict/uncertainty and complete provenance. No third candidate,
new paid run or owner blocking gate. The section15 canonical queue remains fixed.


NI-10 certified on PR150 head/main455 tests, both applicable groups PASS.
NI-11 implements multiple explicitly authorized source-record snapshots using
existing ordinary preparations, explicit source paths and exact visible record/
statement bindings. Before/after local revision and exposure remain separate;
contradictory/incomparable sources remain unresolved, no calendar/receipt truth.
Certify exact head/main, then immediately NI-12 source-bounded two-participant
perspective contrast. Preserve section15 queue, historical evidence and freezes;
only CG04/05 pending, no new paid provider calls or third module.


NI-11 certified on PR151 head/main465 tests, both applicable groups PASS.
NI-12 implements source-bounded independent two-participant contrast via retained
v0.6, ordinary question selection and existing access/cutoff projection. Shared
exposure is not shared belief; unauthorized observer source stays hidden.
Certify exact head/main then immediately NI-13 bounded multi-event integration;
select only existing operations justified by the question/source. No third module,
paid calls or frozen/consumed evidence changes; preserve section15 continuation.


NI-12 certified on PR152 head/main475 tests, both applicable groups PASS.
NI-13 implements explicit ordinary event-section integration and minimum existing
belief/meaning/preference/responsibility composition. Before/after local revision,
visible event/source bindings and private exposure stay scoped; invalid selected
event never falls back to the whole narrative. Certify head/main, then NI-14
ordinary Chinese/English integration robustness, reproduced source-grounding
failures and one complete provider-free integrated closure. Preserve section15,
CG04/05 freezes/history, zero new paid calls and no third candidate.


NI-13 certified on PR153 head/main485 tests, both applicable groups PASS.
NI-14 completes one ordinary bilingual entrypoint and repairs reproduced source/
actor/predicate/action/outcome-reference failures, preserving uncertainty and every
historical default/frozen input. Integrated local closure327+176=503 PASS with
five actual final-input probes. Accept delivery only after exact-head/main CI
matches the closure runtime; final GitHub handoff supplies actual SHA/run/hash.
Section15 NI10–14 implementation queue is complete; no currently queued/identified
provider-free implementation remains after exact-main certification. CG04/CG05
still occupy both unvalidated slots. Do not open a third large candidate or filler
PR. Any further retained integration must address a concrete demonstrated failure
and record its unique implementation task here. Paid proposals stay deferred,
unchanged, and are never the sole reason to stop available independent work.
