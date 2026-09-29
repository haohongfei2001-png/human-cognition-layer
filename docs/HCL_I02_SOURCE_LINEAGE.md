# I02 — exposed calibration systems and confirmation firewall

Status: **KNOWN EXPOSURES PINNED / ZERO CONFIRMATION SYSTEMS QUALIFIED**.
The [lineage receipt](../reports/HCL_I02_EXPOSURE_LINEAGE.json) records the
two I02 source systems that entered paid C/P/G calibration. The
[executable guard](../scripts/i02_source_lineage.py) composes I01's ordinary
input/fairness check with a check against those historical author, template,
writing-system and source-group identities. This matters when a future
confirmation catalog omits calibration cases: I01's catalog cross-split check
alone cannot see a past calibration system in that catalog.

The MuSR **first source group** and Moral Stories **first record** were
exposed, but the I01 contract requires disjoint authors, templates and
writing systems across calibration and confirmation. Other rows in the same
author-team system therefore cannot become unseen confirmation merely by
changing row ID. This does not invalidate their historical calibration
receipts; it limits the later inference. The guard rejects such reuse even
when the new source group differs. It also requires a separate repository-wide
exposure audit, rights, source-first item validity and equal arm access. These
assertions need external evidence; passing this function is not proof that
they are true.

A bounded metadata screen checked the author-team
[ETHICS repository](https://github.com/hendrycks/ethics), its
[MIT repository license](https://github.com/hendrycks/ethics/blob/master/LICENSE)
and [Hugging Face card](https://huggingface.co/datasets/hendrycks/ethics).
The pinned card commit is `b8b47c589f8bee77175b8648e5497278b68da48a`;
its README SHA256 is
`29f0e8b49953f7599366c446b3e89efb90d08faf73a7e2dfb04ef39595e41a34`.
No data file or native label was opened or sent to a model. A public search
result nevertheless displayed **one scenario snippet of unknown row ID**.
That system is conservatively marked *screened, not unseen confirmation*.
MIT metadata also does not settle actual task fit or item semantics. The
source was not promoted or used for a call.

The registry is deliberately scoped to **known I02 exposures**, not a claim
that every historical HCL experiment has been audited. A real I03 package
must complete the repository-wide audit and protect truly unexposed source
systems before any outcome is viewed. The [source-first semantic scorer](HCL_I02_SEMANTIC_SCORER.md)
also needs reviewer procedure and case obligations fixed before confirmation.
No new provider call, data-row download, LongMemEval access or HCL runtime
change occurred in this package.

**EVALUATION_DELTA:** changing a row ID or omitting calibration cases from a
future catalog no longer makes the two exposed author/template/writing
systems eligible for confirmation in the I02 guard. **HCL answer
CAPABILITY_DELTA:** none; the current phase is independent evaluation.

**NEXT_READY:** find and verify an unexposed independent source system with
clear model-input rights and real task fit, then freeze a protected split and
source-first item audit. Do not reuse either consumed calibration grant.
