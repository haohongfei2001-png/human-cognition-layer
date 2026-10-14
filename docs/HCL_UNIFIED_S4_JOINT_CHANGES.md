# Finite joint minimum-cardinality changes

Status: **INTEGRATED_OFFLINE_PARTIAL**. This is the next original M13 §4 slice,
connected to M13 §5, M14 §5 and the applicable T15/T17/T18 tests. It does not
close those mechanisms, test families or S4. Provider calls, spend, deployments
and sealed-content reads are zero.

## Explicit language and edit unit

The additive request `hcl-judgment-candidates-4` extends the source-bound v2
concept judgment with `joint_changes(baseline, target, edits)`. Its baseline is
one complete, legal assignment of every declared CHOICE. The target is either
one `M13_ACCEPTANCE` query or one `M14_DECISION`, identified by the containing
cognitive model's source/model IDs and the argument/query or decision identity.
The actual argument namespace and original source records are bound separately.

The finite language has at most twelve distinct atoms:

- `CHOICE_REPLACE`: assign one existing alternative to one declared selector.
- `PREMISE_RETRACT`: deactivate one premise in a specified argument/model scope.
- `RULE_RETRACT`: deactivate one rule in that same explicit scope.

One atom costs one edit. Repeated declarations of the same atom are deduplicated;
an exact replacement by the baseline label is ignored. Two different alternatives
for the same selector cannot appear in one terminal edit set. No sequence of
intermediate states is imposed. All replacements are applied simultaneously,
then the full assignment is checked against the original joint constraints.
Thus an interlocked terminal assignment can be legal even though each single
replacement is illegal.

This is **declared-selector/scoped-activation minimum cardinality**, not semantic
concept distance. Two selectors referring to the same family still count as two
selector edits; two independent uses are not silently collapsed by family. A
single selector consumed in several places counts once. The result does not
claim that arbitrary equivalent presentations have the same concept complexity.
Atoms bind host, scope, semantics, usability assumptions, consumers and exact
source anchors. Atom IDs are local to this source-bound program, not reusable
global authority. Labels, copied declarations or proof identity cannot themselves
satisfy the semantic target.

The first language deliberately excludes new principle discovery, priority or
weight optimization, new definitions, open-ended edits, and actual fact changes.
V3-generated repairs retain their separate language and adoption contract; this
v4 request does not reinterpret a v3 repair certificate.

## Actual computation and minimum proof

M12 computes the actual finite definitions and independent-case classifications.
The existing judgment runner supplies actual shared M03/M05/M07 facts, M13 proof
construction/defeat/acceptance, and M14 joint normative branches and exact value
comparison. It uses the same runtime, budget ledger and store. There is no new
scheduler or registry.

Retractions append a fresh inactive guard to the hypothetical argument item.
They do not remove its original source row, falsify its bound fact, edit M03
knowledge, change M05 feasibility, or release an M07 commitment. A separate
filtered dependency view prevents an intentionally deactivated premise/rule
from transmitting an UNKNOWN dependency. Original PINNED classifications and
commitment terms are unchanged. Complete computations for an unaffected model
can be reused only under an exact key including its model, bindings, relevant
classifications, retractions, source versions and rule version. Shared upstream
calculations likewise remain within this one immutable program/snapshot.

M13 targets compare positive/opposed rooted support, grounded acceptance and
joint preferred acceptance pairs. V4 therefore explicitly computes preferred
extensions for its target query even if the original source proposal disabled
that optional query feature; missing or bounded preferred computation is PARTIAL.
This affects only the v4 hypothetical computation, not the original query or old
certificate meanings. M14 targets reuse the existing semantic
projection: recommendation plus correlated normative-state/permission branches
and responsibility acceptance. Trace IDs, proof enumeration, display labels and
extension order are excluded. UNKNOWN dependencies remain explicit; they cannot
be treated as false to manufacture a certified change.

Search enumerates edit sets by increasing cardinality. Every generated set is
charged, including conflicting or illegal terminal assignments. It checks every
smaller layer and **the entire first winning layer**, retaining all tied minimum
witnesses. This is stronger than finding a first witness or an inclusion-minimal
set, and weaker than global minimum change outside the declared language.

`FOUND_ALL_MINIMUM` includes the cardinality and all tied witnesses only after
those layers and all their semantic comparisons are complete.
`NO_EXPRESSIBLE_CHANGE` requires complete enumeration of the entire declared
language. A work, proof-capacity, solver or UNKNOWN frontier yields `PARTIAL`,
with candidate witnesses retained but no certified minimum cardinality or full
minimum list. A partial winning layer never certifies its first observed tie.
The result makes no across-unsearched-versions robustness claim.

