# HCL v0.4 — Open-World Hypothesis Action v0.1

Status: **FROZEN INTERNAL CAPABILITY CONTRACT / NOT YET EVALUATED**

Baseline: remote main `2acbf28153c21ad8d43ea062a7d12043b1868f2a` and the evidence-scoped revision diagnostic closure. That experiment's C/E 6/6 and D/F 5/6 are consumed diagnostic evidence; its six cases are not reused here.

## Capability question

Can the existing always-on v0.4 hypothesis state retain `OTHER_UNKNOWN` when the named interpretations do not explain the evidence, and choose a useful low-risk information-gathering and final action without treating a hidden cause as established? The target is an open-world latent-state decision. This is a direct continuation of the frozen capability plan's limited alternative hypotheses, evidence/counterevidence, and prediction/communication interface. A simpler direct-history reasoner may be equally good or better.

## Bounded mechanism and invariants

- Reuse the mainline append-only evidence store, `HypothesisTracker`, and `HypothesisGuidedPolicy`; do not promote the failed experimental F branch or change the frozen semantic types, time model, policy options, checker, or v0.3 baseline.
- The target names two or three plausible interpretations plus the mandatory `OTHER_UNKNOWN`. Neither the target nor any model prompt reveals the controlled scenario's hidden explanation.
- All raw events remain immutable and visible to the permitted system perspective. Source assertions remain assertions; exposure does not imply belief. The named candidates and `OTHER_UNKNOWN` must cite only observed raw-event IDs. A later response can revise hypotheses but cannot rewrite a prior event or imply an unobserved agent received a correction.
- One bounded probe and one final action per scenario. No unbounded conversation, production integration, training, private owner material, new external benchmark rows, or new provider/model commitment.

## Precommitted comparison

Freeze 6–8 new, independently authored synthetic scenarios and their file digest before any provider call. Include some cases where a named candidate is supported, some where a cause outside the named set is controlled as true, and allowed low-information probe responses that remain insufficient. The visible question must not imply that `OTHER_UNKNOWN` always wins. Each fixture must declare the hidden simulation state, three allowed probes, their response for each possible hidden state, three allowed actions, grounded action mapping, and predeclared high-information probes. Distinct scenarios must cover source disagreement, an unseen correction, and a later response that contradicts an initial interpretation. Do not use prior guided-action, evidence-scoped, external benchmark, or owner-private scenarios as fresh evidence.

Frozen file: `eval/v04/open_world_hypothesis_v01.json`, six independently authored cases, SHA-256 `ad8d8e96ab6e3d251bda416a10e9f6eac028d87d5376b1c8eea0441ea3bcbe41`. The digest was recorded before any provider-backed execution of this file. The six controlled hidden states include three outside the named set and three named candidates; this split is for diagnostic coverage, not a population estimate.

Compare on the same existing `deepseek-flash` model and fixed options:

- C: reconstruct structured hypotheses from full history at each decision;
- D: maintain structured hypotheses across the response;
- E: direct full-history reasoning with the same visible choices and evidence.

The measured result is final-action correctness, high-information probe selection, `OTHER_UNKNOWN` retention and evidence validity, provider calls, input/output characters, and repair count. Unsupported certainty and grounded-state violations require a separate recorded semantic audit of the emitted state and action rationale; automated option correctness cannot substitute for that review. A single frozen pass is an internal diagnostic, not human-state truth, cross-model transfer, or external efficacy. At most eight scenarios may run. C/D each use at most two state updates and two decisions per scenario; E uses two decisions. Each call permits at most one bounded repair, giving an absolute ceiling of 160 provider calls. Stop rather than silently expanding the experiment.

## Correctness and falsifying outcome

Deterministic preflight must pass schema, event IDs, provenance, perspective separation, chronology, `OTHER_UNKNOWN` presence, no stale hypothesis use, and exact fixture digest. A grounded-state violation fails the structured arm regardless of final action. The controlled hidden state supports scoring an action inside a synthetic simulation only; it is not a claim that real human motives have ground truth.

If D is no better than E on safe action or information gain, or any difference does not justify its extra cost, do not claim incremental HCL capability. If D merely beats C in calls or stability, label it maintenance efficiency. If E dominates again, prefer the simpler path for this task class. Preserve all raw misses; never tune on observed cases and rerun them as fresh evidence. A new behavior change requires a separately frozen independent set.

The owner-authorized scope is one internal contract. No public release, external benchmark exposure, paid cross-model experiment, model training, private example disclosure, or general architecture amendment follows from this contract.
