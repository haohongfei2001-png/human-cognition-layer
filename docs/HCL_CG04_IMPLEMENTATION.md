# CG-04 implementation and limits

CG04-A–D implement an explicit optional operation in `hcl/v1/cg04.py` and the v1
router/context/answer path. Generic value/preference words do not activate it.

## Actual capability

`PreferenceCase` selects one actor and a caller scenario (role/context). Each
`PreferenceStatement` carries exact source, preferred/other value names,
authority, explicit boolean conditions and an optional local revision reference.
`ContextConditionClaim` carries an exact narrator statement about a condition
in that source scenario; it is a source claim, not live world truth.

The checker projects event and record cutoffs and reader/character/observer access
before serializing case state. It then checks each condition from visible claims:
met, not met, unknown or contested. Only source-supported statements matching
the selected role/context and satisfying all conditions are applicable. Third-
party reports remain attributed. Other roles/contexts remain separate.

Explicit same-scope later self revisions supersede only the referenced earlier
statement. A new opposed statement alone leaves both active. Opposed pairwise
claims or longer directed cycles are unresolved conflicts. No transitive
preference, global weights, winner or inconsistency judgment is inferred. Choice
events do not create or revise preferences. Missing conditions are unknown.

## Bounded input

The first typed validator and provider-free ordinary-text parser deliberately
share a small complete-line English grammar. Labels are case-sensitive single
tokens starting with a letter, with up to 32 letters/digits/underscores/hyphens.
No synonyms, free moral paraphrases, numeric preference weights or broad value
ontology are automatically interpreted. Example authorized source lines:

```text
Alice: As medic in fieldwork, I prefer safety over speed if rain is true.
Narrator: In fieldwork, rain is true.
Alice: As courier in deliveries, I prefer speed over safety.
Alice: As medic in fieldwork, I now prefer speed over safety instead of safety over speed.
Bob: In fieldwork, Alice as medic prefers privacy over speed.
```

Conditions may join up to four `key is true/false` clauses with `and`.
Narrator preference reports use the same third-person form as Bob's line but
remain explicit narrator source claims. Revisions require an unambiguous earlier
self statement with the named prior pair, same actor/role/context and strictly
earlier event time. Repeated indistinguishable earlier pairs fail closed rather
than being resolved by a hand-entered pointer. No condition persistence or
retrospective current-state inference occurs outside the declared source scenario.

Every typed quote must match the entire source record line, preventing a selected
substring inside a denial or quotation from changing its meaning. Ordinary prose
uses line order as synthetic time; calendar cutoffs require typed timed records.
Unknown non-preference lines remain source data without inferred preferences;
ambiguous preference/revision syntax yields an insufficient preparation. The
ordinary parser supplies reader-only records because prose alone does not establish
who received/understood a statement. Typed validated access metadata is needed
for character or observer use. This implementation does not claim unrestricted
natural-language preference understanding.

## API and receipts

```python
from hcl.v1 import CognitionRequest, HCLCognitionLayer

request = CognitionRequest(
    'Which explicit preference applies in this scenario?',
    target_actor='Alice',
    narrative='Alice: As medic in fieldwork, I prefer safety over speed.',
    preference_analysis=True,
    preference_role='medic',
    preference_context='fieldwork',
)
prepared = HCLCognitionLayer(lambda messages: 'bounded answer').prepare(request)
```

No gold or private value state is entered by the caller. The scenario is a
question parameter, not evidence that Alice occupies the role. Debug receipts
preserve the actual source preparation and final messages; the normal answer
adapter invokes the caller's model once, with zero extraction calls. Hidden
source statements, condition IDs and prior pointers do not enter final model
context. Oversized context closes to uncertainty.

`preference_checker_enabled=False` preserves identical policy, question,
source and projected case input while removing only `preferences.checked`.
That is the H-new boundary. CG-03's frozen package still rebuilds byte-identically
after this integration. The historical CG-03 registry entry was corrected from
its stale A-only status to its actual development-only RETAIN disposition.

This is provider-free correctness, not established external utility. Independent
validation and any new provider spending require their own later grant.
