# HCL v0.6 FANToM C/P/D v0.1 — Attempt 1 Invalid Harness Closure

Status: **INVALID / DEVELOPMENT EVIDENCE CONSUMED / REPAIR ON SAME SELECTION ALLOWED / NOT AN HCL SCORE**

## Exact run

- workflow: `HCL v0.6 FANToM C/P/D v0.1 Once`
- run: `36128133383`
- trigger/main: `c7788f22378bbf5c8f2f74fea5cf02910ffd298f`
- artifact: `10860698515`
- artifact digest:
  `sha256:0a14b744a738eaeeb00c1da16536c8fb13b35bcf7776e26e3f885a351a8b0efb`
- completed conversations: 8/8
- failures recorded by runner: 0
- provider calls: 32

The workflow itself completed successfully, but its benchmark result is invalid.

## Observed failure

All 24 answer calls returned an empty final `content` string:
- C: 8/8 empty;
- P: 8/8 empty;
- D answer: 8/8 empty.

Therefore:
- every parsed prediction was null;
- C/P/D were all reported as 0/8;
- this 0/8 result is **not a model capability result** and **not an HCL result**.

The D conversation-access adapter used JSON mode and did return non-empty data:
- 8/8 adapter calls completed;
- adapter repair count: 0 on all eight conversations;
- access-state hashes were produced.

This isolates the failure to the answer transport path rather than the
conversation-selection or access-adapter path.

## Root cause

Current official DeepSeek API behavior for `deepseek-flash` enables thinking
mode by default. Non-thinking mode requires:

```json
{"thinking": {"type": "disabled"}}
```

in the OpenAI Chat Completions `extra_body`.

The repository's `deepseek_flash` provider profile already contained this
extra body, but `OpenAICompatibleBackend` applied provider-specific
`json_extra_body` only when `json_mode=True`.

Consequently:
- D adapter JSON calls received the non-thinking configuration and worked;
- C/P/D answer calls used `complete(...)`, did not receive the DeepSeek
  non-thinking extra body, and ran with default thinking enabled;
- the bounded `max_tokens=64` answer budget was consumed without producing a
  final `content` string.

This is a transport/harness defect.

## Consumption / freshness boundary

Provider execution began on all eight frozen FANToM development conversations.

Therefore all eight remain **consumed development evidence**.

A repair run may use the same eight conversations only because:
- it is explicitly a repair of a transport-invalid development run;
- it will not be called fresh evidence;
- it will not be used as sealed efficacy evidence;
- the original invalid artifact remains preserved.

The repair must not select replacement conversations in response to outcomes.

## Repair

Minimal repair:
1. apply the frozen provider-specific extra body to both text and JSON Chat
   Completions requests;
2. add provider-free request-shape coverage proving DeepSeek text requests carry
   `{"thinking":{"type":"disabled"}}`;
3. make the C/P/D runner fail closed when a final answer is empty;
4. run provider-free CI;
5. use a new exact-parent, first-attempt-only repair trigger;
6. rerun the same frozen selection.

Repair token:
`HCL_V06_FANTOM_CPD_V01_REPAIR_20260925_A2`.

The original planning envelope remains sufficient: attempt 1 recorded a
conservative character-as-token peak upper bound of USD 0.290442; one bounded
repair execution of comparable size keeps the cumulative conservative planning
bound below USD 1.00.

## LongMemEval

Unaffected:
- no LongMemEval trigger;
- sealed 32 rows remain provider-unconsumed.

**Current gate: HCL_V06_FANTOM_CPD_V01_TRANSPORT_REPAIR_PROVIDER_FREE_CERTIFICATION**
