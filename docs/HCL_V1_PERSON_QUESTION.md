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


## Retained belief and conditional responsibility

Failure: ordinary question selection did not compose retained belief with CG03;
an incidental predicate such as `I believe gate is planned` could also become a
stated-intention factor through CG03's legacy keyword path. The simple alternative
is the base evidence-bounded policy. The entrypoint now selects existing
preparations; CG03 excludes belief/preference/meaning/property source from factor
or action/outcome anchoring. Explicit negative control (`could not have stopped`)
is grounded as a negative control claim, independently of other factors.
**CAPABILITY_DELTA:** HCL can prepare an expressed belief and a caller-dependent
responsibility explanation together, without treating a belief, concept property,
outcome or later learning as action-time knowledge/control/intention/moral truth.

Questions: `Explain Alice's belief and conditional responsibility.`,
`解释 Alice 的信念与条件责任依据。`, or
`Explain Alice's conditional responsibility.`. Supply existing typed
`responsibility_premises=(NarrativePremise(...),)`; these are explicit caller
normative requirements, not correct mental state. Missing premises refuse the
structured responsibility conclusion, never import a model's moral view.

Default `premise_scope='ALL_SOURCE'` preserves the historical CG03 source contract.
An explicit `premise_scope='FOCAL_EPISODE'` instead binds each caller rule to its
focal action/outcome and the source claims for its required factors. This retains
all required factor witnesses and their actor/time/access checks, while unrelated
belief lines, factors and delivery-cue rows do not become normative evidence.
It never implies the actor accepts the rule or that the rule is moral truth.
The lower-level `responsibility_premise_scope` request flag exposes the same
explicit choice on the existing ordinary CG03 path. Private views still require
source-grounded narrated access; hidden relevant basis refuses the case, hidden
unrelated factors stay unknown. Source-order snapshots propagate the caller rule
and scope, excluding future action/outcome/factor/exposure state.

Thirteen new provider-free tests cover actual private/reader model input, actor/
source classes, indirect vs direct intention, explicit knowledge, negative control,
later learning, source-order, missing premises and selective visible rule basis.
All current default CG03 cases are identical to the consumed frozen package;
CG04/05 inputs/helpers remain identical. This is prospective engineering
correctness, not a rerun or new external efficacy. Existing CG03 stays development-
only RETAIN; v0.6 retains its historical bounded evidence. No new candidate,
provider call, grant/trigger, ontology or LongMemEval access.


## Multiple authorized source records / local revision

Failure: a single ordinary narrative could not preserve before/after supported
state across distinct source records, and concatenation could silently impose an
order or access basis. The simple alternative is separate evidence-bounded source
answers. This integration reuses the same existing ordinary preparations for each
explicit source path and combines their complete snapshots into one answer input.
**CAPABILITY_DELTA:** one question can explain source-local belief/meaning/access/
conditional-responsibility changes while keeping incomparable branches unresolved.

```python
from hcl.v1 import AuthorizedSourceRecord, prepare_source_revision
prepared = prepare_source_revision(layer,
    "Across sources, Explain Alice's belief.",
    (AuthorizedSourceRecord('first', first_text, 'CALLER_AUTHORIZED'),
     AuthorizedSourceRecord('revision', revision_text, 'CALLER_AUTHORIZED', 'first')))
```

Use `Across sources, <supported ordinary question>` or
`按来源变化，<supported Chinese question>`. `answer_source_revision` uses the
existing answer adapter once. No source library is searched and no extraction
provider is called. Bounds:2–4 distinct records,24 lines/16,000 source characters
in total; individual mechanisms retain their narrower limits.

`CALLER_AUTHORIZED` is explicit permission for this request to process supplied
text, not reliability, world truth, private-state gold or license certification.
Every record requires an explicit identity. `after_source_id` must name an earlier
supplied record; it declares one source-order path, not calendar or verified
receipt time. Multiple roots/branches remain incomparable, with no merged state.
Each snapshot starts fresh with only its own declared path; later material and
exposure cannot backfill earlier views. Private views retain existing explicit
narrated access requirements. A later visible exposure can support only the later
view, not rewrite the earlier snapshot.

Final input preserves all checked state in its existing lossless encoding, plus
exact per-operation event→source-record/statement bindings. Explicit local belief
or meaning revisions reuse existing scoped supersession. Opposite visible self
assertions from distinct sources without explicit revision are marked unresolved
source conflict; the retained runtime assertion is not an automatic resolution.
Property/factor conflicts keep existing checker decisions. Hidden text and its
binding do not enter private inputs. Raw record hashes are audited in receipts,
not evidence of truth. Invalid authority/identity/order, nested scope or mixed
statement scope refuses all-source/library fallback. Total snapshot/provenance
budget overflow drops every snapshot together.

Ten provider-free tests and actual before/after/private/conflict message receipts
exercise the new path. This is integration correctness, not external efficacy.
CG04/05 remain the only two implemented-unvalidated/deferred candidates; no paid
call, new grant/trigger or LongMemEval access.


## Two-participant source-bounded contrast

Failure: composing actor-local state does not itself justify comparing two minds;
one participant's exposure/self-report could be copied to the other. A simple
alternative is two evidence-bounded answers. This integration independently
projects retained v0.6 belief/perspective for two explicitly named participants,
then transmits both complete source-bounded states to one final answer.
**CAPABILITY_DELTA:** an ordinary question can compare supported participant views
while exposing distinct public/nonpublic evidence, self-report and unknown state.

`prepare_perspective_contrast(layer, "Contrast Alice and Bob's views of proposal
as fair in team.", ordinary_source)` or `比较 Alice 与 Bob 在 team 中对 proposal
是否 fair 的视角。`; `answer_perspective_contrast` calls the existing adapter once.
Default views are independent character projections, requiring existing exact
narrated exposure syntax. `observer_actor='Carol'` restricts each view to what
Carol can establish; unauthorized reader text is never a fallback. Typed raw
EventRecords can preserve explicit upstream public/access and event/record-time
metadata, with no caller mental-state gold. Public declarations are not verified
world truth or delivery receipts. Ordinary text does not invent public status.

Shared available source IDs mean access basis, not shared acceptance. The relation
compares only direct self-report stances about the exact context/item/term; narrator
or third-party estimates remain reported source evidence. Unknown system evidence
is not character uncertainty. Explicit self uncertainty remains distinct from
missing evidence. Differences imply no deception, irrationality, relationship
state, motive or moral blame. Statement-prefix selection occurs before both views;
typed event/record cutoffs exclude later content separately. Invalid actor/scope/
metadata refuses reader fallback. Total context budget drops both views together.

Ten meaningful tests and actual private/public/observer input receipts exercise
these boundaries; all prior frozen/default inputs remain compatible. Integration
correctness only; no third candidate, provider execution or historical upgrade.
