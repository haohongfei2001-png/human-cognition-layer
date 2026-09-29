# I02 — initial source rights and independence screen

Status: **0 QUALIFIED / PROVIDER-FREE / I02 CONTINUES**. This is a bounded
metadata and rights screen, not content sampling, benchmark selection, or a
confirmation package. The executable [gate](../scripts/serious_eval_source_gate.py)
and [registry](../reports/HCL_I02_SOURCE_SCREEN.json) refuse model-input use
until AI-use rights, item-level source validity, exact content hash and
disjoint historical exposure have affirmative receipts.

| Source | Primary finding | Current action |
|---|---|---|
| [OpenStax *Introduction to Philosophy*](https://openstax.org/books/introduction-philosophy/pages/1-introduction) | Its official attribution terms impose CC BY-NC-SA conditions and separately require prior written permission for ingestion into LLM or generative-AI offerings. The review questions therefore cannot be sent to the evaluation provider under the current setup. | **REJECTED_EXPLICIT_AI_INPUT_RESTRICTION**. No page or question is selected for a provider call. |
| [Project Gutenberg *Persuasion* #105](https://www.gutenberg.org/ebooks/105) | The official catalog says public domain in the USA. Its own reuse notice tells users outside the USA to check applicable local law. That is not a global evaluation permission receipt. | **DEFERRED_JURISDICTION_RIGHTS_CHECK**. No text selected. |
| [MuSR pinned GitHub repository](https://github.com/Zayne-sprague/MuSR/tree/b1f4d4168a9cfc6760e8b74d728e4516023dfaa5/datasets) and [license](https://github.com/Zayne-sprague/MuSR/blob/b1f4d4168a9cfc6760e8b74d728e4516023dfaa5/LICENSE) | The repository is MIT-marked and exposes an object-placement file, pinned at blob `bc083672c66a0fca5fa7de6b43a062e9a38ec3f5`. Its README says scenarios were generated with ChatGPT/GPT-4. The exact GitHub data-rights scope and item validity were not established. A direct raw-file fetch timed out; no row was selected from this distribution. | **PROVISIONAL_REQUIRES_DATA_RIGHTS_AND_ITEM_AUDIT**. Do not conflate this file with the separate author-team Hugging Face distribution. |
| [TAUR-Lab/MuSR on Hugging Face](https://huggingface.co/datasets/TAUR-Lab/MuSR) | The author-team dataset card declares **CC BY 4.0**. Its pinned `object_placements.csv` at `7c365b439a222150f317764d4f16ae6c96d7d94a` has SHA256 `98cd17d2c9ea53664e274365e901c90dfcaa40d17547dfbd369f1cd26fd2a81c`, 256 questions across only 64 distinct narratives. The first narrative's four rows are exposed for calibration; two questions received a limited source-first read. See [receipt](../reports/HCL_I02_MUSR_CALIBRATION_SOURCE_AUDIT.json). | **CALIBRATION_ONLY_ITEM_AUDIT_PARTIAL**. Rights for this distribution are clearer, but no confirmation item or model comparison is qualified yet. |

In the inspected MuSR narrative, a character directly encounters an item at
one location; that first native answer is source-plausible. A second answer
depends on whether another character saw an earlier move before entering an
isolated booth. The prose suggests but does not explicitly settle every
perceptual step. Treat its native choice as a **plausible generated label**, not
verified private-belief truth. All four questions sharing this narrative are
one calibration source group, never four independent samples. The source-only
[parser and gold firewall](../scripts/i02_musr_calibration.py) pins bytes,
enforces grouping, and strips native answer fields from the prepared arm input;
its synthetic tests do not certify the dataset. At the time of this initial screen no MuSR row had been sent to a provider. The later first-group C/P/G calibration is exposed and closed; see [its immutable closure](../reports/HCL_I02_CPG_CALIBRATION_CLOSURE.md).

Historical HCL-authored cases and previously consumed benchmark rows remain
development evidence. A source being independently published does not prove
model-pretraining novelty, label truth, appropriate narrative structure or
permission to ingest it. Source identifiers and metadata are deliberately
kept separate from future hidden confirmation items.

**EVALUATION_DELTA:** a source cannot enter the paid comparison merely because
its repository appears open or its topic fits HCL. The gate fails closed on
AI-use restrictions, unknown license scope, missing source-first validation,
missing exact hashes and historical exposure. Four provider-free tests witness
these boundaries; no human-cognition CAPABILITY_DELTA or efficacy result is
claimed.

**NEXT_READY within I02:** complete item-level source/actor/time/access audit
for a disjoint candidate subset of the CC BY 4.0 distribution, then qualify
additional independent writing systems and C/P/G on separate calibration.
Keep GitHub MuSR and Hugging Face MuSR separate by file/version; do not promote
metadata rights or two exposed questions into a confirmation claim. If any
source remains rights-uncertain, exclude it and proceed to another.
LongMemEval remains sealed. No provider calls or spending in this screen.
