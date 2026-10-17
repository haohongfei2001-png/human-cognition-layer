# Controlled ordinary-input candidate entry, disconnected integration

Status: **INTEGRATED_OFFLINE**. This is an implementation increment under the
approved §0.1, S2–S4 and D3 requirements, not another overall plan or a stage exit.
The ordinary caller supplies source text, a question and finite execution limits;
`affect_request(...)` selects exactly one `affect.evaluate` obligation for the
existing `HCL.run` / `HCL.stream` engine. It is not a general task/domain router.

## Production-shaped protocol, explicit missing live pieces

`ControlledCandidateGateway` prepares the documented OpenAI Chat Completions
request shape: model, system/user messages, JSON-object response format, one
choice, `max_completion_tokens`, non-streaming transport and `store=false`.
It decodes the documented completion model/id, visible assistant content,
finish reason, prompt/completion/total token usage and cached prompt tokens.
Reference checked 2026-10-17: [OpenAI Chat Completions API reference](https://developers.openai.com/api/reference/resources/chat).
The completion cap/usage includes reasoning tokens, but no hidden reasoning is
requested, used or retained. The host's model identifier must match exactly;
alias resolution, tools, refusals and incomplete finishes are not silently accepted.

Only the exact built-in `DisconnectedChatTransport` with finite supplied response
bodies is installed. Subclasses, arbitrary callbacks and LIVE grants are rejected.
There is no endpoint, HTTP sender, SDK, credential loader, environment-secret
lookup, retry service, provider account or payment. This tests protocol assembly,
parsing, accounting, recovery and actual local computation. Injected candidate
fixtures do **not** test natural-language extraction or live provider behavior.

A subsequent live increment still needs separately authorized current provider,
model, exact source input, number of calls, total fee ceiling and rate version;
an installed authenticated host transport and provider-specific capability/
billing verification; then actual ordinary-input extraction and error analysis.
No callback or capability flag can promote this release to LIVE. Historical
UniversalHCL, provider pins, grants and old 36KB limits are not revived.

## Host authorization and accounting

`CandidateAuthorization.for_request(request, ...)` binds the full serialized
TaskRequest SHA, including principal, session, question, source handles and
versions, goals and limits. The host must explicitly call
`gateway.register_authorization(request, grant)`. A grant decoded from a source,
model response, checkpoint or reopened store does not install authority.
Authority is checked at reservation and immediately before dispatch, after all
pre-send fault seams. Same-process hostile Python is outside this host trust
boundary; this is not a sandbox for arbitrary Python callbacks.

The grant pins provider/model, source versions, maximum calls, input/output token
caps, maximum total simulated nanodollars and versioned uncached/cached input
and output nanodollar-per-token rates. There are no hard-coded provider prices.
The conservative input bound covers the complete serialized request body,
including the system prompt and protocol wrapper. Existing per-call and total
byte, output, repair, graph and local-computation bounds also apply.

Calls use additive versioned `MeteredCandidateRequest` / `MeteredCandidateReturn`
content objects in the existing hash-checked task/call event log. Existing SQLite
columns, old dataclass fields, old context v1 and old receipt bytes do not change.
No global scan reads another task's sources: the grant's exact task fingerprint
prevents cross-request reuse. A host issuing a changed fingerprint explicitly
issues a new task-bound grant; authorization IDs are not an account-wide quota.

- Reservation commits before SEND_STARTED and dispatch. Every new candidate or
  repair attempt consumes the same task grant; `max_mock_calls=0` is valid.
- Mode is always `DISCONNECTED_PROTOCOL_SIMULATION`. Real `provider_calls=0`
  and `provider_spend_usd=0` remain truthful. Independent `metered_transport_calls`,
  observed protocol tokens, simulated settled/held cost and uncertainty expose
  all simulated activity, including nonzero usage and fees.
- Exact usable usage settles at the pinned rates. Missing/malformed/contradictory
  usage or mismatched model identity retains the full reservation. Missing cache
  usage may settle only when cached and uncached input rates are identical.
  Positive request/visible response cannot claim zero corresponding tokens.
- Observed over-cap tokens/cost are retained, never clamped to the approval;
  output and further calls are rejected. Invalid finish/refusal does not erase
  known usage. Provider/protocol failures do not trigger semantic repairs.
- Any exception after entering transport is UNKNOWN regardless of its claimed
  error label. The reservation remains held; neither reconnect, recovery,
  replay nor a new repair may resend it. Confirmed local pre-dispatch failure
  releases money but retains the call identity. Crashes retain conservative
  holds until explicit authenticated recovery establishes a pre-send state.
- Revoking a grant stops future sends. It does not erase already incurred usage
  or invalidate an already accepted computation. Current source ACL/version
  checks still gate dispatch, computation, replay and final delivery.
- Source erasure retains only allowlisted mechanical accounting, never source,
  model or authorization identifiers. Exact output/checkpoint recovery uses
  existing authenticated recovery and no-resend rules.

## Candidate contract and actual computation

The opt-in `affect_compile_v2` packet contains full mental/plan/causal and affect
field contracts, source versions and exact source spans, including v2 attribution
bridges, structure-availability gates, atom projections and finite repair data.
Model visible content is a versioned `hcl-affect-source-return-2` envelope with
exact source versions and a `hcl-affect-candidates-2` proposal. Duplicate JSON,
Boolean-as-version aliases, wrong versions, foreign spans, computed verdicts and
unsupported fields are rejected. A matched span is not semantic truth evidence.

Only representation/source-alignment errors are eligible for the existing bounded
field-diagnostic repair loop, under the original question/sources/schema/model/
rates and shared call, money and feedback limits. A repair regenerates a proposal
for revalidation; it is not a proof of minimal semantic edit or correct extraction.
It cannot modify host authorization, install tools, add sources or return an answer.

The same `AffectCompiler`, `LocalModelOperator`, M03 perspectives, M06 finite
same-background counterfactuals, M08 appraisal and M05 coping calculations run.
The existing `AnswerAssembler` consumes their exact result fields. No new solver
or model-written final-answer path exists. Conditional attribution is not intent,
blame, psychological truth or a real-world action recommendation.

## Evidence and migration

- `tests/test_unified_controlled_candidates.py`: ordinary entry, request/return
  shape, independent mock/metered accounting, bounded repair, budget refusal,
  malformed/UNKNOWN returns, pre-send revocation, late ACL, concurrency, explicit
  recovery, replay, source erasure and no-callback/live installation.
- `tests/test_unified_controlled_candidate_upgrade.py`: execute the actual PR452
  runtime, exact main `dbf18b4ab9843b2e75866297235870a727c58bae`, tree
  `ab34de705c577976fc6b5b8eef25829c57d84a87`, 244 explicitly inventoried runtime
  files, then controlled schema 3/4 migration. Existing v1/v2 affect and v3
  literature contexts, proofs, answers/claims, interrupted seams and ACL retain
  their original bytes; accepted work is not recomputed and no old call is resent.
- `scripts/witness_unified_controlled_candidates.py`: bind ordinary/stream,
  counterevidence/unreceived contrast, repair consumption and UNKNOWN holds to
  the exact checked-out head and runtime hash. All transport candidates are
  explicitly injected fixtures; actual cognition is computed by existing code.

Full S1/S2/S3/S4, LIVE_FUNCTIONAL, cross-domain natural routing, semantic extraction
quality and downstream gain/effect evidence remain open. The stopping point for
this increment is verified disconnected integration and honest live prerequisites.
