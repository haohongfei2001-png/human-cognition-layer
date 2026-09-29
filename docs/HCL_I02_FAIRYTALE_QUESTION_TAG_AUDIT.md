# I02 — FairytaleQA question-tag task-fit screen

Status: **PINNED CATEGORY AUDIT / LONG-CHARACTER FAMILY FIT UNPROVEN / NOT QUALIFIED**.

The [prior metadata preselection](HCL_I02_FAIRYTALE_METADATA_CANDIDATE.md)
fixed one source group before model or H outcomes. The [blind edition
match](HCL_I02_FAIRYTALE_BLIND_PROVENANCE.md) established text provenance.
This package processed the exact publisher question CSV at commit
`a24ddc17364666b7c13a425b9970c87368b03417` only for categorical
metadata. Its SHA256 is
`54a03fb11936d2363371ecbeb74f08695680fffd699507f9db0fcd7f5fb92f13`;
the publisher Git blob is `a8b6251f1826940eef45b4ba7abef8a05089778e`.
The [executable audit](../scripts/i02_fairytale_question_metadata.py) checks
both identities and emits the [category-only receipt](../reports/HCL_I02_FAIRYTALE_QUESTION_TAG_AUDIT.json).
Question and answer **text was not displayed, inspected or saved** by the
implementer; the question file's bytes were processed in memory for tags.

Of 61 questions, 55 are publisher-tagged local and six summary. The six
summary items are tagged five `causal relationship`, one `action`, and zero
`character` or `feeling`. There are five `character` and four `feeling`
questions among the whole 61, but all are local. Tags do not establish
whether a question requires tracking character development across the story.
In particular, a long source and many questions alone cannot qualify the
I01 **long character development** family. A later source-first item audit
could establish suitable cross-section reasoning, but the current evidence
does not. No candidate substitution is authorized by these counts.

The source remains excluded from provider input and confirmation. Question
rights scope, item semantics, split novelty and the I01 arm/model/scorer
freeze remain open. This check used zero provider calls, zero historical
budget and no LongMemEval access. It does not change HCL runtime or support
an HCL efficacy claim.

**EVALUATION_DELTA:** the task-fit screen now prevents a 5,731-word story
from being silently counted as long character development solely because
it is long. **HCL answer CAPABILITY_DELTA:** none; I02 is source qualification.
