# G05 — Premise, concept and counterfactual sensitivity

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** From an ordinary question over G04 source arguments,
HCL now compares up to three *independent* one-factor changes: an exact fact
premise assumed false, one actor's G03 concept reading switched to another
source-backed reading, or one explicit source-reported value priority reversed.
It identifies which argument path loses support or changes interpretation and
which path is structurally unaffected. It leaves truly unresolved conclusions
unresolved instead of rewriting source evidence or declaring a winner.

`ArgumentSensitivityWorkspace` reuses G04's premise/source map and G03's
actor/context concept comparison. The question accepts bounded “If …, what
changes?” sentences; unmatched, ambiguous or cross-context changes are
refused. A fact variant must match an exact argument premise; a concept switch
must match exactly one recorded same-term comparison and enter an argument; a
value reversal must reverse exactly one explicit speaker priority and enter
that speaker's argument. Each scenario preserves its caller origin and records
its source basis, the unchanged G04 base, affected and unaffected arguments,
and the actual final model input. Source correction or access revocation
invalidates saved input. A historical source-prefix view does not backfill
later arguments or priorities.

“Structurally unaffected” only means the supplied one-factor perturbation did
not touch that argument path. It does not mean the conclusion is true. A
changed reading or value premise makes the conclusion conditional and
unresolved; it does not prove a truth flip. A fact report is not world truth;
an already contested or unsupported premise remains unresolved. No generic
formal solver is invoked without separately declared formal input.

The [ordinary witness](../reports/HCL_WAVE_G05_WITNESS.json) saves all three
variants and actual final model messages. Twelve targeted tests cover
positive sensitivity, robust path, contested and missing facts, same versus
different concept readings, unsupported and unrelated variants, actor/context,
source-prefix replay, access/record cutoffs, stale input and context budget.
Provider calls/spend: zero. LongMemEval sealed. NEXT_READY: G-HC gate before
Wave H.
