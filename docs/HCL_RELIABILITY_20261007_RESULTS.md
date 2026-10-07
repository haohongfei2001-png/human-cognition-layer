# October 7 ordinary-default reliability smoke: failed and closed

## Outcome

The single approved smoke stopped on its **first planning call**. The provider
returned 6,376 prompt tokens and 4,096 completion tokens; the frozen executor
rejected that return as `INCOMPLETE_ANSWER_NO_RETRY`. No operation was selected or
executed, no native HCL result was produced, and no final-answer request was sent.
There is no final answer to score for content quality. The required complete
source-first smoke gate fails, so the four Base/HCL pairs were not run.

This is a real failure of the current ordinary 4,096/high configuration on this
frozen authored input. It does not prove every 4,096-token request must fail, or
identify the exact cause from private planner text. The public evidence does not
include the raw provider envelope, exact finish reason, planner text or reasoning
breakdown; therefore it does not establish that all 4,096 tokens were reasoning,
or that visible planning content was blank.

The workflow succeeded in executing the bounded attempt, stopping and exporting
its permitted evidence. Green workflow checks are **not** a passed reliability
smoke. The post-repair native-policy/source-version behavior was not reached in
this run. No comparison, efficacy, production-readiness or I02-I06 result follows.

## Immutable execution identity

- Runtime file-map SHA256:
  `da8349d12f8d13001e565ccdc8dbd6933cdbff5d8ec3b6369823c01925a379e9`.
- [Frozen package](../.github/frozen/hcl-reliability-20261007/package.json)
  canonical SHA256:
  `0d8530ce5c2838015141423aa97fa701752583fbdd9f83b97ccb90b383bec5e4`.
- [Five fixed cases and rules](../.github/frozen/hcl-reliability-20261007/cases.json)
  canonical SHA256:
  `fa39ec373700214c1280ea5413fa46cbfe006641d02a8a094757b87f05507e2f`.
  All five were frozen and publicly exposed before any output. No case, rubric,
  model, token allowance or request limit was changed in response to the result.
- Executor adoption E: `226778837f9fff4db1870ad5e0b7b9f984f09361`.
- Grant-only adoption G: `49e2f30768cab8e8a51b342a004377b749112b7e`
  ([PR #385](https://github.com/haohongfei2001-png/human-cognition-layer/pull/385)).
- Single-parent marker M: `88b8e48c2ca989d15e7642172dfd68d056a4ff1d`
  ([PR #386](https://github.com/haohongfei2001-png/human-cognition-layer/pull/386)).
  Its only parent is G and its only changed path is the new stage-one marker.
- [Actual run 37610274523](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37610274523),
  workflow attempt 1, artifact 11477217275.
- Artifact ZIP SHA256:
  `a178a989d8a6405e5df9b19c6a004c3e32d67e0b52ab0677c6f0abefa7e8623f`.
- [Exact exported public evidence](../reports/HCL_RELIABILITY_20261007_1_PUBLIC_EVIDENCE.json)
  raw-file SHA256:
  `e2d190fa9fe4de3a634e8545ab222caa4693dc6a101ee1281578413d963fbdfe`.

The ZIP digest matched GitHub's artifact metadata and only the named public JSON
was extracted. That JSON is committed byte-for-byte. The native evidence contains
one correctly bound record with **zero operations**, not fabricated execution.
The independent source-first review is recorded separately in
[the review JSON](../reports/HCL_RELIABILITY_20261007_1_SOURCE_REVIEW.json);
it does not rewrite the exported receipt's pending-review field.

## Requests, cost and authority closure

The request used the existing DeepSeek account and `deepseek-v4-pro`, enabled/high
thinking, planning max_tokens 4,096 and unchanged final allowance 8,192. Its full
canonical request was 30,338 bytes, below the 36,000-byte bound; no truncation or
source shortening occurred. Full-request SHA256:
`5d1d85113dba32f829c739908ee35673eb89aedccd936c702e7b45b5f6c0f7b6`.
That identity equals the pre-output frozen planning request.

One model call was made. Official same-run peak-price and existing-account
readiness checks passed before dispatch. At CNY 9 input / 27 output per million
tokens, `(6376 × 9 + 4096 × 27) / 1000000 = CNY 0.167976`.
This is a conservative usage-rated estimate, **not an invoice**. The complete
CNY 0.777888 authorization reservation remains in the ledger; it is not a claim
that the provider charged that amount. SDK time was approximately 45.40 seconds;
the whole arm took approximately 45.92 seconds.

The new stage-one [grant](../.github/HCL_RELIABILITY_20261007_1_GRANT.json) is
`CLOSED_NO_TRANSFER_NO_RETRY`, with zero remaining calls and money authority.
Its original READY bytes remain at M, canonical SHA256
`3bbcdab3fa8965f68d22b98b2388534c0ae68c46719fc9d0d7a7592579744850`.
The receipt independently closed at the end of execution. The second stage was
never granted or triggered. Neither its CNY 10.30 / 12-call conditional allowance
nor any unused part of stage one's CNY 1.70 / two-call allowance can fund a new
attempt. The separate overall CNY 12 / 14-call ceiling does not create residual
authority. There was no retry, token/model upgrade, paid judge, recharge, new
credential, subscription or budget transfer. The absolute 14:00 UTC deadline
remains the original outer bound; failure closed the experiment earlier.

Only the five synthetic questions, safe execution statistics and the permitted
bounded native record are public. No final answer exists. No hidden reasoning,
complete planner response, provider envelope, credential or private user data is
included. Historical grants, experiments and HCLA remain unchanged.

## Next permitted work

Continue provider-free diagnosis of ordinary planning completion. Any proposed
repair must preserve real native execution, full source facts, source/citation
validation and the frozen experiment's negative evidence. Offline tests can
establish contract or size properties, not prove a model will plan correctly.
A new paid measurement requires a new bounded approval; this closed experiment
cannot be resumed, upgraded or supplied with replacement questions. The original
[preparation document](HCL_RELIABILITY_20261007.md) is retained as its pre-run
snapshot, rather than rewritten as if it predicted this result.
