# HCL Development Plan

Status: **CANONICAL LIVE EXECUTION PLAN — LONG-HORIZON CAPABILITY GROWTH / WAVES A–F COMPLETE / WAVE G COMPLETE / G-HC PASS_PROVIDER_FREE / WAVE H / H01–H05 CORRECTNESS_VERIFIED / G-ARCH PASS_ARCHITECTURE_READY_FOR_SERIOUS_EVALUATION / I01 FROZEN / I02 NEXT_READY**

The long-horizon capability architecture, levels, Waves A–H, all 41 work packages,
maturity gates, serious evaluation standard, optimization sequence and leaderboard
policy are canonical in
[HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md](HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md).

This file is the live execution control plane. `STATUS.md` records current facts
and evidence dispositions. Remote `main`, exact-SHA CI and immutable historical
receipts remain the code/evidence facts. Historical closure documents remain
evidence and are not rewritten as active development policy.

## 1. Objective and fixed priority

HCL exists to add a genuinely useful Human Cognition Layer to a replaceable strong
base model. The target is evidence-bounded, perspective-sensitive, revisable,
cross-capability reasoning about people, belief, goals, plans, interaction,
relationships, identity, values, narrative, responsibility, concepts and
philosophical questions.

Development priority remains:

> **real capability growth > validation > leaderboard**

The current medium-horizon objective is to build the capability architecture to
maturity. Provider-backed efficacy comparison, independent benchmark qualification,
cross-model transfer and leaderboard work are deliberately later phases.

## 2. Current evidence dispositions — unchanged by this policy migration

| Asset | Canonical disposition |
|---|---|
| v0.4/v0.5 | foundation: evidence/provenance/actor/time/explicit stance and revision; no broad efficacy claim |
| v0.6 | **bounded RETAIN** for perspective/belief under historical limited evidence; no general Theory-of-Mind claim |
| CG01 | **SIMPLIFY / CLOSED** ordinary-text route; optional typed checker utility remains inconclusive |
| CG02 | **INCONCLUSIVE / CLOSED**; bounded social-act correctness may be reused; no qualified external utility |
| CG03 | **RETAIN_DEVELOPMENT_ONLY / CLOSED**; source/time/access responsibility factors under explicit premises |
| CG04 | **RETAIN_DEVELOPMENT_ONLY / CLOSED**; contextual preference/applicability/unknown/conflict boundaries |
| CG05 | **RETAIN_DEVELOPMENT_ONLY / CLOSED**; speaker/context local concepts, uncertainty, counterexamples and revision |
| NI10–14 | provider-free **correctness-only integration**; external incremental utility remains unproven |
| v0.7/v0.8 | simplified optional typed intention/goal and affect/appraisal evidence structures |
| v0.9/v0.10 + formal tools | generic exact conditional tools, not human-cognition efficacy evidence |
| LongMemEval | **SEALED / DEPRIORITIZED**; do not read, trigger, reinterpret, delete or consume |

No development-only evidence is upgraded to independent evidence. No consumed
package is reopened or rerun by this plan.

## 3. Superseded development policies

The following old execution rules are superseded for the architecture-building
phase:

1. **No per-capability mandatory provider-backed C/P/G/H/H-new loop.**
   A work package does not need a paid or provider-backed efficacy experiment
   before dependent capability work may continue.
2. **No per-capability mandatory independent benchmark search.**
   Benchmark/source qualification is not a prerequisite for each new operation.
3. **No two-implemented-unvalidated-capability ceiling.**
   Correctly integrated but efficacy-untested capabilities may accumulate as the
   architecture is built. Concurrent unintegrated experimental branches should
   still remain small and controlled.
4. **Validation does not block dependency-safe capability growth.**
   Correctness defects do block the affected dependency chain; absence of
   efficacy evidence alone does not.

These changes alter development cadence, not historical evidence conclusions.

## 4. Architecture-building test contract

Every work package must have a positive, user-observable **CAPABILITY_DELTA**.
It is not enough to prove only that HCL refrains from bad inference. The package
must also demonstrate what new reasoning becomes possible when evidence is
sufficient.

Each package requires exactly these engineering obligations:

- **unit correctness** — positive, negative, unknown/conflict and boundary behavior;
- **negative inference tests** — actor/source/time/perspective/assumption and
  domain-specific illegal promotions;
- **composition test** — at least one real dependency with existing capability,
  including local change and unaffected-scope preservation;
- **ordinary-input smoke** — natural language reaches the real entry path without
  caller-supplied correct hidden mental state; replay/stub and live status remain
  distinct;
- **historical regression** — retained semantic boundaries continue to hold.

Passing these checks means **safe enough to continue building**. It does not mean
external efficacy, independent generalization or strong-model enhancement is
established.

## 5. Completed Wave A — Unified Core and Ordinary Input

Wave A absorbs the generic semantic-preparation/native-entry work previously named
EG01-A. The independent-source qualification, fair efficacy package and provider-
backed comparison portions of old EG01-A are deferred until after G-ARCH.

### A00 — Canonical adoption and governance — COMPLETE

Capability delta: development is now controlled by one long-horizon architecture
that separates implementation, ordinary-input operational status, efficacy and
activation. Historical evidence remains unchanged while obsolete validation
gates no longer block capability growth.

This canonical adoption slice:

- adds the full 41-package Master Plan;
- changes the live queue to Waves A–H;
- supersedes the old per-capability validation loop and two-candidate ceiling;
- preserves all evidence dispositions, sealed data and closed budgets;
- does not change runtime code or authorize provider execution.

### A01 — Shared evidence / scope / interpretation / dependency core — CORRECTNESS_VERIFIED

