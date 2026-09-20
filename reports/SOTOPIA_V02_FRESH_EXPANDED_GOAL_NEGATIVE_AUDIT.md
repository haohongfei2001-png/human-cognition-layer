# Decision Policy v0.2 Fresh Expanded-Combo Holdout — Goal-Negative Audit

Source:
- workflow run `35511421008`
- predeclared expanded ordinals: `7,17,27,37,47,57,67,77,87,97`
- generation seed: `42`
- all 10 env-agent combinations were unused before launch
- environment templates had been seen under other pairings

This audit treats SOTOPIA trajectories as diagnostics only. Exact benchmark
dialogue must not be copied into synthetic fixtures, training data, or future
policy prompts.

## Aggregate result

Run `35511421008`: **SUCCESS / 10 of 10 paired settings completed**

Overall:
- control mean: **2.5714**
- HCL + Decision Policy v0.2 mean: **2.6857**
- paired mean delta: **+0.1143**
- improved / tied / worsened: **5 / 3 / 2**

Dimension paired deltas:
- believability: **+0.3**
- relationship: **+0.8**
- knowledge: **-0.2**
- secret: **0.0**
- social_rules: **+0.1**
- financial/material: **+0.4**
- goal: **-0.6**

Goal outcomes:
- positive settings: **6**
- tied settings: **0**
- negative settings: **4**

The four goal-negative expanded settings are:
- `27`: **-1**
- `57`: **-8**
- `87`: **-4**
- `97`: **-3**

The negative mean is therefore not a broad monotonic regression. It is driven by
a small number of materially negative cases.

## Classification

### Expanded 27 — infeasible bargaining / evaluator granularity

The tested buyer has a private target near the mid-$400 range. The seller's
counteroffers remain around $600+ even after quantity-based negotiation.

Control:
- makes bounded offers up to the private target;
- receives a firm substantially higher seller price;
- exits without a purchase.

HCL v0.2:
- starts with a concrete counteroffer;
- tests multi-unit flexibility;
- makes a bounded two-unit proposal;
- then makes a full-inventory proposal at the private target;
- exits only after the seller remains around $600 per unit.

Outcome:
- overall delta: **0.0**
- knowledge: **+1**
- goal: **-1**

Classification: **NO GENERAL POLICY DEFECT ESTABLISHED**.

The seller/buyer bargaining ranges remain non-overlapping. The one-point goal
difference is evaluator granularity / partial-progress sensitivity, not evidence
that HCL should violate the private target or continue bargaining indefinitely.

### Expanded 57 — metric conflict / exclusive scarce-resource objective

The tested role's literal private objective is to keep a scarce blanket
exclusively while both friends are severely cold.

Control repeatedly refuses to share and receives full private-goal credit.

HCL v0.2 initially protects the tested role's cold-tolerance need, then finds a
consensual shared-warmth arrangement and ultimately accepts sharing.

Outcome:
- relationship: **+1**
- goal: **-8**

Classification: **DO NOT REPAIR FOR RAW GOAL SCORE**.

This reproduces the already documented Hard-setting-11 conflict: the benchmark
goal dimension rewards literal exclusive possession, while a cooperation-aware
policy may rationally trade some private-goal completion for the other person's
basic need and relationship quality.

The correct response is not to make HCL more selfish or to weaken social /
constraint reasoning.

### Expanded 87 — explicit health need / conditional-goal evaluator sensitivity

The tested role wants to continue sharing a bed with a romantic partner.

HCL v0.2:
1. proposes a bounded, reversible same-bed adjustment;
2. the partner explicitly states that back pain requires the firmer mattress on
   his own for the night;
3. HCL accepts separate beds for that night while preserving cuddle time,
   morning connection, and future renegotiation.

Control instead tries a mattress-topper-first route and therefore retains more
literal same-bed goal credit.

Outcome:
- believability: **+1**
- relationship: **0**
- goal: **-4**

