# Hi-ToM External Validation v0.1 — Higher-Order Paired Pilot Plan

Status: **AUTHORIZED / ZERO-PROVIDER INVENTORY**

## Motivation

FANToM v0.2 full-context closed MIXED:
- primary overall net = 0;
- inaccessible belief net = +1;
- information-state net = -1;
- independent information-state/output-interface audit did not establish a
  repeatable parser/interface defect.

The next highest-value question is therefore whether the favorable belief signal
transfers to a benchmark designed specifically for higher-order recursive
Theory of Mind.

## Source

Benchmark:
- Hi-ToM

Pinned repository:
- `ying-hui-he/Hi-ToM_dataset`
- commit:
  `4279d3f783ff4f3b9fcced2a2fec9f6328683f82`

Dataset:
- `Hi-ToM_data/Hi-ToM_data.json`
- git blob SHA:
  `23ab2aee6b2e80115dd645d88b91529ad2a29309`
- 1,200 QA rows total
- Apache-2.0 license.

Repository-documented structure:
- prompting style: VP / CoTP;
- story length: 1–3 chapters;
- ToM order: 0–4;
- deception / communication condition represented in dataset metadata.

Use:
- evaluation only;
- no training/tuning.

## Inventory findings

Pinned data contains:
- 600 VP rows;
- 600 CoTP rows;
- 120 VP rows for each ToM order 0–4;
- 120 unique VP stories;
- for each `deception × story_length × order` cell: exactly 20 VP rows.

v0.1 uses **VP rows only**.

We do not use the dataset-provided CoT prompt and do not ask the base model for
chain-of-thought. The paired runner constructs a direct multiple-choice prompt
from:
- story;
- question;
- choices.

## Zero-provider selection

Fixed selection salt:

`HCL-HITOM-V01-20260922`

Global constraints:
- selected stories must be unique across the whole pilot;
- exact source row IDs are frozen before provider calls;
- no model result is viewed before sample freeze.

Per ToM order target:
- order 0: 12
- order 1: 12
- order 2: 12
- order 3: 12
- order 4: 12

Within each order:
- 2 rows from each `deception × story_length` cell;
- 2 deception values × 3 story lengths × 2 rows = 12.

Total:
- **60 questions**
- **60 distinct stories**

Selection method:
1. filter to VP;
2. group by order / deception / story_length;
3. rank each candidate by SHA256(fixed salt + stable row identity);
4. in fixed order 0→4 and fixed cell order, greedily choose the lowest-ranked
   candidate whose story hash has not been used elsewhere;
5. fail the gate if any cell cannot supply 2 globally story-disjoint rows.

## Paired configuration after predeclaration

Common:
- existing DeepSeek endpoint/key;
- model: `deepseek-flash`;
- seed: 42;
- temperature: 0;
- same user prompt in both arms;
- direct multiple-choice answer only.

Control:
- direct DeepSeek.

Treatment:
- frozen HCL v0.3 answer loop;
- HCL always-on;
- state budget 8192;
- answer/check budgets 4096;
- Decision Policy / Action Checker not used.

HCL behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

## Primary evidence

Higher-order primary:
- orders 2, 3, 4
- n = **36**

Primary paired outcome:
- improved = control wrong / HCL correct;
- worsened = control correct / HCL wrong;
- net paired gain = improved - worsened.

Report separately:
- order 2
- order 3
- order 4
- deception true / false
- story length 1 / 2 / 3.

## Lower-order stability controls

Controls:
- order 0 + order 1
- n = **24**

## Predeclared interpretation

Positive requires all:
1. higher-order primary net paired gain >= **+4** over 36;
2. no individual order 2/3/4 subgroup has net paired gain <= -2;
3. lower-order control net paired gain >= -2.

Negative if either:
- higher-order primary net paired gain < 0; or
- lower-order control net paired gain <= -3.

Otherwise:
- **MIXED / INCONCLUSIVE**.

These are bounded pilot rules, not statistical-significance claims.

## Scoring

Choices are parsed from the dataset's lettered option string.

Gold answer text is deterministically mapped back to the unique option letter.

Model output requirement:
- exactly `[A]`, `[B]`, ... as applicable.

Accepted parser:
- a single unambiguous bracketed option letter;
- or a leading option letter with optional `Answer:` prefix.

Missing/ambiguous output = incorrect.

No LLM judge, semantic regrade, manual regrade or post-hoc adjudication.

## Privacy/output boundary

Persist only:
- frozen row ID;
- story hash;
- order/deception/story-length strata;
- normalized option prediction;
- correctness;
- paired outcome;
- response byte count/hash;
- compact HCL mode/uncertainty/check/revision metadata;
- error type.

Do not persist in result artifacts:
- story text;
- question text;
- choices text;
- gold answer text;
- prompts/messages;
- response text;
- full HCL state;
- credentials.

## Claim boundary

Hi-ToM v0.1 can support only bounded higher-order ToM transfer evidence.

It cannot support:
- official full-benchmark performance;
- cross-base transfer;
- training;
- interactive Decision Policy efficacy;
- HCL 1.0 certification.

No selected Hi-ToM row may be used for tuning after paid launch.