**CAPABILITY_DELTA:** the same source evidence can support multiple cognition
operations through shared source, actor, time, scope, interpretation and dependency
identity, and a local evidence change can invalidate only the conclusions that
actually depend on it.

Required behavior:

- minimal shared `SourceSpan`, `Scope`, `Claim`, `Interpretation`,
  `Dependency` / equivalent structures;
- preserve source report versus system inference versus conditional tool result;
- preserve event time, information-access time, record time and source/narrative
  order without fabricating dates;
- multiple independent supports survive removal of one support;
- no rootless self-supporting inference cycle;
- adapters reuse retained v0.6 / v1 semantics rather than copying new actor/time
  logic into every module.

No large ontology, database rewrite or new provider call is required.

Delivered: `hcl/cognition/`, retained-operation source revision, positive witness,
14 targeted boundary/composition tests and full historical regression. A01 remains
UNTESTED for efficacy; see `docs/HCL_WAVE_A01.md`.

### A02 — Unified ordinary semantic-preparation entry — CORRECTNESS_VERIFIED

**CAPABILITY_DELTA:** ordinary text can produce source-anchored candidate people,
events, propositions, references and relations for the shared core without the
user choosing internal operation flags or supplying the correct mental state.

Delivered: `prepare_semantics` / `CognitionWorkspace.prepare_semantic` provides
source-local entity, speech-event, proposition, reference and relation candidates;
explicit first-person binding, source filtering before backend invocation and
separate structure/quote/semantic diagnostics. The replaceable backend is tested
with replay; no live efficacy claim. Generic entry work from EG01-A is absorbed
without benchmark/case/gold-specific logic.

### A03 — Support, challenge, alternatives and invalidation propagation — CORRECTNESS_VERIFIED

**CAPABILITY_DELTA:** HCL can revise its own interpretations locally when supporting
evidence is challenged, withdrawn or replaced, without rewriting source facts or
unrelated state.

Delivered: rooted challenges, clean alternative support, analyst replacement
records, ordinary expressed-position comparison and actual final support/challenge
closure. Eight A03 tests plus fourteen A02 tests cover the five engineering
obligations; see `docs/HCL_WAVE_A02_A03.md`.

### A04 — Retained-capability adapters into the shared core — CORRECTNESS_VERIFIED

**CAPABILITY_DELTA:** retained v0.6 perspective/belief and CG03/04/05 operations
can consume the same ordinary-source semantic material and preserve their distinct
uncertainty/premise semantics.

### A05 — First real cross-capability vertical slice — CORRECTNESS_VERIFIED

**CAPABILITY_DELTA:** one ordinary-source update propagates through at least two
real cognition operations and changes only the dependent conclusions, with an
auditable actual state/input receipt.

After A05, continue directly to Wave B unless a real correctness/safety dependency
blocks it. Do not stop merely because no large efficacy experiment has been run.

A04–A05 delivered the common-material adapter into real retained checkers,
explicit translation assumptions, source-to-operation projection dependencies,
stale-support answer rejection and one final-adapter call. The positive slice
changes a concept check and the dependent belief/concept comparison while
preserving unrelated Noor. See `docs/HCL_WAVE_A04_A05.md`. Live provider status
remains unverified; this does not block Wave B construction.

## 5b. Completed Wave B — Dynamic Epistemic Cognition

**B01 — CORRECTNESS_VERIFIED:** separate public expression, private-belief interpretation,
exposure, understanding and knowledge claims; construct query-bounded nested
mental propositions. Speech/exposure alone must not establish private belief or
higher-order acceptance. Require a positive nested interpretation witness.

B01 delivered bounded nested modal trees, ordinary-query holder selection, a real
attribution/subject-report join, scoped negation and dependency-local withdrawal.
Public expression is not private belief; private estimates carry an explicit
unverified sincerity assumption. Fifteen targeted checks plus full regression;
see `docs/HCL_WAVE_B01.md`. Efficacy remains UNTESTED.

**B02 — CORRECTNESS_VERIFIED:** differentiated communication/access updates, including
public/private delivery, missed/negated contact and three-person divergence.
Availability must not automatically establish exposure, understanding or belief.

B02 delivered three-person communication views, explicit positive/negative/later
receipt handling, availability/addressing separation, pre-extraction projection
and hidden-content non-interference. Twelve targeted tests plus full regression;
see `docs/HCL_WAVE_B02.md`.

**B03 — CORRECTNESS_VERIFIED:** character revision versus analyst revision; later evidence
can correct the current interpretation of the past without changing what was
available in an earlier knowledge snapshot. Preserve challenges, acceptance,
rejection and supported alternatives distinctly.

B03 delivered bitemporal source corrections, explicitly anchored character revision,
challenge/acceptance/rejection handling and ordinary-dialogue snapshots with actual
dependency receipts. Fourteen targeted checks plus full regression; see
`docs/HCL_WAVE_B03.md`.

**B04 — CORRECTNESS_VERIFIED:** ordinary copy cues form source-related report
families without majority/independence claims; conflicts, character uncertainty
and system missing evidence stay distinct. Bounded three-holder queries preserve
outer/inner modality. Fourteen targeted checks plus full regression; see
`docs/HCL_WAVE_B04.md`.

**B05 — CORRECTNESS_VERIFIED:** ordinary-input multi-person/higher-order integration, local
access revision and retained concept/responsibility operations. B05 now updates
Noor-dependent nested, concept and conditional-control checks while reusing Mira
and Kai outputs; ordinary input and actual final-adapter receipt are preserved.
Eleven targeted checks plus full regression; see `docs/HCL_WAVE_B05.md`.

## 5c. Completed Wave C — Goals, Plans and Appraisal

