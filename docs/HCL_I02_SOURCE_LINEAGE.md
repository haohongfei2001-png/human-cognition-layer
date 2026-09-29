# I02 — exposed calibration systems and confirmation firewall

Status: **KNOWN I02 AND HISTORICAL EXPOSURES PINNED / ZERO CONFIRMATION SYSTEMS QUALIFIED**.
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

The v2 lineage receipt now also imports five historically exposed systems
already documented before I02: CogToM, SOTOPIA-Hard, FANToM, Hi-ToM and SAGA.
The [v0.4 exposure register](HCL_V04_EVALUATION_EXPOSURE_REGISTER.md)
records prior CogToM use, all SOTOPIA-Hard environment templates, earlier
FANToM conversations and Hi-ToM rows. Later [FANToM](HCL_V06_FANTOM_CPGD_FRESH_V01.md)
and [SAGA](HCL_V07_SAGA_FRESH_CPGD_V01.md) provider pilots exposed further
author-team material. I01's stronger writing-system split means an unseen
row within those systems cannot be called an independent confirmation
system. The guard checks exact declared author, template and writing-system
identities from the receipt; provenance still must verify that a new source
has been identified honestly.

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

A later [bounded QuALITY screen](HCL_I02_QUALITY_BOUNDED_SCREEN.md) opened
one CC BY-marked Nesta publisher article and the first writer's nine
development question texts. It did not open options or gold and did not call
a provider. Source-first task fit failed for I01 abstract concept/philosophy,
so the article and its question template are added to the screened exclusion
list. A Gutenberg catalog's automated plot summary for a separate Hannes Bok
story was also visible and is recorded there. Neither is an unseen
confirmation source. The executable guard rejects their declared author,
template or writing-system identities; the required repository-wide audit
still must verify that any future catalog declares identities honestly.

The registry is deliberately scoped to **these known I02 and pre-I02
exposures**, not a claim that every historical HCL experiment has been
audited. A real I03 package
must complete the repository-wide audit and protect truly unexposed source
systems before any outcome is viewed. The [source-first semantic scorer](HCL_I02_SEMANTIC_SCORER.md)
also needs reviewer procedure and case obligations fixed before confirmation.
No new provider call, data-row download, LongMemEval access or HCL runtime
change occurred in this package.

The later [narrative source boundary screen](HCL_I02_NARRATIVE_SOURCE_BOUNDARY.md)
adds the development-exposed *Amy Foster* NarrativeQA questions and four
native reference-answer pairs, plus two Narrative Crossroads teacher modules
whose wants/fears and sample responses would be oracle-like model input.
It records related original story authors as well as question-system authors.
The guard now also rejects an exact recorded source-text digest even if a
candidate invents new lineage IDs; differently formatted or paraphrased copies
still require the independent repository-wide provenance audit. No item was
qualified or sent to a provider.

**EVALUATION_DELTA:** changing a row ID or omitting historical rows from a
future catalog no longer makes the two I02 and five named pre-I02
author/template/writing systems eligible for confirmation in the I02 guard. **HCL answer
CAPABILITY_DELTA:** none; the current phase is independent evaluation.

**NEXT_READY:** find and verify an unexposed independent source system with
clear model-input rights and real task fit, then freeze a protected split and
source-first item audit. Do not reuse either consumed calibration grant.
