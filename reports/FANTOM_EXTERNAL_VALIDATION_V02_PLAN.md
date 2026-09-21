# FANToM External Validation v0.2 — Full-Context Independent Pilot Plan

Status: **AUTHORIZED / INVENTORY ONLY**

## Motivation

FANToM v0.1 short-context pilot closed as MIXED:
- primary information-asymmetry: 14/16 vs 14/16;
- inaccessible belief: 6/8 vs 6/8;
- information-state questions: 8/8 vs 8/8;
- accessible belief control: 8/8 vs 8/8;
- fact control F1 delta: +0.0151;
- zero categorical improved/worsened pairs.

The limiting issue was discriminative power / ceiling identity, not a detected
HCL regression.

v0.2 therefore increases difficulty without touching consumed v0.1 items.

## Independent sample boundary

Source remains pinned FANToM v1:
- repository: `skywalker023/fantom`
- commit: `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

v0.2 may use only FANToM conversation IDs **not present** in
`eval/fantom/selection_v01.json`.

v0.1 consumed conversations are permanently excluded.

## Full-context semantics

Input uses FANToM `full_context`.

For belief questions:
- preserve the benchmark's belief accessibility label.

For answerability and information-accessibility binary questions:
- follow FANToM's official full-context setup logic;
- within a set, if any binary target is not fully answerable/accessible
  (`correct_answer != yes`), treat the set's binary questions as
  `inaccessible` for full-context grouping;
- `no:long` is normalized to the binary label `no` for scoring.

No short-context accessibility grouping is silently reused for these binary
families.

## Zero-provider selection

Fixed selection salt:

`HCL-FANTOM-FULL-V02-20260921`

Selection is metadata-only and occurs before any model call.

Fixed stratum order:
1. inaccessible first-order belief;
2. inaccessible second-order belief;
3. full-context inaccessible answerability binary;
4. full-context inaccessible information-accessibility binary;
5. accessible first-order belief;
6. accessible second-order belief;
7. fact control.

Within each stratum:
- rank by SHA256 of fixed salt + question identity;
- skip all v0.1 conversation IDs;
- greedily enforce global conversation-level disjointness inside v0.2.

Target:
- 8 inaccessible first-order belief MC;
- 8 inaccessible second-order belief MC;
- 8 full-context inaccessible answerability binary;
- 8 full-context inaccessible information-accessibility binary;
- 4 accessible first-order belief MC;
- 4 accessible second-order belief MC;
- 8 fact controls.

Total:
- **48 questions**
- **48 distinct conversations**
- **0 overlap with v0.1 conversations**

If any stratum cannot supply its target after exclusions/disjointness, stop the
gate. Do not substitute another stratum.

## Paired configuration after predeclaration

Common:
- DeepSeek `deepseek-flash`;
- existing endpoint/key;
- seed 42;
- temperature 0;
- same full-context user benchmark prompt in both arms.

Control:
- direct DeepSeek.

Treatment:
- frozen HCL v0.3 answer loop;
- HCL always-on;
- state budget 8192;
- answer/check budget 4096;
- Decision Policy / Action Checker not used.

## Primary and control groups

Primary: **32**
- 16 inaccessible belief;
- 8 answerability;
- 8 information accessibility.

Controls: **16**
- 8 accessible belief;
- 8 fact.

## Predeclared pilot interpretation

Positive requires all:
1. primary net paired gain >= **+3** over 32;
2. HCL accuracy not below control in inaccessible-belief subblock;
3. HCL accuracy not below control in information-state subblock;
4. accessible-belief net paired gain >= **-1**;
5. fact mean token-F1 delta >= **-0.05**.

Negative if any:
- primary net paired gain < 0;
- accessible-belief net paired gain <= -2;
- fact mean token-F1 delta < -0.05.

Otherwise:
- MIXED / INCONCLUSIVE.

These are pilot interpretation rules, not statistical-significance claims.

## Claim boundary

v0.2 can support only bounded full-context evidence on a fresh FANToM
conversation sample.

It does not support:
- official FANToM leaderboard performance;
- full-benchmark performance;
- cross-base transfer;
- Decision Policy efficacy;
- HCL 1.0 certification.

No v0.2 selected question may be used for tuning after launch.
