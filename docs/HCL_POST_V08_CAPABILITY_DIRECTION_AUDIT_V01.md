# Post-v0.8 Capability Direction Audit v0.1

Date: 2026-09-27. Select **evidence-constrained causal and counterfactual
reasoning** as a bounded conceptual reasoning candidate. v0.8 is frozen
SIMPLIFY; no CAREBench tuning continues. PR #83 closure merged as
`98115af8511df8252064da4eb207c9a443d19f19`, exact-main regression
`36263721472` passed.

This addresses how a changed condition can propagate to an outcome while
preserving the factual context, and when available evidence is insufficient.
It is a conceptual/narrative reasoning building block, not a claim to cover
open-world literary interpretation. No later version sequence is fixed.

| Direction | Current decision |
|---|---|
| Relationship/social cognition | [Multi-party relationship research](https://aclanthology.org/2026.iwsds-1.38/) motivates a gap. The corpus's public relationship evidence and current-model deficit are not established here; do not infer actual relationships from stylistic stereotypes. Defer. |
| Emotion/affect | The completed eight-source check did not establish typed-state utility over strong C. Keep the simplified evidence/uncertainty method and leave this candidate. |
| Narrative/character | Existing perspective, goals and affect assets remain reusable, but another mental-state classifier would repeat closed directions. Causal alternatives offer a distinct conceptual building block. |
| Moral/value | Conflicting standards are legitimate; crowd agreement is not moral truth. No source-qualified incremental mechanism selected here. Defer. |
| Conceptual reasoning | Select bounded factual conditioning, intervention and counterfactual consequence under explicitly declared models. A deterministic tool can expose logical constraints and preserve uncertainty without a psychological ontology. |
| Philosophical reasoning | Multiple defensible answers need a stronger utility criterion. No canonical-truth score or architecture selected. Defer. |

[Executable Counterfactuals, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/a50aa557c4be35aa2bf13a471601e23f-Abstract-Conference.html)
finds that holding latent context from a factual run is harder than simply
changing an input for evaluated reasoning models. It also warns that fully
observed formal exercises may only test intervention, despite counterfactual
wording. [WhatIfBench's primary abstract](https://arxiv.org/abs/2608.27953)
reports remaining gaps in open-domain causal explanations. These results
motivate a candidate; they do **not** establish a stable deficit of the current
DeepSeek alias or prove this small Boolean tool will solve open-world stories.

The minimal implementation precedes dataset inspection. It reuses EventRecord
and v0.6 source/time/access views, adopts published structural-causal-model
semantics, enumerates compatible factual contexts, then changes equations.
It never equates correlation, outcome or action with an established cause or
private motive. Source model assumptions remain conditional hypotheses.
The implementation is ordinary tool integration, with no novelty claim for
abduction–intervention–prediction or Boolean constraint solving.

After independent correctness, the external audit found CounterBench usable
only for a transparently **supplemented formal development task**. Its causal
wording needs an explicit equation interpretation; two selected sources have
inconsistent factual constraints under that interpretation. Its available
conditional cases do not adequately exercise informative latent abduction.
Native labels are withheld and no original benchmark score is produced.

Therefore stage a small direct/scaffold/tool-assisted check to establish
whether even this bounded computation warrants added cost. This candidate
must simplify to strong prompting if it lacks a development increment; if a
generic exact tool is sufficient, retain that simpler method rather than a
specialized cognition architecture. Fresh/full-abduction evidence needs a
separately qualified source; CounterBench alone cannot certify it. See
`docs/HCL_V09_COUNTERBENCH_DEVELOPMENT_UTILITY_V01.md`.
