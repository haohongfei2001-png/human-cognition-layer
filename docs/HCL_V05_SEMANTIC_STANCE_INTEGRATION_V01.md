# HCL v0.5 Semantic Stance Integration v0.1

Status: **PROVIDER-FREE INTEGRATION CANDIDATE**

## Purpose

Connect raw human-language events to the deterministic v0.5 current-stance
state machine without returning control of current-state inference to the LLM.

The semantic model is restricted to event-local extraction. It may propose only:

- AFFIRM(subject, issue, value)
- DENY(subject, issue, value)
- REVISION_EXPOSURE(subject, issue, new_value, prior_value)
- UNRESOLVED(subject, issue, value)

It may not output a final/current belief summary.

## Deterministic trust boundary

The extractor output is validated before it can affect state.

- AFFIRM / DENY / UNRESOLVED normally require the subject to be the event actor.
- REVISION_EXPOSURE requires an actual access path in the event.
- A correction sent only to another agent cannot become target exposure.
- World/system truth not delivered to the target cannot become target stance.
- Receipt cannot become acceptance.
- Revision new/old values must differ.
- Duplicate semantic events are deduplicated deterministically.
- Invalid extraction gets at most one bounded semantic repair.
- Repeated invalid extraction fails strictly rather than inventing state.

Raw evidence is canonical: the runtime stores the immutable raw event before
semantic extraction. A semantic/backend failure therefore cannot erase the
source event or fabricate a derived stance. Failed events retain an explicit
semantic-failure record and may be reprocessed deliberately; ordinary duplicate
ingest does not silently retry them.

The runtime is idempotent by raw event ID and rejects changed-content reuse of an
existing ID.

## Issue/value identity

The semantic extractor receives a catalog of issue/value keys already observed
in prior stance events and is instructed to reuse matching keys exactly.

This integration intentionally avoids text-overlap heuristics for issue
equivalence. The model proposes symbolic identity; deterministic code validates
event access and state transitions.

Future work may require stronger ontology identity if fresh evidence shows key
fragmentation. That question is not answered by v0.2 consumed rows.

## Evidence boundary

This package uses only provider-free scripted backends and new generic examples.

It does not rerun v0.2, call a provider, consume a new capability fixture, use
owner-private research examples, train a model, or make a capability claim.

**Gate: HCL_V05_SEMANTIC_STANCE_INTEGRATION_V01_PROVIDER_FREE**
