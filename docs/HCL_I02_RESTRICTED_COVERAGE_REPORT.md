# I02 — restricted catalog coverage report

Status: **EXECUTABLE STRUCTURAL SCOPE REPORT / NO SOURCE OR EFFICACY QUALIFIED**.

I01 fixes four task families and a three-writing-system maturity target, while
its prose permits narrower claims when coverage is smaller. The original
`validate_catalog` correctly rejected a catalog below the full target, but
offered no way to record valid, restricted coverage. The separate
`scripts/serious_eval_catalog_coverage.py` validates every case and calibration/confirmation
boundary before returning the observed family and writing-system counts.
Its report always marks `provider_approved=false` and
`efficacy_claim_qualified=false`. The existing `validate_catalog` still
requires the complete I01 structural target.

Run `python -m scripts.serious_eval_catalog_coverage --catalog CATALOG.json` to obtain
a metadata-only structural report. Add `--require-full-coverage` to fail when
the four-family/three-system target is absent. The CLI never prints the source
text or question, and a restricted report does **not** authorize model input,
open confirmation material, certify license, validate item semantics, qualify
C/P/G, or lower the eventual maturity target. Source-first rights and content
gates remain separate. The current test witness is HCL-authored structural
fixture data and is never an independent evaluation item.

Positive witness: a two-family, two-system fixture returns the exact observed
scope and a false full-target flag. Negative witnesses reject unequal H source
input and writing-system leakage across calibration and confirmation even for
restricted catalogs. The original complete-catalog and I01 frozen-runtime
regressions still pass. Provider calls and spend: zero. LongMemEval: sealed.

**EVALUATION_DELTA:** I02 can now record bounded source coverage without
silently promoting it to I01 maturity or treating a structurally valid partial
catalog as an invalid case. **HCL answer CAPABILITY_DELTA:** none; independent
source qualification remains `NEXT_READY`.
The historical frozen I01 validator and paid calibration package hashes remain
unchanged.
