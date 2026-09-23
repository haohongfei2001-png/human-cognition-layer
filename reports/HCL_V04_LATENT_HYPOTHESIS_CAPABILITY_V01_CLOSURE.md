# HCL v0.4 Latent-Hypothesis Capability v0.1 — Closure

Status: **COMPLETE / REPRESENTATION WORKS, NO INCREMENTAL PREDICTION UTILITY**

Internal development evidence only.

## Frozen protocol

- plan: `reports/HCL_V04_LATENT_HYPOTHESIS_CAPABILITY_V01_PLAN.md`
- fixtures: `eval/v04/latent_hypothesis_capability_v01.json`
- six controlled hidden-state scenarios;
- twelve behavior predictions;
- same model: `deepseek-flash`;
- seed: 42.

Arms:
- C — static full-history hypothesis reconstruction;
- D — dynamic persistent hypothesis tracking;
- E — ordinary full-history prediction with the same candidate definitions.

## Canonical run

- workflow: `HCL v0.4 Latent Hypothesis Capability v0.1`
- run: **35849522485**
- head: `bcc2e5499d8021ae89f39a725f00347bed49d227`
- result: **SUCCESS**
- artifact: **10745056495**
- digest:
  `sha256:862cf542be1bb2d8deee5d632b6bfea75742804cdd43b8738a26d22e7f488978`

## Behavior prediction

- C: **11/12 = 91.7%**
- D: **12/12 = 100%**
- E: **12/12 = 100%**

D corrected one behavior-prediction miss made by C:

- scenario: teammate_delay
- second query
- gold: START_TASK
- C: CONTINUE_AVOIDING
- D: START_TASK
- E: START_TASK

This is evidence that persistent sequential hypothesis updating can reduce one
static-reconstruction drift in this development set.

It is **not** an incremental end-to-end capability signal because ordinary
full-history reasoning E also answered correctly.

## Hidden-candidate diagnostic

The controlled hidden candidate was top-ranked or tied for top in:

- C: **12/12**
- D: **12/12**

Therefore the bounded hypothesis representation can maintain a compatible latent
interpretation on these controlled scenarios.

This does not establish real-human psychological validity.

## C vs D state stability

C and D normalized hypothesis states were identical on only:

- **1 / 12** query points.

Despite large representational differences:
- predictions matched on 11/12;
- D was correct on the one prediction disagreement.

Interpretation:
- latent hypothesis reconstruction is highly path-sensitive;
- persistent history can change the representation materially;
- the current set does not show that most of those differences matter for
  downstream behavior prediction.

## Cost

### C
- calls: 24
- input characters: 98,092
- output characters: 18,912

### D
- calls: 45
- input characters: 189,265
- output characters: 52,953

### E
- calls: 12
- input characters: 28,182
- output characters: 281

Dynamic per-event hypothesis updating is currently the most expensive arm.

Therefore:

> per-event latent-state maintenance is not justified as a general default by
> this result.

## Capability decision

Retain:
- bounded competing hypotheses;
- evidence/counterevidence;
- OTHER_UNKNOWN;
- version/audit history.

Do not claim:
- prediction superiority over ordinary memory;
- cost advantage;
- human mind-reading validity.

Do not keep making passive prediction tasks harder merely to force a D > E
result.

Instead move to a capability where an explicit hypothesis set can plausibly
change behavior in a structurally meaningful way:

> **Hypothesis-Guided Information Acquisition and Action**

The next module should use unresolved competing hypotheses to choose:
- which question to ask;
- which observation to seek;
- which reversible probe to perform;
- when enough information exists to act.

This returns the project to Adaptive Social Inference rather than passive
classification.

## Update-policy consequence

Per-event LLM hypothesis updates are too expensive as a default.

For future use:
- prefer lazy / query- or decision-triggered update;
- persist prior state;
- process newly accumulated relevant evidence in batches;
- use event-driven immediate update only when the downstream task requires it.

## Next gate

No external benchmark is authorized yet.

**Gate: HCL_V04_LATENT_PREDICTION_COMPLETE_HYPOTHESIS_GUIDED_ACTION_READY**
