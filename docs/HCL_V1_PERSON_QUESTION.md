# Ordinary questions for existing person/context preparation

Failure: callers had to choose operation flags and scenario fields before ordinary
composition ran. A simple alternative is the base model plus evidence-bounded
policy. The small opt-in entrypoint selects existing preparations from complete
explicit question semantics, never correct mental state. Simplify it if routing
cannot preserve source/actor/access boundaries or it adds no utility over that
simpler path in a future separately authorized comparison.

**CAPABILITY_DELTA:** an ordinary question and ordinary source now produce retained
belief and existing local-concept state plus a scoped comparison in one actual
final input, without manually constructing mental states or pipeline operations.

```
from hcl.v1 import HCLCognitionLayer, answer_person_context
layer = HCLCognitionLayer(existing_answer_adapter)
answer = answer_person_context(layer,
    "Compare Alice's belief and meaning of fair for proposal in team.",
    ordinary_source)
```

Supported finite question grammar (named labels are source/task labels):

- `Explain Alice's belief.` / `What does Alice believe?` / `解释 Alice 的信念。`
- `Interpret Alice's meaning of fair for proposal in team.`
- `Compare Alice's belief and meaning of fair for proposal in team.`
- `比较 Alice 在 team 中对 proposal 是否 fair 的信念与词义标准。`

`prepare_person_context` returns actual messages, prepared state and receipts
without a model call. `answer_person_context` uses the existing answer adapter
exactly once, with optional `debug=True`. No extraction provider/API is scheduled.
The existing ordinary-source grammar remains bounded; this is not unrestricted
language understanding. A question supplies actor/context/item/term scope only,
never belief, correct meaning, gold or premise truth. Only source assertions
create state. CG05 is still optional IMPLEMENTED_UNVALIDATED, not a retained core
upgrade. No new capability candidate is introduced.

Default perspective is reader analysis. Private views require an explicit
`perspective_mode`, optional named observer, and `narrative_access=True` to use
exact narrated exposure preparation. Missing access remains unknown. Ambiguous,
embedded, mixed-actor or unsupported queries refuse structured analysis; only
reader fallback may preserve authorized raw narrative. Private fallback never
imports that reader source. Oversized contexts drop whole analysis. Injected
persistent historical runtimes are rejected; each request is isolated.

Question and source bounds, actor/attribution/perspective/uncertainty, actual single
model input and fallback behavior are checked by12 new provider-free tests. Default
CG04/05 frozen inputs remain identical. This is engineering correctness only;
no new external utility claim or historical evidence upgrade. Calls/spend0/USD0,
LongMemEval SEALED, CG04/05 deferred packages unchanged.


## Explicit source-order snapshots

Failure: a whole-narrative current view cannot answer what was supported before a
later belief/meaning revision or later exposure. The simple alternative is a
caller-selected source prefix. The entrypoint now checks that selection and routes
only the selected source through existing preparation; no new semantic module.
**CAPABILITY_DELTA:** HCL can answer an earlier explicit person/context question
while preserving earlier belief/meaning/access and excluding later evidence.

Use `as_of_statement=3`, or `At statement 3, Compare Alice's belief and meaning of
fair for proposal in team.`, or `截至第 3 条陈述，比较 Alice 在 team 中对 proposal
是否 fair 的信念与词义标准。`. A statement is one nonblank source line; limits1–24.
This is explicit authorized source order, not a calendar timestamp or independently
verified delivery time. The final policy and source scope say so.

Selection occurs before any belief/concept/access preparation. Only prefix text
enters semantic work and actual final messages. Receipt stores original/selected
source hashes and selected statement numbers; the original/future-source digest
is audit-only, absent from the model input. A later access cue cannot grant an
earlier private view. Future malformed semantic lines cannot poison a valid early
snapshot. Missing evidence is unknown, not ignorance, refusal or uncertainty of
the character.

Invalid, nested, conflicting or out-of-range source scopes refuse structured
analysis and do not provide the whole reader source as fallback. An unsupported
question inside a valid scope may keep only that reader prefix. Private fallback
still omits reader text. State plus explicit scope metadata counts toward the
context budget; whole-state refusal drops all operations/comparison together.

Ten provider-free tests cover actual single-call input, early revisions/exposure,
future malformed source, source hashes, Chinese prefix, strict scope refusal and
budget. Engineering correctness only; all prior evidence dispositions and frozen
packages remain unchanged, no paid calls or third candidate.
