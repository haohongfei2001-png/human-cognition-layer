# HCL v0.1 Disjoint Holdout Analysis

## Outcome

HCL v0.1 did **not** improve the 100-group disjoint CogToM holdout.

| Metric | Vanilla DeepSeek | DeepSeek + HCL v0.1 | Delta |
|---|---:|---:|---:|
| Mean group accuracy | 98.60% | 96.80% | **-1.80 pp** |
| All-5-variants-correct | 97.00% | 95.00% | **-2.00 pp** |
| Semantic consistency | 98.00% | 97.00% | **-1.00 pp** |
| Error groups | 3 | 5 | +2 |

The holdout was seed 43 and excluded all 200 seed-42 design/audit groups.

## Per-item changes

HCL improved two unstable groups:

- `d2_064_1` — Persuasion Story Task: **0.8 → 1.0**
- `b4_087_1` — Naturalistic Story: Misattribution: **0.8 → 1.0**

HCL harmed four groups:

- `k5_072_1` — Familiary-focus of Attention: **1.0 → 0.0**
- `n6_039_1` — Humor Task: **1.0 → 0.2**
- `b4_068_1` — Naturalistic Story: Misattribution: **1.0 → 0.8**
- `c5_028_2` — See-Know Task: **1.0 → 0.8**

All other groups were unchanged.

## Failure diagnosis

### 1. Always-on HCL is the wrong architecture

The owner's seed insight was narrow and epistemic:

- distinguish world truth from agent knowledge;
- require an evidence bridge for second-order beliefs;
- preserve multiple hidden causes when observations are underdetermined.

v0.1 applied that machinery to **every** item, including humor and tasks where direct reasoning was already sufficient.

This creates an intervention tax: a strong base model can be made worse by forcing unnecessary doubt.

### 2. Over-analysis harmed non-epistemic tasks

On the Humor Task, HCL explicitly expanded literal and causal interpretations of a joke setup. That pushed the answer toward a semantically serious continuation rather than the intended punchline.

This is a concrete example of why a human-cognition layer should be **selective**, not a universal "think more" prompt.

### 3. Technical analyzer failure must never be allowed to change an answer

For at least `k5_072_1` and `c5_028_2`, the HCL analysis state was empty. The answering stage still ran with an empty HCL state and changed otherwise-correct answers.

A portable cognition module must be fail-open:
- if its analysis is unavailable or invalid, return the base model's answer unchanged.

### 4. The underlying epistemic idea still has some signal

The method improved one Persuasion item and one Misattribution item from 0.8 to 1.0, and one of the owner's original observations concerned hidden-cause ambiguity.

That is not enough to claim success, but it is enough to justify one narrower revision.

### 5. Broad CogToM is close to ceiling for this base model

Vanilla DeepSeek scored **98.6%** on this disjoint 100-group sample.

That means broad CogToM accuracy is a poor optimization target for a strong current model: there is little upside and much more room to introduce regressions.

CogToM should therefore become a **diagnostic/unit-test suite**, not the eventual headline benchmark.

## Decision

Reject HCL v0.1 as an always-on architecture.

Proceed to **HCL v0.2 — Selective Epistemic Safeguard** with these constraints:

1. run vanilla reasoning first;
2. activate HCL only when the task genuinely requires nested epistemic / hidden-cause reasoning;
3. if the router or analyzer fails, preserve the vanilla answer;
4. do not activate on humor / general preference / straightforward tasks;
5. evaluate on a fresh holdout that excludes both the original 200 design groups and the v0.1 100-group holdout.

This is a method revision, not a claim that the owner's principle was already validated.
