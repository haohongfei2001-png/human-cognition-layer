# HCL v0.6 Fresh FANToM C/P/G/D Pilot v0.1

Status: **SELECTION AND PROVIDER-FREE PACKAGE FROZEN / PROVIDER NOT RUN**

## Research question

Does the frozen v0.6.1 specialized perspective layer add value beyond the same
base model answering directly (C), a thin perspective instruction (P), and a
competent generic structured chronology (G)? This is a 32-conversation fresh
pilot, not a general human-cognition or leaderboard claim.

## Frozen source and selection

- FANToM source repository: `skywalker023/fantom` at
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`.
- Archive SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`.
- v0.6.1 mechanism main before selection:
  `47f26c9fa106ed4b8f7e0253c2fedbf518fc312a`.
- Salt: `HCL-V06-FANTOM-CPGD-FRESH-V01-20260925`.
- Immutable selection:
  `eval/v06/fantom_cpgd_fresh_selection_v01.json`.
- Selection file SHA-256:
  `9d19063aa96793dfd9cfc8c5707825a75b905f34501786f147f64480f5d7f704`.
- Exclusions: 80 historical v0.1/v0.2 conversations, plus development
  `119,197,240,7,220,189,208,36`; the manifest carries the complete IDs.
- 32 unique full conversations, one deterministically ranked question each;
  8 each in inaccessible first-order belief, inaccessible second-order belief,
  inaccessible answerability, and inaccessible information access.
- Committed manifest contains IDs and hashes, never question or gold text.

The selector uses dataset labels only to form the four strata and choose one
question. It does not tune or change the mechanism. The exact manifest is
recomputed from the pinned archive in preflight and before execution.

## Arms and firewall

All arms use DeepSeek API `deepseek-flash`, temperature 0, seed 42, identical
64-token answer output budget, and disabled thinking. Actual response model
identities are recorded and required to agree across arms. The provider SDK
has retries disabled; every attempted request is metered.

- **C:** full source conversation and task, direct answer.
- **P:** same conversation/task with one thin perspective instruction.
- **G:** question-blind structured timeline with every utterance, actor,
  mentioned participant, time, source, ordinary hearing access, provenance and
  uncertainty. It contains no HCL belief or perspective projection. It cannot
  silently drop events.
- **D:** frozen v0.6.1 first-order character views and bounded pairwise
  second-order access state, constructed from the same access extraction as G.

The shared access adapter receives only the complete source conversation and
speaker turns. G and D states are fully constructed **before** the selected
task and options are released to any answer arm. No `missed_info`,
`joining_speaker`, gold, option ordering, family or prior outcome enters state
construction. G uses the same access map as D, which makes it a strong generic
structure control rather than a deliberately weak baseline.

## Operational caps and authorization

Frozen maximums: C/P/G/D each 32 answer requests; access adapter 64 requests
(one extraction plus at most one repair per conversation); **192 requests**
overall. Component input/output character caps are enforced in the runner.
The combined maximum is 8.56 million input characters and 760,000 output
characters. At the frozen conservative character-as-token peak-price planning
rates, the character-cap maximum is USD **3.48**. The runner also shares a
USD **3.50 operational rated-cost ledger** across every arm. Before each
request, it reserves a conservative input-token bound from UTF-8 bytes plus
1,024 framing tokens and the full output-token cap. If the reservation would
exceed USD 3.50, it makes no request. After a response, it charges the
provider-reported cache-hit, cache-miss and output tokens at the peak rates
from [DeepSeek's published pricing](https://api-docs.deepseek.com/quick_start/pricing/).
Missing usage or transport uncertainty charges the full reservation and
stops the consumed run. This is a provider-rated cost guard, not an invoice
guarantee if the provider changes prices or bills outside documented usage.

Existing owner authorization in the prior v0.6 C/P/D protocol covered a
different, eight-conversation development run up to USD 1.00. It does **not**
authorize this larger fresh pilot. The one-shot workflow is staged but cannot
make a provider call until the owner approves at least the USD 3.50 planning
cap and the matching repository authorization variable is set. No new account
or credential may be purchased; LongMemEval remains untouched.

## Execution and interpretation

The future paid run requires an exact-parent, first-attempt, trigger-file-only
main commit and passes provider-free regressions before any request. A partial
run remains consumed evidence and is not relaunched as fresh. Result artifacts
record the selected IDs/hashes, answer strings/predictions/correctness, access
maps, state hashes, repairs, request counts, input/output characters and wall
time. Raw benchmark conversations/questions/gold are not committed.

Analysis must report paired D-vs-C, D-vs-P and D-vs-G discordant counts. An
exact McNemar analysis may accompany them; a percentage alone is insufficient.
The pilot is small and one-model. After the result, freeze one of RETAIN,
SIMPLIFY or REVISE/DEMOTE, then leave FANToM rather than tuning on these fresh
cases. In parallel, benchmark-independent v0.7 provider-free development can
proceed without consuming this pilot.
