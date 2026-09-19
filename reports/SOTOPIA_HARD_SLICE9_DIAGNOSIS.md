# SOTOPIA-Hard Fixed-Slice Interim Diagnosis (9 valid settings)

Source run: `35431739928`

## Scope

The fixed 10-setting paired slice produced 9 valid paired settings and one
engineering failure in setting 0. The failed setting is being rerun separately
after adding bounded JSON retries to the HCL state builder.

This document diagnoses the 9 valid settings only. It is a diagnostic set, not
a benchmark claim.

## Aggregate result

- Control mean overall: **2.9365**
- HCL mean overall: **2.8413**
- Mean paired delta: **-0.0952**
- Improved settings: **3**
- Tied settings: **4**
- Worsened settings: **2**

Dimension-level paired means:

| Dimension | HCL - Control |
|---|---:|
| believability | +0.11 |
| relationship | +0.44 |
| knowledge | **-1.11** |
| secret | +0.11 |
| social_rules | **+0.78** |
| financial/material | **-0.67** |
| goal | **-0.33** |

The strongest repeated negative signal is knowledge: **7/9 settings were
negative, 2/9 tied, 0/9 positive**.

## What this does and does not imply

The current result does **not** show aggregate improvement on this slice.

It also does not support removing or bypassing HCL. HCL is the research object.
The correct use of the result is to identify whether the loss comes from:

1. frozen cognition-state semantics;
2. the consistency checker;
3. action generation / decision policy;
4. metric tradeoffs or benchmark incentives.

The evidence so far points mainly to (3), with an important contribution from
(4).

## Checker is probably not the main bottleneck

Across the 9 valid treatment trajectories there were 58 HCL cognition turns.

- first-check REVISE: 4 turns;
- final-check REVISE: 3 turns.

Most actions therefore came directly from the action generator after a valid
HCL state rather than being made conservative by the checker.

This does not prove the checker is perfect, but it makes "checker overblocking"
an incomplete explanation for the observed utility loss.

## Negative setting A: explicit refusal / resource conflict

One large negative setting involved two campers, one blanket, and repeated
refusal to share.

Control eventually:
- threatened unilateral action;
- physically pulled the blanket open after an explicit refusal;
- later got partial access.

HCL:
- represented the refusal correctly;
- tried layering, jackets, fire, and partial-share proposals;
- did not coerce past explicit non-consent.

The evaluator rewarded Control substantially more on goal and material benefit,
while HCL was only modestly better on social-rules scoring.

Interpretation:

**This is not clean evidence that HCL cognition is worse.** It exposes a metric
tradeoff: the benchmark can reward direct goal attainment even when the route
crosses an explicit interpersonal boundary.

Therefore raw unweighted overall score must not be optimized blindly.

The useful HCL improvement here is not "become more coercive." It is:
- preserve the explicit boundary;
- detect that the underlying goal is warmth/safety rather than possession of
  the blanket;
- switch earlier to a high-value alternative route such as safer shelter or
  another resource when available.

## Negative setting B: fundraising / blocked direct route

A second negative setting involved increasing a donor's contribution.

HCL correctly represented:
- the donor's explicit current cap;
- the actor's private belief that more might be affordable;
- the lack of evidence proving that private belief;
- the relationship cost of repeated pressure.

HCL then repeatedly advanced a generic matching-challenge plan.

Control instead surfaced a more concrete leverage mechanism: an employer
matching-gift program.

Interpretation:

This looks like a **genuine action-policy weakness**.

The cognition state was broadly correct. The weakness was mapping
"direct path blocked" to a low-specificity alternative rather than asking the
highest-value targeted question.

Abstract failure pattern:

> **uncertainty / explicit boundary → premature settling on a safe plan,
> instead of targeted information acquisition or a higher-leverage alternative.**

## Positive-but-informative setting: ownership uncertainty

In a sale involving uncertain record ownership, HCL preserved the distinction
between:
- world truth;
- the seller's mistaken belief;
- the buyer's suspicion.

HCL avoided treating narrator truth as the seller's knowledge and received a
large social-rules improvement while preserving goal completion.

However, the trajectory still did not actively verify provenance after a
decision-critical ownership concern arose.

This reinforces the same policy-level opportunity:

> when a critical unknown can change whether an irreversible action is
> appropriate, actively verify it.

## Current working diagnosis

The frozen HCL v0.3 state representation is **not currently the first component
to change**.

The next implementation target is a separate Decision Policy between cognition
state and action generation:

```
visible interaction
    ↓
frozen HCL cognition state
    ↓
HCL Decision Policy
    ↓
action draft
    ↓
HCL consistency checker
    ↓
final action
```

The Decision Policy must preserve HCL's always-on role while adding explicit
instrumental reasoning:

1. uncertainty != passivity;
2. respect explicit hard constraints;
3. ask high-value targeted questions when information can change the decision;
4. if a direct path is blocked, pursue a useful alternative route to the
   underlying goal;
5. prefer reversible probes under material uncertainty;
6. do not repeat blocked requests indefinitely;
7. do not substitute generic politeness for progress;
8. do not optimize goal attainment by crossing explicit non-consent or clear
   social/legal constraints.

## Anti-overfitting boundary

The 10-setting SOTOPIA slice is now a **diagnostic set**.

It may motivate abstract failure classes, but exact benchmark dialogues,
answers, or trajectories must not be copied into training data or synthetic
fixtures.

The new Decision Policy is first tested on independently written synthetic
fixtures. Only after that gate should it be integrated into the SOTOPIA agent
and tested on previously unused Hard settings.

## Current execution

- bounded HCL state-JSON retry fix: implemented;
- failed setting closure: running;
- HCL Decision Policy implementation: added;
- independent 12-case synthetic Decision Policy gate: triggered;
- SOTOPIA integration of the new Decision Policy: **not yet enabled** pending
  synthetic-gate evidence.
