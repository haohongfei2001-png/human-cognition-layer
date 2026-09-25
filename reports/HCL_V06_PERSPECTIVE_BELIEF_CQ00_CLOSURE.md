# HCL v0.6 Perspective/Belief CQ-00 Closure

Status: **CLOSED / FANToM QUALIFIED / DynToM NOT QUALIFIED FOR CURRENT EVIDENCE-CONSTRAINED PRIMARY USE / ZERO PROVIDER CALLS**

## Scope

CQ-00 tested whether the first v0.6 candidate capability — evidence-constrained character perspective and belief revision — can enter a small external development qualification without leaking prior exposure, gold answers, hidden mental-state trajectories or benchmark-specific semantic rules.

No v0.6 cognition runtime was implemented. No provider-backed model was called. The frozen v0.5 LongMemEval efficacy package was not triggered.

## Exact zero-provider certification

PR candidate CI:
- workflow: `HCL v0.6 Perspective Belief CQ-00`
- run: `36119304220`
- conclusion: **SUCCESS**
- artifact: `10856742534`
- artifact digest: `sha256:a22cea64022a09045d5ac13a8676abf9b36ac41f5e363cfe1fbc4c35cc429609`
- provider calls: **0**

The provider-free artifact froze source pins, exposure accounting and deterministic development/audit selections before any model outcome was observed.

## FANToM qualification

Pinned source:
- repository: `skywalker023/fantom`
- commit: `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- dataset SHA-256: `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Exposure boundary:
- historical v0.1 + v0.2 consumed conversations: **80**
- exclusion is enforced at the complete-conversation level, including all questions associated with each consumed conversation.

After excluding those 80 conversations:
- eligible conversations found by the CQ-00 task-family inventory: **165**
- deterministic development selection: **8 complete conversations**
- selected IDs: `119, 197, 240, 7, 220, 189, 208, 36`
- selection covers first-order inaccessible belief, second-order inaccessible belief, full-context answerability and full-context information-access families.
- no selected conversation content was manually inspected during selection;
- no selected development conversation has been provider-consumed.

Decision: **FANToM PASS for CQ-01 development qualification.**

This is not fresh efficacy evidence. These eight conversations become development-consumed on first manual outcome inspection or provider execution and cannot later be relabeled as sealed efficacy evidence.

## DynToM source audit

Pinned source:
- repository: `GAIR-NLP/DynToM`
- commit: `9c95b1b8300f3e352626feae51aaeeda111b6d3d`

Zero-provider inventory found:
- **1,161** trials containing public stories and belief-focused questions;
- the upstream question-generation code derives belief state/change answers from a hidden mental-state sketch stored separately from the public story.

This does not make DynToM invalid. It means that, for HCL's current evidence-constrained claim, the hidden sketch cannot automatically be treated as an observable psychological truth. CQ-00 therefore froze four audit trials before content inspection and compared only their public narrative evidence with the generated belief labels.

Deterministic audit trials:
- `111`: **PASS**
- `364`: **FAIL — strict evidence sufficiency**
- `420`: **FAIL — strict evidence sufficiency**
- `534`: **FAIL — strict evidence sufficiency**

Audit criterion:
a belief label or transition is acceptable for the current HCL claim only when the public story directly supports it or makes it the uniquely warranted interpretation. A plausible interpretation that is stronger than the text, one of several reasonable readings, or changes modal/temporal force is not treated as psychological ground truth.

Observed failure classes:
- stronger/non-unique belief inference from behavior or conversational reaction;
- interpersonal states such as forgiveness/upset inferred beyond what the public narrative uniquely establishes;
- modal/temporal strengthening, such as a future possibility becoming a categorical present belief.

Result:
- strict-pass audit trials: **1/4**
- trials with at least one material evidence-sufficiency problem: **3/4**

Decision: **DynToM FAILS CQ-00 for current evidence-constrained primary use.**

This is a benchmark-fit result, not a claim that DynToM is a poor benchmark. DynToM is designed to evaluate agreement with generated dynamic mental-state trajectories; the current HCL candidate instead requires a tighter public-evidence boundary.

Eight additional trials were deterministically reserved before the audit:
`612, 987, 178, 903, 1018, 984, 674, 357`.

Their story/question/gold content was **not inspected** and no provider accessed them. They remain unconsumed, but they are not eligible for CQ-01 under the current contract. A future DynToM use would require a separately frozen benchmark-independent evidence criterion; it must not be repaired by inspecting these reserved trials.

## CQ-00 conclusion

The v0.6 candidate direction survives qualification only through FANToM at this stage.

CQ-01 may therefore ask a narrower question:

> On eight disjoint, previously unconsumed FANToM conversations, does a current strong base model still make repeated information-perspective / belief errors after a thin perspective scaffold?

CQ-01 must run only:
- **C** — strong direct reasoning control;
- **P** — thin perspective scaffold.

No specialized v0.6 state machine is authorized yet.

The CQ-01 implementation gate remains:
- residual errors in at least 3 distinct development scenarios;
- at least 2 semantic families among information access, belief attribution and temporal revision, insofar as the qualified source supports them;
- semantic audit confirms real reasoning errors rather than formatting, truncation or disputable gold.

Because DynToM failed CQ-00, cross-source reproduction is not required for this small development qualification. A later specialized D mechanism still requires fresh external efficacy beyond these development conversations.

## LongMemEval disposition

Unchanged:
- trigger file absent;
- sealed 32 efficacy rows provider-unconsumed;
- paid run deprioritized;
- frozen selection, chronology, firewall, one-shot, generic-baseline budgeting, paired statistics and cost accounting retained as reusable infrastructure.

## Current gate

CQ-00 is closed.

Before CQ-01, the owner must separately choose/authorize:
- the current strong base model/provider;
- exact model identity and reasoning budget;
- API access;
- a bounded monetary cap.

**Current gate: HCL_V06_PERSPECTIVE_BELIEF_CQ01_FANTOM_PROVIDER_MODEL_COST_AUTHORIZATION**