**C01 — CORRECTNESS_VERIFIED:** source-bounded goals/subgoals, means, plans, conditions,
opportunities, completion and abandonment. Keep stated intention distinct from
observed behavior and later outcome. Reuse v0.7/v0.8 thin structures and conditional
checks. C01 now provides a real goal/selected-plan/opportunity join, subgoal and
plan lifecycle separation, and dependent update after goal abandonment. Twelve
targeted checks plus full regression; see `docs/HCL_WAVE_C01.md`.

**C02 — CORRECTNESS_VERIFIED:** competing action explanations with required knowledge, goals,
opportunity and counterevidence; explicit action-time ignorance weakens the
knowledge-dependent explanation without proving another motive. C02 now reuses
C01 pre-action goals and the conditional checker to preserve mixed explanations,
source conflict and explicit negative evidence. Thirteen targeted checks plus full
regression; see `docs/HCL_WAVE_C02.md`.

**C03 — CORRECTNESS_VERIFIED:** belief-dependent plan feasibility and revision; distinguish
character-subjective feasibility from a declared model, and do not infer value
change from plan change. C03 now joins C01 plans with B03 belief revision and
explicit model conditions; subjective support can coexist with model contradiction.
Eleven targeted checks plus full regression; see `docs/HCL_WAVE_C03.md`.

**C04 — CORRECTNESS_VERIFIED:** event/goal/control/certainty appraisal, mixed affect and
reappraisal; expression, reported feeling and inferred appraisal must stay distinct.
C04 now reuses v0.8 to preserve mixed feeling reports, explicit reappraisal and
current goal-sensitive checks without inferring an actual emotion. Fourteen
targeted checks plus full regression; see `docs/HCL_WAVE_C04.md`.

**C05 — CORRECTNESS_VERIFIED:** integrated belief → plan → conditional action explanation
→ appraisal; a changed premise updates dependent checks while unsupported
emotion remains a hypothesis or unknown, never a certain label. Thirteen targeted
checks cover actual dependency changes, action-time boundaries, access, source
revision and shared extraction. See `docs/HCL_WAVE_C05.md`.

## 5d. Completed Wave D — Social and Strategic Cognition

**D01 — CORRECTNESS_VERIFIED:** social acts and commitment lifecycle, separating original
words, conditions, receipt, acceptance, expectation, withdrawal and fulfillment.
Fourteen targeted checks plus full regression; source-time receipt is checked at
each expectation. See `docs/HCL_WAVE_D01.md`.

**D02 — CORRECTNESS_VERIFIED:** bounded mutual understanding and explicit confirmation/repair;
both hearing an utterance is not mutually acknowledged shared understanding.
Thirteen targeted checks plus full regression; original receipt, back-report
receipt and final confirmation receipt are checked separately. See `docs/HCL_WAVE_D02.md`.

**D03 — CORRECTNESS_VERIFIED:** competing benign error, deliberate falsehood, concealment
and literally true but potentially misleading communication explanations; false
content alone never establishes deception. Fourteen targeted checks plus full
regression; exact statement omission anchors and source-time premise checks
prevent arbitrary strategy attribution. See `docs/HCL_WAVE_D03.md`.

**D04 — CORRECTNESS_VERIFIED:** localize and revise misunderstanding through access, local
meaning, omitted conditions and role expectations; clarification must not rewrite
the original commitment or automatically restore trust. Twelve targeted checks
plus full regression; actual source-rooted interpretation replacement and historical
meaning checks are exercised. See `docs/HCL_WAVE_D04.md`.

**D05 — CORRECTNESS_VERIFIED:** three-party cooperation, bounded authorization and joint
plans under sourced local rules; distinct audiences and third-party reports must
not become an omniscient group actor. Fifteen targeted checks plus full regression;
new permission, revocation and selective receipt change coordination checks.
See `docs/HCL_WAVE_D05.md`.

## 5e. Completed Wave E — Relationship, Identity, Role and Value Dynamics

**E01 — CORRECTNESS_VERIFIED:** domain-scoped relationship evidence: who regards whom,
concerning what, and with which support. Capability trust does not become moral
trust; one person's view does not become a reciprocal view. Eleven targeted
checks cover scope, reason support and explicit revision.

**E02 — CORRECTNESS_VERIFIED:** information/control/stated-choice alternatives
for failure, separate apology receipt and reported forgiveness. Thirteen targeted
checks plus combined composition; E01 and E02 ship as one coherent relationship
work package. See `docs/HCL_WAVE_E01_E02.md`.

**E03 — CORRECTNESS_VERIFIED:** separate self-narrative, third-party identity attribution,
role requirements, behavior and personal endorsement; role occupancy does not
imply endorsement of every role norm. Twelve targeted checks and a positive witness cover local revision and actual final inputs; see `docs/HCL_WAVE_E03.md`.

**E04 — CORRECTNESS_VERIFIED:** context-dependent choice comparisons, conditional partial-order paths, incomparable values and cross-role tension; reuses CG04 and E03. Thirteen tests and ordinary positive witness; see `docs/HCL_WAVE_E04.md`.

**E05 — CORRECTNESS_VERIFIED:** linked relationship–identity–role–value comparisons and source revision updates; twelve tests and positive witness. See `docs/HCL_WAVE_E05.md`.

## 5f. Completed Wave F — Long-Horizon Narrative Cognition

**F01 — CORRECTNESS_VERIFIED:** episodic source recovery by event/person/proposition/transition/dependency with exact extracts, access filtering and versioned invalidation. Thirteen tests and positive witness; see `docs/HCL_WAVE_F01.md`.

**F02 — CORRECTNESS_VERIFIED:** source-declared story, recall, disclosure, local narrative order and system-record axes, with unique challenge/receipt links and access-safe historical views. Nineteen tests and positive witness; see `docs/HCL_WAVE_F02.md`.

