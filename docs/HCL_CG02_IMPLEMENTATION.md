# CG-02 implementation and provider-free scope

The canonical scope and phase order remain in [the capability contract](HCL_CG02_CAPABILITY_CONTRACT.md). This document describes the implemented A-D behavior; provider-free correctness is distinct from external benefit.

## Runtime operation

`CognitionRequest` accepts `social_analysis=True`, source `evidence`, and typed `social_acts`, `social_interpretations`, and `social_access_statements`. A person-targeted social query also routes to `cg02_social_commitment`. A generic word without a target remains on the direct model path. The operation reuses reader, character, and observer-about-target modes. The `CognitionContext.social` field carries checked state into the final model input; a debug `PreparedAnswer` retains the exact messages and preparation receipt.

`SocialAct` binds kind, speaker, source span, event time, intended addressee when named, content, up to three explicit conditions, and an optional earlier act reference. The checker enforces exact source spans, source actor/time, bounded acts/actors/events, condition provenance, response order and valid withdrawal ownership. A named addressee is not proof of actual delivery: `recipient_ids` and explicit narrator access reports are checked separately. Missing access is `UNKNOWN_ACCESS`, never negative access. Explicit denial requires an anchored narrator statement after the referenced event.

`ParticipantInterpretation` is a source anchored report by that participant. It does not replace the original act or prove private understanding. The checker compares quoted expected conditions with source conditions, records omitted or added conditions, access state, withdrawal order, and bounded explanatory factors. It leaves content paraphrases unverified. Reader-only evidence is excluded from character and observer views. The answer policy rules out deception, betrayal, promise-breaking, trust, relationship and blame conclusions without separate evidence.

## Ordinary text and semantic preparation

The default provider-free parser accepts at most 32 nonempty lines. Its narrow grammar recognizes complete `Speaker to Recipient: "..."` dialogue lines, conditional `If ..., I will/can ...` commitments, explicit proposal/request/acceptance/refusal/withdrawal markers, and later quoted self-reports using `promised`, `expected`, `thought`, or `understood`. Each line remains an exact source event. Order is line order, not calendar time. Unrecognized text remains source evidence and yields no checked act. The parser deliberately does not invent a recipient, private belief, condition or social act from a loose paraphrase.

Only `allow_semantic_preparation=True` with an explicitly supplied `semantic_preparer` can invoke an adapter when deterministic preparation found no act. Its typed `SocialPreparation` output must pass source-line, actor/recipient, count, span, time and checker validation. Invalid output fails closed; the debug receipt preserves bounded raw output, model ID, provider-call count, cost and failure when supplied. The default schedules zero extraction provider calls. The answer adapter itself is caller supplied.

For a future H-new ablation, `HCLCognitionLayer(..., social_checker_enabled=False)` retains the same route, source preparation and visible evidence but omits `context.social` checked state. This switch is for controlled comparison only. Every selected H case must prove the six treatment-presence conditions in the canonical contract before any paid validation request.

## Limits

The deterministic grammar is intentionally narrow and English only in this first round. Chinese social queries route, and typed Chinese source evidence can be checked, but ordinary Chinese text is not automatically extracted. Calendar cutoffs require timed `EventRecord` input. Event access proves exposure only. Content paraphrases and participant memories remain unresolved unless the source directly supports them. Provider-free tests certify these boundaries, not a semantic advantage over a prompt or generic representation.
