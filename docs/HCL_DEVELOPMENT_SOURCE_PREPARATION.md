# Development source preparation, ahead of future comparisons

Source/task preparation can run alongside general runtime repairs. This packet
reuses existing source history, comparison, scorer and exposure infrastructure;
it does not start I03–I05 execution or introduce a new runtime mechanism.
[Machine receipt](../reports/HCL_DEVELOPMENT_SOURCE_PREPARATION.json).

## Ready for operational protocol preparation: MindGames

The [author dataset card](https://huggingface.co/datasets/sileod/mindgames/blob/e378f4c70f66413a00c664373f4f43064b3ba752/README.md)
licenses the data Apache-2.0. The [author repository](https://github.com/sileod/llm-theory-of-mind)
also supplies Apache-2.0 code. [Sileo and Lernould, EMNLP Findings 2023](https://aclanthology.org/2023.findings-emnlp.303/)
describe generated dynamic-epistemic reasoning tasks, not human private-state truth.

Pin: e378f4c70f66413a00c664373f4f43064b3ba752, train parquet
`data/train-00000-of-00001-29e951c428782278.parquet`, 11,174 rows.
Before reading labels or model outputs, fix the first six native integer indexes
by SHA256(`HCL-MINDGAMES-SOURCE-20261001/` + index). No label, difficulty, model
prediction or H treatment filter. Selected indexes: 3274,41454,41671,54915,65380,1556.
The complete fetched distribution is development-exposed and excluded from final.

The ordinary task consists of the original premise and hypothesis, with the native
`entailment` / `not_entailment` vocabulary. `development_mindgames_source.py` keeps
both strings byte-identical and separates the label/formal `smcdel_problem`,
`pbcheck`, model prediction, confidence, difficulty and setup metadata from input.
Future Base/H must receive the same complete premise/hypothesis. Do not inject a
formal state, handcrafted route, answer hint or new premise about a particular case.

Source-first review of all six finds labels consistent under the benchmark's
idealized factive knowledge and shared public-announcement conventions. A direct
card observation and public positive/negative announcements support the positive
cases; unseen-card and contradiction cases support the negative cases. This is a
bounded developer source review, not a human/independent efficacy certificate.
Detailed row-level reasons and immutable native-row/source hashes are in the receipt.
Six rows from one generator do not establish six independent sources or broad
cognition coverage. Long narrative, value integration and philosophy remain uncovered.

Independent read-only review agrees with all six native labels and the six
ToMBench dispositions. This is development-team review, not final independent
efficacy. A future runner must select only `ordinary_input`; the preparation
metadata deliberately contains `native_label` for audit and must never be sent
as a whole to a provider.

Remaining before any run: exact
current runtime and common prompt/model/scorer/input freeze; conservative total
call/cost reservation; a new explicit bounded budget. No credentials, grant,
workflow trigger or model call exists in this preparation. Existing comparison
runners and provider profiles are reused only through a new reviewed package;
closed grants and immutable consumed runners are not reopened.

## Deferred: two ToMBench task distributions

Publisher [zhchen18/ToMBench](https://github.com/zhchen18/ToMBench/tree/4f491f0784ed31ef93a8837615fbc48f885cf78d),
MIT, evaluation only/no training. This is an already exposed writing system.
Preselect three rows each from Discrepant Intentions and Completion of Failed
Actions by SHA256(`HCL-SOURCE-PREP-20261001/` + task + `/` + zero-based row index),
without outcome/label/treatment filtering. Keep all six; substitute none.

- Intentions row36: broadly supported accidental-action option, with a wording caveat
- Intentions row8: reject native source/question/options mismatch; a coffee-shop
  story has unrelated office-cleaning/scrap-paper choices
- Intentions row16: explicit mistaken-instruction explanation supports the label
- Failed Actions row15: plausible closing-library response, not a reported actual action
- Failed Actions row6: competing goals leave the chosen action underdetermined
- Failed Actions row17: low phone battery does not establish the native go-home prediction

Native labels remain unchanged. In particular, a source-grounded objection to the
mismatched row must not become an HCL error or a target for a runtime patch. The
whole six-row candidate is deferred as a reliable aggregate evaluation packet.

## Provenance and parallel readiness

Both combined selected-text scans at main c59f618 found no matching 12-word window
in 3,708 reachable UTF-8 Git blobs; 54 sealed object IDs were excluded before body
reads. No oversized blob was skipped. This is bounded reachable-history evidence,
not deleted-ref, chat-history or model-pretraining novelty. Current safe history
entry rejects shallow/partial/replaced/grafted histories. All opened publisher
lineages, distributions, selected native-row and source hashes enter the final
exposure firewall. No original distribution or private model response is published.

Existing I03 comparison-arm and source-first scorer helpers, I04 information-state
ablation witness and I05 generic/Qwen capability profiles already exist. Their
presence is preparation evidence, not completed generalization, mechanism
attribution or transfer. Source qualification and offline checks can advance now;
actual model competence, powered comparisons and I06 disposition require observed
qualified results. Final sealed confirmation stays separate and deferred.