**F03 — CORRECTNESS_VERIFIED:** full selected recorded evidence closure with alternative and joint support, challenge, revision and selective cache reuse. Ten tests and ordinary positive witness; see `docs/HCL_WAVE_F03.md`.

**F04 — CORRECTNESS_VERIFIED:** one authorized dated chapter yields simultaneous source-anchored explanations of apparent action change, separating reported knowledge, explicit goal/value revision, role pressure and audience strategy without inferring private cause or moral character. Fourteen tests and ordinary positive witness; see `docs/HCL_WAVE_F04.md`.

**F05 — CORRECTNESS_VERIFIED:** branch-specific, authorized multi-chapter replay preserves opposed source reports, three time cutoffs, historical corrections and F04 development comparisons. Eleven tests, ordinary positive witness and 12-actor/120-event provider-free scale smoke; see `docs/HCL_WAVE_F05.md`. The scale check is not comprehension evidence.

## 5g. Completed Wave G — Moral, Conceptual and Philosophical Integration

**G01 — CORRECTNESS_VERIFIED:** ordinary user and source text produces typed but conditional premise candidates, distinguishing user-supplied, explicitly analyst-adopted, source-reported institution and character origins. Only completely parsed adopted/user conditions can bridge to CG03. Eleven tests and positive witness; see `docs/HCL_WAVE_G01.md`.

**G02 — CORRECTNESS_VERIFIED:** one ordinary G01 rule feeds separate CG03 action-time factor checks for up to four actors; a narrow separately adopted collective rule can compare two actors and an explicit joint report without inferring group mind, private intention or world feasibility. Thirteen tests and ordinary positive witness; see `docs/HCL_WAVE_G02.md`.

**G03 — CORRECTNESS_VERIFIED:** ordinary authorized text now yields local necessary/sufficient/typical criteria, explicit counterexamples, actor/context comparison and non-retroactive revision. Twelve tests and ordinary positive witness; see `docs/HCL_WAVE_G03.md`.

**G04 — CORRECTNESS_VERIFIED:** ordinary opposed arguments now separate source-reported fact challenges, G03 concept readings and explicit value conflicts, retaining bounded conditional premise maps, targeted counterexamples and analogy proposals. Twelve tests and ordinary witness; see `docs/HCL_WAVE_G04.md`.

**G05 — CORRECTNESS_VERIFIED:** ordinary independent one-factor questions now compare fact-premise, local concept-reading and explicit value-premise changes across G04 source arguments, retaining structurally unaffected paths and unresolved truth. Twelve tests and ordinary witness; see `docs/HCL_WAVE_G05.md`.

**G-HC — PASS_PROVIDER_FREE:** same ordinary scene composes G03 concept reading, G04 source argument and G05 sensitivity across a source correction while an unrelated argument remains semantically stable. B01/B02 mental-object distinctions, F05 long-source replay, ACL/time refusal and budget failure were reviewed; live efficacy remains unverified and the earlier E03 live-entry anchor refusal is preserved. See `docs/HCL_G_HC_GATE.md`.

**H01 — CORRECTNESS_VERIFIED:** ordinary single-fact questions now take an exact narrator-source path; concept, opposed-argument and hypothetical questions execute only G03, G03→G04 or G03→G04→G05 respectively under explicit depth/branch/operation/provider budgets. Twelve tests and same-source four-path witness; see `docs/HCL_WAVE_H01.md`.

**H02 — CORRECTNESS_VERIFIED:** two opposed source arguments now retrieve separately authorized F01 evidence; exact narrator support/counterevidence changes premise status, third-party speech remains attribution only, and no-gain retrieval stops. Fourteen tests and ordinary before/after witness; see `docs/HCL_WAVE_H02.md`.

**H03 — CORRECTNESS_VERIFIED:** a source-bound execution graph now connects reported belief, plan, promise expectation and relationship interpretation through actual support edges. One ordinary-source correction revises the dependent checks and retires stale final input while a separate source stays cached. Eight targeted tests and an exact-input witness; see `docs/HCL_WAVE_H03.md`.

**H04 — CORRECTNESS_VERIFIED:** a full bounded F03 selected closure now feeds a source-quoted conditional answer with a leading recorded explanation, unresolved alternatives, decisive counterevidence, scope and assumptions. It refuses truncated closure and never claims semantic judge correctness. Eight targeted tests and ordinary before/after witness; see `docs/HCL_WAVE_H04.md`.

**H05 — CORRECTNESS_VERIFIED:** one difficult question now selects a source-local B03/C03/D04/E05/F03/H04 chain and F05 cross-chapter reported conflict, preserving unresolved cross-source identity and record-time revision. A simple narrator question selects H01 direct lookup. Eight targeted tests, 100-event pressure case, ordinary witness and exact final input; see `docs/HCL_WAVE_H05.md`.

**G-ARCH — PASS_ARCHITECTURE_READY_FOR_SERIOUS_EVALUATION:** the one-shot live entry at main `5f14b829ee6247389bc326eb14736342723de2d0` completed two DeepSeek Flash calls, with six exact unique source quotations, five bounded offset repairs and checked state in the actual final input. Source-first closure, raw requests/responses, usage, cost estimate, hashes and limitations are in `reports/HCL_G_ARCH_ENTRY_CLOSURE.md`; the seven-criterion decision is in `docs/HCL_G_ARCH_GATE.md`. This is an authored functional smoke, not independent efficacy. The USD 0.04 grant is closed, E03 remains failed/closed, and no second trigger is authorized.

**I01 — FROZEN:** `docs/HCL_I01_EVALUATION_CONTRACT.md` and `reports/HCL_I01_EVALUATION_FREEZE.json` fix the main architecture surface, question, four families, fair C/P/G/H input/output shape, source independence split, attribution obligations and no-outcome boundary. The provider-free guard rejects authored/unauthorized/unequal/oracle candidates; six tests witness it. No cognition gain or independent efficacy is claimed.

