# HCL v0.4 Evidence-Scoped Revision v0.1 — Controlled Diagnostic Closure

Verdict: **INTERNAL DIAGNOSTIC COMPLETE / NO INCREMENTAL UTILITY / NOT PROMOTED**

## Frozen boundary and execution

- Contract and six independently authored synthetic scenarios: `docs/HCL_V04_EVIDENCE_SCOPED_REVISION_V01_CONTRACT.md` and `eval/v04/evidence_scoped_revision_v01.json` on experimental PR #4.
- Fixture SHA-256: `7f08cbe1f5dd8207f505f37a9354440c28450d2462f7b0177cf184b10a4aa6ab`, committed before provider execution.
- Experimental exact branch head: `b6a174ce3356f7fe1407567c6754eae73b37aff3`.
- Deterministic minimal-slice run `35872042185` at implementation head `9b25ecf3e13d44073eb96cb505586bf61585c75a`: SUCCESS. The final trigger commit changed only the run marker; the comparison run itself repeated the fixture-hash, compile and correctness preflight before provider calls.
- Frozen single-model C/D/E/F run `35872423297` at `b6a174ce3356f7fe1407567c6754eae73b37aff3`: SUCCESS. The run used the existing `deepseek-flash` provider, fixed scenario/options/model, explicit call caps, and no external benchmark rows.

| Arm | Final action | High-information probe | Calls | Input characters | Output characters |
|---|---:|---:|---:|---:|---:|
| C — full-history reconstruction | 6/6 | 6/6 | 25 | 112,253 | 25,572 |
| D — eager persistent hypotheses | 5/6 | 5/6 | 42 | 184,777 | 56,839 |
| E — direct full-history reasoning | 6/6 | 5/6 | 12 | 32,350 | 2,576 |
| F — evidence-scoped query-time revision | 5/6 | 5/6 | 25 | 107,976 | 25,314 |

On `volunteer_shift`, C and E selected the discriminating ride probe and correct action. D and F selected a lower-information caregiving probe and the wrong final action. F's hidden candidate remained top-or-tied after response, but that did not recover the action. This is a functional miss, not merely a formatting failure. F skipped explicitly unrelated evidence and reduced calls compared with eager D, but E was both more accurate and much cheaper. The observed six cases cannot be tuned and rerun as fresh evidence.

## Correctness and claim boundary

The experimental ledger stored raw events before inference, blocked stale-state reads, retained target scope across restart, rejected out-of-scope evidence citations, and passed the deterministic v0.4 correctness tests. Those gates prove bounded implementation behavior, not human-state truth or generalization. No independently rated human judgments, external benchmark, cross-model transfer, production integration or owner-private examples were used. The result does not establish HCL incremental cognitive capability.

The F implementation stays on PR #4 as audit evidence and is **not** promoted into main or made the default path. Continue to use the simpler existing path while a different capability question is frozen independently. Do not consume new external benchmark rows or reinterpret the controlled diagnostic as a positive result.
