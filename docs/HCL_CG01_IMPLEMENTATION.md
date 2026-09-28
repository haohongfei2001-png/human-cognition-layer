# HCL-CG-01 implementation and provider-free boundary

Status: **PROVIDER-FREE IMPLEMENTED; EXTERNAL ORDINARY-TEXT PATH SIMPLIFIED**.
Correctness tests do not establish an external model improvement or a true
private motive. The one-time development [closure](../reports/HCL_CG01_EXTERNAL_DEVELOPMENT_CLOSURE.md)
found no attributable CG-01 increment.

## User-visible capability delta

For a bounded action explanation, HCL now tracks what the proposed explanation
would require the actor to know, want explicitly, or be able to choose at the
action time. A later explicit report that an actor first learned of a meeting
after it ended invalidates a deliberate, meeting-aware absence explanation. It
does not imply support for the meeting, lack of opposition, a changed belief, or
any unique alternative motive. Silence about knowledge stays `UNKNOWN`.

## Entry and perspective modes

`CognitionRequest` accepts `perspective_mode=PerspectiveMode.READER_ANALYSIS`,
`CHARACTER_PERSPECTIVE`, or `OBSERVER_ABOUT_TARGET`. The default is reader
analysis for an action-explanation question, a character view for explicit
knowledge/belief questions with a target, and an observer view when an observer
is supplied. A generic English `why` or Chinese `为什么` alone does not activate
person cognition. Explicitly scoped character and observer views only receive
evidence visible under v0.6 access rules. Narrator text never becomes character
knowledge simply because it describes that character.

## Ordinary text path

```python
from hcl.v1 import CognitionRequest, HCLCognitionLayer

layer = HCLCognitionLayer(lambda messages: 'The deliberate explanation is weakened.')
receipt = layer.answer(CognitionRequest(
    'Why did Alice miss the meeting?',
    narrative=("Alice missed Bob's meeting. Bob thought Alice stayed away to oppose him. "
               "Alice first learned about the meeting after it ended.")), debug=True)
assert receipt.prepared.context.explanations[1]['status'] == 'INVALIDATED'
```

The bounded deterministic preparer accepts up to 24 short narrative sentences.
Its current high-precision English grammar recognizes a named actor's attendance
or departure action, explicit first learning, stated prior knowledge, stated
opportunity constraints, and an observer's opposition attribution. It produces
at most three named candidates plus an open unknown candidate. It does not infer
unstated mental facts. Unrecognized text remains available as reader evidence,
and candidate preparation fails closed. Narrative sentence indexes use synthetic
timestamps **only for relative order**, not calendar facts; calendar cutoffs
require caller-supplied timed `EventRecord`s. Plain narrative is reader-only by
default because prose does not establish which character received it.

For a narrative outside that grammar, an optional `semantic_preparer` adapter can
be supplied to `HCLCognitionLayer`. It is called only when the request explicitly
sets `allow_semantic_preparation=True` and deterministic preparation found no
candidate. The adapter returns a typed `SemanticPreparation` with exact source
spans, candidates, facts, raw output, model ID, provider call count and cost.
Invalid output fails closed. Its full input/output stay in
`PreparedAnswer.preparation_receipt` for debug audit, never in the character or
observer final-model context. No provider adapter is bundled and no paid call is
made by the default path.

After the external run, a generic provider-free repair made the external
adapter align only unique whitespace variants to exact source spans, derive
event order from those spans, reject unanchored events and dependent claims,
and preserve paid extraction output/cost when validation fails. These changes
do not alter the consumed run or establish external utility.

The typed `check_explanations` and `revise_explanations` APIs accept validated
`ExplanationCandidate` and `ConditionFact` records for richer upstream semantic
preparation. They enforce event/source identity, action time, bounded actors and
events, perspective availability, explicit contradiction and local revision.
Third-party denials remain challenges; an explicit narrator report can
contradict a required condition. Earlier learning does not prove retained
knowledge. The status `CONSISTENT_CONDITIONAL` means requirements are supported,
not that the candidate is a true motive.

`answer(..., debug=True)` preserves the exact final-model messages and the
actual source rows, perspective mode/access state, candidates, condition states,
support/challenge/contradiction IDs, uncertainty and final context sent to the
model. Default preparation records zero extraction calls; the answer adapter is
called once. The answer adapter's provider cost is unknown and caller-managed. Ordinary
answers receive a policy to keep internal status words out of user-facing text.

## First-round bounds and limits

At most 4 actors, 24 events, 3 named candidates and 2 update points. No new
database, personality profile, trust score, relationship graph, emotion ontology
or rational-choice optimizer. This deterministic preparer covers a small explicit
grammar; it is not general narrative understanding. The final answer model must
still obey the evidence policy. The completed C/P/G/H/H-new comparison showed
no end-to-end gain: semantic preparation failed for all four cases and H/H-new
were identical. Prefer a simple prompt for this ordinary-text task class;
keep the checker optional for source-validated typed evidence.
