# Decision Policy v0.2.1a — Output Budget Validation

## Scope

Owner-authorized amendment:

`HCLDecisionPolicy.max_tokens: 4096 -> 8192`

No other behavior-bearing change is permitted by this round.

Freeze contract:
- `hcl/v03/FROZEN_DECISION_POLICY_V021A.md`

## Canonical validation run

- run: `35594584730`
- launch commit: `40ff6d1169359858ebc4be308c9dffd24311a53e`
- artifact: `10635169895`
- artifact SHA-256:
  `efc4580e37d249476c258be5d39a1c7ddae375416fd2e429fd6f8e67a0d0f6f0`
- result: **SUCCESS**

An earlier first attempt `35594522038` failed before provider-backed
validation because the structural test job had not installed pinned SOTOPIA.
The failure was `ModuleNotFoundError: sotopia`; scope/static checks had
already passed. The workflow dependency was corrected and the gate rerun
without changing HCL behavior.

## Structural certification

Passed:
- exact behavior diff from pre-amendment main contains only
  `hcl/v03/decision_policy.py`;
- that file differs only by the default Decision Policy output budget:
  `4096 -> 8192`;
- static compile;
- no-network diagnostic/budget tests.

No-network scope assertions:
- Decision Policy default: **8192**
- Action Checker: **4096**
- HCL state builder: **8192**
- answer generation: **4096**
- answer checker: **4096**

The existing outer Decision Policy three-attempt loop and inner backend
four-empty-content loop are unchanged.

## Independent synthetic / regression results

### Verification-stopping Decision Policy

- raw: **12 / 12 PASS**
- no fixture weakened.

### Action Checker anti-loop

- raw: **5 / 5 PASS**

### Negotiation-position regression

- raw: **12 / 12 PASS**

### Historical goal-pursuit regression

Raw:
- **11 / 12**
- sole miss: `gp03_irreversible_legal_uncertainty`
- actual strategy: `ALTERNATIVE_PATH`

Exact bounded adjudication:
- raw score preserved as 11/12;
- exact known case only;
- safe BLOCKED/hard-constraint/fallback structure retained;
- gate: **PASS**.

No new raw regression is introduced by the 8192 budget amendment.

## Decision

**V021A_OUTPUT_BUDGET_SYNTHETIC_GATE: PASS**

This establishes that the authorized output-budget amendment is structurally
bounded and does not regress the existing independent synthetic behavior.

It does not yet establish SOTOPIA integration or resolve consumed ordinal48.

Next:
1. SOTOPIA custom-agent smoke on v0.2.1a;
2. if smoke passes, consumed ordinal48 diagnostic confirmation;
3. preserve original post-repair holdout as 8/10 incomplete.