**I02 — NEXT_READY:** qualify independent source provenance, license and access plus competent C/P/G comparators. Freeze model IDs, prompt/scaffold implementations, scorer rubric, sample size and cost/latency bands before confirmation. Do not view confirmation outcomes to tune H. C/P/G share complete ordinary inputs and final answer fields; G has a separately charged generic source-map step and original source in final input. The [first-group MuSR calibration](reports/HCL_I02_CPG_CALIBRATION_CLOSURE.md) made C, P and G-map calls; G-map violated its shape contract, G-final was not called, and its unique authorization closed. The [second-source Moral Stories calibration](reports/HCL_I02_MORAL_CPG_CALIBRATION_CLOSURE.md) made C/P/G-map/G-final calls: G-map v2 worked, but all three final comparators missed an explicit security goal while correctly refusing unsupported harmful intent. Its USD 0.06 grant is closed, with no rerun. Neither exposed calibration qualifies comparator semantics across task families or H efficacy. Initial rights screening excludes OpenStax model input and holds Gutenberg and the distinct GitHub MuSR distribution pending rights checks; see `docs/HCL_I02_SOURCE_SCREEN.md`. Zero confirmation sources are qualified. A separately pinned CC BY 4.0 author-team MuSR CSV is **calibration-only**: 256 questions share 64 narratives; the first group is exposed and its second item has unresolved perceptual support. Complete item-level audit and independent-source diversity before confirmation; do not treat license metadata or generated gold as semantic truth. Both MuSR and Moral Stories author/template/writing systems are calibration-exposed, so their other rows cannot be treated as unseen confirmation under I01. The [ordinary information-state repair](docs/HCL_I02_INFORMATION_STATE_ENTRY_REPAIR.md) initially found zero checked observations on the exposed native question; its [v2 repair](docs/HCL_I02_INFORMATION_STATE_V2_REPAIR.md) now passes provider-free H/H-new treatment presence and structural fairness with a chained runtime amendment. This is correctness evidence only. The generic semantic scorer v1 now distinguishes a stated goal from unproved harmful intent in source-first review; next qualify source diversity and a protected confirmation split. Do not rerun either spent calibration or claim H efficacy.

Full contracts and dependencies
remain in the Master Plan. No automatic per-package paid comparison.

## 6. Construction queue

The canonical queue is:

```text
A01 → A02 → A03 → A04 → A05
→ B01…B05
→ C01…C05
→ D01…D05
→ E01…E05
→ F01…F05
→ G01…G05
→ G-HC
→ H01…H05
→ G-ARCH
→ Serious Independent Evaluation
→ independent generalization
→ strong-base / P / G / H comparison
→ mechanism and integration ablation
→ cross-model transfer
→ optimization
→ Authoritative Leaderboard Target Audit
→ final leaderboard push
```

The full per-package contract, dependencies, capability delta and stop criteria are
in the Master Plan.

**41 work packages do not mean 41 PRs.** Work should merge coherent stable slices.
Do not split work merely to create activity, and do not create filler PRs to run
for an arbitrary amount of time.

## 7. Limited early live-adapter exception

After the ordinary semantic entry path forms during Waves A–C, one small live
adapter smoke may be designed to answer only:

> Does real provider input actually enter the intended real mechanism with valid
> source binding and usable structure?

It is not an efficacy ranking, is not C/P/G/H/H-new, is not repeated after every
wave, and cannot be used as an external-utility claim.

Latest owner default authorization permits necessary, bounded normal development
calls through existing provider/API/credential/billing infrastructure. Record calls,
usage and actual or reasonably determined cost; do not repeat answered questions.
New external setup and clearly abnormal cost are deferred while independent work
continues. Old experiment grants and residual budgets remain closed.

## 8. Mandatory maturity shift

### G-HC

The Hard-Cognition-Ready gate controls entry into Wave H. It requires substantive
multi-operation composition, bounded high-order mental state distinctions,
ordinary-input connectivity, long-horizon source handling, local revision and no
known severe actor/source/time/access defects.

### G-ARCH — mandatory gear shift

G-ARCH is checked only after H05. Once H05 is complete and G-ARCH passes, HCL may
not continue indefinite capability construction merely because another module can
be imagined.

It **must switch to Serious Independent Evaluation**:

```text
G-ARCH
→ independent generalization
→ strong base / strong prompt / competent generic scaffold / HCL comparison
→ mechanism + integration attribution
→ second model family / cross-model transfer
→ source-first retain / simplify / redesign decision
```

Failure to meet G-ARCH means repair the identified architecture deficiency; passing
G-ARCH means stop architecture expansion as the main line and test the complete
system.

## 9. Serious evaluation and strong-base target

Only after G-ARCH:

- qualify independent, native, difficult human-cognition tasks;
- compare against a then-current strong base configuration, a strong prompt/process
  and a competent generic scaffold;
- measure full end-to-end HCL from ordinary input;
- use fair mechanism-only and H-flat/integration ablations;
- require meaningful semantic gains, not merely statistically nonzero or JSON
  compliance gains;
- test at least two independent model families before mature cross-model claims;
- report reverse harm, abstention/coverage, cost and latency.

The quantitative and qualitative maturity criteria are canonical in the Master
Plan and must be frozen before confirmation results are inspected.

## 10. Optimization and leaderboard order

Leaderboard work remains last:

```text
G-ARCH
→ independent generalization
→ strong-base / P / G / H comparison
→ cross-model transfer
→ optimization
→ Authoritative Leaderboard Target Audit
→ final leaderboard push
```

Do not choose a leaderboard now. Do not add benchmark-specific logic during Waves
A–H.

## 11. Work autonomy and gates

