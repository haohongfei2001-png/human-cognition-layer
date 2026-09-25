# HCL v0.6 FANToM C/P/D Post-hoc Case Audit

Status: **DEVELOPMENT DIAGNOSIS ONLY / v0.6.1 ALREADY FROZEN**

Evidence: A2 run `36137611816`, artifact `10865463427`, ZIP digest
`sha256:577272f0d6fe994c70a3c334898a7627f53b14a86b6937f4ca5db7aa0b6c87e6`.
The pinned FANToM archive digest is
`sha256:1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`.
No provider call was made for this audit. Attempt 1 (`36128133383`) remains
invalid transport evidence, not a 0/8 capability result.

## All eight frozen development cases

| Conversation / set | Stratum | C | P | D | Gold | Interpretation |
|---|---|---|---|---|---|---|
| 119 / 119-0-2 | first-order belief | A | A | A | A | all correct |
| 197 / 197-1-1 | first-order belief | B | B | B | A | all wrong |
| 240 / 240-0-0 | second-order belief | A | A | B | B | D-only correct |
| 7 / 7-0-0 | second-order belief | B | B | B | B | all correct |
| 220 / 220-0-0 | answerability | yes | yes | no | no | D-only correct |
| 189 / 189-1-0 | answerability | no | no | no | no | all correct |
| 208 / 208-1-2 | information access | no | no | no | no | all correct |
| 36 / 36-0-2 | information access | yes | yes | yes | no | all wrong |

Result: C=4/8, P=4/8, D=6/8; D-only=2, D regressions=0.
All eight conversations are permanently development-consumed. A2 is a repair
run on those same conversations and cannot become fresh efficacy evidence.

## Four focal cases

### 240 — D-only second-order save

The inner character first appears after two other speakers exchanged detailed
personal experiences. The outer character participated in that earlier exchange
and can establish the late entrant's access boundary. D selected the
inaccessible-belief option; C and P selected the omniscient alternative. All
arms produced parseable `[A]`/`[B]` outputs, so this is not parser or format
luck. The task option orientation was frozen before A2. The source structure and
answer pattern support a **credible bounded second-order perspective save**.
Because A2 retained only a hash of D's access state, this cannot prove exactly
which internal access edge caused the answer.

### 220 — D-only answerability save

The target joined after two specific experiences required for the precise
answer had been discussed. Later dialogue gave only a broad topic summary.
D answered `no`; C and P answered `yes`. All three binary outputs were valid.
The result is consistent with D's separated character view and late-join
boundary, rather than option ordering or a parser artifact. As in 240, the
archived access-state hash does not expose the exact path through D state.

### 197 — unresolved all-arm miss

The later participant entered a conversation already discussing siblings.
The person was not introduced with an explicit join phrase, creating a generic
first-presence hazard for an access adapter that sees the complete speaker
roster. All arms chose the same wrong option. The A2 artifact did **not**
preserve a turn/listener map, so an adapter error cannot be distinguished from
downstream reading or answer selection. The causal claim remains a
**hypothesis**, not a proven A2 root cause. v0.6.1's deterministic first-presence
floor addresses this benchmark-independent failure class and was checked on
unrelated provider-free conversations. The consumed case was not rerun.

### 36 — partial-summary all-arm miss

The target joined after a detailed set of fitness experiences. A subsequent
summary covered some related activities, while the selected information bundle
required more precise details. All arms answered `yes` despite gold `no`.
This identifies a general semantic hazard: topic overlap or a partial summary
cannot establish knowledge of a complete compound fact. The saved A2 artifact
does not allow a definitive split between D access serialization and D answer
readout. v0.6.1 states the precise-support rule explicitly and checks it on
independent fixtures; it does not claim a corrected FANToM score.

## Classification and decision

- 240, 220: credible perspective/access saves; output format and option
  orientation do not explain the difference. Exact internal causality remains
  limited by the A2 artifact's hashed access state.
- 197: plausible general first-presence/access defect; exact A2 cause unresolved.
- 36: general precise-knowledge versus partial-summary defect; whether it arose
  in access state or answer readout is unresolved.
- No case supports a conversation-ID rule, benchmark-family rule, gold-derived
  runtime input, or tuning the consumed eight toward 8/8.

The benchmark `missed_info`, `joining_speaker` and gold fields were used only
for this post-hoc diagnosis. They remain forbidden inputs to future G/D state
construction. v0.6.1 was already implemented and certified on main
`0bf56af7baf305ca3bebb9035c4a989794a50eb8`; this audit does not reopen
the mechanism. LongMemEval remains untouched.
