# G03 — Local concept criteria and revision

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** From ordinary authorized text, HCL can now distinguish an
actor's necessary, sufficient and typical criteria for a local concept. It can
test those criteria against attributed feature claims, identify reported
counterexamples, compare actor/context readings and replay an explicit concept
revision without rewriting earlier applications. This extends CG05's bounded
conjunctive definition check; it does not establish shared meaning or moral
truth.

`ConceptCriteriaWorkspace` accepts one versioned source domain, an ordinary
question and optional observer/time/source-prefix scope. Each parsed statement
retains its exact source quote, offset, order, version and span ID. Only exact
explicit rule, feature, use, equivalence and revision forms enter the operation;
unparsed claims stay unresolved. Conditions reuse CG05's explicit bounded
predicate grammar. Source line order is not calendar time. A correction or
access change invalidates saved final model input.

A failed necessary criterion refutes only the local conditional application;
meeting it does not prove application. A met sufficient criterion supports only
the local conditional application; failure leaves it unestablished. Typical
match never entails application. Conflicting narrator feature reports remain
contested. A positive use despite failed necessary condition, or negative use
despite met sufficient condition, is a source-reported counterexample rather
than a reason to erase either statement. Same-word readings are compared only
with source-backed actor/context distinctions. Different words require both an
explicit same-actor equivalence statement and matching live criterion sets.
Revision requires an exactly matching prior active local criterion; malformed
or mismatched revisions remain unresolved. Earlier source-prefix snapshots and
their uses are preserved.

The [ordinary witness](../reports/HCL_WAVE_G03_WITNESS.json) saves the source,
before/after states and actual final model messages. Twelve targeted tests cover
the positive case, counterexamples, negative inference, actor/context and
source boundaries, revision replay, ACL/time, stale input and unsupported forms.
Provider calls/spend: zero. LongMemEval sealed. NEXT_READY: G04 abstract
argument and philosophical disagreement localization.
