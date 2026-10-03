# A02 structural scope isolation

A02 now uses one offset-preserving structural view to classify candidate
containment and eligible narration cues. A quoted character cannot change the
outer scene by saying “In reality”; recognized speaker labels remain labels
even when named Hypothetically or In Reality. A delimiter inside a closed fence cannot
corrupt a later report. Explicit unembedded `Narrator:` cues use the existing
scene grammar, including source-ordered resumption and later qualifications.
The existing line-start scene-prefix vocabulary now persists as an eligible outer
cue, closing the original Narrator-prefixed hypothetical-scene blocker.

Speech candidates and source payloads remain available at their original Unicode
character offsets. Structural `CONDITIONAL_OR_EMBEDDED` is an ambiguity category:
it does not establish a hypothetical world, negate an actual transcript, or
certify semantic correctness. Backend proposals cannot override the locally
derived scope. Original raw responses and candidate schema remain unchanged.

## Bounded grammar and review corrections

The supported structural grammar is double quotation, nested square brackets,
and line-bounded backtick fences with at least three backticks. A closing fence
requires at least its opener's length and whitespace only after the ticks. Fence
contents cannot change external quote/bracket state. Existing colon/script actor
bodies remain opaque units; unclosed admitted containers continue to EOF.
Additional delimiter/escape conventions and an actual-transcript source-frame
admission contract remain separate work. Colon headings that also satisfy the
existing actor-name grammar, including `Hypothetically:` and `Hypothetical Scene:`,
remain ambiguous; an empty heading can consume the following line without
emitting its nested speaker. Explicit
`Narrator:` forms are covered; no special actor-name exception is introduced.

Actual cues clear only earlier qualifications. Ending a container does not clear
an active hypothetical scene. Masking cannot manufacture a cue across a removed
qualification; rejection of such a cue cannot hide a following valid cue that
shares its terminal period as a boundary. Four concrete review regressions were
preserved as paired positive/negative tests before freezing the runtime.

The unchanged 12-case proposal and nine boundary cases remain engineering
fixtures with their original baseline observations and hashes. They are not
semantic/model-selection gold or efficacy evaluation material.

## Recovery and immutable evidence

The earlier local candidate was lost in a workspace rollback. Its runtime was
reconstructed exactly and verified by reproducing SHA256
`847b332d2c50a2bf4488f0eadf53176464993a8c416a1fb1e1542a9c5e95f5df`
when evaluated with its old B04 file hash. The recovered candidate is based on
PR355 main `a588cbc45400bea5e51078d1447a48f437972033`; current B04 is unchanged.
The recovery checkpoint report records the facts known at local `db3e6d3`.
A subsequent reviewed bounded runtime delta adds persistent existing-prefix cues
and shares their qualified state with narrator-report suspension;
its paired controls and fresh validation are recorded separately.

The new amendment preserves all108 existing historical pins and adds five pins
for adopted B04 evidence and the two scope fixtures. Replacing only semantic.py's
file hash restores the preceding runtime. A byte guard rejects changes outside
the four reviewed scope functions. Historical plans, grants, receipts, replay
runtimes and negative answers remain immutable.

Dependency-install polling initially returned “automatic approval review was
cancelled.” Read-only inspection found no process or installed packages. One
subsequently authorized restoration of the same pinned official-registry packages
succeeded; no alternate package route was used. This involved no provider call.

## Integration limits

This batch adds no adapter. Both original fenced and Narrator-hypothetical copy cues now receive embedded
A02 scope. B04 still consumes both incorrectly because its copy-cue selection
needs its own exact-span eligibility check. The separate recheck report retains
both consumer failures; the original historical blocker report is unchanged.
The original fenced C04 emotion case now returns no reported emotion.
The native B04 message/36,000-byte transport boundary remains separate. C04 and
other remaining integrations depend on source-relative scope and complete usable
state, not adapter-count targets. A validated live final answer and efficacy
remain unproved. All paid grants are closed with zero new authority.
