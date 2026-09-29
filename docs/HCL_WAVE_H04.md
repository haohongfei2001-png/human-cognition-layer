# H04 — Answer synthesis with bounded support audit

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** HCL can now turn a connected H03 execution path into
separate answer sections for exact source reports, the most supported recorded
conditional explanation, other unresolved or weakened explanations, and a
conditional conclusion. It carries decisive counterevidence and assumptions
into the actual final model input. After an ordinary source correction, the
answer changes its leading explanation and counterevidence rather than
silently retaining an obsolete narrative.

`AnswerAuditWorkspace` reuses the H03 belief→plan→expectation→relationship
support chain, E05's source-checked factor comparisons and F03's full selected
recorded evidence closure. The closure is checked before synthesis, including
access scope, all recorded support groups and challenges; it is refused when
the node budget would truncate it. The final context contains exact line
quotes with source ID/version/offset, actor and observer, candidate status,
decisive source quotation, support-closure counts, conditional boundaries and
explicit assumptions. It is bounded by source-anchor and context budgets.
`BOUNDED_RECORDED_CLOSURE_NOT_SEMANTIC_PASS` means the recorded chain was
audited. It does not certify semantic truth, independent evidence coverage or
model compliance.

The [ordinary witness](../reports/HCL_WAVE_H04_WITNESS.json) shows Mira's
action-time knowledge self-report and belief corrected. Before correction,
`INFORMATION_GAP` is the single most supported *recorded conditional*
failure explanation, `CONTROL_CONSTRAINT` remains unresolved, and an
explicit action-time statement counters the informed-choice alternative.
After correction, no failure explanation is conditionally supported; the
new self-report counters `INFORMATION_GAP`. Noor's reported distrust and the
unresolved control factor remain. The witness saves exact before/after model
input and a provider-free readable draft.

The draft and optional one-call answer adapter preserve source report versus
world fact, assumption versus knowledge, plan feasibility versus actual
intent, competing explanation versus actual cause, and reported regard versus
private feeling. No automatic judge claims absolute correctness. Local source
correction invalidates old answers; unrelated source answers are reused.
Eight targeted tests cover positive synthesis, exact offsets, correction,
unknown/refusal, actor/condition boundaries, ACL, budgets, final input and
historical semantics. Full v1/historical regression and exact-head/main CI
remain required. Provider calls/spend: zero. LongMemEval sealed.

**NEXT_READY:** H05 integrated difficult slice, resource pressure and
ordinary-task regression before G-ARCH.
