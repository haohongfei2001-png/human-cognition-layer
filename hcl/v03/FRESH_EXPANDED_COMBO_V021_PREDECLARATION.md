# Decision Policy v0.2.1 — Post-Repair Expanded-Combo Holdout Predeclaration

Purpose:
test whether the verification-deadlock repair preserves/improves behavior on a
new set of previously unused SOTOPIA-Hard env-agent/persona combinations.

This is **not fresh-scenario generalization**. Every SOTOPIA-Hard environment
template has been seen before. The only freshness claim is at the env-agent
combination/persona-pairing level.

## Frozen implementation

Behavior-bearing implementation is frozen at:

`f6e591db8d22ae0e2175769852a1a8aa9c3e106a`

See:
- `hcl/v03/FROZEN_DECISION_POLICY_V021.md`

No behavior-bearing HCL/Decision Policy/Action Checker change is allowed after
this declaration and before holdout closure.

## Predeclared holdout

Before viewing any outcome, fix:

- environment ordinals: `1,3,5,7,9,11,13,15,17,19`
- combo ordinal: `3`
- expanded ordinals: `8,18,28,38,48,58,68,78,88,98`
- generation seed: `42`
- paired design: same environment/agents/seed for control and treatment
- control: `DirectSocialAgent / Direct DeepSeek`
- treatment: `HCLSocialAgent / same Direct DeepSeek`
- partner/evaluator stack: unchanged from the prior paired expanded-combo runs

## Freshness audit

Pinned Hard inventory established:
- 20 environment positions;
- 5 env-agent combos per environment;
- 100 expanded settings.

Previously consumed successful expanded settings include:

1. combo ordinal 0 across all 20 environments:
   `0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95`

2. combo ordinal 1 on even environment ordinals:
   `1,11,21,31,41,51,61,71,81,91`

3. combo ordinal 2 on odd environment ordinals:
   `7,17,27,37,47,57,67,77,87,97`

The failed environment-ordinal 20-29 preflight consumed no benchmark episodes.

The newly selected combo-3 odd-environment settings:
`8,18,28,38,48,58,68,78,88,98`

are disjoint from all consumed expanded ordinals above.

Combo ordinal 3 has not previously been used by the recorded expanded-combo
holdouts.

## Selection rationale

- use an entirely untouched combo ordinal (`3`);
- use a deterministic odd-environment parity slice rather than selecting cases
  based on expected performance;
- cover the Hard list from low to high ordinal positions;
- include environment 19 as part of the parity rule, not by cherry-picking;
- environment 19 is specifically useful as a stress template for the previously
  diagnosed verification-deadlock class, but because that template was already
  inspected during diagnosis it is **not** independent fresh-scenario evidence.

## Claim boundary

If successful, this holdout supports only:
- post-repair robustness on previously unused persona/pairing combinations
  inside already-seen Hard environment templates.

It does not support:
- fresh-scenario generalization;
- official leaderboard comparability;
- final HCL efficacy;
- cross-base-model transfer;
- training-data conclusions.

## No-tuning rule

Once this predeclaration is committed:
- do not change behavior-bearing HCL code before the holdout completes;
- do not inspect partial trajectory outcomes to tune the policy;
- preserve every raw setting result;
- classify failures only after all 10 paired settings complete;
- any subsequent repair consumes this slice as diagnostic evidence and it can no
  longer be described as fresh.
