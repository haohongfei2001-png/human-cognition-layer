# HCL Communication Boundary Failure Adjudication Audit v0.1

Status: **PREDECLARED / OBSERVATIONAL / NO BEHAVIOR CHANGE**

## Purpose

Determine whether the three raw boundary failures are:
- runtime semantic failures;
- evaluator lexical/structural false negatives;
- fixture-design false negatives;
- or mixed.

## Frozen behavior

Runtime behavior remains exactly:
`da09c1fc8b82a538f6b0fdbbbe101e58b839241b`

No HCL prompt, schema, retry, fixture, or evaluator change is authorized while
the audit is open.

## Cases

Exactly:
- `cb02_direct_teacher`
- `cb06_unread_notice`
- `cb10_conflicting_sources`

Run exactly 4 independent state builds per case, 12 total.

No draft/checker/revision/final-answer calls.

Because these are repository-owned synthetic fixtures, complete normalized
state JSON may be persisted.

## Frozen adjudication criteria

### cb02_direct_teacher

Semantic conformance requires:
- target agent represented;
- SIMPLE;
- low;
- no decision-relevant missing bridge;
- state semantically records that the target knows the communicated start time.

Equivalent natural-language rendering of the time is allowed. Exact fixture
substring spelling is not itself a cognition-semantic requirement.

### cb06_unread_notice

Semantic conformance requires:
- target agent represented;
- state does not attribute knowledge of the unread deadline;
- EPISTEMIC is acceptable;
- low or medium uncertainty is acceptable.

Missing-bridge adjudication:
- zero missing bridges is semantically acceptable if the state treats the
  no-access path as explicitly established by "not opened + nobody told";
- a non-empty bridge is also acceptable if it accurately represents the absent
  information-transfer path;
- manufacturing uncertainty about whether the agent secretly received the
  information despite the explicit premise is not acceptable.

This adjudication follows frozen question-granularity and
no-manufactured-uncertainty rules.

### cb10_conflicting_sources

Semantic conformance requires:
- target agent represented in the agent-specific state, allowing a harmless
  case/whitespace/localized alias but not total omission;
- state records access to both conflicting communicated values;
- state does not claim the target knows one resolved inspection day;
- EPISTEMIC/high;
- unresolved conflict represented in hypotheses, missing bridges, uncertainty,
  or summary.

Total omission of the target from `agents` is a runtime state-fidelity defect,
not an evaluator false negative.

## Closure categories

For each raw failed case classify:
- `EVALUATOR_FALSE_NEGATIVE`
- `FIXTURE_DESIGN_FALSE_NEGATIVE`
- `RUNTIME_SEMANTIC_DEFECT`
- `MIXED_OR_UNSTABLE`

A case may be called a false negative only if at least 3/4 repeated states
satisfy the frozen semantic adjudication criteria.

If fewer than 3/4 do, treat the runtime behavior as unstable/defective.

## Methodological boundary

Even if all three raw failures adjudicate as false negatives, the original
boundary run remains raw 7/10. A subsequent gate decision must explicitly
distinguish raw from adjudicated results; it may not silently rewrite history.

No external benchmark evidence.
