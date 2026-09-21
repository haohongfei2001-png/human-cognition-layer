# FANToM External Validation v0.2 — Full-Context Paired Pilot Closure

## Decision

**MIXED / INCONCLUSIVE**

This is the predeclared v0.2 interpretation.

## Canonical run

- workflow: `FANToM External Validation v0.2 Full-Context Paired Pilot`
- run: `35609498441`
- launch commit: `fae8f8810f63c459b01f8fae7a97159bb976dae1`
- result: **SUCCESS**
- aggregate artifact: `10644692374`
- aggregate artifact SHA-256:
  `6a6098bf460646f19070e6d8943eb5a0943d18aec972cfba4839e5eea49d82a7`

Source:
- FANToM upstream commit:
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Sample:
- **48 questions**
- **48 distinct conversations**
- full-context input
- **0 conversation overlap with v0.1**
- deterministic frozen selection
- no LLM judge / semantic regrading / manual regrading.

All 6 paid shards and the aggregate completed successfully. All shard and
aggregate privacy gates passed.

## Primary result

Primary information-asymmetry block:
- n = **32**
- control correct = **26 / 32**
- HCL correct = **26 / 32**
- control accuracy = **81.25%**
- HCL accuracy = **81.25%**
- improved = **2**
- worsened = **2**
- both correct = **24**
- both wrong = **4**
- net paired gain = **0**

The positive criterion required primary net paired gain >= +3 and no primary
subblock regression.

The positive gate is therefore **not met**.

The negative gate is also not met because:
- overall primary net is not negative;
- accessible-belief net is not <= -2;
- fact-control F1 delta is positive.

Therefore the frozen interpretation is MIXED.

## Primary belief subblock

Combined inaccessible first-/second-order belief:
- n = **16**
- control = **12 / 16 = 75%**
- HCL = **13 / 16 = 81.25%**
- improved = **1**
- worsened = **0**
- both correct = 12
- both wrong = 3
- net paired gain = **+1**

By stratum:

### Inaccessible first-order belief
- n = 8
- control = 7/8 = 87.5%
- HCL = 7/8 = 87.5%
- improved = 0
- worsened = 0
- net = 0

### Inaccessible second-order belief
- n = 8
- control = 5/8 = 62.5%
- HCL = 6/8 = 75%
- improved = **1**
- worsened = 0
- net = **+1**

The single primary-belief improvement is on a second-order inaccessible-belief
question. HCL mode was EPISTEMIC with medium uncertainty and no revision was
required.

This is a favorable bounded signal, but n=16 and one changed item are far too
small for a general efficacy claim.

## Primary information-state subblock

Answerability + information accessibility:
- n = **16**
- control = **14 / 16 = 87.5%**
- HCL = **13 / 16 = 81.25%**
- improved = **1**
- worsened = **2**
- both correct = 12
- both wrong = 1
- net paired gain = **-1**

This subblock fails the positive requirement that HCL accuracy not be below
control.

### Full-context inaccessible answerability
- n = 8
- control = 6/8 = 75%
- HCL = 6/8 = 75%
- improved = 1
- worsened = 1
- net = 0

One worsened item has:
- control prediction: valid `yes`
- HCL normalized prediction: **null**
- HCL mode: EPISTEMIC
- uncertainty: high
- both revision passes executed.

Because the deterministic yes/no parser could not extract a leading verdict,
this item is at minimum an **output-interface failure**. The artifact does not
persist response text, so it cannot be safely reclassified beyond that. Raw
incorrect status is preserved.

### Full-context inaccessible information accessibility
- n = 8
- control = 8/8 = 100%
- HCL = 7/8 = 87.5%
- improved = 0
- worsened = 1
- net = **-1**

The changed item has:
- control normalized prediction: yes
- HCL normalized prediction: no
- HCL mode: EPISTEMIC
- uncertainty: medium
- no revision.

This is a real categorical disagreement under the frozen scorer. It must remain
a raw HCL regression for this pilot. The consumed benchmark content must not be
used for direct prompt/state tuning.

## Accessible-belief stability control

Combined accessible belief:
- n = **8**
- control = **7 / 8 = 87.5%**
- HCL = **7 / 8 = 87.5%**
- improved = 1
- worsened = 1
- both correct = 6
- both wrong = 0
- net = **0**

By stratum:
- accessible first-order: 4/4 vs 4/4, net 0
- accessible second-order: 3/4 vs 3/4, improved 1 / worsened 1, net 0

No aggregate control regression is established.

## Fact stability control

- n = **8**
- control mean token-F1:
  **0.2128511971**
- HCL mean token-F1:
  **0.2676538557**
- paired mean delta:
  **+0.0548026587**

This is above the predeclared -0.05 regression boundary.

It is a small positive control signal, not a primary efficacy endpoint.

## Categorical changed outcomes

Across the 40 categorical questions:
- improved = 3
- worsened = 3
- net = 0.

Changed items by role:
- primary inaccessible second-order belief: +1 HCL improvement;
- primary answerability: +1 / -1;
- primary information accessibility: -1;
- accessible second-order control: +1 / -1.

The aggregate artifact intentionally contains no conversation/question/gold or
response text.

## Predeclared interpretation

Positive required all:
1. primary net >= +3;
2. no inaccessible-belief accuracy regression;
3. no information-state accuracy regression;
4. accessible-belief net >= -1;
5. fact F1 delta >= -0.05.

Negative if any:
- primary net < 0;
- accessible-belief net <= -2;
- fact F1 delta < -0.05.

Observed:
- primary net = 0;
- belief subblock improves +1 net;
- information-state subblock regresses -1 net;
- accessible-belief net = 0;
- fact F1 delta = +0.0548.

Therefore:

**predeclared interpretation = MIXED / INCONCLUSIVE**

## Cross-round interpretation

FANToM v0.1 short-context:
- primary net = 0
- no categorical changes at all
- largely ceiling/identity limited.

FANToM v0.2 full-context:
- primary net = 0
- more discriminative:
  - belief +1 net
  - information-state -1 net
- controls remain aggregate-stable;
- fact token-F1 is positive.

This is more informative than v0.1 but still does not establish net HCL
categorical efficacy.

The evidence suggests two distinct questions for future work:
1. whether HCL belief modeling produces a repeatable advantage on harder
   second-order belief tasks;
2. whether the answer-loop/output interface can preserve strict task-format
   requirements and information-access judgments without introducing
   regressions.

The second question must not be repaired by tuning against the consumed v0.2
questions.

## Claim boundary

Supported:
- HCL transfers to a harder, full-context FANToM sample disjoint from v0.1;
- no aggregate accessible-belief or fact-control degradation is observed;
- a small favorable belief signal exists;
- a small unfavorable information-state signal also exists.

Not supported:
- net FANToM efficacy improvement;
- official FANToM leaderboard performance;
- full-benchmark performance;
- cross-base transfer;
- interactive Decision Policy efficacy;
- HCL 1.0 efficacy certification.

## Next methodological gate

Do not tune on v0.2.

Before another external benchmark run, the highest-value next step is an
**independent output-interface / information-state audit** using synthetic,
non-FANToM fixtures:

- strict yes/no and A/B format preservation after HCL revisions;
- answerability vs information-access distinctions;
- high-uncertainty answers where HCL must still emit the required categorical
  verdict;
- checker/revision behavior that must not replace a required output format with
  explanatory prose;
- genuine information-state counterexamples unrelated to FANToM content.

Only an abstract independently generated repair, if any, may change HCL.
Any behavior-bearing repair must then repeat the frozen synthetic/state gates
before new external evidence is consumed.
