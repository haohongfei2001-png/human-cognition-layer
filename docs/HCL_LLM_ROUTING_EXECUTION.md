# LLM-directed understanding and required HCL execution

The owner's October 3, 2026 correction makes the initial division of work explicit:
the large model may understand the request, select useful HCL operations and
construct their arguments. Independent deterministic language understanding is
not a prerequisite for development or delivery. HCL then runs the selected
existing mechanisms and returns their actual outcomes for answer composition.
Selection should be accurate; execution counts alone do not establish relevance,
semantic correctness or benefit.

## Small current-runtime correction

The adopted `UniversalHCL` already delegated planning to a model. The mismatch was
that its policy explicitly permitted an empty plan followed by a model answer,
and final composition also continued after every selected adapter was unavailable
or rejected. Calling that route HCL orchestration did not establish a native
capability invocation.

The revised entry keeps the existing inventory and bounded operation arguments.
It requires at least one actual native result before the
answer-model call. The receipt and final input separately record selected
operations, dispatched operations, returned native results and each full native
outcome. Empty plans and all-unavailable/rejected plans remain visible and stop
before an answer call. They do not trigger a forced operation, fallback model
answer, extra planning call or retry.

A relevant native operation can honestly return insufficient evidence. That
result may support a limited answer; positive checked treatment is not a delivery
prerequisite. Existing per-operation treatment flags and full result payloads
remain intact. A nonempty result or an invocation counter cannot prove that the
model chose well. No deterministic semantic relevance classifier is introduced.

## Existing structured-input bridge

The same first planning response may now include `semantic_candidates` for one
selected B01, C01 or C03 operation and one complete source. The bounded field uses
the existing conditional adapter's event/canonical-statement schema, with 1–24
exact original quotations, source IDs and optional character offsets. Structural
validation occurs before dispatch. The existing semantic adapter validates the
anchors and retains the model's proposed statements as unverified interpretations.

Those already-metered arguments are replayed locally into
`prepare_retained_reader`. This is not a third provider call. The unchanged native
tools check the derived representation; the complete original source remains the
only quotable evidence. Native policy, conditional state, original-to-derived
bindings, translation assumptions and real support IDs reach the answerer. Source
revision or withdrawal of a translation invalidates dependent results. A correct
quote does not certify that the model's interpretation is correct.

The selected family's treatment is recorded separately from other conditional
checks. Omitting candidates preserves the original local path. Other families,
including C02 and B02, do not accept this optional field. This implements a
limited bridge for three existing families, not natural-language coverage for all
14 ordinary entries. Native tool contracts and parsers are unchanged.

## What remains necessary

Model-created operation questions may adapt the user's intent into the current
accepted forms. The original outer task and complete original source/version
remain in final composition. Exact source bindings, original caller authority for
conditional rules and counterfactuals, source revision/withdrawal checks and
canonical citation validation remain necessary. Model interpretations are not
new source facts, private mental truth or newly authorized normative premises.

No native grammar, source parser, capability-count, provider/model, token-default
or budget changes in this amendment. Structured native inputs are normal tool
contracts; the tools need not become general natural-language parsers. The bridge
above translates model understanding into a limited set of existing inputs with
source provenance. Remaining families need their own suitable structured-input
integration. A question with no relevant current native input has an explicit
unavailable outcome, rather than an invented HCL execution.

## Concrete complete path and verification

1. Original question and complete source reach the existing metered LLM planner.
2. Its validated operation arguments enter the selected native workspace. For
   example, a broad explanation request may become the internal C02 question
   `Why did Noor skip the meeting?` while the user's original wording is retained.
   For B01/C01/C03, anchored model interpretations may additionally supply the
   existing conditional structured input in the same planning response.
3. The actual native conditional explanations, insufficient evidence or other
   outcome reach final composition with all source and support dependencies.
4. The answer model answers the original question. Original-source citation and
   support checks accept or reject the unchanged returned answer.

Offline tests cover all three conditional-reader families, exact-source and
derived-source citation separation, malformed/oversized candidate refusal,
translation withdrawal and full transport overflow. They also cover the real C02
call with interpreted arguments, a real C04
insufficient-evidence outcome, a source-free G01 caller-condition preparation,
mixed successful/unavailable operations, no-operation refusal and withdrawal.
Scripted model ports verify wiring and boundaries only. They do not prove model
selection accuracy, full natural-language coverage or improved answers. The
representative five-candidate fixture fits complete requests of 28,136 planning
bytes and 34,950 answer bytes for each selected family. Under the unchanged
4,096/8,192 token configuration, its conservative peak-rate reservation is
US$0.22086768 per complete two-phase flow. These are measured request bounds, not
spending authority or invoice costs. Larger combined payloads stop at 36,000 bytes
without removing candidates, policies or original evidence.

The next delivery check is a bounded real-model complete flow on the adopted
runtime, after result readback and explicit live authority are ready. The dormant
consumed G05 regression preparation remains a separate historical candidate; its
request/package hashes cannot be reused for this amended runtime. All historical
grants remain closed. No paid call, new key or efficacy claim is made here.
