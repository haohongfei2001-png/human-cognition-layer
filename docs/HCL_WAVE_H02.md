# H02 — Finite rival explanations and discriminating evidence

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** Two opposed source arguments can now remain distinct
candidate explanations while HCL retrieves *separately authorized* evidence
that changes the status of a specific premise. In the ordinary witness, one
candidate receives a direct narrator report of its premise and the other
receives an explicit narrator counterreport. The latter is weakened
conditionally; the former is not thereby promoted to a true or unique answer.
When retrieval adds no matching support, counterevidence or attributable
uncertainty, the search stops rather than repeating reflection.

`DiscriminatingEvidenceWorkspace` reuses H01's question/actor selection, G04's
two source-reported arguments and F01's indexed, source-local, access-filtered
event retrieval. The argument source and evidence corpus are distinct; finding
the argument itself cannot count as new corroboration. At most two opposed
arguments and six explicit premises are compared. A query retrieves at most
eight excerpts by default and is rejected if truncation could hide relevant
counterevidence. Each accepted excerpt keeps exact original text, source span,
corpus record version, speaker/assertion scope and the support/challenge label.
Third-party speech can sharpen attribution uncertainty but never verify the
fact. A miss is not absence or a character's ignorance.

The source pool is versioned and filtered by observer, event, access and analyst
record cutoff before F01 indexing. Source correction, visible additions and
access revocation invalidate saved final model input; a hidden unrelated source
does not. Retrieval count and no-gain/budget stop reasons are explicit. The
present matcher accepts exact narrator premises and explicit `is/was/could/has
not` opposites; other negation and paraphrase remain unresolved. No broader
natural-language evidence entailment or world-truth claim is made.

The [ordinary witness](../reports/HCL_WAVE_H02_WITNESS.json) saves before/after
rivals, retrieved event IDs, gain labels and actual final model input. Fourteen
targeted tests cover positive discrimination, no-gain stop, source boundaries,
quoted attribution, correction, hidden/late/access-denied evidence, budgets,
explicit negation and missing evidence. Full v1 and historical regressions
remain exact-head/main gates. Provider calls/spend: zero. LongMemEval sealed.
NEXT_READY: H03 cross-capability support and counterevidence propagation.
