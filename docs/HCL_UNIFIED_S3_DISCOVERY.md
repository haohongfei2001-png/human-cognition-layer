# S3 work in progress: shared residual-guided mechanism discovery

This increment continues approved M04 on main
`b24c826a10e299ff9c3d713dc0dcdd0ff2d65dd3` / PR #431. It is a first bounded
implementation, not closure of M04, S3, S4 or any T01–T32 acceptance family.
The approved S1–S7 stages, all P/M/T obligations and research exits remain.

## One actual discoverer and one actual entry

`hypothesis.discover` runs in the existing authenticated HCL run/run_sync/stream
execution graph. Its `discovery-model-1` LocalModel contains a source-bound
Explainandum, immutable context templates and observations, candidate programs,
a bounded edit grammar and prospective probes. The model port supplies an
unverified reconstruction. It cannot provide predicted labels, fit scores,
computed matrices, posterior probabilities or executable Python.

`operators/abduction.py` is the shared discovery mechanism. Production adapters
in `discovery_model.py` execute the existing real M03 event/belief, M05 action
value, M06 finite causal and M13 argument operators. They do not use a string
lookup, answer-key matching or prepopulated prediction matrix. The domain
adapter receives a mechanism and conditioning context, never the observation's
expected value. Comparison happens only after the solver returns. This typed
separation does not certify that the proposed conditioning interpretation is
semantically faithful or free of observational leakage; open extraction and
semantic role checking remain research obligations.

The first integrated examples genuinely change predicted actions after a
newly composed observation-channel mechanism, and change grounded acceptance
after a proposed rule interpretation is edited. M08/M09/M11 suppliers remain
required as those real domains are built. No duplicate domain-specific
"discoverer" is introduced, and no fixture stands in for an implemented solver.

## Mechanism programs, residuals and edits

The bounded data AST has latent parameters, observation conditions, named
mechanism bindings (`transition`), Boolean applicability constraints and actual
solver-query selectors (`predict`). Conditions compose declared features with
AND/OR/NOT, equality and conditional expressions; rational arithmetic is bounded.
Observation bindings change a candidate's seen/received/understood/trusted
channel. Named transition bindings currently change declared goal utility,
action cost, ordinary-premise status or strict-rule status. They cannot target
source text, observed explanation targets, ACLs, result values or arbitrary
object paths. Every resulting template is revalidated by its domain compiler.

Residuals come from the actual Observation×Hypothesis matrix. The editor can
replace/extend/restrict/negate observation conditions and substitute declared
latent values. It constructs new AST combinations rather than selecting among
three canned explanations. Each edit records parent/child content hashes,
changed path, old/new mechanism and the residual observation IDs that prompted
it. Consumption validates the declared grammar edit against both actual program
hashes and the parent's computed residuals. Recomputed, partially recomputed and
uncomputed proposals remain distinct; a resource cutoff cannot be described as
a fully recomputed edit. All prior prediction obligations are scheduled again;
original sources, observations and older candidate programs remain unchanged. A fully explained program is
not edited merely to generate more text.

This grammar does **not yet** invent new event-time ranges, identities, causal
structures, habit/opportunity models or conceptual readings. Independent model
proposal beyond the injected initial programs is also not yet implemented.
These remain M04 construction obligations, not work silently moved to S6. The
current implementation establishes a replaceable, real first algorithm and a
shared entry while full mechanism discovery stays open.

## Evidence factors, uncertainty and competing explanations

Matrix cells retain the actual solver result/field references and one of
EXPLAINED, CONTRADICTED, COMPATIBLE_UNDERSPECIFIED, UNMODELED or UNCOMPUTED.
Set-valued predictions stay set-valued. An empty view, exhausted solver or
missing query is not a negative prediction or successful explanation.

Explicit retelling/derivation links and repeated context/query/source-span
observations are registered in connected factor families. Contradictory reports
are preserved as separate rows in their family. Distinct query obligations can
share a sentence without becoming the same factor. Repeating a report does not
increase evidence or trigger another evaluation of the same context. Context
identity excludes only its display ID: exact structural aliases with renamed
observation/factor labels share a factor and computation, while distinct query
obligations and genuinely changed conditions remain distinct. Cyclic
report lineage is invalid. Source groups and factors are not a proof of
statistical independence; no likelihood multiplication or calibrated posterior
is produced.

Pareto comparison uses sets of explained, contradicted and underspecified
factors plus explicit AST complexity and actual solver-batch work. Unique rare
evidence cannot be erased by an aggregate coverage score or complexity penalty.
Uncomputed/unmodeled columns cannot win merely by avoiding computation.
Dominated candidates remain in the archive. The bounded expansion beam is a
search-resource policy, not a claim that excluded expansions are implausible.

