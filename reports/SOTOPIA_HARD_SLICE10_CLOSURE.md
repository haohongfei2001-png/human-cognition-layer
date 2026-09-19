# SOTOPIA-Hard Fixed 10-Setting Paired A/B — Closure

Primary slice run: `35431739928`  
Failed-setting closure run: `35449140294`

## Experimental design

This is a fixed 10-setting method-validation slice from the official
SOTOPIA-Hard data, using the pinned upstream revision
`a0aaafb440e570e5e61b7c44a44e5e417c545383`.

For each paired setting:
- Control tested role: Direct DeepSeek
- Treatment tested role: the same Direct DeepSeek + always-on HCL v0.3
- Partner: Direct DeepSeek
- Evaluator rubric: SOTOPIA's seven official dimensions
- Same environment, profiles, private goals, tested role, and action order

This is **not** the official leaderboard configuration because the partner and
evaluator model are custom DeepSeek rather than the benchmark's default
reference configuration.

## Closure

The first 10-setting run completed 9 settings. Setting 0 failed only because the
HCL state builder returned malformed JSON.

The state builder was changed to retry malformed JSON up to three times without
bypassing HCL. Setting 0 was then rerun successfully.

Final usable paired settings: **10 / 10**.

## Aggregate

| Metric | Control | HCL | Paired delta |
|---|---:|---:|---:|
| Overall mean | 2.7429 | 2.7000 | **-0.0429** |

Setting outcomes:
- HCL improved: **4 / 10**
- tied: **4 / 10**
- worsened: **2 / 10**

Dimension-level mean paired deltas:

| Dimension | HCL - Control | Positive / Tie / Negative |
|---|---:|---:|
| believability | 0.00 | 1 / 8 / 1 |
| relationship | **+0.80** | 5 / 4 / 1 |
| knowledge | **-1.20** | 0 / 2 / 8 |
| secret | -0.20 | 1 / 8 / 1 |
| social_rules | **+1.20** | 3 / 7 / 0 |
| financial/material | **-0.60** | 2 / 5 / 3 |
| goal | **-0.30** | 3 / 5 / 2 |

## Main finding

The result is approximately neutral on overall score, with a clear internal
tradeoff.

HCL tends to improve:
- relationship preservation;
- social-rule compliance.

HCL tends to lose:
- knowledge acquisition;
- financial/material utility;
- some direct goal progress.

The strongest repeated signal is **knowledge**:
- negative in **8 / 10** settings;
- tied in 2;
- positive in 0.

This is more diagnostic than the near-zero overall mean.

## Why the negative overall is not a reason to bypass HCL

One of the two strongly negative settings rewarded the Control trajectory for
crossing an explicit interpersonal boundary in order to obtain a scarce
resource. Control got much more goal/material credit; HCL respected the
refusal and pursued alternatives.

That setting demonstrates that an unweighted benchmark total can mix:
- desirable instrumental effectiveness;
- socially problematic goal pursuit.

Therefore the research target is not "make HCL imitate whatever gets the
highest raw overall score."

At the same time, other losses look genuine. In fundraising, for example, HCL
correctly respected a stated personal donation cap but settled early on a
generic matching challenge instead of probing a higher-value concrete mechanism
such as employer matching.

## Current diagnosis

The frozen HCL v0.3 cognition-state semantics are **not** the first thing to
change.

The more likely defect is the mapping:

```
correct cautious cognition
    ↓
overly cautious action
```

The current action generator does not explicitly optimize:
- value of information;
- alternative paths to the underlying goal;
- reversible probing;
- stopping rules after a blocked route;
- instrumental usefulness subject to explicit constraints.

## Decision-policy response

A separate HCL Decision Policy has been implemented after the frozen cognition
state and before action generation.

It explicitly encodes:

1. uncertainty != passivity;
2. respect explicit hard constraints;
3. use targeted high-value information probes;
4. switch to alternative routes when the direct route is blocked;
5. prefer reversible probes under uncertainty;
6. do not give up useful opportunities merely to reduce uncertainty;
7. do not substitute generic politeness for progress;
8. do not cross explicit non-consent or clear social/legal constraints just to
   improve goal score;
9. stop/defer/exit when marginal value is low.

This does **not** change the frozen HCL v0.3 state semantics and does not bypass
HCL.

## Anti-overfitting rule

These 10 settings are now a **diagnostic set**.

They may identify abstract failure classes, but their exact dialogues,
trajectories, and evaluator answers are not training data.

The Decision Policy is being evaluated first on 12 independently written
synthetic fixtures. It must pass that gate before SOTOPIA integration.

The next external validation must use previously unused SOTOPIA-Hard settings.
