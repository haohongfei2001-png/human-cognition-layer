# HCL v0.4 Open-World Hypothesis v0.1 — Controlled Diagnostic Closure

Verdict: **INTERNAL DIAGNOSTIC COMPLETE / NO INCREMENTAL UTILITY / NOT PROMOTED**

## Frozen boundary and exact evidence

- Experimental PR #5 froze the independent contract and six synthetic scenarios before provider use. Fixture SHA-256: `ad8d8e96ab6e3d251bda416a10e9f6eac028d87d5376b1c8eea0441ea3bcbe41`.
- The existing `deepseek-flash` model was used once on experimental exact head `7b190fb1a029b70292e4944b45b2b06919190f8e`. [Workflow 35880082830](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/35880082830) passed fixture-hash, deterministic runner/state/policy tests, then the frozen C/D/E comparison. Its artifact retains per-case rows and raw synthetic outputs for audit.
- No external benchmark row, private research example, new provider, cross-model transfer, public release, or runtime integration was used.

| Arm | Final action | High-information probe | Hidden candidate top/tied | Calls | Input characters | Repairs |
|---|---:|---:|---:|---:|---:|---:|
| C — full-history reconstruction | 6/6 | 6/6 | 6/6 | 25 | 92,096 | 1 |
| D — persistent hypotheses | 6/6 | 6/6 | 6/6 | 26 | 98,041 | 2 |
| E — direct full-history reasoning | 6/6 | 6/6 | not applicable | 12 | 27,143 | 0 |

## Semantic audit and limits

All 27 structured candidate outputs retained `OTHER_UNKNOWN`; their cited event IDs belonged to the scenario's raw initial events or its single probe response. The six probes and final action rationales were reviewed against their visible event histories. No output explicitly claimed that Lina received the lift report, Mira received the missing-file discovery, Theo saw the bus notice, or Ravi received the corrected loan policy before the corresponding probe.

There is an early certainty problem in `equipment_loan`: both C and D marked `OTHER_UNKNOWN` **SUPPORTED** using the office's policy correction before Ravi was asked. The correction established a real authorization requirement, but the visible record did not yet establish that lack of approval caused Ravi's non-confirmation; Ravi had not received the correction. This exceeds the evidence for the target question. Under the frozen contract's grounded-state rule, **C and D fail the semantic gate on this case despite 6/6 action scores**. The later response supports the action to obtain approval. The initial overstatement is preserved, not repaired or rescored.

The controlled hidden state is only a synthetic scoring device. Six scenarios do not establish human-state truth or transfer. D had no probe or action advantage over E, used more than twice the calls and input, and incurred two repairs. The existing simpler path remains preferred for this task class. The experimental PR is retained unmerged for audit; no runtime HCL behavior is promoted.

Another capability question requires a separately frozen independent contract. Do not tune these six cases and rerun them as fresh evidence.
