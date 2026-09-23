# HCL v0.4 C/D/E Capability Comparison v0.1 — Closure

Status: **COMPLETE / NO INCREMENTAL ACCURACY SIGNAL**

This was an internal development diagnostic, not external benchmark evidence.

## Frozen protocol

- plan: `reports/HCL_V04_CDE_CAPABILITY_COMPARISON_V01_PLAN.md`
- fixtures: `eval/v04/cde_capability_v01.json`
- six independent repository-owned scenarios;
- twelve exact-label query points;
- same base model: `deepseek-flash`;
- seed: 42.

Arms:

- C — full-history reconstruction using v0.4 cognition semantics;
- D — dynamic persistent v0.4 HCL;
- E — ordinary full-history memory with strong perspective reasoning.

HCL answer checker, Decision Policy and Action Checker were excluded so that
their effects could not be mistaken for cognition-state value.

## Invalid historical runs

Historical failures are preserved:

### run 35846050675

Terminal FAILURE.

Cause:
- dynamic D encountered duplicate model-supplied assertion IDs across events;
- SQLite correctly rejected the collision.

Repair:
- proposition/assertion identity was made deterministic and event-scoped;
- contract CI returned green before rerun.

No capability conclusion is taken from this run.

### run 35846425931

Workflow SUCCESS, but **evaluation invalid**.

Observed apparent scores:
- C: 0/12;
- D: 1/12;
- E: 1/12.

Artifact inspection showed nearly all answer labels were empty strings.

Cause:
- the comparison answer step used a short ordinary text completion;
- on the current DeepSeek configuration, default thinking consumed the small
  answer budget before a user-visible label was produced.

This was an output-interface / transport defect, not a cognition result.

Repair:
- all three arms were changed identically to structured JSON label output using
  the already validated JSON/non-thinking transport;
- fixtures, gold labels, cognition mechanisms and scoring were unchanged.

## Canonical valid run

Canonical run:
- workflow: `HCL v0.4 CDE Capability Comparison v0.1`;
- run: **35847392708**;
- head: `67f228c07c30d9790d5dc8606fb9adb8f054580c`;
- result: **SUCCESS**;
- artifact: **10744210386**;
- artifact digest:
  `sha256:da56b6bb436ab2d51b35196bdd4609c12023de918bae810fef74d53732291594`.

## Accuracy

All three arms produced the same aggregate exact-label accuracy:

- C: **11/12 = 91.7%**
- D: **11/12 = 91.7%**
- E: **11/12 = 91.7%**

Therefore:

> v0.1 provides **no incremental accuracy signal** for dynamic persistent HCL
> over full-history reconstruction or ordinary memory on this short first-order
> development slice.

## Error signatures

All three arms missed the same query point:

`meeting_correction_rejected / query 0`

Situation:
- Alice explicitly stated that she believed the meeting was at three;
- later she merely received a message claiming four;
- at that query point she had not yet accepted or rejected the new claim.

Gold:
- THREE.

Predictions:
- C: UNCERTAIN;
- D: UNCERTAIN;
- E: FOUR.

The v0.4 structured state in C/D still preserved Alice's explicit
`BELIEF_ESTIMATE + AFFIRM(three)` together with exposure to the new source
claim.

Interpretation:

> The remaining C/D error is primarily a downstream state-to-answer semantics
> problem: a supported prior belief was treated as if mere exposure to a
> conflicting claim automatically made current belief uncertain.

This is a general interface issue, not a reason to patch the specific scenario.

## C vs D state stability

C and D produced identical normalized state signatures on:

- 8 / 12 query points.

They differed on:
- four query points.

Despite these state differences, C and D produced the same answer on all 12
queries.

Interpretation:

- repeated full-history reconstruction introduces semantic variation;
- v0.1 does not show that this variation currently harms final answer accuracy;
- persistent D may have stability/engineering value, but no capability advantage
  is established here.

## Cost / call accounting

### C — reconstruction

- model calls: 39
- JSON calls: 39
- input characters: 118,983
- output characters: 30,136

### D — dynamic persistent HCL

- model calls: 31
- JSON calls: 31
- input characters: 98,550
- output characters: 21,493

Relative to C, D used:
- 8 fewer model calls;
- about 17% fewer input characters;
- about 29% fewer output characters.

This is evidence of an **incremental maintenance / reuse efficiency advantage**
over rebuilding cognition from scratch.

It is not evidence of better cognition accuracy.

### E — ordinary memory

- model calls: 12
- JSON calls: 12
- input characters: 15,759
- output characters: 222

E was dramatically cheaper than either structured-cognition arm while matching
their 11/12 accuracy on this small short-history set.

Therefore:

> v0.1 does not justify the extra structured-cognition cost on short, explicit,
> first-order belief tasks.

## Correctness interpretation

This does not mean HCL is cognitively wrong.

The earlier correctness closure remains intact.

It means:

- the current short task slice is mostly solvable by ordinary memory;
- D has not yet established incremental downstream utility;
- persistence currently shows a reuse/efficiency advantage over C, not an
  accuracy advantage;
- the state-to-answer interface still overreacts to conflicting exposure.

## Development consequence

Do not rerun v0.1 after changing the interface and call it new evidence.

The v0.1 fixtures are now consumed development evidence.

Next:

1. fix the general state-to-answer rule:
   - an existing supported belief estimate is not superseded by
     SOURCE_ASSERTION / INFORMATION_EXPOSURE alone;
   - later evidence must support a belief update before the downstream layer
     treats belief as changed;
2. validate on a disjoint internal v0.2 development set;
3. make v0.2 longer and multi-query enough to test whether persistence adds
   value beyond ordinary full-history memory;
4. preserve E as a strong baseline.

No external benchmark consumption is authorized.

**Gate: HCL_V04_CDE_V01_COMPLETE_NO_INCREMENTAL_ACCURACY_SIGNAL_V02_READY**
