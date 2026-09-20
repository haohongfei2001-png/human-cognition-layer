# SOTOPIA-Hard Repeat Stability — Seeds 42/43/44

Primary fresh holdout:
- seed 42 run: `35450229188`

Predeclared repeats:
- seeds 43 and 44 run: `35482453412`

All runs cover the same previously unused SOTOPIA-Hard ordinals 10-19.

## Overall paired deltas

| Seed | Control | HCL + Decision Policy | Paired delta | Improved / Tied / Worsened |
|---|---:|---:|---:|---:|
| 42 | 2.4714 | 2.8857 | **+0.4143** | 7 / 1 / 2 |
| 43 | 2.8000 | 2.7143 | **-0.0857** | 3 / 1 / 6 |
| 44 | 2.8000 | 2.8143 | **+0.0143** | 5 / 1 / 4 |

Mean of the three paired means: **+0.1143**.

The positive overall effect from seed 42 did **not** replicate robustly across the
two predeclared repeats.

## Dimension stability

Paired deltas by seed:

| Dimension | seed 42 | seed 43 | seed 44 | Pattern |
|---|---:|---:|---:|---|
| believability | +0.50 | +0.10 | +0.30 | positive in all 3 |
| relationship | +0.40 | +0.60 | +0.30 | positive in all 3 |
| knowledge | 0.00 | +0.10 | +0.30 | non-negative in all 3 |
| secret | 0.00 | 0.00 | 0.00 | neutral |
| social_rules | +0.50 | +0.30 | +0.50 | positive in all 3 |
| financial/material | +1.20 | -0.10 | -0.10 | not stable |
| goal | +0.30 | -1.60 | -1.20 | negative in both repeats |

## Interpretation

The repeat evidence is mixed.

Stable signals:
- relationship improves across all three runs;
- social-rules score improves across all three runs;
- believability improves across all three runs;
- the earlier large knowledge deficit does not reappear; knowledge is
  non-negative in all three runs.

Unstable signals:
- the seed-42 financial/material gain does not repeat;
- the seed-42 goal gain reverses in both repeat runs;
- therefore the overall +0.4143 should not be treated as a stable efficacy
  estimate.

The current module appears to have repaired the earlier knowledge loss while
retaining relationship/social-rule benefits, but direct goal pursuit remains
unstable and is now the main unresolved capability.

## Important experimental limitation

The exposed seed controls the direct agent backends. It does not perfectly
control every possible source of stochasticity in the SOTOPIA environment or
the custom DeepSeek evaluator. These runs therefore measure end-to-end
stability under predefined agent seeds rather than an ideal isolated RNG
experiment.

## Decision

**Repeat-stability gate: MIXED / NOT YET READY FOR STRONG CROSS-BASE CLAIMS.**

Do not tune on exact SOTOPIA 10-19 trajectories.

Next step:
1. audit goal-regression trajectories across seeds at the abstract failure
   pattern level;
2. determine whether the loss is due to Decision Policy strategy selection,
   action realization, or evaluator/metric tradeoff;
3. create independent synthetic goal-pursuit fixtures from the abstract failure
   class;
4. only then decide whether to revise Decision Policy v0.1 or proceed to a
   cross-base transfer diagnostic.
