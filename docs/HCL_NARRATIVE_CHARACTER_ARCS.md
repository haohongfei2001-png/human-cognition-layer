# M09 → M11: explicitly bound, packet-local character readings

This increment consumes the existing M09 finite longitudinal operator inside
ordinary `literature.analyze`. It does not change M04's search language or infer
preferences, cross-source identities, unbounded temporal semantics, character
truth, narrator authority or aesthetic merit. Full M09/M11/S4 remain open.

## Explicit opt-in contract

The existing provider context remains byte-for-byte `hcl-literature-context-1`
and continues to request `hcl-literature-fragment-1`. This increment does **not**
claim automatic production or extraction of new character bindings. A caller's
explicit candidate port may instead return `hcl-literature-fragment-2`, with all
v1 fields and a required `character_arcs` list. This uses the same authenticated
entry, durable reading coordinator, original packet scope, compiler, execution,
verification, stream and answer path. Advertising v2 in provider requests is a
separate future versioned protocol change.

Each arc has exactly `id`, `source_id`, `actor`, `assumptions`, `bindings`, `task`.
The task is a single-model `hcl-relationship-candidates-1` proposal, compiled
against only the named original source's spans in this packet. Every agent's
source must agree. The actor must be the actual actor of all observation/forecast
episodes. Each required episode appears once in `bindings`, with exactly
`episode_id`, `event` (`fragment`, `id`) and integer `at`. This integer must equal
the existing M09 episode time; discourse position supplies no time. Event IDs
are not merged by equal labels. Repeated reports of one episode require no new
binding and retain M09's existing correlated-factor identity.

Bound events must belong to this packet and one explicitly resolved frame; all
frame ancestry, event and episode evidence must belong to the declared original
source. Arc and event assumptions must be active, and remain conditional in
final delivery. The host checks known event-clock order paths between bound
events, including indirect paths and orders declared in another packet. A
contradiction is rejected rather than silently changing either clock.

At most four arcs per packet, sixteen per composition, and 32 episode bindings
per arc are accepted. These are explicit finite compilation bounds. Each arc
retains its own packet-local identity. Same actor or arc labels in other packets
never combine M09 models. Cross-packet character assembly remains explicitly
uncomputed. Original event chronology, historical self-identifications and
other-attributions remain unchanged; rewrite/reorder variants are not evidence.

## Computation, delivery and resources

The narrative operator first uses its existing finite temporal/form/comparison
allowance, then passes the exact remaining local budget to each actual
`RelationshipModelOperator`. Existing shared M03/M05/M07/M08 calculations,
mechanism parameters, zero-change alternatives, dynamic trajectories, fit and
complexity Pareto comparisons, factor deduplication and hypothetical predictions
are reused without new scoring semantics. Unfinished search retains its actual
frontier and cannot claim globally preferred change points.

The v2 certificate contains actual M09 results, original source versions,
explicit event/episode/time and actor bindings, assumptions, resource usage and
issues. Verification recompiles each original packet-local proposal, checks the
join and whole known clock graph, and independently reexecutes M09 with the
original remaining allowance. Metadata, nested program, predicted matrix,
trajectory, source, rule version and work changes cannot be substituted for
verified consumption.

Final `HCL.run`/stream delivery consumes these fields: mechanism parameters and
trajectory segments, change points, competing Pareto fits and complexity,
evidence factors, historical identity reports, qualified future predictions and
frontiers. Binding assumptions are visible. Existing expression budgets remain
in force: a too-small delivery allowance does not publish a complete character
claim. Neither full byte coverage nor a complete finite library search establishes
whole-work semantic completeness.

## Compatibility and evidence

V1 candidates keep their original compiled fields, computation version and
answer text; no empty v2 field is injected. The exact PR449 main predecessor
`04d23b02dcd3f0485dda4d5a0c6ee190ae3352a5` (tree
`0728463342d638af0904baf6fc2eed3714d6b1c9`, 239 runtime Python files, hash
`0bd755b62f53161a473336907b53ebf6b891f2e5ae7bcb3b069c05797c0db923`)
is explicitly supported. A separate real predecessor process creates completed,
RETURNED, UNKNOWN, computed and committed narrative tasks under schemas 3 and 4.
The tests check original inference and claim bytes, zero provider resend,
owner-authorized recovery, old-writer fencing and UNKNOWN refusal.

The new witness uses an independent synthetic source/candidate builder and
real `HCL.stream`/`run_sync`: late counterevidence changes the Pareto trajectories
and final answer, irrelevant material leaves the arc unchanged, repeated reports
retain one evidence factor, and exhausted work never establishes global
comparison. The tests also cover malformed binding, clock conflict, nested
certificate forgery, expression limits and current v2 restart seams. These are
provider-free conditional fixtures, not natural-language extraction results or
research exit certificates.
