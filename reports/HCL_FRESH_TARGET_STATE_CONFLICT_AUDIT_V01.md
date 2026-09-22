# HCL Fresh Target Synthetic State-Conflict Audit v0.1

Status: **PREDECLARED / OBSERVATIONAL / NO BEHAVIOR CHANGE**

## Trigger

Fresh causal diagnosis under the frozen generic answer-loop semantic repair
established:

- target sf07 state direct support: 8/8;
- target draft semantic success: 0/8;
- target first inversion at DRAFT: 8/8;
- A/B positive control sf02 final success: 8/8;
- EPISTEMIC positive control sf03 final success: 8/8.

The content-free artifact proves direct observed/knows support exists, but cannot
show whether other state fields simultaneously introduce contradictory or
misleading claims.

## Frozen behavior

Behavior anchor:
`4ab45463bbeacbe3eb8eaa91be7ec908130ce980`

No HCL runtime, prompt, schema, fixture, parser, or retry setting may change.

## Scope

State-builder observation only.

Fixtures:
- target: `sf07_exact_positive_signal`;
- control A/B: `sf02_direct_positive_schedule`;
- control EPISTEMIC: `sf03_direct_positive_location`.

Run exactly 8 independent state builds per fixture, 24 total.

Do not run:
- draft generation;
- checker;
- revision;
- final answer generation.

## Evidence

Because all three fixtures are repository-owned synthetic text and contain no
user/private data, this audit may persist the complete normalized state JSON.

For every state persist:
- fixture ID;
- repetition;
- full normalized state JSON;
- canonical state SHA-256;
- mode;
- uncertainty;
- hypothesis count;
- missing-bridge count;
- direct observed/knows support booleans for the fixture's target proposition.

Do not persist credentials or provider exception text.

## Fields to inspect after execution

For target and controls compare:

1. target-agent `observed`;
2. target-agent `knows`;
3. target-agent `believes`;
4. `explicit_facts`;
5. `hypotheses`;
6. `missing_bridges`;
7. `uncertainty.level` and `uncertainty.reason`;
8. `decision_relevant_summary`.

The closure must answer:

- Does the target state directly support the gold proposition in observed/knows?
- Does any other state field explicitly deny that support?
- Does any field introduce uncertainty about an already directly established
  proposition?
- Are those patterns target-specific or also present in controls?

## Interpretation

### STATE_INTERNAL_CONFLICT_ESTABLISHED

Use only if repeated target states contain direct observed/knows support and
also an explicit contradictory state claim about the same access/knowledge
proposition in hypotheses, missing bridges, uncertainty reason, summary, or
target-agent fields.

### NO_STATE_INTERNAL_CONFLICT_FOUND

Use if target states consistently contain direct support and no explicit
contradictory claim about the same proposition is found.

### MIXED_STATE_CONFLICT

Use if explicit contradiction appears in some but not most target repetitions.

### AUDIT_INCOMPLETE

Use if more than 2 target state builds fail or target-agent probing fails in
more than 2 target states.

The closure may cite concrete synthetic state excerpts because they contain no
private/user data, but should quote only the minimum needed to establish the
field relationship.

## No repair during audit

No answer-loop or state-layer change is authorized until this audit closes.

## External-evidence boundary

No external benchmark evidence.

## Claim boundary

This audit distinguishes internal state conflict from downstream answer-model
misweighting. It does not establish external efficacy.
