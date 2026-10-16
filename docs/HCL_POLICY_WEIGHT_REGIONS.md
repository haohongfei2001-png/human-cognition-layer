# Exact weight regions over bounded two-step policies

This offline composition implements the existing M05 and M14 §§3/5 scope,
with T17/T18 revision/robustness evidence. S3/S4 and full M14 remain open.

## Contract

Judgment v5 accepts the same explicit `policy_horizon: 2` as v1. A domain's
EXPECTED, MAXIMIN or MINIMAX_REGRET rule evaluates each complete root plus
observation-continuation mapping jointly across all dimensions and scenarios.
There is no dimension-specific or hidden-state-specific continuation selection.
V2–v4 compositions still reject the opt-in. Existing single-step v5 inputs,
certificate payloads and tie semantics remain unchanged.

The actual M03/M05/M07/M13 calculation is performed once. Weight-domain changes
do not change facts, feasibility, commitments or fixed action-time hard norms.
Every actual reachable step, including zero-probability actual worlds, must be
feasible and norm-permitted before utility comparison. Future-changing norm
guards are outside this increment. Final values subtract all executed costs;
terminal branches stop. EXPECTED requires one explicit scenario distribution.

Exact normalized rational domains retain all complete-policy scalar optima,
including dominated MAXIMIN ties. The flag enabling this behavior comes only
from the compiled decision, never from an action identifier. Independent tests
enumerate policies and compare every affine crossing and open interval with a
separate rational scalar oracle. Three/four-dimensional point domains are also
covered; general polyhedral mathematics uses the existing certified solver.

The policy catalog records readable roots and observation continuations. Both
full and compact actual HCL answers consume that catalog and verify the whole
source-bound result. Forged mappings, tie semantics or horizons fail delivery.

## Bounds and compatibility

The existing 256-policy and 256-cell caps, proof byte cap and shared work budget
are unchanged. Policy enumeration, region coverage, proof or work exhaustion,
and unresolved normative branches prevent complete robust/possible claims.
An empty domain confers no vacuous recommendation. A deliberately complex
fractional-cost regret fixture can exceed the proof cap; this remains a frontier,
not a reason to increase the cap or assert completeness.

The exact shipped PR447 main e3b169abe54578ccbc9c8cb91aea0708ddb2d3df
(238 runtime Python files) is an additive pinned predecessor. Independent old
processes persist completed, returned, unknown-send, computed and committed
v1 policies and v5 single-step judgments. Upgrade checks retain old proof and
claim bytes, recover without provider resend, and retain governance, ACL,
erasure and writer fences. No stored certificate is rewritten as a new policy
weight certificate.

## Evidence

- `tests/test_unified_policy_weight_regions.py`: actual HCL consumption, exact
  independent oracle, ties, revisions, tampering, bounds and durable recovery.
- `tests/test_unified_policy_weight_upgrade.py`: genuine PR447 predecessor.
- `scripts/witness_unified_policy_weight_regions.py`: eight offline cases.

No preference inference, automatic adoption, paid provider calls, arbitrary
horizons or general policy-search completion is claimed.
