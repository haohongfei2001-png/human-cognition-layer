# HCL Development Plan

Status: **CANONICAL LIVE EXECUTION PLAN — LONG-HORIZON CAPABILITY GROWTH / WAVES A–B COMPLETE / WAVE C / NEXT_READY=C01**

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

## 5c. Current Wave C — Goals, Plans and Appraisal

**C01 — NEXT_READY:** source-bounded goals/subgoals, means, plans, conditions,
opportunities, completion and abandonment. Keep stated intention distinct from
observed behavior and later outcome. Reuse v0.7/v0.8 thin structures and conditional
checks; require an ordinary-input positive goal/plan witness. Then C02 competing
action explanations → C03 belief-dependent plans → C04 appraisal → C05 integration.

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

- Current wave: **Wave C — Goals, Plans and Appraisal**
- A00: **COMPLETE** through adoption of the long-horizon canonical plan
- **NEXT_READY: C01_GOAL_AND_PLAN_OBJECTS**
- Provider work: **BOUNDED NORMAL DEVELOPMENT UNDER LATEST OWNER DEFAULT AUTHORIZATION**
- A01–A05/B01–B05 actual provider calls / spend: **0 / USD 0**
- Independent qualification active: **DEFERRED UNTIL POST-G-ARCH SERIOUS EVALUATION**
- Leaderboard: **OFF**
- LongMemEval: **SEALED / NOT ACCESSED**

Work should continue at **C01**, then continue through the dependency-safe queue
without asking for a new decision after every package.
