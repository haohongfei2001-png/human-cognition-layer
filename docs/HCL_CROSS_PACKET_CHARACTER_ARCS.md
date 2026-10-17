# Explicit source-local cross-packet character arcs (v3)

Status: finite **INTEGRATED_OFFLINE** increment for M09 §4–5 → M11 §3,
S3 ∥ S4 and T12/T13/T27. It does not close M09, M11, S3 or S4, establish
natural-language extraction, infer personal identity, or certify a whole novel.
The original redesign scope and research exit conditions remain unchanged.

## Explicit candidate contract

Provider requests remain byte-for-byte `hcl-literature-context-1`, requesting
`hcl-literature-fragment-1`. A caller must explicitly select a candidate port
that returns `hcl-literature-fragment-3`. V1/v2 proposals, compiled outputs,
computation versions, answers and stored claims retain their existing protocol.
V3 uses the ordinary authenticated reading coordinator, compiler, operators,
verification, run/stream, durable cache and recovery, not a separate endpoint.

V3 retains every v1 field and adds `character_models` and
`character_contributions` (at most four of each per packet). Unlike v2, it does
not carry `character_arcs`. Mixed v1/v2/v3 readings are allowed, but a v2 arc
keeps its local identity and is never silently joined into a v3 model.

A declaration has exactly:

- `id`, `source_id`, `actor`: source-local identities, never display-name matching
- `frame`: exact `{fragment, id}` of a locally declared frame
- `assumptions`: active in its packet; `segment_ids`: original local evidence
- `model`: the existing single M09 model shape, with all additive collections
  listed below empty. Its mental identity, source-local agents, initial variables,
  assumptions, causal scaffold, finite mechanism library, interaction horizon,
  acknowledgement depth and search policy are declared once and cannot be
  overwritten by a later packet.

A contribution has `id`, `source_id`, `actor`, `frame`, `assumptions`,
`segment_ids`, an exact `declaration` reference (`fragment`, `id`), `bindings`,
and `additions`. All nested source references must belong to that actual packet
and original source. This is checked before durable compilation and again at
final verification; referencing a convenient span in another packet is rejected.
Dependency identifiers may reference explicitly declared shared records.
A declaration/contribution header cannot account for evidence by itself: its
source references must be covered by actual typed payload records.

`additions` contains these exact append-only collections:

- `mental`: `events`, `queries`, `plans`
- `interaction`: `utterances`, `acts`, `commitments`, `games`
- `affect`: `episodes`, `channels`
- `relationships`, `roles`, `identities`, `observations`, `forecasts`

A repeated record ID must have exactly the same content apart from accumulated
original provenance. No scalar overwrite, changed initial knowledge, mechanism
replacement, or implicit row update is supported. References must close before
computation. Neither the last packet nor each contribution repeats the whole
model, previous episodes, earlier observations or original text.

Every contributed episode and referenced observation/forecast episode has one
local binding of `episode_id`, `event` (`fragment`, `id`) and integer `at`.
Explicit repeat reports can point to the same earlier episode/event binding.
Composition requires agreement on source, actor and exact frame, active binding
and event assumptions, complete episode coverage, unique event bindings, and
one resolved same-source frame ancestry. The entire known event-order graph,
including later indirect constraints, must agree with declared episode times.
Missing declarations, conflicting times/rows, foreign sources/frames and
inactive cognitive-event hypotheses are rejected. Two actors with equal labels
remain separate models. No state is looked up across requests or sessions.

## Real composition and resource limits

The compiler assembles one ordinary M09 model per explicit declaration and runs
it once, after sorting by declared event time and stable local record identity.
Source/discourse order never assigns a clock. A later narration can revise the
reader's interpretation; a message affects an actor only at its explicitly
modeled receipt time. Historical identity reports remain distinct from current
inferences, roles and other-person attributions.