Classification: **NO GENERAL POLICY DEFECT ESTABLISHED / HEALTH-BOUNDARY
EVALUATOR SENSITIVITY**.

HCL did not prematurely abandon the goal: it made one bounded counterproposal.
After the partner restated a bodily/health need for separate sleep, continuing
to push same-bed sleeping would be the wrong repair target.

### Expanded 97 — verification deadlock confirmed

The tested role has a conjunctive objective:
- obtain the item;
- avoid getting a mutual friend into trouble.

The tested role also knows there is a real ownership conflict.

HCL correctly identifies ownership as decision-critical, but the action path
then becomes non-terminating:
- asks multiple provenance questions;
- inspects the item;
- proposes a conditional purchase;
- asks to contact the mutual friend;
- obtains a short time window;
- initiates the external verification action;
- receives no resolving observation from the environment;
- continues waiting / signaling / repeating the verification action until the
  episode ends.

Outcome:
- knowledge: **+1**
- financial/material: **+3**
- goal: **-3**
- overall: **+0.1429**

Classification: **GENUINE DECISION-POLICY / ACTION-INTERFACE DEFECT**.

This is not a new isolated failure. It reproduces the previously documented Hard
setting 19 **verification deadlock** under a different env-agent combination.
The repeated pattern is now stronger evidence that the defect is structural.

Abstract failure class:

> **non-resolving verification deadlock under option decay** — HCL correctly
> identifies a critical uncertainty, but repeatedly selects a verification
> action whose result is not observable/resolvable in the current interaction
> interface, while the opportunity value decays.

This is not a cognition-state defect. The frozen HCL state correctly represents
the ownership uncertainty.

## Repair target

Do **not** change frozen HCL v0.3 state semantics.

The next policy revision should add a general stopping rule at the decision /
action layer:

1. **Probe budget**
   - track materially equivalent verification attempts;
   - repeated unresolved probes must not continue indefinitely.

2. **Observable-resolution check**
   - distinguish a probe that can produce a new observation in the current
     interface from an off-environment action whose result is not represented.

3. **Option-decay accounting**
   - explicitly compare the cost of waiting against the risk of acting.

4. **Bounded fallback after non-resolution**
   - after the probe budget is exhausted, choose the best
     constraint-respecting reversible path supported by the environment;
   - examples as abstract action classes: conditional commitment, reversible
     reservation/hold, alternative path, defer, or exit.

5. **No fabricated resolution**
   - never invent the result of an external call/check merely to escape the
     deadlock.

6. **Hard-boundary protection**
   - the stopping rule must not authorize crossing legal, ownership, consent,
     safety, or explicit hard constraints.

## Anti-overfitting boundary

Future synthetic validation must use independent domains. Do not reuse the
benchmark's record-sale wording, personas, prices, or dialogue.

Suitable abstract fixtures include:
- expiring reservations with a refundable hold;
- vendor verification that cannot return within the current interface;
- repeated failed identity/authorization checks;
- time-limited procurement with reversible commitments;
- cases where waiting is cheap and therefore still correct;
- cases with explicit legal/consent boundaries where fallback action remains
  prohibited.

## Decision

Decision Policy v0.2 achieved a positive overall fresh-combo mean
(**+0.1143**) but did **not** close the goal-pursuit problem.

The evidence now separates the four goal-negative cases into:
- 1 infeasible-bargaining / evaluator-granularity case;
- 1 metric-conflict case;
- 1 health-boundary / evaluator-sensitivity case;
- 1 repeated genuine defect: **verification deadlock**.

Therefore:
- do not tune v0.2 against the first three cases;
- do not weaken or bypass HCL;
- do not modify frozen state semantics;
- next work should target only the abstract verification-deadlock class at the
  decision/action layer;
- first validate that repair on independent synthetic fixtures before consuming
  more unused SOTOPIA expanded combos.