Work owns ordinary:

- bugs and regressions;
- unit/integration failures;
- CI failures and reruns that do not spend provider budget;
- type/schema/import errors;
- merge conflicts;
- stale live documentation caused by the active slice;
- harness defects in provider-free engineering.

One runtime boundary should have one active writer. Re-read remote `main`,
`STATUS.md` and this live plan before each coherent slice.

Default autonomy now covers ordinary engineering, research/architecture choices
and bounded normal provider development costs in existing infrastructure. It does
not authorize expanded private-data scope, unclear licenses, access-control bypass,
new legal commitments or identity disclosure. Defer paths needing new external
onboarding/credentials or abnormal spending and continue independent work.
Serious independent evaluation remains post-G-ARCH; evidence standards do not change.

No old budget transfers. LongMemEval stays sealed.

## 12. Stop / rollback rules

Stop or rollback the affected path when there is a severe actor/source/time/access
mix-up, hidden-source leakage, unsupported motive/emotion/deception/value/
responsibility promotion, rootless inference cycle, or representation collapse
between cases that must remain semantically distinct.

Simplify a specialized module into generic state/scaffold when it adds fields but
no observable reasoning delta, or later independent evidence shows its benefit is
fully explained by generic resources.

A failed CI job is an engineering problem, not an owner gate. A missing efficacy
result is not a reason to stop available architecture work. A genuine semantic
defect is.

## 13. Current execution fact

