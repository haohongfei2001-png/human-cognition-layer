# I02 — strict generic G workspace boundary v4

Status: **PROVIDER-FREE CANDIDATE / MODEL SEMANTICS UNQUALIFIED**.

The v1/v2 C/P/G calibration runners and their paid receipts remain immutable.
The v3 candidate already asks P and G to preserve explicit reported goals.
Its generic map parser, inherited from v1, checked that each quote occurs in
the authorized source but allowed undeclared fields inside a `source_index`
row. It then passed those fields to G's final model input. A map row such as
`{"source_id":"s","quote":"...","gold":"..."}` therefore crossed the
declared intermediate workspace boundary even though `gold` was not a valid
source citation.

The [v4 boundary](../scripts/serious_eval_arms_v4.py) keeps the v3 C, P and
G-map messages and their one-map-plus-one-final call accounting. It requires
exact top-level keys, exact `source_id`/`quote` keys per row, bounded array and
string sizes, typed unresolved questions and unique JSON keys. It passes a
canonical clean map to the existing v3 final builder, which still checks every
quote against the complete original source and retains that source and the
same four final answer fields. An unsupported quote, oracle-like extra field
or duplicate key fails before G-final can be called. The parser does not
silently repair a model response, and it does not judge semantic accuracy.

The [ordinary-input witness](../reports/HCL_I02_G_WORKSPACE_V4_PROVIDER_FREE_WITNESS.json)
saves actual C/P/G-map/G-final candidate messages and a script digest for a
synthetic example. Tests cover the positive final input, source retention,
negative extra fields, duplicate keys, malformed unresolved items and
unsupported quotations. Full historical v1 regressions and the I01 current
runtime hash check pass. Provider calls/spend: **0 / USD 0**. LongMemEval:
**SEALED / NOT ACCESSED**.

**EVALUATION_DELTA:** the generic comparator now has an executable boundary
between its source-index workspace and final model input; undeclared
intermediate fields cannot be laundered into G-final. **HCL answer
CAPABILITY_DELTA:** none. Prompt wording and actual model competence remain
unvalidated. Use this candidate only in a separately frozen future calibration
after source rights, task fit and one-use cost are established.

**NEXT_READY:** I02 unexposed source and comparator qualification. No I03
efficacy run is authorized by this provider-free result.