The original M03/M05/M07/M08/M09 compilers validate the complete assembled
model. V3 derives explicit `source_layers` from each layer's real record
provenance. M03 receives exactly its own source set; M07/M08/M09 retain the full
joined evidence set and validate their respective anchors. Thus an observation-,
interaction-, appraisal-, or identity-only later packet need not invent a
cognitive event, resend past events, or mislabel its evidence as unmodeled.
These deterministic layer bindings are independently rederived and compared in
the final certificate. Unanchored header evidence is rejected. Legacy v1/v2
compiler calls retain their original all-source coverage and bytes.

Original caps stay in force: at most 16 observations, 16 episodes,
8 plans, 8 mechanisms, 8 trajectory segments and 256 searched candidates, with
all existing subordinate bounds. There are at most 16 total character arcs per
composition, including legacy arcs. There is no per-packet reset of these caps.
Narrative work is charged first; each M09 run gets precisely the remaining
local allowance. Its actual frontier, unknown predictions and incomplete
comparison are preserved. Reading all supplied bytes still cannot certify
semantic completeness; unread packets yield no final joint claim.

V3 emits `explicit-narrative-episode-1` only after validating the explicit join.
Its M09 computation version is `s3-conditional-longitudinal-2`. A longitudinal
factor is scoped by original source, declared model, actor, the underlying M08 `episode_id` and
event time. M08 version/display IDs cannot create new factors: multiple versions/aliases
or conflicting times for one underlying episode in this finite join are rejected,
as are contradictory action reports
for one episode. Distinct explicitly declared underlying events stay independent.
New report IDs, different reporting contexts and later original
spans do not make the same explicit episode independent evidence. Separate
report provenance remains visible; conflicting action reports fail closed. Legacy M09
source-span factors and all v1/v2 bytes are unchanged. No new fit metric,
preference prior or heuristic score is introduced.

Mechanically grouping the same original segments into different packets yields
identical assembled M09 input and computation; only explicit packet provenance
changes. The witness also verifies this through actual run/stream delivery.
This does not claim invariance under changing semantic proposals or silently
identifying differently named events.

## Verification, answers and recovery

The certificate retains the exact declaration and contributing packet IDs,
source versions, source segments, explicit actor/frame/time bindings, condition
references, actual M09 values, resource usage and issues. Verification checks
original contiguous coverage, UTF-8 offsets and deterministic segment identities,
recompiles v3 packets against their actual originals, reassembles the join,
checks the entire clock graph and independently reruns M09 with the recorded
remaining allowance. Rehashing an altered program does not bypass provenance,
join, result or budget checks.

The ordinary answer consumes the resulting mechanisms, competing trajectories,
change points, evidence factors, original identity reports and qualified future
predictions, and identifies the explicit contribution set. Expression limits
still withhold complete claims. ACL withdrawal blocks cached delivery.

The real PR450 main predecessor is
`21cab9f3d3fd9c90262be7c0cc7ccb02bb0b24b0`, tree
`d30354d1c9a87b2785d392c706e206465a60210e`: 241 runtime Python files, hash
`38f8a0d032ec9fe00e791037a5614a4da8c3c3bf0f55940070294d68adda1495`.
An independent old-runtime process creates actual v2 completed, RETURNED,
computed, committed and UNKNOWN tasks under schemas 3 and 4. Controlled
side-copy migration preserves original inference/claim/answer bytes and provider
context, fences the old writer, reuses saved returns with zero resend, and
refuses UNKNOWN recovery. V3 tests also exercise interruptions after an early
return, the final return, computation and commit, plus UNKNOWN refusal.

Evidence entry points:

- `tests/test_unified_cross_packet_characters.py`
- `tests/test_unified_cross_packet_character_upgrade.py`
- `scripts/witness_unified_cross_packet_characters.py`
- The unchanged complete unified suite and previous 27 independent witnesses,
  plus this independent witness, run on the exact published PR head.

The new witness constructs its own original synthetic source and candidate
port, reads three character packets plus an unrelated packet, and verifies
late-counterevidence changes, removed-link ablation, unrelated invariance,
repeat-report factors, observation-only later evidence, grouping invariance, actual answer consumption, replay,
and exhausted-work frontiers. These are conditional offline computations, not
automatic extraction or a research-stage exit certificate. Provider calls and
spend remain zero; sealed content is never read.
