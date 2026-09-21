# FANToM External Validation v0.1 — Inventory and Predeclaration Plan

Status: **AUTHORIZED / INVENTORY_ONLY**

## Why FANToM

FANToM is selected as the next external source because it directly stresses:
- belief tracking under information asymmetry;
- answerability;
- information accessibility;
- first-/second-order Theory of Mind;
- a control condition without information asymmetry.

It is independent of the already-consumed SOTOPIA-Hard environment templates.
The benchmark conversations were generated for FANToM and human validated.

Source:
- repository: `skywalker023/fantom`
- pinned commit: `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- repository license: MIT
- official dataset archive:
  `https://storage.googleapis.com/ai2-mosaic-public/projects/fantom/fantom.tar.gz`
- upstream-published SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`
- dataset use: evaluation only.

No FANToM data may be used for training or tuning.

## Why not ToMATO for this gate

ToMATO is a valid ToM benchmark, but its generation pipeline consumes SOTOPIA
agents/environments and its dataset retains SOTOPIA provenance fields. It is
therefore not sufficiently independent for the current "new external source"
gate.

## Why not EQ-Bench 4 yet

EQ-Bench 4 is highly relevant to HCL's eventual social-interaction validation,
but its official methodology relies on several additional commercial
persona/judge providers. That would introduce new credential/cost boundaries.
It is deferred rather than weakened into a non-official substitute.

## Stage 1 — zero-provider inventory

Before any model call:

1. download the exact FANToM v1 archive;
2. verify the upstream SHA-256;
3. inspect only benchmark metadata/schema;
4. enumerate candidate deterministic question families;
5. select candidate IDs with a fixed hash rule while enforcing global
   FANToM conversation-level disjointness;
6. publish counts + IDs;
7. do not query DeepSeek.

Fixed selection salt:

`HCL-FANTOM-EXT-V01-20260921`

Candidate families for the first bounded paired pilot:

- inaccessible belief, first-order;
- inaccessible belief, second-order;
- accessible belief, first-order;
- accessible belief, second-order;
- inaccessible answerability binary;
- inaccessible information-accessibility binary;
- fact control.

Selection is performed in this fixed stratum order:
1. inaccessible first-order belief;
2. inaccessible second-order belief;
3. inaccessible answerability binary;
4. inaccessible information-accessibility binary;
5. accessible first-order belief;
6. accessible second-order belief;
7. fact control.

Within each stratum, candidates are ordered by the fixed hash salt and selected
greedily only when their FANToM conversation ID has not already been selected
for any earlier stratum. This prevents correlated questions from the same
conversation entering the 32-question pilot.

Belief evaluation will use a deterministic two-choice presentation generated
from the benchmark's correct/wrong belief answers. Choice order is derived from
the same fixed hash salt, not runtime randomness.

The initial target is **32 paired questions**:

- 4 inaccessible first-order belief;
- 4 inaccessible second-order belief;
- 4 accessible first-order belief;
- 4 accessible second-order belief;
- 4 inaccessible answerability binary;
- 4 inaccessible info-accessibility binary;
- 8 fact controls.

If a stratum has fewer than the requested count, inventory must stop the gate;
do not silently substitute another stratum.

## Stage 2 — predeclaration

After inventory and before provider calls, commit:

- exact selected question IDs;
- exact FANToM set IDs;
- exact question family/order/accessibility;
- deterministic choice orientation for belief MC;
- prompt templates;
- scoring rules;
- paired model configuration;
- claim boundary.

No selected answer text needs to be copied into the repository.

## Stage 3 — paired pilot

Only after Stage 2 is committed:

Control:
- direct `deepseek-flash`;
- same endpoint/key;
- seed 42;
- temperature 0.

Treatment:
- HCL v0.3 always-on answer loop;
- same `deepseek-flash`;
- frozen state semantics;
- existing v0.2.1a runtime;
- no Decision Policy/action layer (this is a static cognition test).

Primary paired metrics:
- inaccessible belief MC accuracy;
- inaccessible answerability binary accuracy;
- inaccessible information-accessibility binary accuracy.

Control-stability metrics:
- accessible belief MC accuracy;
- fact token-F1.

Also preserve question-level paired outcomes.

## Claim boundary

This v0.1 pilot is:
- independent external cognition evidence;
- not SOTOPIA efficacy evidence;
- not an official FANToM leaderboard run;
- not cross-base transfer;
- not training evidence;
- not HCL 1.0 certification.

No tuning is allowed against selected FANToM questions before pilot closure.
