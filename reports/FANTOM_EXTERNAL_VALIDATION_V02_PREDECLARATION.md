# FANToM External Validation v0.2 — Full-Context Paired Pilot Predeclaration

Status: **FROZEN BEFORE PROVIDER CALLS**

## Motivation

FANToM v0.1 short-context pilot closed MIXED / INCONCLUSIVE with:
- primary 16: control 14/16, HCL 14/16;
- categorical improved/worsened: 0/0;
- accessible belief: 8/8 vs 8/8;
- fact F1 delta: +0.0151.

v0.2 changes only the validation difficulty/sample:
- use FANToM full-context;
- double primary sample size from 16 to 32;
- use 48 entirely new conversations.

HCL runtime and base provider remain unchanged.

## Source

- benchmark: FANToM
- upstream repository: `skywalker023/fantom`
- pinned commit:
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset archive SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`
- dataset version: 1.0
- use: evaluation only.

## Zero-provider inventory

Canonical inventory:
- run: `35608769203`
- result: **SUCCESS**
- artifact: `10642254950`
- artifact SHA-256:
  `99ca92874cbc5cbf1640829e5155ac21a447a0c8dcfcf640bb9d883f9a8f8afd`
- provider/model calls: **0**
- FANToM sets: 870
- v0.1 conversations excluded: 32.

Candidate counts after v0.1 exclusion:
- inaccessible first-order belief: 542
- inaccessible second-order belief: 299
- full-context inaccessible answerability binary: 2678
- full-context inaccessible information-accessibility binary: 2673
- accessible first-order belief: 204
- accessible second-order belief: 265
- fact control: 746.

## Frozen selection

Machine-readable manifest:
- `eval/fantom/selection_v02.json`

Selection salt:
- `HCL-FANTOM-FULL-V02-20260921`

Selection rules:
1. exclude every conversation in v0.1;
2. fixed stratum order;
3. rank candidates by SHA256(salt + question identity);
4. greedily enforce global conversation-level disjointness;
5. derive belief A/B option orientation from the same fixed salt;
6. stop if any stratum cannot meet its target.

Final sample:
- **48 questions**
- **48 distinct conversations**
- **0 conversation overlap with v0.1**

Strata:
- 8 inaccessible first-order belief MC;
- 8 inaccessible second-order belief MC;
- 8 full-context inaccessible answerability binary;
- 8 full-context inaccessible information-accessibility binary;
- 4 accessible first-order belief MC;
- 4 accessible second-order belief MC;
- 8 fact controls.

## Full-context semantics

All prompts use FANToM `full_context`.

Belief accessibility follows the benchmark belief metadata.

For answerability and information-accessibility binary grouping, v0.2 follows
FANToM's official full-context setup rule:
- if any binary target in the set is not `yes`, the set's binary questions are
  treated as full-context `inaccessible`.

For scoring:
- `no:long` is normalized to `no`.

## Paired model configuration

Common:
- provider: existing DeepSeek endpoint/key;
- model: `deepseek-flash`;
- seed: 42;
- temperature: 0.0;
- same full-context user benchmark prompt in both arms;
- no new credential/provider;
- no prompt tuning after launch.

Control:
- direct DeepSeek;
- output budget: 4096;
- neutral system message only instructing direct format-following.

Treatment:
- frozen HCL v0.3 answer loop;
- same DeepSeek backend;
- HCL always-on;
- state budget: 8192;
- answer/check budgets: 4096;
- Decision Policy v0.2.1a and Action Checker are not used because this is static
  cognition QA.

HCL behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

## Prompt and scoring

Common benchmark header appears exactly once in the shared user prompt.

Belief MC:
- deterministic A/B ordering from frozen manifest;
- request exactly `[A]` or `[B]`;
- deterministic parser; ambiguous/missing verdict = incorrect.

Binary:
- request exactly `yes` or `no`;
- leading yes/true -> yes;
- leading no/false -> no;
- other output = incorrect.

Fact:
- request short answer phrase;
- lower-case whitespace token F1 using Counter overlap.

No LLM judge, embeddings, semantic regrading, manual regrading or post-hoc gold
adjudication.

## Sharding

- 6 deterministic shards;
- 8 frozen questions per shard;
- maximum parallelism 2;
- all 48 questions must complete before result interpretation.

Partial shard results must not be inspected for tuning or protocol amendment.

## Primary evidence

Primary:
- **32 questions**
- 16 inaccessible belief;
- 8 answerability;
- 8 information-accessibility.

Primary paired outcome:
- improved = control wrong / HCL correct;
- worsened = control correct / HCL wrong;
- net paired gain = improved - worsened.

Primary subblocks:
- inaccessible belief: 16
- information-state: 16.

## Stability controls

- accessible belief: 8
- fact control: 8.

## Predeclared interpretation

Positive requires all:
1. primary net paired gain >= **+3** over 32;
2. HCL accuracy not below control on inaccessible belief;
3. HCL accuracy not below control on information-state subblock;
4. accessible-belief net paired gain >= **-1**;
5. fact mean token-F1 delta >= **-0.05**.

Negative if any:
- primary net paired gain < 0;
- accessible-belief net paired gain <= -2;
- fact mean token-F1 delta < -0.05.

Otherwise:
- **MIXED / INCONCLUSIVE**.

These are bounded pilot rules, not significance claims.

## Output/privacy boundary

Artifacts may persist only:
- question/set/conversation IDs;
- stratum/family;
- normalized prediction;
- correctness/token-F1;
- response byte count/hash;
- compact HCL mode/uncertainty/check/revision metadata;
- error type.

Artifacts must not persist:
- FANToM conversation text;
- benchmark question text;
- correct/wrong answer text;
- prompts/messages;
- response text;
- full HCL state;
- credentials.

## Claim boundary

v0.2 can support only bounded full-context cognition-transfer evidence on a
sample disjoint from v0.1.

It cannot support:
- official FANToM leaderboard performance;
- full benchmark performance;
- interactive Decision Policy efficacy;
- cross-base transfer;
- training;
- HCL 1.0 certification.

Once the paid run launches, all 48 selected questions are consumed and must not
be used for tuning.
