# Frozen Decision Policy v0.2.1 — Verification-Deadlock Repair

Status: **FROZEN FOR POST-REPAIR EXTERNAL HOLDOUT**

## Implementation anchor

Smoke-tested implementation anchor:

`f6e591db8d22ae0e2175769852a1a8aa9c3e106a`

The following behavior-bearing files are frozen for the next external holdout:

- `hcl/v03/decision_policy.py`
- `hcl/v03/action_checker.py`
- `hcl/integrations/sotopia_agent.py`

The HCL v0.3 cognition-state semantics remain frozen under the existing state
contract and were not changed by this repair.

Subsequent commits before the holdout may add only:
- closure/status evidence;
- predeclaration;
- CI/workflow plumbing;
- trigger files.

Any behavior-bearing change to the three files above invalidates this freeze and
requires a new independent synthetic gate + integration smoke before external
holdout use.

## Evidence before freeze

Independent synthetic gate:
- run `35518761327`
- new verification Decision Policy: **12/12**
- Action Checker anti-loop: **5/5**
- negotiation regression: **12/12**
- goal-pursuit regression: **11/12 raw**, exactly the historical
  `gp03_irreversible_legal_uncertainty` taxonomy boundary, boundedly
  adjudicated without rewriting the raw score.

Integration smoke:
- run `35519183891`
- **SUCCESS**
- repaired verification fields appear in live Decision Policy output;
- HCL remains always-on including environment-forced no-op turns.

## Frozen repair semantics

The external holdout tests the following repair as-is:

1. equivalent-probe family tracking;
2. finite probe budget;
3. observable-resolution detection;
4. option-decay accounting;
5. bounded constraint-respecting fallback;
6. no fabricated verification result;
7. hard legal/ownership/consent/safety boundaries remain binding;
8. genuinely new resolvable channels remain allowed.

## Prohibitions until holdout closure

- no tuning against the predeclared holdout;
- no HCL state-semantic changes;
- no selective bypass of HCL;
- no model training;
- no cross-base-model transfer;
- no claim that unused env-agent combinations are fresh scenarios.
