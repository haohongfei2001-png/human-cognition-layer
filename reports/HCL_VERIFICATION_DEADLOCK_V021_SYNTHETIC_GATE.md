# HCL Verification-Deadlock Repair v0.2.1 — Synthetic Gate

## Scope

This gate validates the abstract repair for:

> non-resolving verification deadlock under option decay

The repair is confined to the Decision Policy / action layer. Frozen HCL v0.3
cognition-state semantics are unchanged.

## Canonical run

GitHub Actions run: `35518761327`

Commit under test:
`e5714e522e2cb0e02749c370f0a563d498c74f98`

Result: **SUCCESS**

## New verification-stopping Decision Policy suite

Fixture:
`eval/decision_policy/fixtures_v04_verification_stopping_synthetic.json`

Result:
- **12 / 12 PASS**
- pass rate: **100%**

Covered failure/control classes include:
- exhausted equivalent probes with expiring reversible options;
- off-interface verification with conditional fallback;
- unanswered preference probes with reversible default;
- a genuinely new resolvable channel after failed old probes;
- irreversible legal/provenance uncertainty;
- automatic future resolution with low option decay;
- hard safety prerequisites that remain binding after probe exhaustion;
- ordinary direct progress with no verification requirement.

## Action Checker anti-loop suite

Fixture:
`eval/action_checker/fixtures_v02_verification_stopping.json`

Result:
- **5 / 5 PASS**
- pass rate: **100%**

The checker:
- rejects repeated exhausted verification;
- rejects fabricated resolution;
- allows reversible bounded fallback;
- allows a genuinely new resolvable channel;
- preserves hard safety boundaries.

## Regression — negotiation-position semantics

Fixture:
`eval/decision_policy/fixtures_v03_negotiation_position_synthetic.json`

Result:
- **12 / 12 PASS**

The verification repair did not regress:
- soft-position vs hard-constraint distinction;
- direct bounded counterproposals;
- anti-self-anchoring behavior;
- alternative-path semantics under hard route blocks.

## Regression — goal-pursuit semantics

Fixture:
`eval/decision_policy/fixtures_v02_goal_pursuit_synthetic.json`

Raw result:
- **11 / 12**
- historical raw score preserved.

The sole raw miss remains:
`gp03_irreversible_legal_uncertainty`

Observed strategy:
- `ALTERNATIVE_PATH`
- goal state `BLOCKED`
- hard ownership/legal constraints preserved;
- verification marked unresolvable/exhausted at the current interface;
- fallback required.

Adjudication:
- **accepted known taxonomy boundary**
- regression gate: **PASS**

This does not post-hoc convert the raw result to 12/12.

Checker:
`scripts/check_goal_pursuit_regression.py`

## Structural repair

Decision Policy now carries:
- `verification_status`;
- `equivalent_probe_count`;
- `option_decay`;
- `fallback_required`.

The SOTOPIA adapter also passes compact prior HCL decision/action history into
the next policy call so equivalent-probe exhaustion does not rely only on
free-form dialogue reconstruction.

## Claim boundary

This is independent synthetic and regression evidence only.

It does **not** establish external SOTOPIA efficacy.

Before consuming another unused SOTOPIA-Hard expanded combo holdout:
1. run SOTOPIA custom-agent integration smoke on the repaired implementation;
2. predeclare the next fresh combo slice;
3. only then run external paired validation.
