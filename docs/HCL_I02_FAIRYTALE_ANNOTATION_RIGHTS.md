# I02 — FairytaleQA annotation provenance and rights boundary

Status: **AUTHORSHIP AND ROOT LICENSE PINNED / PROVIDER INPUT NOT RELEASED**.

The [publisher's repository at the selected commit](https://github.com/uci-soe/FairytaleQAData/tree/a24ddc17364666b7c13a425b9970c87368b03417)
describes the dataset's questions and answers as developed by education
experts. It identifies the question CSVs as those experts' QA pairs and
explains the two annotator answers in validation/test. The same repository
has a root [Apache 2.0 license](https://github.com/uci-soe/FairytaleQAData/blob/a24ddc17364666b7c13a425b9970c87368b03417/LICENSE).
The [executable evidence check](../scripts/i02_fairytale_annotation_rights.py)
pins both files to SHA256 and publisher Git blobs; the
[receipt](../reports/HCL_I02_FAIRYTALE_ANNOTATION_RIGHTS.json) contains only
identity and gate fields. No story, question or answer text was displayed.

This adds direct publisher evidence for annotation authorship and a root
repository license. It does **not** automatically settle every rights issue:
the underlying story has its own [blind edition and scoped rights
record](HCL_I02_FAIRYTALE_BLIND_PROVENANCE.md), provider processing geography
has not been verified, and this check is not a legal clearance for every
jurisdiction or distribution mode. The selected question's meaning and
[long-character task fit](HCL_I02_FAIRYTALE_QUESTION_TAG_AUDIT.md) remain
unaudited. The I01 source, split, arm, model and scorer freeze is also
incomplete. Accordingly `model_input_allowed=false` and
`confirmation_qualified=false` remain hard boundaries.

**EVALUATION_DELTA:** annotation authorship and root-license evidence are
now pinned to the exact upstream version rather than inferred from a
repository badge. **HCL answer CAPABILITY_DELTA:** none. Zero provider calls,
zero historical-budget reuse; LongMemEval remains sealed.
