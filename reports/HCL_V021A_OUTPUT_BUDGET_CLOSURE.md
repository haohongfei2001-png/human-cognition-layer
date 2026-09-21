# HCL Decision Policy v0.2.1a — Output Budget Amendment Closure

## Decision

**VALIDATED / CANONICAL**

Owner-authorized behavior amendment:

```text
HCLDecisionPolicy.max_tokens
4096 -> 8192
```

Behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

No other behavior-bearing HCL change is included.

## Why the amendment was necessary

Consumed ordinal48 provider-attempt diagnosis (run `35588167021`) proved that
the frozen 4096-token Decision Policy limit was repeatedly consumed entirely by
DeepSeek reasoning:

- empty-final-content provider attempts: **30**
- every empty attempt:
  - `finish_reason=length`
  - `completion_tokens=4096`
  - `reasoning_tokens=4096`
  - reasoning content present
  - final content 0 bytes
- transport exceptions: 0

The root cause was therefore output-budget exhaustion, not missing credentials,
provider routing, HCL state semantics, Action Checker behavior, or a simple
single malformed JSON response.

## Amendment-scope and synthetic validation

Canonical gate:
- run `35594584730`
- artifact `10635169895`
- result: **SUCCESS**

The gate proved that, relative to pre-amendment main
`610344ed7a916ca656b1e8dd23b68a091a8a5e6d`, the only behavior-bearing
change is the Decision Policy default output budget.

Unchanged:
- Action Checker;
- HCL state builder;
- answer generator/checker budgets;
- Decision Policy prompt/taxonomy;
- verification-deadlock semantics;
- provider/model/endpoint/key;
- seed/temperature;
- 4-attempt inner empty-content loop;
- 3-attempt outer JSON loop.

Raw synthetic/regression evidence:
- verification-stopping Decision Policy: **12/12**
- Action Checker anti-loop: **5/5**
- negotiation-position: **12/12**
- historical goal-pursuit: **11/12 raw**
- sole goal-pursuit miss remains exactly
  `gp03_irreversible_legal_uncertainty`;
- existing exact bounded adjudication: PASS.

The raw historical result remains 11/12 and is not rewritten.

A first gate run `35594522038` failed before provider-backed synthetic tests
because the dedicated workflow omitted the pinned SOTOPIA dependency required
by an existing runner-structure unit test. The correction only installed the
pinned dependency; no behavior or fixture criterion was weakened.

## SOTOPIA integration smoke

Run:
- `35595222418`
- result: **SUCCESS**
- artifact: `10636505914`
- artifact SHA-256:
  `714a08ec85b0c2c49b9cd5c358767eb775139263abcbf7ec844191f1120e1b5e`

The workflow first proved behavior-bearing files were identical to the v0.2.1a
anchor.

Raw assertions include:
- HCL state present;
- Decision Policy present;
- verification fields present;
- Action Checker PASS;
- forced no-op remains HCL always-on.

## Consumed ordinal48 confirmation

Predeclaration:
`reports/ORDINAL48_V021A_CONFIRMATION_PREDECLARATION.md`

Confirmation run:
- `35595588158`
- launch commit:
  `81615c6ef69c2ae77f3ae0d487785d9143d4530c`
- artifact: `10636821661`
- artifact SHA-256:
  `0f70339a227e35bfc7d6c6ff0d42d1e67813f1776956da0728e460622f26c771`
- result: **SUCCESS**

Predeclared confirmation criteria all passed:
- episode attempts executed: **1**
- final episode outcome: **success**
- exact no-valid-JSON RuntimeError: **false**
- provider-attempt events: **3**
- every Decision Policy provider call requested `max_tokens=8192`.

Provider-level raw metadata:

1. call 1:
   - `finish_reason=stop`
   - final content: **1465 bytes**
   - reasoning: **2499 tokens**
   - total completion: **2859 tokens**

2. call 2:
   - `finish_reason=stop`
   - final content: **1825 bytes**
   - reasoning: **5878 tokens**
   - total completion: **6315 tokens**

3. call 3:
   - `finish_reason=stop`
   - final content: **1760 bytes**
   - reasoning: **6123 tokens**
   - total completion: **6604 tokens**

No provider call:
- hit `finish_reason=length`;
- returned empty final content;
- required the backend's second provider attempt;
- triggered an outer Decision Policy JSON retry;
- raised a transport exception.

The 5878- and 6123-reasoning-token calls are direct diagnostic evidence that
the old 4096 ceiling was insufficient on this consumed setting, while the
authorized 8192 ceiling provided enough headroom for final JSON.

## Claim boundary

This confirmation is **not fresh evidence**.

It establishes only that:
- the diagnosed output-budget failure reproduced under 4096;
- the same consumed setting completed under the narrowly authorized 8192
  amendment;
- the amendment survived independent synthetic regression and SOTOPIA smoke.

It does **not**:
- retroactively complete the original post-repair holdout;
- convert the original 8/10 result into 9/10 or 10/10;
- restore freshness to ordinal48 or combo3;
- establish HCL efficacy;
- authorize a new benchmark holdout.

The original post-repair holdout remains:
**8/10 INCOMPLETE**.

## Canonical runtime

Decision Policy v0.2.1a is now the validated runtime candidate:
- HCL v0.3 state remains frozen;
- HCL remains always-on;
- Decision Policy output budget is 8192;
- all other frozen behavior remains unchanged.

No training or cross-base-model transfer has been started.
