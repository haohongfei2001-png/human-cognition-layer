# Verified reasons in conditional weight-domain answers

This implements a bounded user-facing delivery slice of approved M14 §5 and
T17/T18. Full M14 and S3/S4 remain open. No decision rule, preference model,
solver, action or adoption operation is added.

## Actual delivery

New v5 results use `s4-weight-region-reasoned-delivery-1`. Their bounded
`reasoned_delivery` certificate is reconstructed from the existing source-bound
program, actual upstream judgment and exact region analysis. HCL.run/stream
consume it in full and compact claims. The answer explains:

- Named dimensions in declared coordinate order, exact constraints and
  recommendation regions/boundaries, including ties.
- Separate framework/domain provenance, declarer, time and source segments;
  analysis does not adopt a declaration or infer personal preferences.
- Concrete infeasible/prohibited/unresolved alternatives and hard-norm IDs.
  Every mentioned two-step alternative has a readable root and observation map,
  including excluded alternatives, not just recommended policy hashes.
- Existing same-scenario dimensional differences between permitted alternatives.
  Negative left-minus-right values are costs of the left alternative; positive
  values are gains. This creates no new whole-domain ranking or universally
  strongest alternative under unknown weights.
- Existing factual guard states/references and argument query acceptance states
  that require recomputation if changed. This does not claim a hypothetical
  change must reverse the recommendation.

EXPECTED, MAXIMIN and MINIMAX_REGRET retain their original mathematics. Neither
worlds nor actions/continuations are selected separately by scenario/dimension.
Hard obligations remain uncompensated by utility.

## Bounds and verification

Explanation traversal and generation consume the same local work budget.
A 64 KiB explanation certificate ceiling tightens delivery; existing policy,
region and full-proof caps do not expand. Exhaustion returns an explicit
resource-limited explanation and clears global robust, unique and possible
recommendations. No decisive objection is silently truncated into a complete
recommendation. Retained cells remain conditional proof material. Unknown
branches and incomplete coverage are explicitly qualified.

`verify_weight_regions` replays the selected certificate version, including
explanation metadata/text. Compact claims retain that exact field and existing
analytical projections. Forged dimensions, provenance, revision conditions,
text or version fail delivery. Mapping rendering is canonical across restart.

## Compatibility and evidence

Historical v5, regret and policy-weight certificates replay without added
fields, extra work or changed answer text. The real PR448 fixture projects all
238 runtime Python files from main `2c27ff69631657d7498dd4e790850d218d27d019`.
Completed, returned, unknown-send, computed and committed tasks exercise both
schemas. Old proof/claim/answer bytes, no-resend recovery, UNKNOWN holds, ACL,
erasure and old-writer fences remain intact.

- `tests/test_unified_weight_region_delivery.py`: actual answers, unchanged
  calculations, round trips, legacy rendering, tampering, frontiers and recovery.
- `tests/test_unified_weight_delivery_upgrade.py`: genuine PR448 migration.
- `scripts/witness_unified_weight_region_delivery.py`: 15 single-step/policy,
  unknown, budget, empty-domain and ACL cases with exact-head runtime hashes.

No paid provider, open semantic accuracy, automatic normative adoption or full
stage completion is asserted.