One allowance covers input/atom validation, generation, legality clauses, M12
matching, cached-model binding validation, actual M13/M14 work, and target
projection/comparison/validation. Deterministic validation units count AST nodes;
underlying solvers retain their existing operation units and explicit bounds.
Full certificate delivery independently replays that same bounded computation,
following the existing pure-verifier contract. It is not an extra provider call.
The existing 4 MiB audit and 128 MiB migration limits are unchanged. Proof growth
can stop search before that capacity; it cannot enlarge the limit or discard
counterevidence to obtain a complete certificate.

## Wire compatibility and adoption boundary

The new result kind is `CONDITIONAL_JOINT_CHANGE_JUDGMENT`, local dialect
`judgment-model-4`; the joint branch computation is explicitly versioned.
Historical v1/v2/v3, persistent-1/2 and `critical_retractions` wire meanings and
answers are untouched. No new dataclass or codec-field exception is introduced.

All layers are replay-checked: source/host bindings, normalized language, baseline,
legal terminal assignments, actual classifications/facts/arguments/decisions,
semantic target, layer counts, ties, minimum scope and inference qualifications.
The compact delivered claim references the verified search and evaluated targets;
the immutable store retains the full proof. Current source, ACL, erasure and
accepted-effect gates remain the ordinary engine's responsibility.

Joint-change proposals do not adopt themselves. In particular, this result kind
is intentionally absent from concept-only adoption/follow support kinds. A mixed
retraction proposal cannot be smuggled through a concept adoption event.
`hcl-concept-proof-capsule-1` continues accepting only its original repair kind;
v4 does not introduce or reuse a compression tag. The prior capsule regression
uses the currently certified zlib 1.3.2 implementation, not arbitrary future
compression implementations.

## Evidence and limits

`tests/test_unified_joint_change_oracle.py` independently enumerates legal complete
assignments and retraction subsets, constructs tiny proof graphs, enumerates
complete three-valued labellings, and computes permissions/recommendations with
rational arithmetic. It does not use production target projections to establish
oracle outcomes. Cases include mixed concept/rule synergy, two genuinely distinct
concept families, illegal singleton intermediates, all ties, no expressible change,
UNKNOWN, cancellations/redundancy, permutation/duplicates, scopes, negative examples,
original commitments, support-only changes and permission changes with the same
recommendation.

`tests/test_unified_joint_changes.py` covers the ordinary HCL/run/stream/compat
entry, bounded work, source-bound full replay and forged layers, exact restoration,
current ACL/erasure, inactive original rows, unaffected-model reuse and rejection
of concept-only adoption and capsule-1 reinterpretation.

The true predecessor is main `efe7d78b83e50a3723f46280163bb786be74b7f1`, tree
`ded6a65a18763b3d1aa78b0010dd7664ea7ed143`, exactly 230 runtime Python files,
code fingerprint `8310ca28dad0ceeadb24b2dc432827a280680b84e30c014d8e38203bf003413f`.
`tests/test_unified_joint_change_upgrade.py` runs that actual old code in separate
processes to create schema-3/4 v1/v2/v3 judgments, original compressed proofs,
and real adoption/follow/successor states. It preserves request/answer/claim/object
bytes, CAS, UNKNOWN holds, zero resend and terminal writer fencing. Independent
workloads use separate bounded stores. All older predecessor pins remain.

The migration matrix retains the full 14-candidate v3 repair in both schemas for
all five judgment checkpoints and for completed adoption with two successors,
including byte-preserving replay, current ACL and physical erasure. The four
persistent computed/committed workloads use a smaller three-positive-example
repair with a correspondingly explicit synthetic source. Its two negative
examples and target case are unchanged. The old process checks the full/small
candidate, partition and consistent-candidate counts (14/15/4 and 5/5/2), the same
two triggering counterexamples and the unique two-pattern repair. Each interrupted
adoption has two computed successor proofs and exactly one/two committed
successors at the computed/committed seam; both restored successors classify the
target as a member and recommend protection. This preserves the predecessor
type/state and safety matrix, not the original 14-candidate-by-every-recovery-state
data cross-product. Test-only reuse removes identical wire decoding and a third
proof replay only after observing the real verifier succeed on the exact same
proof bytes. Completed cached delivery retains its separate explicit replay.

`scripts/witness_unified_joint_changes.py` binds ordinary-entry computed values,
consumed fields and zero-new-send replay to the checked commit and all runtime
file hashes. Existing 21 witnesses and historical/diagnostic regressions remain.
This is injected-interpretation offline evidence, not open-language completeness,
universal philosophical or moral correctness, live model functionality or measured
gain over a base model.
