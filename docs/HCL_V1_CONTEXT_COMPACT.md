# Explicit lossless cognition-context compaction

## CAPABILITY_DELTA

Under the same bounded answer-context budget, HCL can now carry complete checked
local readings that previously failed the budget gate. This is integration of
existing cognition, not a third unvalidated module or a new efficacy disposition.

`CognitionRequest(..., compact_context=True)` opts into source-reference encoding.
The default remains identical to all frozen development inputs. Sources are
projected before encoding. Their actor/source/event/record times and full raw text
remain in the evidence pool. Exact repeated quotes become source references;
checked rows inherit unchanged case-input fields and retain explicit overrides
and deletions. Identical provenance fields become shared table columns. Known
empty-default fields may be omitted; absence never means a negative claim.

`expand_cognition_context` restores every field. The encoder verifies its own
lossless round trip before use. A redacted or unmatched quote stays literal.
Missing source/case references fail rather than invent evidence. No source,
uncertainty, normative premise, counterexample, actor or time is selected away.
Internal reference labels appear only in model/debug context; user answers stay
plain. `PreparedAnswer.context` retains full prepared state; `messages` records
exact actual transmitted encoding and its policy. No extraction calls or new API.

Provider-free tests cover all 12 CG03/04/05 development narratives, typed private
views, hidden revisions, missing references, unmatched quotations, exact model
input round trips and a budget where full context fails but compact context fits.
The CG03 five-factor and normative-premise distinctions survive unchanged.
The 12 complete serialized model inputs (including the extra decoding policy)
shrink from **108554 to 99516 bytes (8.33%)**. [Byte receipt](../reports/HCL_NIGHT_CONTEXT_BYTE_AUDIT.json).
These are JSON transport bytes; tokenizer usage, billed cost and base-model
answer quality are **unmeasured**. This does not satisfy the eventual <=2x-P
maturity target or alter CG03's consumed 4.34x-P cost observation.

No frozen package/source/gold/prompts/scorer/arms/treatment was modified. CG04 and
CG05 remain the only two pending candidates, READY / DEFERRED_OWNER_AUTHORIZATION.
Next: compose existing source-projected operations for a single ordinary-input
answer while preserving operation-specific source boundaries and no automatic
premise/private-state transfer. Keep one writer and one coherent PR.
