# HCL State-JSON Reliability Repair v0.1

Status: **PREDECLARED / REPAIR AUTHORIZED BY INDEPENDENT DEFECT AUDIT**

## Trigger

Independent state-generation reliability audit v0.1 established a repeatable
state JSON reliability defect under the frozen DeepSeek-backed HCL v0.3 state
builder:

- 22 / 24 synthetic cases reached before workflow timeout;
- 18 distinct cases exhausted all 3 HCL-level state-generation attempts;
- 4 cases succeeded;
- 0 backend/transport/other exceptions were observed.

See:
- `reports/HCL_STATE_GENERATION_RELIABILITY_AUDIT_V01.md`
- `reports/HCL_STATE_GENERATION_RELIABILITY_AUDIT_V01_CLOSURE.md`

## Frozen cognition semantics

This repair must not change:
- `hcl/v03/FROZEN_STATE_SEMANTICS.md`;
- `hcl/v03/state_schema.json`;
- the HCL v0.3 mode taxonomy;
- epistemic / belief / uncertainty semantics;
- `STATE_SYSTEM` meaning or required state fields;
- the always-on HCL doctrine.

Consumed Hi-ToM / FANToM / SOTOPIA content is forbidden as repair input.

## Minimal repair

### 1. Provider-native JSON mode for state generation

`OpenAICompatibleBackend` gains a state-specific structured completion method:

`complete_json(...)`

It uses the same:
- model;
- provider endpoint;
- API key;
- seed;
- temperature;
- max token budget;
- existing non-empty response retry behavior;

and adds only:

`response_format={"type": "json_object"}`

for state-generation calls.

DeepSeek's official Chat Completions API documents JSON Output via this
`response_format` and requires the prompt itself to request JSON. The frozen
HCL state prompt already explicitly requests JSON.

### 2. HCL state builder capability selection

`HCLAnswerLoop.build_state()`:
- prefers `backend.complete_json(...)` when the backend exposes it;
- otherwise falls back to the existing `backend.complete(...)` contract.

This keeps test/fake/alternate backends compatible.

### 3. Retry invariant

Do not increase the HCL-level retry budget.

The existing maximum remains:
- 3 HCL-level state-generation attempts.

The existing backend non-empty-response retry behavior remains unchanged.

### 4. No scope creep

This repair does not change:
- user-facing draft generation;
- answer checker generation;
- revision generation;
- Decision Policy;
- Action Checker;
- external benchmark scoring;
- any consumed sample.

## Zero-provider unit gates

Before provider-backed validation, tests must prove:

1. `complete_json()` sends exactly
   `response_format={"type":"json_object"}`.
2. ordinary `complete()` does not add JSON mode.
3. `build_state()` prefers `complete_json()` when available.
4. `build_state()` still supports a legacy backend exposing only
   `complete()`.
5. JSON-mode empty-response retry behavior remains bounded and returns the first
   non-empty response.
6. HCL-level state retry count remains at most 3.
7. state schema and `STATE_SYSTEM` are not modified by this repair.

## Independent repair validation

Use the exact same 24 repository-owned synthetic recipes from:

`eval/answer_loop/state_generation_reliability_v01.json`

No case wording, stratum, or defect criterion may change for the repair result.

Execution may be **sharded only for runtime reliability**:
- 6 shards × 4 cases;
- each shard receives one frozen stratum;
- maximum parallelism up to 3;
- aggregate only after all 24 cases terminate.

The original serial audit timeout is preserved as historical evidence and is not
rewritten.

## Repair pass gate

The repair passes state-generation reliability only if all are true:

- 24 / 24 synthetic cases complete successfully;
- `state_json_exhaustion_count == 0`;
- `backend_or_other_exception_count == 0`;
- all content-free artifact privacy checks pass.

Any failure means the repair gate does not pass.

## Regression gates after repair pass

A provider-backed reliability pass alone is insufficient.

Before new external evidence may be consumed, the repaired behavior must also
pass:

1. existing HCL state-fidelity synthetic regressions;
2. existing answer-loop/checker synthetic regressions;
3. prior independent info-state/output-interface synthetic audit;
4. zero-provider repository unit tests relevant to HCL v0.3.

No fresh external benchmark may start before those regression gates close.

## Claim boundary

A passing repair establishes only that the independently reproduced state JSON
execution defect has been repaired on the frozen synthetic reliability suite.

It does not establish:
- Hi-ToM efficacy;
- SOTOPIA efficacy;
- cross-base transfer;
- HCL 1.0 certification.
