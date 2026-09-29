# I02 — generic G workspace candidate v5

**Status: provider-free comparator implementation / model competence not yet
qualified.** The I01 comparator contract requires a competent generic method,
not a deliberately thin evidence list. Earlier G candidates kept exact source
quotes and unresolved questions, but had no executable relation, plan or
source-revision state. The independent
[v5 implementation](../scripts/serious_eval_generic_workspace_v5.py) is a
candidate repair; it does not change HCL runtime or any consumed v1–v4
prompt, receipt, cost or disposition.

V5 retains v3 C and P messages byte-for-byte. G-map sees the same complete
ordinary source and question and requests four generic fields: exact source
quotes, proposed support/challenge/qualification links, bounded answer steps,
and unresolved questions. A strict boundary rejects duplicate JSON keys,
undeclared/oracle fields, absent or ambiguous quotes, nonexistent link targets,
unsupported plan operations and oversized state. It derives source offsets,
versions and hashes locally; neither model-generated offsets nor relation
semantics are treated as truth. The final G call receives the original full
source plus the checked, explicitly provisional workspace. G-map and G-final
remain two charged calls. On a source correction, the workspace and all its
relations become stale until the map is recomputed; no old quote or plan may
silently survive.

The [ordinary-input witness](../reports/HCL_I02_G_WORKSPACE_V5_PROVIDER_FREE_WITNESS.json)
saves actual C/P/G-map/G-final messages for a synthetic example. Unit checks
cover positive source-span composition, negative/oracle fields, link and plan
boundaries, local revision and v3/v4 historical regression. These checks prove
the interface and source memory only. They do not show that a provider emits a
valid map, understands the case, or makes G a competent semantic comparator.
Before any confirmation result, a separate development-source calibration
must measure G's map validity, explicit fact coverage, counterevidence and
cost against C/P. Invalid maps or missed supported facts remain failures; do
not repair a consumed case by rerunning it or by viewing H outcomes.

**EVALUATION_DELTA:** G now has executable generic source memory, dependency
links and bounded answer planning with conservative invalidation.
**HCL answer CAPABILITY_DELTA:** none. **Provider calls/spend:** 0 / USD 0.
**LongMemEval:** sealed, untouched. **NEXT_READY:** source qualification and
separate comparator semantic calibration before an I03 confirmation freeze.
