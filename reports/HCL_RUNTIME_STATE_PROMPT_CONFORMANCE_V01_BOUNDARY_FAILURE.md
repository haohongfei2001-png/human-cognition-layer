# HCL Runtime State-Prompt Conformance v0.1 — Boundary Failure Record

## Canonical boundary run

- run: `35720589183`
- terminal result: **FAILURE**
- zero-provider preflight: **PASS**
- fresh boundary execution: **10 / 10 completed**
- runtime exceptions: **0**
- raw strict pass: **7 / 10**
- artifact: `10690883430`
- digest:
  `sha256:90b03b563fecf8ac5561d6a9bee1d961337a9f95a39a89667ef9638f2b056693`

## Raw failed cases

### cb02_direct_teacher

Passed:
- schema;
- agent identity;
- SIMPLE mode;
- low uncertainty;
- zero missing bridges.

Failed only:
- lexical `knows_all` match for the frozen time expression.

This may be a semantic-equivalent serialization false negative.

### cb06_unread_notice

Passed:
- schema;
- target agent identity;
- EPISTEMIC mode;
- low uncertainty;
- target does not know the forbidden deadline.

Failed only:
- fixture required a non-empty `missing_bridges` list, but runtime state
  produced zero missing bridges.

The text explicitly establishes that the agent never opened the notice and
nobody told her. Under frozen question-granularity semantics, an absent evidence
path may already be decision-relevantly settled rather than "missing".

This is a potential fixture-design false negative and requires adjudication
against the frozen semantic contract.

### cb10_conflicting_sources

Passed:
- schema;
- EPISTEMIC mode;
- high uncertainty;
- non-empty missing bridge.

Failed only:
- evaluator did not find a target agent key matching `Chen`.

This may be a harmless serialization alias or a real loss of agent-specific
state. Full-state inspection is required.

## Boundary decision

The predeclared strict raw gate failed and remains historical evidence.

Do not:
- relabel this run as 10/10;
- rerun it until green;
- change runtime behavior from these three summary flags alone.

Next work is a bounded full-state adjudication audit of the three failed
repository-owned synthetic cases under the exact frozen repair candidate.
