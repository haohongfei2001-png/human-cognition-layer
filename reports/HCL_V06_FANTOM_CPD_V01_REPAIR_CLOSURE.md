# HCL v0.6 FANToM C/P/D Development Utility Repair Closure

Status: **VALID DEVELOPMENT SIGNAL / DIRECTIONAL GATE PASS / NOT FRESH EFFICACY**

## Attempt history

Attempt 1:
- run `36128133383`;
- artifact `10860698515`;
- artifact digest `sha256:0a14b744a738eaeeb00c1da16536c8fb13b35bcf7776e26e3f885a351a8b0efb`;
- invalid because all 24 C/P/D text-answer calls returned empty final content;
- preserved as consumed harness-failure evidence.

Transport repair:
- main `211473038c1814831cf0ecc173bee600c7d1cb62`;
- DeepSeek non-thinking provider extras applied to text and JSON requests;
- empty final answers fail closed;
- v0.4, v0.5 and C/P/D provider-free main gates all passed.

Repair execution A2:
- run `36137611816`;
- trigger/main `da513e38069e8456dba9a030b079504f0ae48332`;
- artifact `10865463427`;
- artifact digest `sha256:577272f0d6fe994c70a3c334898a7627f53b14a86b6937f4ca5db7aa0b6c87e6`;
- same eight already-consumed development conversations;
- failures: 0;
- provider calls: 32;
- conservative character-as-token peak-price upper bound for A2: USD 0.281624;
- cumulative attempt-1 + A2 conservative planning upper bound: USD 0.572066.

The A2 repair is not fresh evidence. It repairs the invalid transport run on the
same consumed development selection.

## Results

| Arm | Correct | Accuracy |
|---|---:|---:|
| C — direct | 4 / 8 | 50% |
| P — thin perspective scaffold | 4 / 8 | 50% |
| D — HCL v0.6 perspective runtime | 6 / 8 | 75% |

Paired:
- D vs P: D-only correct **2**, P-only correct **0**, both correct 4, both wrong 2;
- D vs C: D-only correct **2**, C-only correct **0**, both correct 4, both wrong 2;
- P vs C: no discordant cases; the thin scaffold produced the same 4/8 correctness pattern as direct control.

Pre-registered directional gate:
- required >=2 P-wrong / D-correct conversations: **PASS (2)**;
- required <=1 P-correct / D-wrong conversation: **PASS (0)**.

Decision: **DEVELOPMENT UTILITY SIGNAL POSITIVE.**

This is not a statistical efficacy claim. n=8, one model family, one
development selection.

## Manual semantic audit

The two D-only improvements were audited against the upstream FANToM
conversation structure without changing scores.

### Conversation 240 — D-only correct

Failure class: **bounded second-order information perspective**.

The queried inner character entered after the relevant detailed information had
already been exchanged. The outer character had evidence of that information
boundary. D selected the inaccessible-belief answer while C and P selected the
omniscient alternative.

Audit decision:
- improvement matches the intended v0.6 second-order perspective mechanism;
- output format was valid in all arms;
- this is a credible perspective-boundary save, not a format artifact.

### Conversation 220 — D-only correct

Failure class: **late-join answerability boundary**.

The target entered after the two specific experiences needed for the precise
answer had been discussed. D answered that the target could not give the
precise answer; C and P answered that the target could.

Audit decision:
- improvement matches the intended first-order access boundary;
- this is a credible perspective-boundary save.

## Remaining failures

### Conversation 197 — all C/P/D wrong

Abstract failure hypothesis:
**implicit first-appearance / late-entry evidence boundary**.

The later participant's first turn is a greeting/entry into an already-running
conversation rather than an explicit phrase such as "may I join". The current
LLM access adapter can know all future participant names and may grant
retroactive access before evidence of presence.

The A2 artifact preserved only an access-state hash, not the normalized
turn/listener map, so the exact causal path for this run cannot be proven
post-hoc. Do not claim this root cause as established.

General repair:
- add a deterministic evidence floor after LLM access extraction;
- no participant may receive turns earlier than their first evidence of
  presence;
- a direct vocative may establish presence before the participant's first
  speaking turn;
- validate on unrelated synthetic conversations, not by rerunning conversation
  197 for a new score.

### Conversation 36 — all C/P/D wrong

Established abstract failure:
**partial related information != precise complete knowledge**.

The later participant receives a broad topical summary after joining, but not
all material details contained in the precise information bundle being queried.
D still answered as if topical/partial access established precise knowledge.

General repair:
- encode a cognition rule that related topic overlap or a partial summary does
  not establish knowledge of a precise compound fact;
- require support for every material detail before treating precise information
  as known;
- validate the rule on independent synthetic fixtures.

## Capability decision

Keep the minimal v0.6 perspective mechanism.

Reason:
- D produced two audited perspective saves beyond both direct reasoning and a
  thin perspective scaffold;
- D introduced zero paired regressions on this development slice;
- the remaining errors expose generalizable semantic gaps rather than evidence
  that the whole perspective mechanism is unnecessary.

Do **not** use this development result to claim:
- general Theory of Mind superiority;
- broad psychology/literature/moral/philosophical gains;
- cross-model transfer;
- external efficacy or leaderboard improvement.

## v0.6.1 repair

Authorized development now:
1. deterministic participant-presence evidence floor;
2. explicit precise-knowledge vs partial-summary semantic boundary;
3. auditable future access-map artifacts without benchmark text;
4. independent provider-free synthetic correctness tests.

Not authorized by this result:
- rerunning the same 8 conversations as fresh evidence after v0.6.1 changes;
- LongMemEval paid execution;
- broad ontology expansion.

After v0.6.1 correctness certification, the next external efficacy evidence must
use a new, disjoint fresh selection and should include a competent generic
structured-state G.

**Current gate: HCL_V06_V061_PERSPECTIVE_BOUNDARY_REPAIR_PROVIDER_FREE_CERTIFICATION**
