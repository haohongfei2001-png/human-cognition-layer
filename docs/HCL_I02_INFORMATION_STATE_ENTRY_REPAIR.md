# I02 — ordinary information-state entry repair

**CAPABILITY_DELTA:** An ordinary search question over prose now causes HCL to
check an explicitly named person's reported observation of an object location.
The final model input carries the exact source quote and offsets, observer,
object, location and narrative-order boundary. A later movement in the reader's
source is kept separate from that person's observed location. The same question
and full source reach the final input when this new operation is ablated.

The [authored provider-free witness](../reports/HCL_I02_INFORMATION_STATE_WITNESS.json)
uses Bea's placement, Alice's explicit observation and Bea's later move. The
checked state reports Alice's last **source-reported observation** as the drawer
and the later source movement as the shelf; it does not say where Alice would
actually search. [Unit checks](../tests/test_v1_information_state.py) cover
exact spans, actor boundary, negation/pronoun refusal, narrative time, local
correction, existing actor-scope composition, unchanged ordinary input under
ablation and a fail-closed paid treatment gate. There are zero extraction calls.

This is a deliberately bounded repair. The complete-clause local grammar accepts
only named observers in direct seeing statements and explicit locations. It
does not bind pronouns, infer visibility from proximity, infer knowledge from
action, or promote source order to event chronology. A reported observation
does not establish private belief, current world location, or future behavior.
Source text stays available to the base model as data. The new capability is
**CORRECTNESS_ONLY_UNVALIDATED**, not evidence of independent efficacy.

The original I01 runtime freeze remains immutable. The
[explicit runtime amendment](../reports/HCL_I02_RUNTIME_AMENDMENT.json) pins
the changed HCL digest before confirmation. The
[post-repair native calibration preflight](../reports/HCL_I02_MUSR_NATIVE_TREATMENT_PREFLIGHT_AFTER_REPAIR.json)
still has **zero checked observations** on the exposed MuSR item. Routing now
selects the operation, but source-supported treatment is absent, so this item
remains **FAIL_TREATMENT_ABSENT_NO_PAID_COMPARISON**. No native answer, gold,
confirmation item or provider call was used to make this repair. No source,
question, output label or MuSR phrase was added to runtime rules.

Next: continue I02 source diversity and competent C/P/G qualification while
keeping the native MuSR paid gate closed. A general semantic extension would
need its own source-grounded positive and refusal evidence, a further disclosed
runtime amendment, and another provider-free preflight. Do not treat an active
router or an empty context as H treatment.
