# HCL v1 minimal cognition integration

CG-01 extends this foundation with explicit reader/character/observer modes and
bounded action-explanation condition checking. See
[CG-01 implementation](HCL_CG01_IMPLEMENTATION.md). A generic `why` / `为什么`
does not activate intention by itself.

Base model first. v1 consolidates existing assets; no v0.11 ontology, learned router, mandatory extraction, or new provider experiment. The executable inventory is [the registry](HCL_V1_CAPABILITY_REGISTRY.md).

## Interface

`CognitionRequest(query, evidence=tuple[EventRecord], history=tuple[str], target_actor=None, observer_actor=None, event_time=None, knowledge_cutoff=None, tools=tuple[ToolRequest], max_context_chars=24000, perspective_mode=None, narrative=None, allow_semantic_preparation=False)` returns a `CognitionPlan` through `CognitionRouter.plan`. `HCLCognitionLayer(base_model, intentions=None, affects=None, semantic_preparer=None).answer(request, debug=False)` returns ordinary answer text; debug returns an `AnswerReceipt` containing the prepared plan, bounded context, actual messages and, when applicable, preparation input/output receipt. The base model adapter is either a callable accepting messages or an object implementing `complete(messages) -> str`. Its credentials and spending remain the caller's responsibility. The default path makes no extraction call; the optional preparation adapter is invoked only with explicit request opt-in.

```python
from hcl.v1 import HCLCognitionLayer, CognitionRequest
layer = HCLCognitionLayer(lambda messages: 'Paris')  # provider-free stub
assert layer.answer('What city is mentioned?') == 'Paris'
request = CognitionRequest('What does Alice know?', target_actor='Alice')
receipt = layer.answer(request, debug=True)
assert receipt.prepared.context.uncertainty
```

## Activation and cost

Deterministic English/Chinese task rules select knowledge/access/belief, explicit goal/plan/motive questions, feeling/appraisal questions, and supplied exact operations. This is a conservative foundation with finite vocabulary, not a universal semantic classifier. Caller-supplied typed operations are explicit task semantics; benchmark identity is never an input. Incidental history/evidence keywords do not activate capabilities. Missing declared causal/formal inputs block computation and produce system-level insufficiency. NL arguments are not converted into graphs. Unknown/inactive capabilities cannot execute.

Direct factual tasks have ZERO HCL overhead: no state construction, projection, tool, or extraction. Selected deterministic projections and bounded local tools are LOW. Explicit opt-in semantic preparation may add one separately recorded adapter call; the default path schedules none. All paths use exactly one final base-model adapter call. The context character cap bounds supplied extra cognition context; oversized contexts fail closed without arbitrary source truncation. Caller query/history bounds and existing exact-solver caps limit work. These are deterministic cost classes, not measured token pricing or a demonstrated utility optimizer.

## Existing assets and sparse context

Perspective/belief uses the frozen v0.6 runtime. Optional intention/affect uses validated v0.7/v0.8 evidence. Inject an existing `HCLV07Runtime` (its `.perspectives` holds v0.6 state), or `HCLV08Runtime` sharing that intention instance, to reuse committed semantic evidence. Existing ingestion interfaces remain available for upstream validated structured evidence. v1 only ingests access-bound EventRecords; it never derives motives, feelings, or belief acceptance from raw text. Without committed typed evidence those fields stay empty and the base model reasons cautiously from the bounded source. Without injection requests use isolated transient state. v0.5 persistence remains an upstream foundation; v1 does not replace its store or promise new persistence semantics.

`CognitionContext` has independently empty fields: evidence, provenance, temporal_scope, actors, perspective, belief, explicit_intention, affect_evidence, uncertainty, tool_results, unsupported_inferences. The unified evidence vocabulary distinguishes DIRECT_SELF_REPORT, EXPLICIT_NARRATOR_REPORT, DIRECT_OBSERVATION, THIRD_PARTY_REPORT, BEHAVIORAL_INDIRECT_EVIDENCE, MODEL_INFERENCE, TOOL_CONDITIONAL_RESULT, SYSTEM_UNKNOWN. This is not a numeric ranking and performs no promotions. Raw EventRecords have unknown attribution until a validated typed record supplies it. Reports, behavior and hypotheses retain their level.

Actor IDs and access metadata are caller-validated facts, not inferred attendance. Supply target/observer explicitly for ambiguous or second-order tasks; a missing unambiguous target fails closed. First-order evidence never includes reader-only narrator text; v0.6 evidence *about* a character's belief remains a separate system estimate channel. Second-order estimates are bounded by the observer's actual access. Both event-time and system-record-time cutoffs apply. History is supplied only on the direct path; on a bounded path convert authorized history into EventRecords rather than forwarding unbounded text. Arbitrary metadata is excluded from answer context.

## Exact-tool interface

`ToolRequest(capability_id, source_event_id, inputs)` supports:

| Capability | Explicit input |
|---|---|
| causal | v0.9 CausalModel, target, optional observations/interventions; quoted source with causal_model_scope |
| argumentation | v0.10 ArgumentFramework, optional semantics/target; quoted complete graph with argumentation_scope |
| formal_verifier | left/right explicit formulas, optional timeout_ms |
| countermodel | premises/conclusion, optional witness or domain_size/timeout_ms |
| formal_reading | one to four explicit readings with source_sha256, premises/conclusion and identity |

Formal sources require `formal_scope=EXPLICIT_FORMAL_INPUT`, exact formula anchors, digest agreement for alternative readings, and bounded solver inputs. Anchoring does not prove NL interpretation. Source absence, private/future source, invalid inputs, inconsistent assumptions, unknown solver results and alternative reading disagreement remain failures or conditional statuses. Each result records status, assumptions, computation, source provenance and TOOL_CONDITIONAL_RESULT. No result is appended to observed evidence or character state. No preferred reading is picked.

## Boundary and verification

`hcl/v1` imports only runtime assets and standard-library support, never eval runners, reports, scripts or provider adapters. No large module moves. The dedicated CI runs independent synthetic v1 integration tests, frozen v0.4–v0.10 provider-free regressions, and runtime compilation without model secrets or external benchmark downloads. These certify integration correctness, not external human-cognition efficacy. The answer policy constrains source use but cannot guarantee an arbitrary base model obeys it; no new model utility claim is made.
