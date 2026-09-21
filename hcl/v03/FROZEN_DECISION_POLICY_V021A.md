# Frozen Decision Policy v0.2.1a — Output Budget Amendment

Status: **VALIDATED / CANONICAL RUNTIME**

Owner authorization was given after the ordinal48 provider-attempt diagnosis
confirmed reasoning-output-budget exhaustion at the explicit 4096-token ceiling.

## Behavior anchor

Authorized behavior-bearing amendment commit:

`ce36d7e6f911910f97437c23455dee33e0e7bc82`

Relative to pre-amendment canonical main
`610344ed7a916ca656b1e8dd23b68a091a8a5e6d`, the only authorized
behavior-bearing change is:

`hcl/v03/decision_policy.py`

```diff
- max_tokens: int = 4096
+ max_tokens: int = 8192
```

No other Decision Policy semantics are amended.

## Unchanged behavior

Remain unchanged:

- HCL v0.3 frozen cognition-state semantics;
- HCL always-on doctrine;
- Decision Policy system prompt;
- verification stopping / observability semantics;
- strategy taxonomy;
- Action Checker;
- HCL state builder budget;
- answer-generation/checker budgets;
- model/provider/endpoint/key;
- DeepSeek thinking mode;
- seed;
- temperature;
- inner four empty-content transport attempts;
- outer three Decision Policy JSON attempts;
- parser and normalization;
- SOTOPIA evaluator same-provider repair.

## Cost authorization boundary

The owner explicitly authorized this 4096 -> 8192 Decision Policy output-budget
increase.

The authorization is limited to this bounded amendment. It does not authorize:

- removing the max-token cap;
- increasing it beyond 8192;
- adding retries;
- changing provider/model;
- starting a new holdout;
- training or cross-base transfer.

## Validation gates

Before the amendment can replace the prior frozen runtime:

1. no-network structural certification;
2. independent verification-stopping Decision Policy suite;
3. Action Checker anti-loop regression;
4. negotiation-position regression;
5. historical goal-pursuit raw regression with only the existing exact bounded
   taxonomy adjudication;
6. SOTOPIA custom-agent integration smoke;
7. consumed ordinal48 diagnostic confirmation.

The original post-repair holdout remains 8/10 incomplete regardless of the
diagnostic confirmation result.


## Validation closure

Canonical evidence:
- synthetic/regression gate: run `35594584730` — SUCCESS
  - verification stopping: 12/12
  - Action Checker anti-loop: 5/5
  - negotiation position: 12/12
  - goal pursuit: 11/12 raw, same historical gp03 boundary only
- SOTOPIA integration smoke: run `35595222418` — SUCCESS
- consumed ordinal48 confirmation: run `35595588158` — SUCCESS
  - one episode attempt;
  - no invalid-JSON RuntimeError;
  - three Decision Policy provider calls;
  - all used max_tokens=8192;
  - reasoning token counts 2499, 5878 and 6123;
  - all finished with `stop` and non-empty final content.

See:
- `reports/HCL_V021A_OUTPUT_BUDGET_CLOSURE.md`

The original external holdout remains 8/10 incomplete and is not retroactively
reclassified.
