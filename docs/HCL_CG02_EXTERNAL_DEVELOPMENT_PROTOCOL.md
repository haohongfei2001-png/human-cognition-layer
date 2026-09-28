# HCL-CG-02 external development package — frozen before provider use

Status: **PROVIDER-FREE FROZEN; PAID VALIDATION NOT AUTHORIZED**. The only next gate is `HCL_CG02_EXTERNAL_VALIDATION_OWNER_AUTHORIZATION`. This protocol follows the [canonical contract](HCL_CG02_CAPABILITY_CONTRACT.md) and [implementation limits](HCL_CG02_IMPLEMENTATION.md).

## Source and question

The package contains four short HCL-authored synthetic English dialogue cases: omitted condition, preserved condition, proposal with acceptance, and expectation before a later withdrawal. They are newly written in this repository, with exact source bytes and SHA-256 digests in [the frozen package](../reports/HCL_CG02_EXTERNAL_PACKAGE.json). No third-party corpus, private source, sealed LongMemEval row or historical consumed benchmark is used. These cases are public and source-audit-exposed. They support only a bounded development probe, not a fresh-set or population claim.

Every arm receives the same source task and strict JSON answer fields: act kind, source condition, expectation relation, access status, response reference, withdrawal order and whether it makes an unsupported moral claim. The gold fields are fixed before provider calls. They were checked against the source-grounded deterministic operation; no gold field appears in a model input.

## Five arms and treatment

All 20 calls, if separately authorized, would use the same `gpt-6-sol` model and default Standard service tier, at most 512 output tokens per call, without tools or retries.

| Arm | Frozen input |
|---|---|
| C | Direct source and task instruction |
| P | Strong simple process prompt: source act, conditions, later quoted expectation, access and timing, then uncertainty |
| G | Generic ordered event rows with speaker, addressed recipient and source text; no specialized social checker |
| H | Actual HCL v1 prepared model messages, including checked CG-02 social state |
| H-new | The same HCL route, preparation and evidence, with only the CG-02 checker state removed |

The package builder executes the ordinary-text parser and checker for every H case. It rejects a case unless source preparation is valid, at least one act and one expectation check execute, H contains checked state, H-new removes it, and final inputs differ only by that state. It also rejects any source/gold mismatch, any unexpected extraction call and any serialized input exceeding 8,000 UTF-8 bytes. The builder cannot call a provider. Rebuild and compare with `python scripts/cg02_external_package.py`; `--write` is reserved for a deliberate package revision before authorization.

## Scoring and decision

The scorer accepts only a JSON object with exactly the seven predeclared fields. It records validity, exact matching fields (0–7), and full-case correctness; malformed output or extra fields fail validity. An unsupported moral assertion fails the corresponding field. Compare all five arms case by case; report raw answers, API usage, billed cost, invalid outputs and paired score differences. The four cases are too small for significance claims. A retained CG-02 increment requires H to improve meaningfully over both P and G, with H-new supporting attribution. Equivalent P/G behavior calls for SIMPLIFY; systematic harm or dependence on hand-prepared oracle state calls for DEACTIVATE; source or measurement failure is INCONCLUSIVE. Do not change cases after seeing results to seek a positive outcome.

## Proposed owner budget, not authorization

[Official OpenAI API pricing](https://developers.openai.com/api/docs/pricing), checked 2026-09-28, lists `gpt-6-sol` Standard short-context at USD 1 per million input tokens and USD 5 per million output tokens. The frozen 20-call maximum, 8,000 input-token conservative bound per call and 512 output-token cap imply at most USD 0.2112 at those rates. Propose a **USD 0.30 hard cap** to allow for price/usage accounting variation. Stop before a call if projected usage would exceed that cap; no automatic retry or additional arm/case. Reconfirm model access and price before any later authorization is exercised. No historical CG-01 budget transfers, no new paid plan, and no call or spend are included in this freeze.
