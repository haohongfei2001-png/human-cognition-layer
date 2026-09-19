# Canonical Status

## Project
Human Cognition Layer

## Current phase
**PHASE-00 — CogToM baseline + manual error audit**

## Research question
Can a portable cognition layer improve a strong language model's reasoning about human beliefs, intentions, knowledge states, emotions, and implicit mental states without modifying the base model?

## Current rules
- No model training in PHASE-00.
- No HCL implementation before the first human error audit.
- Use the official CogToM prompt/evaluator unchanged.
- Keep the upstream CogToM revision pinned.
- Benchmark items and gold answers must not become training examples.
- Learn abstract failure mechanisms, not benchmark answers.

## Upstream benchmark
- Repository: Beijing-AISI/CogToM
- Pinned commit: `28c6781b6ea7d7ef7d491f61adc18f076f8b993c`
- License: MIT

## Baseline provider
- Provider: DeepSeek OpenAI-compatible API
- Model: `deepseek-flash`
- Language: Chinese
- Sampling: deterministic stratified sample, seed 42
- Completion budget: 8192 tokens
- DeepSeek thinking: default enabled

## Completed representative baseline
- GitHub Actions run: `35407860416`
- Groups: **200**
- Option-order variants per group: **5**
- CogToM subcategories covered: **46 / 46**
- Mean group accuracy: **0.960**
- All-five-variants-correct rate: **0.925**
- Semantic consistency rate: **0.935**
- Groups with any error: **15**
- Unresolved extraction failures: **0**
- Transient empty responses recovered by retry: **10**

Lowest observed subcategory scores:
- 2nd-Order False Belief: **0.64**
- Persuasion Story Task: **0.68**
- Test of Emotion Comprehension — Belief Based Emotions: **0.75**
- Synesthetic Fallacy Problem: **0.80**
- Aware of Reader’s Knowledge Task: **0.85**

Full summary and row-level failures are stored in the workflow artifact:
`cogtom-baseline-200-35407860416`.

## Current gate
**HCL_V0_1_DESIGN_READY**

The research owner directly audited cases 01–02. Those two judgments were sufficient to extract a reusable principle: **epistemic uncertainty must be preserved when second-order knowledge or hidden causes are underdetermined**. The remaining 13 cases were provisionally screened by AI using that principle and are explicitly not treated as owner labels.

For each error, record:
1. What is explicitly known?
2. What did the model infer incorrectly?
3. What distinction or reasoning step did it miss?
4. Does the same mechanism appear in another error?
5. What general mechanism might correct it without encoding the benchmark answer?

The earlier provisional “100 error” target is superseded for this first gate: the representative 200-group baseline produced only 15 error groups. Review all 15 first; only if evidence is insufficient should we deliberately collect a larger audit set.

## Next action after human audit
Do **not** train yet.

After the human annotations are available:
1. cluster repeated failure mechanisms;
2. decide whether a portable HCL v0.1 is justified;
3. test HCL as an external module on CogToM before any model training;
4. only later move to SOTOPIA-Hard and eventual EQ-Bench 4 visibility work.


## Human audit seed result

Direct owner judgments:
- Case 01: gold is underdetermined because Xiaoli's belief about Xiaohua's knowledge access is not established.
- Case 02: gold is underdetermined because returning without hangers has multiple latent causes; Xiaoxue cannot safely infer that mother saw her action.

Reusable principles:
1. narrator truth != character knowledge;
2. second-order belief requires an explicit evidence bridge;
3. ambiguous observable outcomes should retain multiple latent-cause hypotheses;
4. underdetermined benchmark gold should not become a training target.

See:
- `reports/HUMAN_AUDIT_SEED_CASES_01_02.md`
- `reports/COGTOM_FAILURES_PROVISIONAL_SCREEN.md`

## Next action

Design **HCL v0.1 — Epistemic Uncertainty Layer** as a portable external module, then test it on a fresh unseen CogToM holdout before any model training.

No model weights should be modified in this phase.
