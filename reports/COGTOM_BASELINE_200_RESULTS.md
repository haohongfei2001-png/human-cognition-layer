# CogToM 200-Group Baseline Result

## Result

DeepSeek `deepseek-flash`, Chinese CogToM, official vanilla prompt/evaluator.

- CogToM revision: `28c6781b6ea7d7ef7d491f61adc18f076f8b993c`
- Sampling: deterministic stratified sample, seed 42
- Groups: 200
- Variants per group: 5
- Subcategories covered: 46 / 46
- Mean group accuracy: **96.0%**
- Strict all-five-variants-correct rate: **92.5%**
- Semantic consistency rate: **93.5%**
- Groups with at least one error: **15**
- Unresolved answer extraction failures: **0**

### Category accuracy

| Category | Accuracy |
|---|---:|
| Belief | 91.33% |
| Comprehensive | 96.80% |
| Desire | 93.60% |
| Emotion | 96.67% |
| Intention | 100.00% |
| Knowledge | 91.00% |
| Non-literal | 100.00% |
| Percept | 100.00% |

### Lowest subcategories

| Subcategory | Accuracy |
|---|---:|
| 2nd-Order False Belief | 64% |
| Persuasion Story Task | 68% |
| Test of Emotion Comprehension: Belief Based Emotions | 75% |
| Synesthetic Fallacy Problem | 80% |
| Aware of Reader’s Knowledge Task | 85% |
| Sarah Task | 90% |
| Expanding Tasks: Flattery | 92% |
| False Belief Task: Location | 92% |
| Naturalistic Story: Misattribution | 92% |
| Strange Story: Pretend | 92% |

## Technical integrity note

The run recorded 10 transient empty-content responses from the DeepSeek API. CogToM's official format-repair/retry path recovered all of them; there were **zero** max-retry extraction failures. They are therefore not counted as unresolved benchmark failures.

DeepSeek thinking remained enabled. A provider-specific 8192-token completion budget was used because a 2048-token smoke run could exhaust the budget before visible answer content on difficult items.

## Interpretation

This is a baseline, not evidence that HCL works.

The useful signal is that failures are concentrated rather than uniform. In particular, second-order belief and persuasion-related reasoning are plausible candidates for repeated cognitive failure mechanisms, but **no taxonomy should be accepted before the human audit of the actual failed items**.

## Artifact

GitHub Actions run: `35407860416`

Artifact: `cogtom-baseline-200-35407860416`

The artifact contains:
- `raw.jsonl`
- `metadata.json`
- `summary.json`
- `errors.jsonl`
- `errors.csv`
- `AUDIT.md`

The next research step is manual review of all 15 error groups.