- Current wave: **I — Serious Independent Evaluation**
- A00: **COMPLETE** through adoption of the long-horizon canonical plan
- **NEXT_READY: I02_UNEXPOSED_SOURCE_QUALIFICATION**
- The [ACL v8 developer-blind semantic diagnostic](reports/HCL_I02_ACL_CPG_V8_DEVELOPER_REVIEW/CLOSURE.md) froze opaque judgments before revealing C/P/G-final identities and reconciled the stored raw receipt to C 6/8, P 7/8, G-final 8/8 on four source-first obligations. The reviewer was also the implementer, and the rubric does not cover every unsupported severity claim. This is development-only, **not independent blind review or qualified strong-comparator semantics**; no H/H-new answer, efficacy result, new provider call or spend. Continue unexposed rights-clear source qualification and independent review before I03.
- The [exact-commit repository exposure screen](docs/HCL_I02_REPOSITORY_EXPOSURE_SNAPSHOT.md) adds an executable negative gate ahead of the frozen v4 source-rights and lineage checks. On main `7758180cb29b65ad1b925ecad801a4b6fc8d07f0`, 12-word overlap rejected the exposed KPU development source across its source file, raw receipt and runner; 29 LongMemEval-named paths were excluded without content access. A snapshot miss cannot prove historical/model-training disjointness or qualify rights and item semantics. **0 new confirmation items, 0 calls, 0 HCL answer gain.** Continue genuinely unexposed source qualification.
- The [blind review handoff](docs/HCL_I02_BLIND_REVIEW_PACKET.md) now converts a complete source-bound raw receipt into opaque final outputs and checks complete scorer-compatible reviews before revealing arms. Real ACL v8 receipt, source/citation mutation, incomplete review, allocation drift and historical scorer regressions pass provider-free. No independent blind judgment has been obtained; no source or HCL efficacy status changes.
- The [one-use ACL C/P/G v8 source-first closure](reports/HCL_I02_ACL_ETHICS_CPG_V8_CLOSURE.md) records a completed DeepSeek Pro thinking-high C/P/G-map/G-final development run: 4 calls, 0 retries, all four interfaces and exact citations valid, estimated USD 0.02662506 / peak-rated USD 0.05325012 under its separate USD 0.24 cap. The source is synthetic and development-exposed; blind semantic scoring and cross-family comparator qualification are unavailable, with unsupported inferences in C/P and G-map noted diagnostically. H/H-new 0 by direct-route observation. Raw receipts are preserved; trigger removed, grant closed, no transfer or rerun. Continue genuinely unexposed source qualification without treating this as H efficacy.
- The [ACL Ethics Tutorial abstract 3 development source](docs/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.md) pins an independently authored CC BY 4.0 synthetic research-ethics abstract, an explicitly adapted group-critique question, and four exact-source obligations before model output. An executable provider-free gate confirms C/P/G v8 complete-input fairness and G-final source retention; H is direct with no cognition treatment and H/H-new provider calls are excluded. All six abstracts and their author/template system are development-exposed. A separate overlay blocks confirmation reuse without changing historical frozen lineage hashes. **0 provider calls, 0 unseen confirmation cases, 0 HCL answer gain.** Next qualify truly unexposed systems and separately freeze any bounded C/P/G v8 model calibration; no old grant transfers.
- The [v8 strong comparator candidate](docs/HCL_I02_STRONG_COMPARATOR_V8.md) gives C/P/G identical DeepSeek V4 Pro native thinking-high call settings and scorer-compatible exact citations. Its separate [ACL synthetic development closure](reports/HCL_I02_ACL_ETHICS_CPG_V8_CLOSURE.md) records 4 completed interface calls but no blind semantic qualification. **0 confirmation items qualified, 0 HCL answer gain.** Earlier non-thinking runs cannot qualify strong C; truly unexposed source review and cross-family blinded comparator calibration remain required before I03.
- The [v4 exact-content source fingerprint overlay](docs/HCL_I02_EXACT_SOURCE_FINGERPRINT_V4.md) composes unchanged frozen v3 qualification with a pinned digest of the consumed KPU case. A mirrored URL and renamed author/template/writing-system/group IDs no longer turn the exact exposed text into confirmation; synthetic positive, denial and tamper tests pass. It is not a paraphrase detector or a repository-wide exposure audit. **0 real confirmation items qualified / 0 provider calls** in this package; I02 still needs unexposed, rights-clear source diversity and source-first item review.
- The [G v7 generic comparator interface](docs/HCL_I02_GENERIC_WORKSPACE_V7.md) is a separate provider-free repair after the consumed KPU v6 map returned exact but overlong source sentences. It keeps C/P, full ordinary source, a 3,500-byte total map cap and exact unique-quote/revision checks; it replaces the v6 180-character per-row limit with the inherited 1,500-character exact-quote safety bound. Synthetic ordinary-input, negative, multi-source composition, revision and historical v6 regression tests pass. **0 v7 provider calls; model semantics unqualified.** The KPU source/grant cannot validate this version. Continue I02 unexposed source qualification before another independently frozen comparison.
- The [KPU conflict case C/P/G v6 development calibration](reports/HCL_I02_KPU_CPG_V6_CLOSURE.md) completed once on main `8f6e2adc72b1ebf5801aa6485402f40a624eb089`: 3 calls (C, P, G-map), zero retries, G-final/H/H-new 0. The 3,436-byte G-map had seven exact source quotations but every row exceeded the frozen 180-character quote bound, so G is **INTERFACE FAILED / SEMANTICALLY UNQUALIFIED**. P's citation shape also fails the frozen scorer; C/P omit several frozen source obligations. Estimated USD 0.00680460, rated peak USD 0.01360920, actual invoice unavailable, below the separate USD 0.15 cap. Raw receipt, run/artifact hashes and source-first review are preserved. The grant is closed with no transfer/rerun and the trigger removed. This is development-exposed, not unseen confirmation or H efficacy. Continue I02 unexposed source qualification and a separately versioned provider-free generic interface repair; do not reuse the KPU case.
- The exact-source [EPC C/P/G v5 development calibration](reports/HCL_I02_EPC_CPG_V5_CLOSURE.md) completed once under its separate USD 0.15 cap: run `36596194865` on main `e277d91663fabc50b8ead8b28b65f6572b239558`, C/P/G-map 3 calls, zero retries, G-final 0 calls. The G-map stopped at its frozen 1,024-token ceiling with incomplete JSON, so G is **INTERFACE FAILED / SEMANTICALLY UNQUALIFIED**. Estimated USD 0.00552090, rated peak USD 0.01104180, invoice unavailable; grant closed with no rerun or transfer. The raw receipt, source-first review, artifact and hashes are preserved. H was direct without treatment and not called. This development-exposed source cannot qualify unseen diversity or H efficacy; continue unexposed source qualification and a separate provider-free G interface repair without changing this consumed run.
- The [candidate G v5 generic workspace](docs/HCL_I02_GENERIC_WORKSPACE_V5.md) adds executable source-versioned quote memory, provisional support/challenge links, bounded generic answer steps and correction invalidation. C/P, original source and answer contract stay fair; G still uses two charged calls when its map succeeds. Provider-free source/negative/revision/composition tests passed, but the consumed EPC run exposed a map-length interface failure. Its semantic competence is **UNQUALIFIED**; any next candidate needs a separately versioned provider-free repair and a genuinely new development source before I03.
- The separately versioned [G v6 compact comparator](docs/HCL_I02_GENERIC_WORKSPACE_V6.md) bounds map rows, quote lengths and UTF-8 response size, preserves full source and v3 C/P, and fails closed on invalid or stale source maps. Provider-free positive/negative/composition/revision/historical checks passed. The subsequent KPU development run used one G-map call, which returned exact but overlong quotations and was rejected; G-final made 0 calls. G remains **MODEL-SEMANTICALLY UNQUALIFIED**. Both EPC and KPU sources are consumed; I02 still needs eligible unexposed source diversity before any I03 comparison.
- The bounded [v3 rights/privacy source screen](docs/HCL_I02_RIGHTS_PRIVACY_SOURCE_SCREEN_V3.md) rejects an OpenStax book with an explicit no-LLM-ingestion notice and a CC BY Open Oregon activity involving potentially identifiable sensitive family history. Neither entered a provider, neither is independent confirmation, and the v2 frozen lineage stays unchanged. The new wrapper requires canonical URL, source/question hashes and reviewer assertions of model-use rights, privacy and native-question fit; assertions alone are not qualification evidence. **0 real source items qualified / 0 calls**. Continue genuinely unexposed source qualification without recycling these systems.
- The [EPC engineering ethics development screen](docs/HCL_I02_EPC_GLASS_SCREEN.md) fixed one independent native open-question source before checking H, separated scenario from editorial/external-code material, and found H's actual ordinary route direct with no cognition treatment. The case and author system are development-exposed, not provider or confirmation qualified. No paid call; continue truly unexposed source qualification and comparator calibration without changing the question to trigger H.
- The [I02 complete-source coverage audit](docs/HCL_I02_LONG_INPUT_COVERAGE.md) records an observed H ordinary-entry failure for every pinned SQuALITY dev source length (25/25 above 16,000 characters); C/P/G accept those lengths under 64,000. The executable provider-free receipt keeps full ordinary inputs and refuses to relabel H rejection as acceptance. Do not truncate or remove long cases to make H eligible. No source item or H efficacy is qualified, no provider call was made, and the frozen HCL runtime is unchanged.
- A [bounded OER source screen](docs/HCL_I02_OER_BOUNDED_SCREEN.md) rejected promotion of the first SQuALITY/Gutenberg story and visible TRU/Rebus/Ethics Bowl material: story jurisdiction, case-specific license and source-bounded item fit remain separate gates. Exposures are now rejected by the executable lineage guard. No paid calls, qualified case or H efficacy result. Continue genuinely unexposed source qualification without recycling these examples as confirmation.
- The [G workspace v4 boundary](docs/HCL_I02_G_WORKSPACE_V4_BOUNDARY.md) closes a generic comparator parser leak: map rows can no longer carry extra answer/oracle-like fields into G-final under a valid quote. It preserves v3 prompts, complete ordinary source and two-call G accounting. Only provider-free correctness is shown; comparator model competence and I03 source qualification remain open.
- A [bounded narrative source screen](docs/HCL_I02_NARRATIVE_SOURCE_BOUNDARY.md) records development exposure of NarrativeQA *Amy Foster* questions/reference answers and Narrative Crossroads teacher modules. Teacher character profiles/sample responses are editorial aids, not ordinary source. The executable lineage guard rejects related story authors and exact screened source digests even when declared IDs change. No I01 item or model input qualified, no calls/spend; continue genuinely unexposed provenance, native task fit and rights screening.
- A [bounded QuALITY development-source screen](docs/HCL_I02_QUALITY_BOUNDED_SCREEN.md) found direct CC BY notices but rejected the preselected article as an I01 abstract concept/philosophy witness; exposed article/questions and a separate catalog plot summary are recorded in the lineage firewall. Zero new model-qualified or confirmation-qualified sources; continue truly unexposed source qualification without switching rows for H outcomes.
- I02 structural catalog audit can now report restricted family/source-system coverage without granting provider or efficacy qualification; the full I01 four-family/three-system gate remains enforced. See [restricted coverage report](docs/HCL_I02_RESTRICTED_COVERAGE_REPORT.md).
- Provider work: **BOUNDED NORMAL DEVELOPMENT UNDER LATEST OWNER DEFAULT AUTHORIZATION**
- Long-horizon live-entry calls: **1 extraction / 0 final / 0 retries**; peak-rated **USD 0.00076710**, estimated **USD 0.00038355**, invoice unavailable. FAILED/CLOSED; no rerun, workflow disabled. [Receipt/closure](reports/HCL_ORDINARY_ENTRY_FUNCTIONAL_CLOSURE.md).
- G-ARCH one-shot: **2 extraction/final calls, 0 retries, peak-rated USD 0.00159300, conservative guard USD 0.00590436 / USD 0.04 cap; CLOSED / NO RERUN**. [Receipt/closure](reports/HCL_G_ARCH_ENTRY_CLOSURE.md).
- I02 C/P/G one-shot: **3 calls (C, P, G-map), 0 retries, estimated USD 0.00367950, rated-peak USD 0.00735900 / USD 0.12 cap; FAILED SHAPE / CLOSED / NO RERUN**. G-final and H/H-new: **0 calls**. [Full raw receipt and source-first closure](reports/HCL_I02_CPG_CALIBRATION_CLOSURE.md).
- I02 Moral Stories second-source C/P/G one-shot: **4 calls (C, P, G-map, G-final), 0 retries, estimated USD 0.00416724, rated-peak USD 0.00833448 / USD 0.06 cap; INTERFACE FUNCTIONAL / SEMANTICALLY UNQUALIFIED / CLOSED / NO RERUN**. H/H-new: **0 calls**. [Full raw receipt and source-first closure](reports/HCL_I02_MORAL_CPG_CALIBRATION_CLOSURE.md).
- Independent qualification active: **I01 FROZEN / I02 NEXT; NO CONFIRMATION RESULT INSPECTED**
- Leaderboard: **OFF**
- LongMemEval: **SEALED / NOT ACCESSED**

