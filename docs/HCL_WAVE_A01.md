# A01 — Shared source revision in retained cognition

**CAPABILITY_DELTA:** one source correction now invalidates its dependent cognition
results and revises a real belief/concept comparison, while a different person's
independent result remains identical and is not recomputed.

`hcl.cognition.CognitionWorkspace` is opt-in. `put_source` registers authorized
text with a version; `prepare(question, source_ids=(...))` calls the retained v1
ordinary entry. The shared core binds both real operation states to the same
source/scope identities. Replacing or removing that source invalidates rooted
support and its descendants. Whole selected documents are conservative read
sets, so adding evidence also invalidates an earlier unknown result. This first
slice invalidates at document scope, not minimal sentence scope (A02–A03).

```python
from hcl.cognition import CognitionWorkspace
w = CognitionWorkspace()
w.put_source('meeting', '''Alice: In team, by fair I mean consent is true.
Narrator: In team, proposal has consent false.
Alice: In team, I believe proposal is fair.''')
p = w.prepare("Compare Alice's belief and meaning of fair for proposal in team.",
              source_ids=('meeting',))
receipt = w.receipt(p)  # actual final messages; no provider call
```

The executable [witness](../scripts/witness_shared_cognition.py) changes consent
false → true. Actual comparison changes `DIFFERS_FROM_LOCAL_SOURCE_CRITERIA` →
`CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA`; both dependent operation results retire,
Bob's independent result remains cached. The checked-in [receipt](../reports/HCL_WAVE_A01_WITNESS.json)
records exact inputs/state and runtime digest. CI reproduces it at both PR head
and merged main and uploads it with the exact-SHA certification.

Source reports, system interpretations and conditional tool results remain
separate. A rooted derivation is not truth. Alternative support sets are OR, their
members AND; a least-fixed-point calculation rejects rootless self-support even
after an earlier root is withdrawn. Multiple supports do not imply statistical
independence or majority confidence. Actor/context/time/assumption scopes cannot
silently cross. Source versions and withdrawn history remain auditable.

Event time, information-access time, record time and source order are separate;
unknown dates stay unknown. The v1 adapter's synthetic ordering timestamps remain
inside its historical representation. A single-source statement snapshot omits
later source text from both actual messages and the shared receipt. This adapter
supports analyst view only; it does not pretend caller authorization is character
exposure. Richer perspectives and general semantic preparation follow in A02–A04.

**Verification:** 14 targeted tests cover positive revision, unit support logic,
negative inference, composition, ordinary-input smoke, source/time/access boundary,
unknown→supported update and source-removal cache rejection. Full v1 and historical
suites remain required by exact-head/main CI. Historical runtime bytes and paid
packages are untouched. No new external material or provider is used.

**State:** CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN. The ordinary
entry is still a bounded source grammar, not general language understanding or
independent efficacy. **NEXT_READY: A02 unified ordinary semantic preparation.**
