# Finite counterexample-driven concept repairs

Status: **INTEGRATED_OFFLINE_PARTIAL**. This slice implements the applicable
M12 §4 and M13 §3–5 concept-feedback/reflection work under the original S4 plan,
with actual M12 classification, M13 acceptance and M14 recommendations. It does
not close M12/M13/M14, T15–T18, S4 or open semantic understanding. Provider calls,
spend, deployments and sealed-content reads remain zero.

## Declared language and actual search

The existing single-pattern LGG is the least general syntactic generalization
of all positives: a matching negative cannot be excluded by merely making the
same pattern more specific while keeping all positives. The new language is
explicitly `OR_OF_POSITIVE_PARTITION_LGGS_1`. Up to five distinct positive ground
terms are partitioned into nonempty, unordered blocks; the existing typed
anti-unifier computes one LGG per block. Their OR is one criterion, with the
original SUFFICIENT or BICONDITIONAL direction preserved. It is not several
biconditionals whose separate failures would incorrectly exclude a case.

An actual matching negative triggers partition edits. All positive and negative
records remain in the comparison, including an identical complete term labeled
both ways. Necessary and typical criteria are not refuted merely because a
negative matches; they retain their direction and receive no such repair.
Withdrawn assumptions prevent repair certification instead of removing the
awkward example. Unknown case information remains unknown.

The domain adapter in `discovery_model.py` takes only computed OR patterns and
unlabeled case terms. Shared `abduction.discover` computes the actual prediction
matrix, explained/contradicted/underspecified residuals, evidence-factor dedup,
prediction classes and Pareto comparison. No candidate can supply its score,
pattern, case prediction or membership outcome in the raw v3 request. Search
lineage identifies the full partition edit and triggering counterexamples.
Equivalent OR programs share a matrix column while every enumerated partition
remains in `equivalent_partitions`; repeated reports are not independent votes.

Complexity is M04's `expression_size` of the explicit adapter/pattern AST;
matching work is a separate resource objective. Pareto is not a moral score.
All nondominated ties survive, and even dominated candidates remain recorded.
Equivalence means only identical predictions on the declared observations;
new ground terms can distinguish equally fitting repairs.

`minimum_consistent_candidate_ids` minimizes structural cost, and the separate
block-minimum field minimizes disjunct count. Both are reported only after
complete triggered enumeration and matching in this declared language. An
unrefuted original only undergoes the single-LGG check: its completeness is
`NOT_SEARCHED_NO_COUNTEREXAMPLE`, with no partition-minimum claim. A contradictory
positive/negative term yields `NO_REPAIR_IN_FINITE_LANGUAGE`, never a global
impossibility theorem.

Every partition expansion, LGG operation and case/alternative/matcher visit uses
one local work allowance. Generation and prediction frontiers remain explicit;
partial search cannot claim a minimum or certify a complete robust recommendation.
Subsequent definitions and all actual M13/M14 branches consume the same remaining
task budget. The existing 4 MiB checkpoint and total-output bounds are unchanged.

## Real downstream reflection, explicit adoption

The additive `hcl-judgment-candidates-3` request contains the existing source-bound
v2 proposal plus one explicit repair target/CHOICE. It preserves raw evidence,
old version definitions, PINNED uses and M07 original commitment terms. Generated
readings have distinct immutable semantic identities; order, display labels and
duplicate supporting examples do not create new generated meanings.

The downstream comparison is explicitly
`ALL_CONSISTENT_FINITE_REPAIRS_PLUS_ORIGINALS`: every generated candidate whose
complete matrix retains all positives and excludes all negatives is classified
on the independent cases and sent into the real M13/M14 code. The original
readings remain as comparisons. `downstream_candidate_ids` and
`excluded_candidate_ids` make this selection checkable. Rejected candidates and
their full counterexamples stay in the matrix and delivered repair claim; they
are not discarded from search or used to enlarge an optimality claim. A large
honest proof that exceeds existing bounds fails closed rather than truncating
its evidence. The local example produces 15 partitions, 14 distinct OR ASTs and
four consistent repairs; both a general two-block repair and the more specific
four-block repair reach the actual decision solver and predict different actions
on an unseen constant.

Finite reflection compares coverage, counterexamples, structural and execution
cost, and actual conditional norm/decision changes. It does not prove globally
minimal premise changes, philosophical truth, semantic completeness or moral
correctness. Suggestions and rankings do not adopt any definition.

Only a separate host `ConceptAdoptionIssue` selects a verified generated reading.
Existing same-session/principal adoption streams and `ConceptFollowIssue` then
reuse PR442's ordinary query invalidation, unique runner, store commit and recovery.
No new registry, scheduler or automatic follow enrollment is introduced. Independent
B/C task bytes, answers and claims stay immutable when D adopts a repair and
computes successors. A pinned promise still means what its original definition
meant; new source text requires recompilation, and UNKNOWN sends never resend.

## Additive certificates and proof size

V1, v2 and `hcl-persistent-concept-judgment-1` retain their old wire meanings.
The new result kind is `CONDITIONAL_CONCEPT_REPAIR_JUDGMENT`; successors involving
it use `hcl-persistent-concept-judgment-2` and a distinct repair-successor kind.
Full deterministic replay verifies partitions, scores, definitions, classifications,
M13/M14 fields and all source/host bindings before claim delivery.

New v3 inherited proofs use a bounded, canonical, lossless
`hcl-concept-proof-capsule-1`: exact codec bytes, SHA-256 and explicit length,
compressed with zlib/base64. This avoids embedding the same large finite proof
repeatedly inside query snapshots and successors. Uncompressed bytes cannot
exceed the existing 4 MiB bound; truncated, noncanonical, trailing, malformed or
oversized streams are rejected. Compression grants no authority. Current source
read-sets, host ownership and exact origin lineage remain outside the capsule
and are verified before decoding. Old proof encodings are not changed.

Fresh source/ACL/erasure gates apply to the structured new result kinds,
independent of whether IDs are native operator IDs or wrapped successor IDs.
Independent live supports can still supply the adopted meaning when another
support is unavailable; no old meaning is silently resurrected.

## Independent oracle and real predecessor

`tests/test_unified_concept_repair_oracle.py` contains separate recursive
partition, LGG, matcher, structural-cost and Pareto implementations. It checks
small full domains, fresh constants, repeated-variable correlation, renaming,
duplicates, conflicting labels, and exact budget frontiers. Integration tests
use the ordinary HCL entry, actual argument/decision results, explicit adoption,
immutable old tasks, replay and security boundaries.

The frozen predecessor is genuine main
`f813ca5fb93ff62b167dd33268cdae4ec0e247d3`, tree
`0bd1ebd1b1d8f461313a50f65a01ccca324102c0`: 227 runtime Python files with
code fingerprint `5aadaf9bfed53e096e2258badb69b0d807f2303443411ef630e436769ad14de0`.
A subprocess of that exact code creates schema-3/4 v1/v2 stores and real
adoption/follow/successor completed/computed/committed states. Side-copy migration
keeps historical requests, answers, claims, UNKNOWN holds, CAS and writer fences;
all older predecessor pins and tests remain unchanged.

Evidence: `tests/test_unified_concept_repair_oracle.py`,
`tests/test_unified_concept_repairs.py`,
`tests/test_unified_concept_repair_upgrade.py`, and
`scripts/witness_unified_concept_repairs.py`. This is finite injected-interpretation
offline evidence, not live model functionality or measured cognitive benefit.
