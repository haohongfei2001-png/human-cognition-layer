# HCL v0.4 Hypothesis-Guided Action v0.1 — Closure

Status: **COMPLETE / CONTROLLED DIAGNOSTIC; INCREMENTAL UTILITY UNPROVEN**

This is an internal six-scenario development result. It is not external benchmark, real-human, cross-model or production evidence.

## Frozen contract and implementation

- Protocol: `docs/HCL_V04_HYPOTHESIS_GUIDED_ACTION_V01.md`.
- Implementation contract: `docs/HCL_V04_HYPOTHESIS_GUIDED_ACTION_CONTRACT_V01.md`.
- Fixture: `eval/v04/hypothesis_guided_action_v01.json`, SHA-256 `2605318bc10cae6710b9597ba82870058a71abcf46315aeeae5a36527d412f3a`.
- Model: `deepseek-flash`; seed: 42; six predeclared controlled scenarios.
- C reconstructs structured hypotheses before and after one probe; D persists and incrementally updates the hypothesis state; E reasons from the same visible history and candidate definitions without a hypothesis store. Each selects one allowed probe and final action. Hidden state and correct actions are evaluator-only.

## Exact evidence

- Candidate PR: #3, head `b8c4bfc237798b60f32cbc8a22e010cbc81575e5`.
- Candidate workflow: `35853990890` SUCCESS; artifact `10746926720`; result SHA-256 `a4ee84484b991114d7541500c5bca535dc8e5e7000ef2e4266ac8d3fe0bf1bec`.
- Integrated runtime main: `825626654eca8794b739f7c3f5108120801cc669`.
- Exact-main workflow: `35854781478` SUCCESS; artifact `10746468596`; result SHA-256 `5d1edb20d270e70af09d6c0f0d4da4308d6fde6e59179032aeb9e5016f3f5e17`.
- Exact-main minimal-slice regression workflow: `35854781504` SUCCESS.
- The workflow checked the frozen fixture digest, validation, and 13 runner/hypothesis/policy tests before the provider comparison.

| Metric | Candidate C | Candidate D | Candidate E | Main C | Main D | Main E |
|---|---:|---:|---:|---:|---:|---:|
| Correct final action | 6/6 | 6/6 | 5/6 | 6/6 | 6/6 | 6/6 |
| High-information probe | 4/6 | 5/6 | 5/6 | 5/6 | 5/6 | 6/6 |
| Calls | 24 | 24 | 12 | 24 | 24 | 12 |
| Input characters | 86,982 | 89,947 | 22,532 | 86,926 | 89,599 | 22,523 |
| Output characters | 21,656 | 22,231 | 2,603 | 21,589 | 21,953 | 2,539 |
| Semantic repairs | 0 | 0 | 0 | 0 | 0 | 0 |

All six selected final actions were correct for C and D in both executions. Candidate E missed `meeting_probe` after choosing `CHANGE_ROOM`; exact-main E chose `ASK_CONSTRAINT` and the correct `SCHEDULE_AFTER_4` action. The two executions used the same code, fixture, model name and seed. This output variation is observed provider behavior; a single candidate advantage cannot be treated as a stable incremental utility result.

C and D selected the same probe in five candidate scenarios and six main scenarios. Their normalized hypothesis states were identical in zero of those five candidate comparisons and one of six main comparisons. All C/D hidden candidates were top-ranked or tied in both runs. Representation remains path-sensitive even when final actions agree.

## Capability interpretation and boundary

The bounded hypothesis representation can guide a valid probe and final action on these controlled cases. Persistent D did not demonstrate stable final-action or probe-quality superiority over ordinary full-history E. E used half the calls and substantially fewer characters. Per-event hypothesis maintenance is therefore not justified as a general default by this slice.

Preserve the implementation as a controlled research capability. A later benefit claim requires a new predeclared mechanism/transfer contract and independent evidence; no new external benchmark rows are authorized by this closure. No owner-private examples were placed in GitHub.

The integrated runtime SHA above is the certified code. This documentation-only closure does not change that runtime.
