# Decision Policy v0.2.1a — Output Budget Amendment Proposal

Status: **AUTHORIZED / IMPLEMENTED / VALIDATED — HISTORICAL PROPOSAL**

This document freezes the next minimal repair candidate for review. It does not
change runtime behavior and does not authorize paid/provider validation.

## Triggering evidence

Consumed ordinal48 provider-attempt diagnostic:
- run `35588167021`
- artifact `10634471138`
- both bounded episode attempts reproduced the frozen Decision Policy failure;
- every observed empty final content had:
  - `finish_reason=length`
  - `completion_tokens=4096`
  - `reasoning_tokens=4096`
  - non-empty separate reasoning content
  - zero-byte final `content`.

See:
- `reports/ORDINAL48_PROVIDER_ATTEMPT_DIAGNOSTIC_RESULT.md`

## Proposed runtime diff

Exactly one behavior-bearing parameter change:

`hcl/v03/decision_policy.py`

Change:

```python
max_tokens: int = 4096
```

to:

```python
max_tokens: int = 8192
```

No other behavior-bearing code change is proposed.

## What remains unchanged

- HCL v0.3 frozen cognition-state semantics;
- always-on HCL doctrine;
- Decision Policy system prompt and taxonomy;
- verification-deadlock semantics;
- Action Checker;
- model: `deepseek-flash`;
- provider endpoint;
- credential path;
- thinking mode / reasoning effort;
- seed;
- temperature;
- four empty-content provider attempts per backend call;
- three outer Decision Policy JSON attempts;
- parser and normalization;
- SOTOPIA evaluator/provider repair.

## Why 8192

- 4096 is empirically exhausted as reasoning on every reproduced empty response;
- successful responses in the same replay stop naturally below 4096;
- 8192 is the smallest simple doubling that creates final-answer headroom while
  preserving the model's existing thinking behavior;
- disabling thinking or lowering reasoning effort would be a broader semantic
  change;
- adding retries at 4096 would repeat the confirmed failure mechanism;
- removing `max_tokens` entirely would expand the cost/output envelope much
  more aggressively.

8192 is still a hypothesis to validate, not a guarantee.

## Cost boundary

This change raises the per-request output-token ceiling and therefore changes the
maximum billable token envelope.

Existing worst-case Decision Policy failure envelope:
- 4 provider attempts × 3 outer JSON attempts × 4096
- **49,152 output tokens**

Proposed worst-case envelope:
- 4 × 3 × 8192
- **98,304 output tokens**

Actual cost may fall if the larger budget avoids repeated failed requests, but
the maximum per-call spending envelope is still increased.

Under the current engineering authority, that is an owner-controlled cost
boundary. The runtime change must not be committed or executed against the paid
provider until explicitly authorized.

## Required gates after authorization

### Gate A — no-network structural certification

Verify:
1. only Decision Policy requests use 8192;
2. state builder / answer loop / Action Checker retain existing budgets;
3. model/provider/seed/temp/messages are unchanged;
4. inner/outer retry counts remain unchanged;
5. transport exceptions remain identity-preserving.

### Gate B — independent synthetic regression

Run, preserving raw results:
- verification-stopping suite;
- Action Checker anti-loop suite;
- negotiation-position suite;
- historical goal-pursuit suite with existing exact bounded adjudication only.

No fixture may be weakened to accommodate the amendment.

### Gate C — integration smoke

Run the existing SOTOPIA custom-agent smoke with frozen state semantics and
always-on no-op behavior.

### Gate D — consumed ordinal48 diagnostic confirmation

Replay only the already-consumed ordinal48 diagnostic under the same:
- environment/combo;
- seed;
- provider/model;
- bounded episode retry ceiling.

Success here is diagnostic confirmation only, not fresh evidence and not an
efficacy result.

## External validation boundary

Even if all gates pass:
- do not retroactively complete the original 8/10 holdout;
- do not call ordinal48 or the old combo-3 slice fresh;
- do not automatically launch a new holdout;
- first update canonical evidence and decide whether an independent unused
  validation source remains methodologically justified.


## Final disposition

Owner authorization was granted and the proposal was implemented exactly as
specified.

Canonical behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

Validation:
- synthetic/regression gate `35594584730`: SUCCESS;
- SOTOPIA smoke `35595222418`: SUCCESS;
- consumed ordinal48 confirmation `35595588158`: SUCCESS;
- updated infrastructure certification `35596299688`: SUCCESS.

Canonical closure:
- `reports/HCL_V021A_OUTPUT_BUDGET_CLOSURE.md`
- `hcl/v03/FROZEN_DECISION_POLICY_V021A.md`

The original external holdout remains 8/10 incomplete.
