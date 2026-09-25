# HCL v0.6 Capability Qualification — Evidence-Constrained Perspective & Belief Revision v0.1

Status: **DESIGN FROZEN / ZERO-PROVIDER QUALIFICATION IMPLEMENTATION NEXT / NO v0.6 COGNITION RUNTIME AUTHORIZED**

## Purpose

HCL v0.6 starts from the long-term HCL objective rather than from a benchmark:

> improve a base model's ability to understand and reason about human cognition — including psychology, people, social cognition, narrative, values, morality and complex concepts — without treating any current HCL mechanism as an end in itself.

The first v0.6 candidate capability is deliberately narrow:

> **Given a multi-person, time-varying conversation or narrative, distinguish what each person could access, what they publicly expressed, what beliefs are supported by the available evidence, and what later evidence is sufficient to support a belief revision.**

This qualification phase asks whether current strong base models still show a stable gap here after a very thin perspective scaffold. It does **not** assume that a specialized HCL mechanism is necessary.

## Why this is the next candidate

Current v0.5 provides useful assets:
- actor and time binding;
- explicit self-stance extraction;
- evidence routing and provenance;
- persistent auditable state;
- deterministic stance revision semantics.

Those assets cover a narrow part of human cognition. They do not establish general belief understanding, third-person mental-state attribution, motivation, emotion, relationship understanding, literary interpretation, moral reasoning or philosophical/conceptual reasoning.

v0.6 therefore tests one adjacent capability that:
1. reuses the reliable evidence/time/actor boundary;
2. has externally testable failure modes;
3. can be falsified before a larger ontology is built;
4. moves HCL from "maintain an explicit stance" toward "reason inside a person's information perspective."

## Frozen claim boundary

This phase may claim only a qualification result about **perspective and belief revision**.

It must not claim:
- general Theory of Mind;
- personality understanding;
- hidden-motive diagnosis;
- emotion dynamics;
- relationship quality;
- moral correctness;
- literary understanding as a whole;
- philosophical or conceptual reasoning as a whole;
- general long-term memory superiority;
- cross-model transfer unless separately executed.

A negative result is valid. If a thin scaffold or a generic structured representation is sufficient, HCL should adopt the simpler mechanism rather than preserve complexity.

## Semantic boundaries that v0.6 must respect

### 1. Information exposure is not belief revision

Receiving a challenge to a prior belief does not imply that the person accepted it, rejected it, or became psychologically uncertain.

The representation must distinguish:
- prior evidence supporting a belief;
- later exposure to challenging evidence;
- explicit acceptance or rejection;
- evidence-supported revision;
- insufficient evidence about the person's current belief.

### 2. Character uncertainty is not system uncertainty

These are separate states:
- **character uncertainty**: evidence supports that the person is unsure;
- **system uncertainty**: the available evidence is insufficient to determine what the person believes.

The latter must never be rewritten as a psychological state of the person.

### 3. Public expression is not automatically private belief

Evidence identity must distinguish at least:
- direct self-report;
- third-party report;
- narrator assertion;
- observed action;
- system inference.

A self-report is evidence about belief, not infallible access to an inner mental state.

### 4. Narrator knowledge is not character knowledge

Information visible to the reader or evaluator must not automatically enter every character's perspective.

### 5. Open beliefs are not forced into one issue/value cell

A proposition may be conditional, partially supported, temporally scoped, or not safely equivalent to another proposition. v0.6 must not force arbitrary proposition merging merely to keep state compact.

## Initial scope

The first candidate supports:
- first-order perspective: what A has access to / can reasonably believe;
- bounded second-order perspective: what A can infer about B's belief from information A has access to;
- temporal evidence changes;
- explicit belief support, challenge and revision;
- abstention when the evidence is insufficient.

It does not support arbitrary recursive mental-state depth.

## Qualification stages

### CQ-00 — zero-provider benchmark and exposure qualification

No model call is allowed.

Tasks:
1. Re-audit the existing exposure register.
2. Pin the upstream FANToM source already used by the project: skywalker023/fantom@1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85.
3. Pin the DynToM source already qualified as a future cognition candidate: GAIR-NLP/DynToM@9c95b1b8300f3e352626feae51aaeeda111b6d3d.
4. Verify that future FANToM freshness is enforced at the **complete-conversation** level. The 80 historically consumed FANToM conversations remain excluded with all associated questions.
5. Inspect only schema, metadata, task families and public evaluation logic needed to define a deterministic development selection. Do not inspect outcomes in order to hand-pick easy or HCL-favorable cases.
6. For DynToM, verify that the public narrative itself is sufficient for the belief-state/change questions selected for qualification. Hidden generator state, transition labels and gold reasoning fields must not enter state construction.
7. Freeze a deterministic, disjoint development qualification set before any provider call:
   - 8 eligible complete FANToM conversations;
   - 8 eligible DynToM belief-focused social scenarios;
   - selected by a deterministic ID hash rule after all exclusion rules are applied.
8. Register those 16 scenarios as **development-consumed upon first provider execution**. They can never become fresh v0.6 efficacy evidence.

