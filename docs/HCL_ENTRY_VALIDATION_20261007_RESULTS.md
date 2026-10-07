# Entry-routing smoke failed end to end

## Actual outcome

The [entry-routing diagnostic](HCL_ENTRY_VALIDATION_20261007.md) ran once on the
adopted source-entry hint runtime. The first response selected only B01, so it did
avoid the declared B02/D02 source/version blockers. It omitted semantic_candidates
and used only an operation question, source ID and empty bindings. The real B01
literal reader executed but found no admitted typed premises and no checked
mental-expression treatment. Executing a reader did not satisfy the frozen
relevant-treatment requirement.

The final model request was still sent, as prescribed by this frozen experiment's
original complete-round rule. Its full request was 10,643 bytes, well below the
unchanged 36,000-byte limit. The provider returned finish_reason=length, 8,192
completion tokens, provider-reported reasoning_tokens=8,192 and zero visible
content characters. The adapter rejected that incomplete return. No final answer
or valid citations were delivered; the exported empty final string is preserved
exactly and is not an answer. Unlike the old 4K diagnostic, this run retained safe
finish/token/content-size metadata, so these facts are directly observable without
publishing internal reasoning.

The receipt is STOPPED_NO_RETRY and the new grant is CLOSED_NO_TRANSFER_NO_RETRY.
The optional second stage was never granted or started. Its four calls/CNY 4,
together with unused parts of the first-stage ceiling, cannot fund a retry.
Workflow success means the bounded execution/export completed; it does not mean
that the semantic or delivery gates passed.

## Interpretation and limits

The earlier [single semantic-input smoke](HCL_SEMANTIC_SMOKE_20261007_RESULTS.md)
had three source-anchored B01 candidates and relevant conditional treatment. Here
that field is absent. Provider-free replay of both original argument objects on
this same current runtime reproduces each original native result exactly: the
previous conditional path is checked; the current literal path is not. Neither
replay changes the original source or supplies replacement live arguments.

The global planner contract had already requested faithful semantic candidates
for prose outside native literal forms. This result shows that one response
omitted them. It does not establish why, prove a deterministic routing-hint
regression, or show general improvement from avoiding two unsupported operations.
No Base arm, second case, ablation, unseen evaluation or second model ran. Prior
narrow successes and failures remain unchanged; formal I02-I06 remains open.

## Original evidence and exact run

- [Run 37659844666](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37659844666),
  attempt 1, workflow 377648078. M `ea753add72b78705343a083a7e713a2a189f29e2`
  has sole parent G `5f6f4a333a7ae380bb553bd3e9a80e826738587b`; E is
  `f4b9371e9fe2232deb9918c9116be4705b325957`.
- Runtime SHA256 `7bbbb74b9877f108bf8052cc252d588302a820f0b8d5d17a9177c76019def12b`.
  [Frozen package](../.github/frozen/hcl-entry-validation-20261007/package.json)
  canonical SHA256 `cea6e1e6a5f7d25d71c3c54a58b17457b96e7d2cc023927160aa6991548fbdef`.
  Original packet/rubric bytes are unchanged; only original case 0 ran.
- Artifact 11500084427, ZIP SHA256
  `9cb08b22e199e354f2304a147ca4cd07bb8058d5540ea832b59b7114e0c0b999`, verified
  against GitHub metadata before extracting its single named public JSON.
- [Original public evidence](../reports/HCL_ENTRY_VALIDATION_20261007_1_PUBLIC_EVIDENCE.json),
  raw SHA256 `092730d2dbb099df110cb63e9338cce234f88e9f58aad3387d06530c694a0701`,
  canonical `89fbf23fcb72c8a8aad763cbb1ce7f5c0ddcc194fcab9476df491904b804d664`.
- [Independent source-first review](../reports/HCL_ENTRY_VALIDATION_20261007_1_SOURCE_REVIEW.json)
  binds the original evidence and distinguishes passing source/routing integrity
  from absent relevant treatment and undelivered answer obligations. Unproved
  answer obligations are not invented errors in a nonexistent final answer.
  Raw SHA256 `56ce1985a034d08f576299e923c1560080fa0223a2e16bf44bbe024dde008d99`,
  canonical `60158db266ff8d26ad6a3468bc5ec5f4a54d0875e521078b0f916d08fcaa091f`.
  All ten answer obligations and four smoke requirements remain unproved; the
  review assigns no invented semantic-error tags to the empty answer. The exact
  frozen stage-two validator rejects the original evidence with
  `PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED`.
- Bounded native evidence canonical SHA256
  `9b12365b77be12d80f5a5ff7ce371b3b724a302036d4abaed3a23685de56d3dd`.
  This one actual B01 record preserves original arguments, native outcome/policy,
  exact sources and receipt/projection binding. No planner reply or reasoning is
  included.

## Calls and closure

| Phase | Prompt tokens | Completion tokens | Full request bytes | Finish | Peak-rate CNY estimate |
|---|---:|---:|---:|---|---:|
| Planning | 6,556 | 7,143 | 31,171 | stop | 0.251865 |
| Final | 2,365 | 8,192 | 10,643 | length | 0.242469 |

Two real calls used **CNY 0.494334 at the prechecked peak-rate estimate**, not a
verified invoice. The conservative full hold was CNY 1.998144; it is not a claimed
provider charge. The [stage-one grant](../.github/HCL_ENTRY_VALIDATION_20261007_1_GRANT.json)
is closed with zero remaining call or spending authority. Its original READY
canonical SHA256 `19183217a5b43a62d126102674beeedd0cccae1710c3061dc0c2d035e8ec5c71`
remains preserved at M. No calendar cutoff applied; the original 600-second stage
window and 180-second request/dispatch margins remained in force.

Next work is provider-free explicit literal/semantic/insufficiency input contracts,
strict-evaluation checks before paying for an answer without required native
processing, and separately bounded planning/final reasoning configurations. These
are proposed reliability repairs, not new tested outcomes. Ordinary evidence-limited
answers must remain possible; no candidate or checked result may be manufactured.
Any further real run requires a new limited approval. This closeout changes no
runtime, frozen package, old grant/report, original evidence or HCLA.
