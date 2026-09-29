# G-ARCH preliminary assessment — source anchor repair frozen

Gate state: **STRUCTURALLY_READY / OPERATIONAL_INPUT_UNVERIFIED / EFFICACY_UNTESTED**.
This is a post-H05 assessment, not a G-ARCH pass or an efficacy result.

| Canonical criterion | Current evidence and disposition |
|---|---|
| Structure | A–H have opt-in implemented operations and explicit limits; provider-free construction only. No new ontology is needed for this gate. |
| Composition | H05 selects B03/C03/D04/E05/F03/H04 plus F05 on a difficult ordinary question; H01 direct source handles a simple question. H03 support edges and H04 answer audit are executable. Provider-free pass. |
| Real ordinary input | **Open.** E03's one real extraction returned exact unique quotes but incorrect model-supplied offsets, and the strict validator refused before a final call. Historical run remains FAILED/CLOSED. A narrow source-derived-offset repair now passes provider-free replay of that actual raw response; a fresh one-shot extraction and final call must still succeed before `OPERATIONALLY_READY`. |
| Long narrative | F05 branch/time/conflict replay and 12-actor/120-event engineering smoke; H05 joins a source-local answer with relevant opposed chapter reports without proving cross-source identity. Provider-free pass with source-local limit. |
| Semantic boundaries | Actor/source/time/access, challenge, quote, uncertainty and assumption tests pass in local/replay CI. Unique exact quotation may override a wrong supplied offset with a receipt. Duplicate or absent quotations still refuse. No absolute semantic correctness claim. |
| Selection/budget | Direct tasks bypass hard operations; hard tasks have event, conflict, closure and context bounds. H02 stops on no-gain evidence; no truncation of key counterreports. Provider-free pass. |
| Auditable freeze | Exact source, prompt/runner, model, no-thinking setting, cap, source/version semantics and runtime hashes are frozen in [the package](../reports/HCL_G_ARCH_ENTRY_PACKAGE.json). Provider-free replay and package check are saved in [the preflight](../reports/HCL_G_ARCH_ENTRY_PREFLIGHT.json). The sole trigger is introduced in a separate PR after the repair package passed exact-main CI; its result remains pending. |

The repair accepts a wrong optional offset only when the full submitted quote
occurs exactly once in the authorized source. It derives the actual span from
that source and records both offsets. It never permits a paraphrase, ambiguous
duplicate, hidden source, invalid event content or unverified mental inference.
Replay of the historical failed provider response now grounds all six literal
events, including five source-derived offsets, and reaches the real final-input
preparation. Replay does **not** change the historical run's failed status.

The new one-shot operational package uses the existing DeepSeek Flash account,
thinking disabled, one extraction and one final JSON call, no retries, and a
**USD 0.04 hard cap** with conservative Pro-rate reservation. The published
Flash peak rates were checked on 2026-09-29 against the
[official pricing page](https://api-docs.deepseek.com/quick_start/pricing/).
No old grant or residual budget is reused. The workflow listens only for a
single future main trigger; its uniqueness and first-attempt gates precede
provider access. A failed gate yields no paid call. Raw requests/responses,
actual model/usage, rated and estimated cost, final input and SHA/run ID must
be reviewed source-first before any gate disposition. Invoice cost may remain
unavailable.

LongMemEval remains SEALED/NOT_ACCESSED. This authored case is an operational
smoke, not independent evidence. No leaderboard work is authorized by this
assessment.

**NEXT_READY:** merge the sole trigger, then review its raw operational receipt. If live entry or final call
fails, repair the concrete defect without reusing this one-shot run.
