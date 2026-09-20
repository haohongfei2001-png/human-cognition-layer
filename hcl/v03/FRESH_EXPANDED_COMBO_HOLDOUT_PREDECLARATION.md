# Fresh Expanded-Combo Holdout Predeclaration

Inventory run `35495418673` established:
- 20 Hard environment positions;
- exactly 5 matching env-agent combos per position;
- 100 expanded settings total;
- 20 first-combo settings already consumed by earlier diagnostics;
- **80 unused env-agent combos remain**.

The Action Checker implementation remains frozen.

Before viewing any new outcomes, the next robustness holdout is fixed as:
- environment ordinals: `0,2,4,6,8,10,12,14,16,18`
- combo ordinal: `1`
- expanded ordinals: `1,11,21,31,41,51,61,71,81,91`
- generation seed: `42`

Selection rationale:
- one previously unused agent combo from each of 10 distinct Hard environment
  positions;
- spread across the full 20-position Hard list instead of clustering early
  environments.

Claim boundary:
- these are **fresh env-agent combinations**;
- their underlying environment templates have appeared in earlier diagnostics;
- therefore this is a pairing/persona robustness holdout, not a fresh-scenario
  holdout and not official leaderboard-comparable.
