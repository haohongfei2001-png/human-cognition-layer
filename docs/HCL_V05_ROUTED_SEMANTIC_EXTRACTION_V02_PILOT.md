# HCL v0.5 Routed Semantic Extraction Pilot v0.2

Status: **FROZEN / PROVIDER RUN NOT STARTED**

## Question

After separating revision-relation recognition from deterministic exposure
routing, is event-local semantic extraction reliable enough to justify another
capability experiment?

This pilot evaluates only:

1. explicit actor self stance:
   - AFFIRM
   - DENY
   - UNRESOLVED
2. subject-free revision relations:
   - issue / new value / prior value

Information-flow routing is deterministic and is not a model-scored decision.

## Fresh package

- 3 streams;
- 12 events each;
- 36 events total;
- 19 self-stance gold records;
- 14 revision-relation gold records;
- new domains: document delivery channel, maintenance day, review queue;
- all event IDs and raw event texts are disjoint from consumed extraction v0.1.

Seeded issue/value catalogs are supplied to isolate semantic extraction from
open-ended ontology induction.

Fixture:
- `eval/v05/routed_semantic_extraction_v02_fixture.json`

Gold:
- `eval/v05/routed_semantic_extraction_v02_gold.json`

Runner:
- `scripts/run_v05_routed_semantic_extraction_v02.py`

## Coverage

Fresh events cover:

- source information that must not become source self stance;
- explicit self belief/acceptance;
- explicit self rejection;
- explicit unresolved stance;
- revision sent only to another recipient;
- relay revision relation;
- direct revision relation;
- repeated revision relation;
- observer-only world revision;
- same-value restatement that is not a revision;
- rumor that is not an explicit revision;
- third-party stance claim;
- DENY(new) + AFFIRM(old).

## Metrics

Primary:
- exact event-level semantic match.

Secondary:
- self-stance TP / FP / FN, precision, recall;
- revision-relation TP / FP / FN, precision, recall;
- repair count;
- extraction error count;
- failure risk classes;
- calls / input characters / output characters / provider wall time.

The artifact also preserves deterministic routed stance events for diagnosis.

False source self-stance or a missed/false revision relation is a mechanism
failure even if aggregate scores are otherwise high.

## Anti-overfitting boundary

- Gold and risk class never enter prompts.
- Fixture/gold digests are frozen before provider use.
- The package is consumed after first provider exposure.
- Do not repair against observed rows and rerun the same package as fresh
  evidence.
- No long-horizon capability run, external benchmark, owner-private example,
  cross-model run, training, publication or leaderboard claim is authorized.

A sufficiently clean result may justify a new independent end-to-end capability
package. Failure requires mechanism-level diagnosis and another fresh
extraction package.

**Gate: HCL_V05_ROUTED_SEMANTIC_EXTRACTION_V02_FROZEN_PREFLIGHT_NOT_RUN**
