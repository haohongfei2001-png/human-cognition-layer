# HCL Decision Policy v0.2.1a — Output Budget Validation Gate

## Authorized amendment

Owner-authorized sole behavior change:

- Decision Policy `max_tokens: 4096 -> 8192`
- behavior anchor:
  `ce36d7e6f911910f97437c23455dee33e0e7bc82`

No other behavior-bearing HCL file changed.

## Canonical validation run

- run: `35594584730`
- launch commit: `40ff6d1169359858ebc4be308c9dffd24311a53e`
- artifact: `10635169895`
- artifact SHA-256:
  `efc4580e37d249476c258be5d39a1c7ddae375416fd2e429fd6f8e67a0d0f6f0`
- result: **SUCCESS**

A prior run `35594522038` failed before provider-backed synthetic tests because
the gate had not installed the pinned SOTOPIA package needed by an existing
runner-structure unit test. The budget/scope tests themselves passed. The gate
was corrected only by installing the pinned dependency; no fixture or behavior
requirement was weakened.

## Amendment-scope certification

The gate compared behavior-bearing files against pre-amendment canonical main
`610344ed7a916ca656b1e8dd23b68a091a8a5e6d`.

Observed behavior diff:
- changed: `hcl/v03/decision_policy.py`
- unchanged:
  - `hcl/v03/action_checker.py`
  - `hcl/integrations/sotopia_agent.py`

The Decision Policy file equals the pre-amendment file with exactly one
replacement:

```text
max_tokens: int = 4096
->
max_tokens: int = 8192
```

No-network tests additionally confirmed:
- Decision Policy default: **8192**
- Action Checker default: **4096**
- HCL state builder: **8192** unchanged
- answer generation: **4096** unchanged
- answer checker: **4096** unchanged
- outer Decision Policy invalid-JSON attempts remain **3**
- transport empty-content attempts remain **4**
- provider/model/seed/temperature forwarding remains unchanged.

## Independent synthetic / regression results

### Verification-stopping Decision Policy

Fixture:
`eval/decision_policy/fixtures_v04_verification_stopping_synthetic.json`

Raw:
- **12 / 12 PASS**

### Action Checker anti-loop

Fixture:
`eval/action_checker/fixtures_v02_verification_stopping.json`

Raw:
- **5 / 5 PASS**

### Negotiation-position semantics

Fixture:
`eval/decision_policy/fixtures_v03_negotiation_position_synthetic.json`

Raw:
- **12 / 12 PASS**

### Historical goal-pursuit

Fixture:
`eval/decision_policy/fixtures_v02_goal_pursuit_synthetic.json`

Raw:
- **11 / 12**
- sole miss:
  `gp03_irreversible_legal_uncertainty`
- actual strategy:
  `ALTERNATIVE_PATH`

The exact existing bounded checker accepted this same historical taxonomy
boundary and no other failure:
- raw total: 12
- raw passed: 11
- raw failed: 1
- accepted_known_boundary: true
- gate_passed: true

The raw score remains 11/12; it is not rewritten as 12/12.

## Decision

**V021A_SYNTHETIC_REGRESSION_GATE: PASS**

The owner-authorized 8192 Decision Policy output budget:
- directly targets the confirmed ordinal48 reasoning-budget exhaustion;
- introduces no detected synthetic Decision Policy regression;
- introduces no Action Checker regression;
- preserves negotiation semantics;
- preserves the existing raw goal-pursuit boundary without widening
  adjudication.

This gate is not external efficacy evidence.

Next:
1. SOTOPIA custom-agent integration smoke on the exact behavior anchor;
2. consumed ordinal48 diagnostic confirmation only;
3. no new holdout automatically follows.
