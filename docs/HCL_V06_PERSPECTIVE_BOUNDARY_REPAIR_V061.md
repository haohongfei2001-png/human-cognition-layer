# HCL v0.6.1 Perspective Boundary Repair

Status: **IMPLEMENTED CANDIDATE / PROVIDER-FREE CERTIFICATION REQUIRED**

## Purpose

v0.6.1 repairs two abstract cognition failures exposed by the consumed FANToM
development utility run without writing benchmark-specific answer rules.

The repairs are benchmark-independent and validated first on unrelated
provider-free fixtures.

## Repair A — participant presence evidence floor

Problem:
an LLM that sees the full participant roster can accidentally assign a
participant access to turns that occurred before any evidence that the
participant was present.

Rule:
- no participant receives an utterance earlier than the first evidence of that
  participant's presence;
- the participant's own first speaking turn establishes presence;
- a conservative direct vocative may establish presence before the first reply;
- model-produced listener assignments earlier than that evidence floor are
  removed deterministically.

This post-processing is independent of any benchmark question or answer.

## Repair B — precise knowledge requires precise support

Problem:
a character may hear a later summary that overlaps with a topic while still
missing material details required by a precise compound fact.

Rule:
- related topic overlap is not equivalent to precise knowledge;
- partial summaries do not establish a more detailed compound proposition;
- downstream perspective reasoning must require support for every material
  detail before treating precise information as known.

This rule is represented in HCL perspective semantic policy and the downstream
answer contract.

## Auditability

Future C/P/D artifacts store a redacted access map:
- turn index;
- speaker;
- listener IDs.

No raw conversation, question or gold text is added to that map.

This allows failures to be separated into:
- access-state construction;
- perspective-state projection;
- downstream reasoning.

## Evidence discipline

The consumed v0.6 development conversations are not rerun to create a new
"improved score" after these repairs.

They remain diagnostic evidence only.

v0.6.1 correctness is established first through independent synthetic fixtures.
Any later external efficacy claim requires a fresh disjoint selection.

## Files

- `hcl/v06/conversation.py`
- `hcl/v06/runtime.py`
- `scripts/run_v06_fantom_cpd_v01.py`
- `tests/test_v06_conversation_adapter.py`
- `tests/test_v06_perspective_belief_runtime.py`
- `tests/test_v06_fantom_cpd_v01.py`

**Current gate: HCL_V06_V061_PERSPECTIVE_BOUNDARY_REPAIR_PROVIDER_FREE_CERTIFICATION**
