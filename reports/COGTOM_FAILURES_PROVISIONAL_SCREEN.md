# Provisional Screening of Remaining CogToM Failures

**Important:** Only cases 01–02 have direct human-owner judgments. Cases 03–15 below are AI-assisted provisional screening using the owner's reusable principles. They are not owner labels.

## Screening categories

- **Likely genuine model failure**: benchmark gold appears reasonably supported and model failure reflects a reusable reasoning error.
- **Likely benchmark ambiguity**: multiple answers remain plausible or the gold requires an unstated assumption.
- **Borderline**: some evidence favors the gold, but certainty is stronger than the story warrants.

## Case-level provisional screen

### 03 — b3_067_3 — 2nd-Order False Belief
**Provisional:** Borderline / likely genuine instability.

Zhao actually sees Lin's anxious practice through the door, then changes behavior in a way that strongly signals awareness. Lin can reasonably infer she noticed his anxiety, although this is still an inference rather than certainty. One wrong permutation out of five looks more like instability than a deep conceptual failure.

### 04 — k3_066_2 — Aware of Reader's Knowledge
**Provisional:** Likely benchmark ambiguity.

The gold assumes the conversational objective is to explain the Great Red Spot to a novice. But the question asks how to "mention" it, and simply sharing the observation is natural. The task embeds a normative communication preference not uniquely implied by the prompt.

### 05 — b3_064_3 — 2nd-Order False Belief
**Provisional:** Borderline / likely genuine instability.

Like case 03, Lin's changed behavior after secretly observing Chen gives strong evidence that she recognized his concern. The gold is plausible, but not logically forced. Three wrong permutations suggest a real sensitivity/instability issue worth inspecting.

### 06 — e9_077_2 — Belief-Based Emotions
**Provisional:** Likely benchmark problem.

"Excited" is weakly supported. Felix has poor signal, reaches connectivity, and prepares to reply; relief or concern are at least as plausible. This item should not be used as a training target without stronger justification.

### 07 — d2_032_1 — Persuasion Story
**Provisional:** Likely benchmark problem.

The user's objection is travel time. Option A directly reduces the stated cost; gold B reframes long travel as enjoyable without solving the objection. The model's choice is arguably better targeted.

### 08 — d2_001_1 — Persuasion Story
**Provisional:** Likely benchmark ambiguity.

Option A directly mitigates crowd risk by preserving an exit option. Gold B reframes queues as tolerable. Both are plausible; there is no unique best persuasion strategy.

### 09 — k2_025_2 — Synesthetic Fallacy
**Provisional:** Likely benchmark problem.

A visual observer can see the physical act of striking a water drum, even if they cannot hear the music. "Wiping a transparent decorative bucket" is not strongly implied. Gold appears dependent on an unstated assumption about what visual information is available.

### 10 — c3_071_3 — Flattery
**Provisional:** Likely benchmark ambiguity.

The story establishes Xiaocheng knows Xiao'an's motive, but does not establish what Xiaocheng knows about Lao Li's awareness. "Completely doesn't know" is too strong. Same family as owner-audited cases 01–02: unsupported second-order certainty.

### 11 — k1_092_1 — Sarah Task
**Provisional:** Likely genuine model failure.

The world explicitly states this agent has no concept of natural weather and is familiar with only artificial environmental processes. Choosing a rainstorm imports human-world priors that violate the agent's available concept space. This is a clean perspective/world-model restriction error.

### 12 — b4_076_1 — Misattribution
**Provisional:** Likely benchmark ambiguity.

The colleague observes stomping and offers coffee. The prompt does not establish that the colleague knows the criticism email, but neither does stomping strongly imply sleepiness. Gold A is itself a speculative causal attribution.

### 13 — c1_044_3 — Pretend
**Provisional:** Likely genuine model failure.

Understanding the pretend action requires familiarity with the target object/schema (microphone), not familiarity with the prop object (corn). Xiaolin lacks microphone knowledge; Xiaoxi lacks corn knowledge but can still map an unfamiliar prop to a familiar microphone function. This is a clean role/schema distinction.

### 14 — c3_002_3 — Flattery
**Provisional:** Likely benchmark ambiguity.

Same structure as case 10. The sister knows the flatterer's motive, but nothing establishes whether the mother is aware of it. "Completely unaware" is overconfident second-order attribution.

### 15 — e3_050_1 — Affective Perspective-Taking
**Provisional:** Likely benchmark ambiguity.

A person who plagiarized and won may feel smug, guilty, anxious, sad, or mixed emotions depending on personality and moral awareness. Gold "proud/smug" is not uniquely entailed.

## Provisional synthesis

The 15-error set appears to contain two very different phenomena:

### A. Benchmark underdetermination / forced certainty
Strong candidates: **01, 02, 04, 06, 07, 08, 09, 10, 12, 14, 15**

Common pattern:
- hidden mental states are treated as uniquely recoverable;
- normative social strategy is treated as objective ground truth;
- one latent explanation is selected despite multiple compatible hypotheses.

### B. Potentially genuine reusable reasoning failures
Strongest candidates: **11, 13**
Borderline candidates worth a closer look: **03, 05**

Possible reusable mechanisms:
- restricting inference to the agent's own concept/knowledge space;
- separating prop identity from the target schema in pretend reasoning;
- tracking whether behavior provides sufficient evidence of another person's hidden observation.

## Research implication

Before building HCL v0.1, the project should **not** optimize toward all 15 gold answers. A substantial fraction may reward overconfidence rather than better human understanding.

A more promising first HCL principle is therefore not "reason harder", but:

> **Represent epistemic uncertainty explicitly and refuse to collapse underdetermined human-state inference into a single certain interpretation.**

This principle should be tested on independent cases before any training.
