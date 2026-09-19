# HCL v0.3 State Fidelity Suite v0.2 — Adjudication

## Raw fresh run

Run: `35414125494`

- 36 fresh cases
- raw automated pass: **32 / 36**
- mode accuracy: **94.4%**
- uncertainty accuracy: **94.4%**
- schema validity: **97.2%**

The four failures were manually inspected as research artifacts rather than automatically treated as HCL defects.

## Failure adjudication

### `s08_explicit_promise`

**Serialization defect, cognition correct.**

The state used Chinese `低` instead of protocol token `low`.

Action:
- keep canonical enum values in English;
- normalize harmless localized enum aliases at the protocol boundary.

### `e02_false_belief_content`

**Fixture underdetermined. Excluded from gate.**

The scene says the mother replaced the original toy with a book and Xiaole left before the replacement, but never states that Xiaole had observed or knew the original toy.

A classic false-belief answer requires the missing premise:
> Xiaole knew the pre-change content.

This is directly analogous to the owner's original concern about benchmark questions that silently assume an information bridge.

The fixture is retained as a useful ambiguity detector but is no longer allowed to decide HCL pass/fail.

### `e06_overheard_information`

**Fixture mode expectation was wrong; HCL state was better.**

Xiaozhao explicitly heard the full announcement. For the question of whether he obtained the information, the access path is direct and complete. According to the HCL v0.3 mode semantics, this is `SIMPLE`, not `EPISTEMIC`.

### `e08_false_information`

**Real mode-classification defect; state content correct.**

The state correctly represented:
- world truth: Thursday;
- teacher belief: Friday;
- Xiaojie's belief after misinformation: Friday.

But it labeled the state `SIMPLE`.

Action:
- world-truth / agent-belief divergence is now explicitly an `EPISTEMIC` condition.

## Regression after fixes

Run: `35414572919`

Raw result:
- **35 / 36**
- mode accuracy: **100%**
- schema validity: **100%**

The only nominal failure was `e02_false_belief_content`, the underdetermined fixture above.

Therefore the adjudicated result is:

> **35 / 35 determinate fixtures passed. One ambiguous fixture retained but excluded from the gate.**

This is not a claim that HCL v0.3 is solved. The next evidence must come from a new, unseen suite.

## Next independent test

`fixtures_v03_paired_fresh.json`

- 24 fresh cases
- 12 minimal contrast pairs
- created after Suite v0.2 was observed
- not used to tune HCL before first run