CQ-00 passes only if both sources can be adapted without leaking gold, hidden mental-state trajectories or benchmark-specific rules into the candidate mechanism.

### CQ-01 — limited strong-model gap probe

This stage requires a separately authorized provider/model choice and bounded monetary cap. It is not authorized by this contract alone.

Run only two arms first:

- **C — strong direct reasoning control**
  - full official context;
  - question released only at answer time;
  - reasonable fixed reasoning/output budget;
  - no HCL state.

- **P — thin perspective scaffold**
  - same context and answer budget;
  - before answering, explicitly organize only which actor had access to which evidence at the relevant time;
  - no persistent HCL state;
  - no benchmark-specific transformation rules;
  - no gold, answer or hidden trajectory access.

The probe must record:
- official task outcome;
- full raw responses;
- whether the error is information-access, belief-attribution, temporal-revision, ordinary reading, output-format or benchmark/gold ambiguity;
- cost and latency.

#### CQ-01 decision rule

A specialized v0.6 mechanism is justified for implementation only if the thin P arm still leaves a **repeated residual perspective/belief error** that:
- occurs in at least 3 distinct development scenarios;
- is represented in both external sources, unless one source fails CQ-00 qualification;
- spans at least 2 semantic error families among information access, belief attribution and temporal revision;
- survives semantic audit as a real reasoning error rather than formatting, truncation or disputable gold.

If this gate does not pass, **do not build a larger perspective/belief state machine**. Close this candidate as unqualified and evaluate another human-cognition capability direction.

### CQ-02 — minimal mechanism authorization

CQ-02 is reachable only after CQ-01 passes.

The minimal D candidate may contain only:
1. **evidence extraction** — actor, proposition, time, source and information-exposure cues;
2. **perspective boundary** — filter evidence by what the target actor could access at that time;
3. **belief evidence state** — support, challenge, explicit acceptance/rejection, revision evidence and system-insufficient-evidence;
4. **bounded answer interface** — answer from the selected perspective without recursive self-reflection loops.

Default implementation principle:
- reuse v0.5 persistence/provenance primitives where useful;
- do not require one model call per event when the whole scenario fits a bounded common context;
- do not introduce personality, emotion, motivation, relationship, moral or philosophical ontologies in this stage.

## Later efficacy comparison

A later fresh efficacy pilot is not authorized yet. If CQ-02 produces a frozen minimal mechanism, the comparison must include all four arms:

- **C** — strong direct reasoning;
- **P** — thin perspective scaffold;
- **G** — competent generic structured state with actor/time/source/uncertainty and no artificial event-loss weakness;
- **D** — frozen v0.6 perspective/belief mechanism.

All arms must receive the same source evidence and comparable total inference budgets. State construction must not see the question, answer, options, gold labels or hidden mental-state trajectory.

Candidate external evidence sources:
- fresh, unconsumed complete FANToM conversations for information asymmetry / belief / answerability;
- DynToM belief-state and belief-change tasks that pass CQ-00 evidence sufficiency review.

A larger 32+32, two-model-family pilot may be frozen later, but is deliberately **not** part of the current qualification authorization.

## Retain / modify / delete rule

Retain a specialized mechanism only when external evidence shows that it reduces the targeted perspective/belief errors beyond C, P and a competent G under fair budgets.

Modify only when failures identify a benchmark-independent semantic boundary defect such as:
- leaked narrator knowledge;
- conflating system uncertainty with character uncertainty;
- treating exposure as acceptance;
- incorrect temporal access;
- incorrect source attribution.

Delete or demote the mechanism when:
- P is already sufficient;
- G is equally accurate at lower complexity/cost;
- gains appear only on repository-authored synthetic fixtures;
- gains depend on weakened baselines;
- structured extraction overwrites correct base-model understanding.

## LongMemEval disposition

The existing v0.5 LongMemEval 32-row C/D/G package remains frozen and valid.

For v0.6:
- do not add its trigger;
- do not consume its 32 sealed rows;
- do not acquire credentials or paid access merely to unblock it;
- preserve its selection, hashes, chronology adapter, gold firewall, one-shot execution design, competent G budget handling, paired statistics and cost accounting as reusable research infrastructure.

LongMemEval may be resumed later if the project specifically needs to answer a long-term state/memory engineering question. It is not a prerequisite for this human-cognition capability qualification.

## Intellectual-property and evidence boundary

- Do not publish owner-private conceptual examples.
- Do not copy benchmark story/question/answer content into the public repository.
- Store only permissible identifiers, hashes, aggregate metadata and derived non-sensitive audit artifacts.
- Every provider-exposed development scenario becomes consumed evidence.
- No result from CQ-01 may be relabeled as fresh efficacy evidence after mechanism development.

## Current authorization

Authorized now:
- CQ-00 zero-provider implementation and certification only.

Not authorized by this contract:
- provider-backed CQ-01;
- v0.6 cognition-runtime implementation;
- fresh efficacy runs;
- LongMemEval paid execution;
- model training.

**Current gate: HCL_V06_PERSPECTIVE_BELIEF_CQ00_ZERO_PROVIDER_QUALIFICATION_NEXT**
