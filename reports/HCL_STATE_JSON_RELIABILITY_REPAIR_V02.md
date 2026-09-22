# HCL State-JSON Reliability Repair v0.2 — Non-Thinking State Generation

Status: **PREDECLARED / IMPLEMENTATION AUTHORIZED AFTER OUTPUT-BUDGET DIAGNOSIS**

## Trigger

Structured-output failure diagnostic v0.1 established a dominant output-budget
exhaustion mechanism under the failed v0.1 repair candidate:

- 191 bottom-level provider calls;
- 189 terminated with `finish_reason="length"`;
- all 189 consumed exactly 8192 completion tokens;
- 149 returned empty content;
- 40 returned non-empty but truncated/non-parseable content;
- only 2 terminated with `stop`, and both were valid JSON objects.

The current production state-generation request uses `deepseek-flash` without
an explicit thinking-mode control.

Current DeepSeek API documentation states:
- thinking mode is enabled by default;
- Chat Completions supports explicit non-thinking mode using
  `thinking.type="disabled"` or `reasoning_effort="none"`;
- completion usage exposes reasoning tokens as part of completion usage;
- JSON Output should use a reasonable max_tokens budget to avoid truncation;
- `deepseek-flash` supports both thinking and non-thinking modes.

Official references:
- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/quick_start/pricing/

## Repair hypothesis

The 8192-token ceiling is being consumed primarily by the provider's default
thinking-mode generation before a complete state JSON is produced.

Therefore the minimal causal repair is:

**disable thinking for HCL state JSON generation only.**

This is deliberately preferred over increasing max_tokens because it changes
one diagnosed transport/generation variable while keeping the existing output
budget fixed.

## Frozen behavior

This repair must not change:

- `hcl/v03/FROZEN_STATE_SEMANTICS.md`;
- `hcl/v03/state_schema.json`;
- `STATE_SYSTEM`;
- state field names or semantic meaning;
- the state `max_tokens=8192` default;
- the HCL-level retry budget of 3;
- the backend non-empty-response retry budget of 4;
- model `deepseek-flash`;
- endpoint;
- seed;
- JSON response format;
- draft/check/revision request behavior;
- always-on HCL doctrine.

Consumed Hi-ToM / FANToM / SOTOPIA content remains forbidden.

## Minimal implementation

Only `OpenAICompatibleBackend.complete_json()` changes.

For JSON state generation it must send:

`extra_body={"thinking": {"type": "disabled"}}`

while preserving:

`response_format={"type": "json_object"}`

Ordinary `complete()` must not automatically disable thinking in this round.
That keeps the repair isolated to state generation.

No prompt shortening, schema compression, parser broadening, token-budget
increase, retry increase, model switch, or provider switch is permitted in v0.2.

## Why not increase max_tokens first

DeepSeek currently documents a much larger possible maximum output budget, but
raising the budget would not establish whether default thinking is the actual
cause of the diagnosed 8192-token exhaustion.

v0.2 therefore keeps 8192 fixed and disables thinking. A later bounded budget
change is allowed only if v0.2 fails and evidence still supports it.

## Zero-provider gates

Tests must prove before provider calls:

1. `complete_json()` sends
   `response_format={"type":"json_object"}`.
2. `complete_json()` sends
   `extra_body={"thinking":{"type":"disabled"}}`.
3. ordinary `complete()` sends neither JSON mode nor the state-only thinking
   override.
4. state max_tokens remains 8192 in `HCLAnswerLoop`.
5. HCL-level state retry budget remains exactly 3.
6. backend empty-response retry remains exactly 4.
7. state schema, frozen semantics, and STATE_SYSTEM are unchanged.

## Independent v0.2 reliability validation

Use exactly the same 24 frozen repository-owned synthetic cases from:

`eval/answer_loop/state_generation_reliability_v01.json`

Execution:
- 6 shards x 4 cases;
- maximum parallelism 3;
- no fixture wording or ordering changes;
- no external benchmark content.

Pass gate:

- 24 / 24 state builds succeed;
- 0 `state_json_exhaustion`;
- 0 backend/other exceptions;
- all state calls use JSON mode;
- zero-provider tests prove thinking is disabled on the state path.

Any failed case means v0.2 reliability does not pass.

## Post-reliability regressions

If and only if the 24/24 reliability gate passes, run the existing regression
families before any new external evidence:

1. HCL v0.3 state-fidelity synthetic regression;
2. answer-loop/checker synthetic regression;
3. prior independent information-state/output-interface synthetic audit;
4. relevant repository zero-provider HCL v0.3 tests.

A semantic regression blocks closure even if JSON reliability is 24/24.

## Claim boundary

A passing v0.2 may establish only that explicitly disabling provider thinking
repairs the diagnosed state-generation execution failure on the frozen
independent synthetic reliability suite, subject to the regression gates.

It does not establish external benchmark efficacy, cross-base transfer, or HCL
1.0 certification.