The [general v2 ordinary information-state repair](docs/HCL_I02_INFORMATION_STATE_V2_REPAIR.md) passes provider-free treatment presence and H/H-new structural fairness on the exposed native item. G-map v2 passed its first actual interface run on the second exposed source, but C/P/G semantic qualification remains open. The [source-first semantic scorer v1](docs/HCL_I02_SEMANTIC_SCORER.md) freezes general review dimensions, exact-source citation validation, unresolved-zero accounting and critical-error eligibility; it is not itself a semantic judge or HCL answer gain. The [source-lineage v2 firewall](docs/HCL_I02_SOURCE_LINEAGE.md) makes the two I02 calibration and five named historical writing systems ineligible as unseen confirmation even under a new row ID; a screened ETHICS system had one public snippet exposed and was not promoted. This bounded list does not complete the repository-wide exposure audit. A [v3 C/P/G provider-free candidate](docs/HCL_I02_CPG_V3_REPAIR.md) asks P/G to preserve explicit goals while narrowing unknown harmful intention, with C and ordinary inputs stable; its model semantics remain unqualified. The preselected FairytaleQA long narrative has an [exact blind match to pinned Gutenberg #4018](docs/HCL_I02_FAIRYTALE_BLIND_PROVENANCE.md). Its [pinned question-tag screen](docs/HCL_I02_FAIRYTALE_QUESTION_TAG_AUDIT.md) finds 55 local and six summary questions, with no summary character/feeling tag. A separate [annotation provenance check](docs/HCL_I02_FAIRYTALE_ANNOTATION_RIGHTS.md) pins expert-authorship statements and the publisher root Apache 2.0 license, while keeping provider geography and use scope unresolved. No story, question or answer text was displayed, but long-character task fit cannot be inferred from length or these tags. The [section-span check](docs/HCL_I02_FAIRYTALE_SECTION_SPAN.md) finds that all six summary items reference only two nearby sections (maximum span two of 43) and none has a summary character/feeling tag. This preselected source is not qualified for I01 long character development; preserve the negative screen and do not substitute a new row based on H outcomes. Continue genuinely unexposed source diversity, protected split, item semantic audit and strong C/P/G qualification before sample-size/model/cost freeze. Both calibration grants are closed and cannot be rerun; no H efficacy scoring or I03 confirmation access yet.
The dependency-safe queue continues
without asking for a new decision after every package.
