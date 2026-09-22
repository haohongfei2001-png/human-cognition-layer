# Hi-ToM External Validation v0.1 — Paired Pilot Predeclaration

Status: **FROZEN BEFORE PROVIDER CALLS**

## Source

- benchmark: Hi-ToM
- repository: `ying-hui-he/Hi-ToM_dataset`
- pinned commit:
  `4279d3f783ff4f3b9fcced2a2fec9f6328683f82`
- data:
  `Hi-ToM_data/Hi-ToM_data.json`
- git blob SHA:
  `23ab2aee6b2e80115dd645d88b91529ad2a29309`
- license: Apache-2.0
- use: evaluation only.

## Zero-provider inventory

Canonical inventory:
- run: `35674853358`
- result: **SUCCESS**
- artifact: `10672173370`
- artifact SHA-256:
  `cf32c62c0203c4b8ff8a0d016e2d68bd10abd674b41db29393d4de2a341ab7fc`
- provider/model calls: **0**.

First inventory run `35674804556` failed because the official JSON root is
`{"data": [...]}`, not a top-level list. Source commit/blob checks passed and no
provider call occurred. The loader was fixed without changing any selection
rule.

Inventory facts:
- total rows: 1,200
- VP rows: 600
- CoTP rows: 600
- unique VP stories: 120
- ToM orders: 0–4
- for every `order × deception × story_length` VP cell: 20 rows.

## Frozen selection

Machine manifest:
- `eval/hitom/selection_v01.json`

Fixed salt:
- `HCL-HITOM-V01-20260922`

Selection:
- VP rows only;
- 2 rows from every `question_order × deception × story_length` cell;
- question order: 0–4;
- deception: false / true;
- story length: 1 / 2 / 3;
- globally unique story SHA across all selected rows;
- deterministic SHA256 rank within each fixed cell.

Final sample:
- **60 questions**
- **60 distinct stories**
- order 0: 12
- order 1: 12
- order 2: 12
- order 3: 12
- order 4: 12.

Each order contains:
- deception=false, lengths 1/2/3: 2 each;
- deception=true, lengths 1/2/3: 2 each.

Gold answer text is deterministically mapped to a unique option letter in all
600 VP rows. Only the gold option letter is stored in the frozen manifest.

## Prompt protocol

Do **not** use the dataset's CoTP prompt and do not ask for chain-of-thought.

Both arms receive the same user prompt containing:
1. the pinned row's original VP `story`;
2. the pinned row's `question`;
3. the pinned row's lettered `choices`;
4. the official Hi-ToM assumptions block;
5. instruction to return exactly one bracketed option letter.

The official assumptions block is identical in all 600 VP rows:

- agents witness everything/movements before exiting a location;
- agent A may infer agent B's mental state only after co-location or
  private/public interaction;
- agents tend to lie; what an agent tells others does not change that agent's
  actual belief; trust depends on exit order as defined by the benchmark;
- private communications are known private, public claims are hearable by all.

No dataset-provided "Think step-by-step" instruction is included.

## Paired model configuration

Common:
- existing DeepSeek endpoint/key;
- model: `deepseek-flash`;
- seed: 42;
- temperature: 0.0;
- same user prompt in both arms;
- no new provider or credential.

Control:
- direct DeepSeek;
- neutral system message requiring direct format compliance;
- output budget 4096.

Treatment:
- frozen HCL v0.3 answer loop;
- same DeepSeek backend;
- HCL always-on;
- state budget 8192;
- answer/check budgets 4096;
- Decision Policy / Action Checker are not used.

HCL behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

## Deterministic scoring

Expected output:
- exactly `[A]`, `[B]`, ..., as applicable.

Accepted parser:
- one unambiguous bracketed option letter; or
- a leading option letter with optional `Answer:` prefix.

Ambiguous/missing option = incorrect.

Gold:
- the unique option letter whose option text equals the pinned benchmark answer.

No LLM judge, semantic regrading, manual regrading or post-hoc adjudication.

## Sharding

- 6 deterministic shards;
- 10 frozen rows per shard;
- slicing by `selected[shard_index::6]`;
- because the manifest has 12 rows per order, every shard receives exactly
  2 rows from each order;
- maximum parallelism: 2;
- all 60 rows must complete before result interpretation.

No partial result may be inspected for tuning or protocol amendment.

## Primary evidence

Higher-order primary:
- order 2 + order 3 + order 4
- n = **36**.

Report:
- overall higher-order accuracy and paired net;
- order 2 separately;
- order 3 separately;
- order 4 separately;
- deception false / true;
- story length 1 / 2 / 3.

Primary paired outcome:
- improved = control wrong / HCL correct;
- worsened = control correct / HCL wrong;
- net paired gain = improved - worsened.

## Lower-order stability control

- order 0 + order 1
- n = **24**.

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

These are bounded pilot rules, not significance claims.

## Output/privacy boundary

Artifacts may persist only:
- sample_id;
- story SHA256;
- question order;
- deception flag;
- story length;
- normalized option prediction;
- correctness / paired outcome;
- response byte count/hash;
- compact HCL mode/uncertainty/check/revision metadata;
- error type.

Artifacts must not persist:
- story text;
- question text;
- choices text;
- gold answer text;
- prompt/messages;
- response text;
- full HCL state;
- credentials.

## Claim boundary

This pilot can support only bounded higher-order ToM transfer evidence.

It cannot support:
- official full Hi-ToM benchmark performance;
- cross-base transfer;
- training;
- interactive Decision Policy efficacy;
- HCL 1.0 certification.

Once paid execution begins, all 60 selected rows are consumed and may not be
used for tuning.
