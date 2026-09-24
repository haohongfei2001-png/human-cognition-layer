# HCL v0.4 Long-Horizon Bounded-Context v0.2 — Closure

Verdict: **COMPLETE / CURRENT V0.4 INCREMENTAL UTILITY NOT ESTABLISHED; E OUTPERFORMS D ON THIS FROZEN SLICE**

This is controlled internal evidence. It is not an external benchmark,
real-human, cross-model, production, publication, or leaderboard result.

## Frozen execution

- Trigger/main commit: `dbf127a95a1b4e180064010dacb22ff98457160d`
- Candidate anchor: `8d7f2b2cf9f027eb6b2046fdd8043f8bab2daac2`
- Workflow run: `35984587967` — SUCCESS
- Job: `107584183596`
- Artifact: `10802613472`
- Artifact ZIP digest:
  `sha256:8519b7eb68d90bab3e68ca3c434ccaabcf57bbf5415be5e5a582cc483fd55660`
- Result JSON SHA-256:
  `ff0e185c6833ae811b575109eb2066c659f8f2c1d2d98aaa6b67f364077cfd31`
- Model: `deepseek-flash`; seed: 42
- Fixture SHA-256:
  `5aad883a58ddfb12c1089381bc1471898eb21cdbe6e143b1d5a5e256d816b110`
- Gold SHA-256:
  `a50be5387f97cc9de8b6b83868518d5c765b2298348029d8d3939dcca5a348af`
- Shape: 3 streams / 240 events / 18 scored queries
- D/E query-time dynamic-context cap: 8000 characters
- E ordinary persistent-memory cap: 6000 characters

All frozen one-shot, candidate, digest, preflight and evidence-completeness
checks passed before the result was accepted.

## Primary result

| Arm | Correct | Accuracy | Provider calls | Input chars | Output chars | Provider wall time | Max query context | Max persistent state |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C full-history diagnostic | 15/18 | 83.3% | 18 | 363,612 | 313 | 16.57 s | 31,998 | n/a |
| D persistent HCL | 14/18 | 77.8% | 258 | 2,220,200 | 234,941 | 390.31 s | 7,990 | 87,549 chars |
| E ordinary persistent memory | 17/18 | 94.4% | 258 | 721,384 | 279,842 | 1400.67 s | 7,999 | 2,390 chars |

D and E had the same number of provider calls and both respected the same
query-time context cap. D used roughly 3.08x E's input characters and maintained
a much larger persistent state. E was slower in provider wall time because its
240 incremental memory updates used text generation, while D's semantic updates
used JSON generation. Correctness is the primary criterion under the frozen
contract.

The primary D-vs-E comparison therefore provides **evidence against the current
D design on this capability slice**. A speed advantage does not override lower
semantic correctness.

## Per-row failures

C failed all three frozen cases whose correct state was unresolved after receipt
of a revision but before acceptance/rejection:

- `s4-q3`: predicted NORTH; gold UNCERTAIN
- `s5-q3`: predicted 120K; gold UNCERTAIN
- `s6-q5`: predicted BETA; gold UNCERTAIN

E failed one of those cases:

- `s6-q5`: predicted BETA; gold UNCERTAIN

D got all three of these receipt-without-stance cases correct. This is a real
positive signal for the recently added receipt != acceptance mechanism, but it
is insufficient to establish overall incremental utility.

D failed four other rows:

- `s4-q5`: predicted UNCERTAIN; gold SOUTH — private-world-fact separation
- `s5-q4`: predicted UNCERTAIN; gold 135K — private-world-fact separation
- `s6-q3`: predicted UNCERTAIN; gold BETA — private-world-fact separation
- `s6-q4`: predicted GAMMA; gold BETA — explicit rejection

## Mechanism diagnosis from preserved evidence

The result artifact preserved the exact model-visible query contexts and D
persistent cognition snapshots, so these failures can be localized without
rerunning consumed rows.

### 1. Historical uncertainty remains active after later explicit stance

In `s5-q4`, D contains a later direct `BELIEF_ESTIMATE` that Maya AFFIRMS
135K, but an older `OTHER_UNKNOWN` stating that Maya had not yet accepted or
rejected 135K remains in `unresolved_conflicts`. The answer stage returns
UNCERTAIN.

This exposes an append-only state-lifecycle defect: later explicit stance does
not deterministically close older uncertainty for the same issue.

### 2. Repeated confirmation can incorrectly reopen uncertainty

In `s6-q3`, Nora explicitly accepted Dock Beta after a relay. A later direct
confirmation of the same Beta-over-Alpha revision is treated as a new revision
exposure. Because the existing Beta stance predates that repeated exposure, the
projection reopens `REVISION_STANCE_UNRESOLVED` instead of recognizing that
the received information is already accepted.

This is a state-transition defect: confirming an already accepted revision must
not by itself erase or suspend the accepted stance.

### 3. Revision identity is too proposition-ID-literal

In `s4-q5`, Lin has a later direct belief that South Room is assigned, but the
revision relation uses a separate proposition whose canonical text is
"South Room replaced North Room". The current resolution rule only recognizes
stances on the exact old/new proposition IDs, so semantically equivalent
acceptance does not close the older revision uncertainty.

This exposes a representation defect between object-level issue values and
meta-level revision statements.

### 4. Raw assertion projection leaves stance polarity too easy to misread

In `s6-q4`, the D query context contains both a directly supported
AFFIRM(Beta) and DENY(Gamma), yet the answer stage chooses Gamma.

The stored evidence is better than the returned answer. The current query
projection still exposes an assertion bag rather than a deterministic current
stance summary, leaving the downstream model to reinterpret polarity and
temporal precedence.

## Research interpretation

The v0.2 evidence does **not** justify promoting current v0.4 persistent HCL as
an improvement over a strong ordinary persistent-memory baseline.

The result is also not evidence that all structured cognition is useless. It
identifies a narrower conclusion:

> The current append-mostly assertion + query-time heuristic projection
> architecture does not reliably converge historical evidence into one
> current agent stance, and its additional structure/cost does not currently
> pay for itself.

The receipt != acceptance distinction should be preserved because it showed a
specific benefit. The next mechanism should not add more answer prompt rules or
rerun v0.2. It should change how current stance is represented/projected.

## Consumption boundary

v0.2 is now consumed internal evidence.

- Do not rerun these 18 rows as fresh evidence after a mechanism change.
- Do not patch prompts against their labels and call the same package fresh.
- Provider-free regression tests may encode the abstract failure modes using new
  concrete examples.
- Any later capability test requires a newly frozen independent package.

No owner-private example, external benchmark, cross-model run, training,
publication claim, or leaderboard action is authorized by this closure.
