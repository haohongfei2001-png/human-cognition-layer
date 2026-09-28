# B02 — Differentiated communication and access updates

**CAPABILITY_DELTA:** one reported exchange yields different actual semantic and
final-model inputs for three people. Mira has her own expression; Noor has an
explicit receipt; Kai's missed message does not enter Kai's input. An explicitly
later receipt adds Kai's access without changing the earlier snapshot or
manufacturing belief, comprehension or acceptance.

`CommunicationScene(ordinary_narrative).view(actor, through_line=...)` compiles
source-reported information paths before any semantic backend is called.
`view.semantic(question, backend=...)` and `view.epistemic(question)` feed A02/B01
with only accessible text. The retained v0.6 `event_accessible_to` policy checks
projected events; original view selection is not performed by exposing hidden
text to a model and deleting fields afterwards.

Supported source cues distinguish publicly available, privately addressed,
heard/read, missed/did-not-hear/read and explicit later receipt. Sending to a
recipient does not prove receipt. Positive and negative reports about the same
contact remain conflicting unless an explicit later receipt supplies a new path.
Conflict withholds the disputed content; it does not assert forgetting or private
uncertainty. Named “last statement” and adjacent “previous statement” references
must resolve exactly. Unsupported/hypothetical or ambiguous audience clauses fail
closed, without inventing an audience.

Visible event identity/order is computed only from the selected material. Changing
or inserting unrelated hidden content does not change visible events or actual
backend/final inputs. Source-line cutoffs select the prefix before access parsing;
later statements/receipts cannot backfill an earlier view. Synthetic v0.6 event
timestamps are marked visible-source-order only; calendar/actual receipt dates
remain unknown. `access_audit` is the analyst's authorizer audit, not part of the
character model input, and contains no hidden message body. It can distinguish
unknown, availability-only, addressing-only, non-receipt and conflict.

[Reproducer](../scripts/witness_communication_views.py) /
[receipt](../reports/HCL_WAVE_B02_WITNESS.json) saves all three actual final inputs
and Kai's later update. Twelve tests cover positive three-person divergence,
private addressing/read receipt, public availability, missing/conflicting access,
explicit later receipt, ordinary-input composition with B01, hidden-content and
hidden-insertion non-interference, future-prefix isolation, reference ambiguity
and empty snapshots with zero backend calls. Full v1 + historical regression and
all prior witnesses remain exact-head/main CI requirements.

**State:** CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN.
No real provider calls/spend. The access grammar is bounded, one clear statement or
cue per line, at most 80 lines/eight actors. These are engineering capacity limits,
not broad language efficacy. Narrated receipt is still source evidence, not proof
of truth or understanding. Historical dispositions and sealed data are unchanged.
**NEXT_READY: B03** character revision versus analyst revision and late disclosure.
