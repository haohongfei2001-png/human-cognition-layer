# F01 — Episodic source retrieval

## CAPABILITY_DELTA

Ordinary multi-chapter speech can now be indexed and retrieved by person label,
reported proposition, explicit transition, source event and existing cognition
claim dependency. A bridge question retrieves both open/closed expressions and a
later transition with exact source anchors. A changed chapter is reindexed while
another chapter remains unchanged; hidden additions do not affect the visible
selection. Source summaries are exact extracts that can be fetched and checked.

`EpisodicIndex` reuses A02's literal parser and A01's versioned evidence/access
checks. Indexing never calls a provider. Character names remain source-local;
pronoun ambiguity and conditional prefixes remain explicit. Local offsets avoid
asking a model to compute source positions. Native operation dependency references
navigate back to source events; they do not import or assert that conclusion.

Selection is lexical and bounded. It is **PARTIAL_RETRIEVAL_NOT_EVIDENCE_CLOSURE**:
missing or truncated retrieval does not establish source absence or character
ignorance. Complete selected-conclusion support/challenge/alternative closure is
F03, not silently claimed here. F02 will add the separate narrative time axes.
The simplest alternative is scanning full authorized chapters. Later evaluation
must determine whether indexed selection helps reasoning under resource limits.

## Verification and limits

Thirteen targeted tests cover positive source recovery, opposing propositions,
person/proposition/transition/dependency indexes, hidden-source non-interference,
revocation and deletion, local version updates, ambiguous/conditional narration,
no cross-document alias, missing evidence, budgets and no provider calls. The
positive ordinary witness saves actual final messages in
`reports/HCL_WAVE_F01_WITNESS.json`. Full v1 and 176 historical tests run in
exact-head/main CI.

Default 512 indexed events (configurable up to 1024), 64k characters per chapter,
32 retrieved events maximum and explicit final context budget. These are
engineering limits, not efficacy evidence or a complete long-narrative capacity
claim. Current parser is bounded explicit English; unparsed prose is not evidence
of absence. Summaries are extractive; no new fact or psychological state is added.
State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.
Provider calls/spend zero. LongMemEval sealed. NEXT_READY: F02 narrative time axes.
