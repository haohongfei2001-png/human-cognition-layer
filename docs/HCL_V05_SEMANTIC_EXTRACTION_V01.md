# HCL v0.5 Semantic Extraction Pilot v0.1

Status: **FROZEN / PROVIDER RUN NOT STARTED**

## Question

Before testing v0.5 on another long-horizon capability task, can the provider
reliably extract event-local stance signals through the new bounded semantic
interface?

This pilot does not score final beliefs or actions. It evaluates only:

- AFFIRM(subject, issue, value)
- DENY(subject, issue, value)
- REVISION_EXPOSURE(subject, issue, new_value, prior_value)
- UNRESOLVED(subject, issue, value)
- and correct empty output when an event supports none of the above.

## Frozen fresh package

- 3 independent streams;
- 12 events each;
- 36 events total;
- 36 gold stance signals total;
- domains: meeting format, retention period, sensor mode;
- all domains, agents, event IDs, primary texts and values are distinct from the
  consumed v0.2 long-horizon package.

Fixture and gold are separate:

- `eval/v05/semantic_extraction_v01_fixture.json`
  - SHA-256: `afb653516b10a420eac0eb9cdcc6b740dc04728dc18cd4e07c5b693be8dfbd7a`
- `eval/v05/semantic_extraction_v01_gold.json`
  - SHA-256: `e2d638003b3cf2b0fdd8f742f9594777ec68caa89ec6dc024e86bf02c3d69964`

Provider-free exact-head evidence:
- v0.5 workflow `35999994122`: SUCCESS;
- v0.5 provider-free tests: **31 / 31**;
- extraction validate-only: PASS, **3 streams / 36 events / 36 gold signals**;
- HCL integration workflow `35999994106`: SUCCESS.

Each stream includes a predeclared issue/value catalog. The provider must reuse
those symbolic keys. This pilot therefore tests semantic stance extraction, not
open-ended ontology induction. Ontology induction remains a separate future
question.

## Coverage

The package includes:

- source information that is not a stance;
- explicit self-acceptance;
- explicit self-rejection;
- explicit unresolved stance;
- direct revision exposure;
- relay revision exposure;
- revision exposure to another agent only;
- third-party claims about someone else's stance;
- world/system revision visible to a different observer;
- rumor without an explicit revision relation;
- DENY(new) + AFFIRM(old) in one event;
- repeated revision confirmation;
- later explicit acceptance.

## Primary correctness

Primary evidence is exact event-level semantic correctness.

Secondary descriptive metrics:

- signal-level precision / recall;
- false-positive signals;
- missing signals;
- bounded repair count;
- extraction errors;
- failure type by predeclared risk class;
- calls, input/output characters and provider wall time.

No numeric score overrides a semantic boundary failure. In particular, false
self-stance attribution or false exposure without an information path is a
mechanism blocker even if aggregate accuracy is high.

## Anti-overfitting boundary

- Gold/risk class never enters prompts.
- Provider-free validation checks that every gold signal itself obeys the
  deterministic v0.5 actor/access rules.
- The 36 events are consumed after the first provider execution.
- Do not repair against observed rows and rerun this package as fresh evidence.
- No long-horizon capability run, external benchmark, owner-private example,
  cross-model run, training, publication or leaderboard claim is authorized by
  this pilot.

A clean or sufficiently interpretable extraction result may justify a new,
independent capability package. A failure requires mechanism-level diagnosis
and a new extraction package after repair.

**Gate: HCL_V05_SEMANTIC_EXTRACTION_V01_FROZEN_PREFLIGHT_PASS_PROVIDER_NOT_STARTED**
