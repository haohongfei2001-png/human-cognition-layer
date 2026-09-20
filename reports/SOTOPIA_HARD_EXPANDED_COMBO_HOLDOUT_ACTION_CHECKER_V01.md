# SOTOPIA-Hard Fresh Expanded-Combo Holdout — Action Checker v0.1

Run: `35496131831`

## Scope

Predeclared expanded settings:
`1, 11, 21, 31, 41, 51, 61, 71, 81, 91`

These are previously unused env-agent/persona combinations drawn from 10
different SOTOPIA-Hard environment positions.

Claim boundary:
- fresh **env-agent combinations**;
- underlying environment templates were seen previously;
- therefore this is pairing/persona robustness evidence, not fresh-scenario
  generalization;
- custom DeepSeek partner/evaluator, not official leaderboard-comparable.

All 10 paired settings completed successfully.

## Aggregate

| Metric | Control | HCL + Decision Policy + Action Checker | Delta |
|---|---:|---:|---:|
| Overall mean | 2.2714 | 2.4286 | **+0.1571** |

Setting outcomes:
- improved: **4 / 10**
- tied: **2 / 10**
- worsened: **4 / 10**

## Dimensions

| Dimension | Control | HCL | Delta | Positive / Tie / Negative |
|---|---:|---:|---:|---:|
| believability | 8.0 | 8.2 | **+0.2** | 3 / 6 / 1 |
| relationship | 0.3 | 0.7 | **+0.4** | 3 / 4 / 3 |
| knowledge | 6.3 | 6.3 | **0.0** | 5 / 2 / 3 |
| secret | -0.6 | -0.2 | **+0.4** | 1 / 8 / 1 |
| social_rules | -1.0 | 0.0 | **+1.0** | 3 / 7 / 0 |
| financial/material | -0.2 | 0.1 | **+0.3** | 2 / 7 / 1 |
| goal | 3.1 | 1.9 | **-1.2** | 2 / 2 / 6 |

## Interpretation

The Action Checker repair survives a change in agent/persona pairing at the
overall level: the paired mean is positive and the previous broad knowledge
deficit is absent.

However, the main unresolved weakness is now clearer:

- goal pursuit is **-1.2** on average;
- 6 / 10 settings are negative on goal;
- this reproduces the negative goal signal already seen in repeat seeds 43 and
  44 (-1.6 and -1.2 respectively).

Therefore the generic checker mismatch was a real defect, but not the whole
cause of weak instrumental goal pursuit.

Stable/encouraging signals:
- social-rules remains strongly positive;
- relationship remains positive on average;
- knowledge is neutral rather than systematically negative;
- financial/material is slightly positive.

Unresolved:
- converting socially calibrated cognition into effective goal progress.

## Next research gate

Do **not** tune on the exact 10 holdout trajectories.

Next:
1. audit the six goal-negative cases at the abstract failure-pattern level;
2. separate metric-conflict cases from genuine instrumental failures;
3. update Decision Policy only if a repeated general failure class is found;
4. create independent synthetic fixtures;
5. reserve a new set from the remaining unused expanded combos for validation.

After this run, **70 unused expanded env-agent combos remain**.
