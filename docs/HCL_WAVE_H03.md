# H03 — Cross-capability execution and local revision

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** A single ordinary account can now yield a connected,
source-rooted conditional path from a person's reported belief through a plan
check to an expectation interpretation and a relationship interpretation.
Correcting the account changes each dependent analyst result, while a separate
source and its final model input remain cached. This goes beyond placing four
independent module outputs in one prompt: the plan claim already depends on the
reported-belief transition; the expectation claim requires the actual plan and
D04 promise check; the relationship claim requires that expectation claim and
E05 source-linked failure/view check. The shared `EvidenceCore` propagates a
challenge or withdrawal along these real edges.

`CognitiveExecutionGraph.prepare_graph` accepts a bounded ordinary question
and an authorized source. It invokes the existing B03/C03 reported-belief and
plan check, D04 expectation check and E05 relationship/role check on the same
semantic workspace. An exact actor/action/condition join is required. The
graph records the two added conditional dependency edges, their source
obligations, input source version, and actual final model input. An analyst
source correction retires the old graph and recomputes only the affected
source/question; unrelated sources are reused without execution. There is one
optional answer backend call and no constructed provider client or retry.

The [ordinary witness](../reports/HCL_WAVE_H03_WITNESS.json) changes Mira's
reported belief about a permit and her self-reported action-time knowledge.
The plan changes from conditionally supported to contradicted under reported
beliefs. The expectation's plan dependency changes; the promise and Noor's
reported expectation stay the same. The information-gap relationship
explanation loses support, while Noor's separately reported distrust stays
reported. The saved before/after final inputs and an unchanged club source
make the delta inspectable.

This is still a narrow, exact ordinary-language slice. Matching source reports
are assumptions about sincerity and accuracy; a plan check is neither world
feasibility nor intent. A mismatch is not a proven cause of misunderstanding,
and a relationship interpretation does not rewrite a person's attitude or
establish blame. Unknown, conflict, third-party, missing action, condition
mismatch and unauthorized access do not silently fill gaps. The graph does not
yet establish broad cross-capability language understanding or independent
model utility. H04 is the next answer audit layer, and G-ARCH remains the
architecture gate before serious independent evaluation.

Eight targeted tests cover positive revision, real dependency propagation,
source-local non-interference, actor/condition refusal, absent evidence,
authorization, budget and actual final input. Full v1/historical regression
and exact-head/main CI are required. Provider calls/spend: zero. LongMemEval
remains sealed.

**NEXT_READY:** H04 answer synthesis and bounded support audit.
