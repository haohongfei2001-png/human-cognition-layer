# F03 — Selected evidence closure and incremental recomputation

## CAPABILITY_DELTA

HCL can now select one conclusion and carry its entire recorded dependency
closure into the final model input. Each alternative support path is kept; every
member required within a path stays together. Rooted challenges, competing
interpretations, conditional premises and historical analyst revision reasons
travel with the conclusion. A source challenge can be withdrawn, changing the
selected conclusion from contested to supported while an unrelated source edit
reuses the prior selected result. Evidence that no longer grounds a conclusion
remains explicitly marked as history.

`EvidenceClosureIndex` traverses the shared A01 graph and optionally links exact
F01 source events. It caches by the selected subgraph fingerprint. Changing an
unrelated chapter does not rerun extraction or rebuild that conclusion; changing
its rooted challenge, support or revision basis invalidates its prepared input.
Current access checks guard archived quotes. If the complete recorded closure
exceeds the node or input budget, selection refuses to drop counterevidence.

The closure is complete **for the selected recorded graph**, not proof that all
relevant world evidence was collected. New source evidence must be attached as a
support/challenge/alternative by the responsible operation. The index cannot
infer missing links or claim that absence of a challenge means no counterevidence.
This boundary matters for long-narrative answers and later answer audits.

The simplest alternative is serializing the full graph. A later serious evaluation
should test whether selective closure improves bounded reasoning enough to keep
this mechanism.

## Verification and limits

Ten targeted tests cover ordinary positive/negative statements, alternative and
joint supports, rooted challenge withdrawal, analyst revision, rootless cycle,
source access, separate observer scope, unrelated-source cache reuse and full
closure budget refusal. The ordinary witness saves actual final inputs before
and after challenge withdrawal in `reports/HCL_WAVE_F03_WITNESS.json`. Full v1
and 176 historical regressions run in exact-head/main CI.

Default 256 selected nodes (configurable to 1024), 64k final input budget.
State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.
No independent efficacy claim or provider calls. LongMemEval sealed. NEXT_READY:
F04 competing character development explanations.
