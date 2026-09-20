# Decision Policy v0.2 — Fresh Expanded-Combo Holdout Predeclaration

Purpose:
test whether the v0.2 negotiation-position repair transfers to previously
unused env-agent/persona combinations without tuning on them.

Before viewing any outcome, the holdout is fixed as:
- environment ordinals: `1,3,5,7,9,11,13,15,17,19`
- combo ordinal: `2`
- expanded ordinals: `7,17,27,37,47,57,67,77,87,97`
- generation seed: `42`

Freshness:
- all 10 env-agent combinations are previously unused;
- their environment templates were already seen under other pairings;
- therefore this is persona/pairing robustness evidence, not fresh-scenario
  generalization.

Selection rationale:
- alternate environment positions from the previous expanded-combo holdout;
- move to a new combo ordinal;
- cover the full Hard environment list rather than clustering a narrow region.

No policy tuning is allowed after this declaration until the run completes.
