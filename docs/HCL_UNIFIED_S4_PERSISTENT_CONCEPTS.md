# Bounded persistent concept adoption and local revision

Status: **INTEGRATED_OFFLINE_PARTIAL**. This slice implements part of the already
approved M02 §5–6, M10 §4, M12 §5 and M15 §5. S3/S4, M12/M13/M14 and the full
T15–T19/T22 acceptance families remain open. No provider, paid service, credentials,
private source transmission, deployment or sealed material is involved.

## Explicit adoption, fixed originals

`ConceptAdoptionIssue` is a host-requested `ExecutionIssue` goal. It names an
adoption stream, one to eight exact previously accepted v2 concept-result proofs,
selected definition labels and an explicit `expected_head`. It does not accept
source-authored authority or silently choose a globally newest definition.
The ordinary v2 entrypoint still compiles anchored candidates and computes their
actual definitions before they can support adoption. Adoption is a separate host
instruction, not a claim that the model or a person endorses a moral principle.

A stream belongs to one authenticated session/principal. Its append-only header
contains the exact semantic identity, usability-condition fingerprint, opaque
support identities, frame, effective time and predecessor. The unique store
commit rechecks compare-and-adopt under the writer transaction. Two revisions of
the same predecessor cannot silently overwrite one another. A future-effective
adoption does not change an earlier-time consumer's query projection.

`ConceptFollowIssue` explicitly opts an already bound v2 computation into one to
four named CHOICE-following relations. Its original raw candidate, complete base
program, fixed-source versions and original commitments remain immutable.
PINNED uses never acquire follow-current semantics; a commitment cannot become a
follow-current use. Existing v1/v2 requests are not enrolled automatically.
Registration supports the actual computation; it is not the delivered capability
on its own.

## Actual cross-request computation

Request A adopts a definition. Independent requests B and C register following
choices and compute their results. Request D adopts a different definition and
contains no B/C consumer list. The existing execution runner discovers the exact
host-scoped reverse-index records and adds local successor nodes to D's graph.
They use D's shared step/work budget, checkpoints and single commit path. D is a
new revision task; its receipt identifies the original requests and successor
goals. The stored B/C tasks, answers and claims are never edited. A stale B/C
request cannot re-deliver its old current-selection result as if still valid.

Each successor runs typed M12 induction/classification and actual M13 proof,
defeat and acceptance followed by M14 permission and value comparison. Fixed
M03/M05/M07 results, opportunities and ordinary facts are reused from the original
bound computation. Source/definition compatibility and exact fixed inputs are
checked. Full certificate replay separately re-executes inherited proofs when
validating delivery; it is not a new branch-local model call or a claim of zero
verification CPU work.

The new `hcl-persistent-concept-judgment-1` envelope records the unchanged base
proof, selected immutable support proofs and actual new computations. It never
modifies a v2 raw candidate and labels that as its old certificate. A supplied
previous result can carry one bounded prior recipe/projection; it cannot recurse
through an unbounded chain. `comparison_basis` explicitly distinguishes comparison
with the original joint base bundle from a prior persistent projection. Runtime
successor tests additionally compare B/C's actual earlier selected results with D.

If a constraint refers to a genuinely new meaning without an authorized compatible
pair, a family/frame/signature changes, a definition is future-inapplicable, or
source text changed and now needs interpretation, the result is
`NEEDS_RECOMPILE`. No provider response is resent and no new semantic certificate
is fabricated. Unfinished local work exposes its frontier and withholds complete
robust recommendations.

## Dependencies, independent support and privacy

`ConceptQuery`/`ConceptDependency` are additive types in the existing
QuerySnapshot/QueryDelta envelope. Old dataclass field sets and serialized bytes
are unchanged. Query invalidation uses `QUERY_DEPENDENCY_CHANGED` and the existing
`_invalidate_changed_queries`/commit-race handling. Exact query projections do not
include unrelated inferences or successor writes, so they cannot invalidate
themselves. Unrelated streams, unselected future adoptions and fixed old tasks
have explicit zero-execution counterexamples.

Each adoption support remains an independent proof with its own source read-set.
The query first validates current source versions and authority, then reads that
proof's payload. One unavailable support does not invalidate another live support
by unioning them into an all-required premise. Only one complete current support
is retained in a consumer's actual projection. If the selected meaning has no
usable support, it becomes unavailable; an earlier meaning is never silently
restored. A new current-authority query may rebind unchanged evidence after an
ACL epoch change, but old cached delivery never borrows that new authority.

Opaque registry headers contain no original passage or explanation. Original
proofs, query views, retained checkpoints and staging objects carry exact source
and origin lineage through existing governance. Synthetic erasure tests remove
one supporting source, preserve an independent authorized proof and rebuild the
same projection. New concept-owned results additionally enforce their original
session/principal at the fresh delivery gate, by structured result kind for both
native operator and runtime-wrapped successor identities. Same semantic definitions
with different withdrawn assumptions remain distinct adoption supports; label order
cannot replace explicitly withdrawn meaning with a live alias. One commit batch
cannot fork the same adoption stream, while distinct streams may commit atomically.
An adoption claim reports only the recorded adoption; consumer revision is certified
only by actual successor results, including at execution-budget frontiers.

## Recovery and evidence boundaries

Adoption, subscription and successor identities are deterministic. The existing
computed-before-commit checkpoint and exact already-committed-effect recognition
handle adoption committed before discovery, successor computed before commit,
and successor committed before checkpoint. Explicit host recovery resumes known
local work without re-executing accepted effects. Existing UNKNOWN model sends
retain their holds and never become a reason to resend.

The genuine predecessor is main
`5c9080559b00b067b31f99cc6ed0ff0c92120feb`, tree
`9dd64c7a00e50cd1f0ff59874ab19aa3d5461f74`: 222 runtime Python files with fingerprint
`9edd62dff949615310c41827aeb10bb5582dd298ca20da124db39154575d09c0`.
The frozen old process creates v1/v2 completed and interrupted stores in schemas
3/4. Side-copy tests preserve original request, answer, claim and CAS bytes,
UNKNOWN holds and terminal old-writer fencing. All earlier predecessor pins and
old-field/byte assertions remain intact. The exact additive codec-tag allowlist
now names these five new types and checks their exact field sets. Three new upgrade test methods include 20 bounded state
combinations, four cutover seams and seven invalid-bundle cases; this is not
whole-system migration coverage.

Evidence paths:
- `tests/test_unified_persistent_concept_solver.py`
- `tests/test_unified_persistent_concept_propagation.py`
- `tests/test_unified_persistent_concept_upgrade.py`
- `scripts/witness_unified_persistent_concepts.py`

Still open: cross-session/principal concept alignment, arbitrary concept
predicates inside mental/commitment models, general cyclic fixed-point revision,
open interpretation/discovery and automatic semantic recompilation, general
multistep policies, complete minimal-revision proofs, all full-domain and real
model functional/effect acceptance. This finite DAG-shaped propagation does not
close any of those obligations.
