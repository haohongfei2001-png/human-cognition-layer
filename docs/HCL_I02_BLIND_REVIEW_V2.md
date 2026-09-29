# I02 blind review v2: residual claims before allocation reveal

Status: **PROVIDER-FREE HANDOFF IMPLEMENTED / NO INDEPENDENT REVIEW**.

The [versioned handoff](../scripts/i02_blind_review_v2.py) takes the same
frozen source-first manifest and completed raw receipt as v1. It emits opaque
answers and a separately held allocation key. The v2 reconciliation requires
both complete prespecified-obligation judgments and a coverage attestation
with exact excerpts and source support judgments for material residual claims.
It runs the unchanged v1 score, checks the supplemental residual audit, and
only then returns phase identities. A v1-only review, omitted output, altered
source/packet, wrong opaque ID, disclosed arm, missing attestation or
unsupported private-state claim fails or yields ineligibility. Historical v1
packets and scores remain attached to their original evidence.

**CAPABILITY_DELTA (evaluation workflow):** a reviewer can no longer use the
active v2 handoff to reveal C/P/G identities and a favorable v1 score while
skipping the full-answer residual-claim record. The positive witness uses the
real ACL v8 raw receipt to produce three anonymous outputs and reconcile
complete v2 records. A negative witness adds an unsupported private-intention
sentence and verifies ineligibility. Nineteen targeted provider-free tests
cover source, allocation, completeness, negative inference, composition and
historical regressions. **HCL answer CAPABILITY_DELTA:** none.

The source auditor and reviewer must still be independent in practice. A
Boolean coverage attestation does not prove claim enumeration or semantic
truth. The exposed ACL case remains development-only, and its original
developer-blind 6/8, 7/8 and 8/8 v1 findings are not upgraded or rescored.
No new confirmation source was qualified.

During bounded source screening, [MeetingToM's author card](https://huggingface.co/datasets/OliviaWang1101/MeetingToM)
showed that its CC BY 4.0 license covers annotations and reconstruction
metadata, while required AMI meeting media must be separately obtained under
their own terms. It is therefore not a ready text-only I02 source. The
[SQuALITY source coverage audit](HCL_I02_LONG_INPUT_COVERAGE.md) still records
25/25 dev stories beyond H's 16,000-character ordinary narrative gate; no
case was promoted by shortening source text. These checks are triage, not
confirmation results.

Provider calls/spend: **0 / USD 0**. LongMemEval: **SEALED**.
**NEXT_READY:** `I02_UNEXPOSED_SOURCE_QUALIFICATION`.