Prediction-equivalence classes concern only the declared current obligations,
contexts, source versions and rule version. Unknown columns are never certified
equivalent. All class members remain available. A prospective probe executes
all members of a class containing a Pareto candidate, including more complex
members that current observations cannot distinguish. Actual predicted outcomes
form partitions and a separating-pair count. Probe text is explicitly hypothetical,
not a new original observation; information gain is not numerically calibrated.
Reward-4/reward-8 models can agree on the observed choice and diverge when a
new hypothetical detour cost is computed. Current equivalence is never global
identifiability. Each observed fit and each prospective prediction carries its
own actual domain assumption environments through compact delivery and answer
text. Probe-only assumptions qualify that future prediction, not the observed
fit; the outer claim also preserves the union of consumed conditions.

## Durable consumption, resource accounting and migration

Only the controller commits the outer actual InferenceResult/Delta. The result
retains candidate programs, full domain computations, context identities,
source dependencies, assumption conditions, matrix, factor registry, edits,
equivalence classes, Pareto set and prospective-probe audit. Compact delivery
consumes their exact fields and rechecks predictions against the retained real
solver fields, including the underlying mental-plan/argument proof contracts.
A modified matrix label, dominance result or probe separation cannot replace
those computations.

The existing global call/local-evaluation/context/output budgets apply. There
are at most eight seed programs, sixteen observed contexts, sixty-four observation
rows, eight prospective probes and sixty-four archived programs. Default search
uses a beam of twelve and at most four new programs per round, with an explicit
round limit. Candidate generation is streamed with a hash set and stops after
one extra proposal proves the beam bound; it does not build a quadratic list
before truncating it. Expressions, parameters, bindings and domain solver work
retain separate finite bounds. Solver-batch accounting is not a claim of CPU
instruction accounting or S6 scale acceptance. An unexpected domain computation
failure preserves the engine's reservation instead of being relabelled a known
zero-cost rejected hypothesis.

RETURNED/computed/committed recovery and cached run/stream reuse existing work
without another model send. UNKNOWN sends retain their holds. Fresh delivery
and replay ACL checks cover all original inputs, including source metadata in
matrix/probe projections; revocation clears the complete delivered content.

Side-copy migration adds only the exact published S4 runtime hash
`f4a534f8b0beed70fde28a90372023efe7161b43eea6955ea1e87046303bc374`
from its 176 runtime Python files. Tests execute that old runtime itself and
preserve finite/FOL/mental/argument completed results and live checkpoint states,
then fence the old writer. No old pins, closed grants or codec field layouts are
rewritten.

## Evidence boundary

`test_unified_s3_abduction.py`, `test_unified_s3_discovery.py` and
`test_unified_s3_discovery_upgrade.py` cover independent finite invariants,
actual entry computations, residual edits, uncommon evidence, duplicate reports,
future probe splitting, resource unknowns, negative AST/source boundaries,
revocation and real predecessor recovery. `witness_unified_discovery.py` binds
the actual computed/consumed fields to the exact head and runtime file hashes.

The source reconstructions and development scenarios are injected test inputs.
These results do not establish open ordinary-language extraction, complete
hypothesis coverage, causal discovery, private mental truth, calibrated human
probabilities, full M04/M05/M13 or LIVE_FUNCTIONAL/EFFECT_CONFIRMED. Full S3/S4,
the five-domain S5 chain, S6 scale, S7 independent effect confirmation and all
original acceptance families remain open. Provider calls/spend and sealed reads
are zero, with no new credentials or service permissions.

## Post-merge domain-qualification correction

PR #432's original discovery composition omitted nested operator issues from
outer status and compact delivery. Real cycle-exclusion and inconsistent-strict-
core examples were reproduced for both observed fits and hypothetical probes:
the direct argument entry returned PARTIAL while discovery returned COMPLETED.
The current composition retains each actual result's issues, finite acceptance
scope, excluded circular rules, strict conflicts and frontier beside its exact
program/context/result identity. Both incomplete and computed probe evaluations
retain these qualifications. A computed label can remain usable as a conditional
value while its task is PARTIAL; it does not certify a complete or consistent
argument theory. Probe caveats qualify that probe rather than a clean observed fit.

The delivery verifier derives the required qualifiers from retained actual
solver evidence and rejects stripped or altered current qualification fields.
The side-copy allowlist now also admits the exact published M04 runtime from
`e5f70bbb2afcfef665c6e9d7a7d3da2bb612cc83`: 179 Python files with bundle hash
`1d8dd8c70f98fe8b370939f016615550b09fc7aa1dbcaf7d27820b479f89ebbd`.
Real old completed tasks and RETURNED/computed/committed checkpoints are tested
across schema 3/4. Historical result objects, event records and accepted-operation
digests remain unchanged. Current replay reassembles its answer from those
committed facts and projects original per-result/per-model evidence paths instead
of pretending synthesized qualifiers were present in the historical record.
Recovered checkpoints use the same current qualification. No model resend or
recomputation of accepted results is required. An UNKNOWN send remains blocked.
The newly assembled delivery still passes full byte budgets and a fresh ACL
check after leaving its read transaction; failure returns no source content.

`test_unified_discovery_limitations.py` and `test_unified_discovery_upgrade.py`
retain these regression and historical-recovery checks. This is a correctness
repair within the same bounded offline M04 increment, not stage completion.
