# G04 — Abstract argument and philosophical disagreement

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** From ordinary authorized source text, HCL now separates
reported conclusions from their premise clauses, preserves a conditional
if-premises-then-conclusion map, and locates opposed speakers' pivotal disputes
across source-challenged facts, G03 local concept readings and explicitly
reversed value rankings that enter the arguments. It attaches source-reported counterexamples and
analogies to the targeted argument while keeping their validity unresolved.
This is more useful than listing two opinions; it states which premise or
reading could change the disagreement.

`ArgumentWorkspace` reuses G03's source version, observer/time/access check and
local concept comparison. Each parsed statement retains exact source text,
offset, order, version and span ID. The source grammar recognizes explicit
“I conclude … because …”, narrator fact reports, fact challenges, “I value X
over Y”, targeted counterexamples and proposed analogies. A claim is opposed
only for explicit `not X` or `is not` forms; other differing conclusions stay
separate. At most three conjunctive premises are split; unsupported or
oversized forms remain unresolved. The conditional map is a source-reported
inference, not an FOL translation or proof. Existing exact formal tools still
require separately declared formal input.

A narrator report is never world truth; a challenge is not proof of negation.
Value priority is public source speech, not a global weight or moral verdict.
Concept readings are actor/context bound and count as pivotal only when the
disputed term appears in both arguments. Unrelated concepts or value rankings
do not become explanations. The analysis does not infer private belief.
Counterexamples challenge a stated target without erasing it. An
analogy records the stated common feature without transferring a conclusion.
Source order is not calendar time. Later challenges do not alter earlier
source-prefix snapshots. Correction or access change invalidates saved final
model input.

The [ordinary witness](../reports/HCL_WAVE_G04_WITNESS.json) includes the
source, before/after argument states and actual final model messages. Twelve
targeted tests cover the positive split, unsupported premises, non-opposed
claims, unlocalized opposition, negative inference, concept composition,
source-prefix replay, actor/context and ACL/time boundaries, corrections,
unsupported forms and exact source spans. Provider calls/spend: zero.
LongMemEval sealed. NEXT_READY: G05 sensitivity across premise, concept and
counterfactual variants.
