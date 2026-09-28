# Explicit narrated source-access integration

## CAPABILITY_DELTA

Character/observer analysis can now use ordinary-text preferences and local concept
readings when the authorized narration explicitly records delivery of those source
statements. It no longer always requires hand-entered EventRecord access metadata.
A missing or ambiguous delivery claim still yields unknown, not false knowledge.
This extends preparation for existing operations, not a third capability candidate.

Opt in with `narrative_access=True` on an existing CG03/04/05 ordinary request.
One bounded exact-source clause is supported:

```
Alice: In team, by fair I mean consent is true.
Narrator: Alice and Bob heard the previous statement.
Narrator: In team, proposal has consent true.
Narrator: Alice heard the previous statement.
```

The narrator clause anchors the immediately preceding source event, at most four
named receivers, and its own event/record time. This is a **reported exposure
claim**, not a verified communication receipt, belief acceptance, understanding,
sincerity or world truth. The emitted statement's source actor stays unchanged;
source actor and explicitly named recipients use the existing v0.6 access rule.
No generic narrator facts, unmentioned statements, negative/embedded/ambiguous
clauses or chained cues gain access. Default parsing remains reader-only where
it was reader-only; frozen default inputs are unchanged.

A later access basis cannot grant access to an earlier event/record cutoff. Reuse
of parsed events in typed calls validates exact cue text, actor list, adjacency,
source reference and timestamps; receiver/public promotion fails. Reader raw
source remains visible in the reader scope even when private access is unavailable.
Private final context excludes narrator access-basis quotations and hidden sources;
research preparation output preserves authorized source anchors for audit.

Existing composition now accepts ordinary character/observer input only when all
operations opt into this same grounded access path and share source/actor/time/view.
Without this option, private composition still needs validated typed EventRecords.
CG03's requirement that premise/action/outcome basis be visible is retained; a
partially delivered narrative may leave the responsibility operation unresolved.
No new moral inference or weakening of normative-source prerequisites.

Twelve tests cover actual ordinary character composition, unknown/other-receiver
conditions, observer boundaries, malformed/negated/chained clauses, earlier event
and record cutoffs, forged anchors, receiver/public promotion, idempotent scope,
reader preservation and invalid flags. Zero provider/extraction calls. This is
provider-free correctness, not external utility or independent evidence.
