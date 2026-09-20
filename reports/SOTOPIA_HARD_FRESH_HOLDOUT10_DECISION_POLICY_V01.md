# SOTOPIA-Hard Fresh 10-Setting Holdout — Decision Policy v0.1

Run: `35450229188`

## Scope

Fresh, previously unused SOTOPIA-Hard ordinals 10-19.

Configuration:
- Control: Direct DeepSeek
- Treatment: same Direct DeepSeek + frozen HCL v0.3 + Decision Policy
- Partner: Direct DeepSeek
- Same environment/profile/private goal/tested role per pair
- SOTOPIA official seven-dimension rubric
- Custom DeepSeek partner/evaluator; therefore not official leaderboard-comparable

All 10 paired settings completed successfully.

## Aggregate result

| Metric | Control | HCL + Decision Policy | Paired delta |
|---|---:|---:|---:|
| Overall mean | 2.4714 | 2.8857 | **+0.4143** |

Setting outcomes:
- improved: **7 / 10**
- tied: **1 / 10**
- worsened: **2 / 10**

## Dimension-level results

| Dimension | Control | HCL+DP | Delta | Positive / Tie / Negative |
|---|---:|---:|---:|---:|
| believability | 7.9 | 8.4 | **+0.5** | 7 / 1 / 2 |
| relationship | 1.0 | 1.4 | **+0.4** | 3 / 5 / 2 |
| knowledge | 5.8 | 5.8 | **0.0** | 4 / 3 / 3 |
| secret | 0.0 | 0.0 | 0.0 | 0 / 10 / 0 |
| social_rules | -0.5 | 0.0 | **+0.5** | 1 / 9 / 0 |
| financial/material | -0.1 | 1.1 | **+1.2** | 4 / 5 / 1 |
| goal | 3.2 | 3.5 | **+0.3** | 7 / 0 / 3 |

## Comparison with the diagnostic slice

The earlier diagnostic settings 0-9 showed:
- overall paired delta: -0.0429
- relationship: +0.80
- social_rules: +1.20
- knowledge: -1.20
- financial/material: -0.60
- goal: -0.30

The fresh holdout after adding Decision Policy showed:
- overall: **+0.4143**
- relationship: **+0.40**
- social_rules: **+0.50**
- knowledge: **0.00**
- financial/material: **+1.20**
- goal: **+0.30**

This is consistent with the intended repair:
- the strong knowledge deficit disappeared on the fresh slice;
- financial/material and goal no longer show the previous negative tendency;
- relationship/social-rule gains remain non-negative.

## Scientific interpretation

This is encouraging **fresh-holdout evidence**, not a final efficacy claim.

The result supports three narrower claims:
1. the Decision Policy did not merely memorize the diagnostic settings;
2. the previously observed knowledge/goal/material losses did not reproduce on this fresh 10-setting slice;
3. HCL+Decision Policy achieved a positive paired mean on this slice.

However:
- n=10 remains small;
- each setting currently has only one trajectory per arm;
- generation/evaluation can still be stochastic;
- the configuration is not official leaderboard-comparable.

## Next gate

Freeze the current implementation before further tuning.

Then repeat the same fresh settings without changing the module, using additional predefined generation seeds / repeats, and estimate:
- paired mean variance;
- sign stability by setting;
- dimension-level stability.

Only after repeated evidence should the project move to cross-base-model transfer.
