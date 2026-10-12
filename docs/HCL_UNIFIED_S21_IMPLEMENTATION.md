# S2.1: source-bound candidate compilation and actual conditional computation

This implements the approved S2.1 offline slice on S1.3/main
`de92d28279d8cb5b3e0ba407a12af0a9cde1fb7d`. The formal plan expressly permits
injected extraction fixtures without real-model authorization. Those fixtures
are a test condition at the model port. They are not an implementation or
validation of open-language extraction. S1, S2 and full T01/T02/T09/T20 remain
open. No new provider, credentials, paid execution, old grant or sealed material
is used. All remaining S1–S7 goals and research criteria retain their scope.

## One executable path

The same `HCL.run`, `run_sync`, `stream` and compatibility facade accept the issue
`logic.compare_semantic_readings`. The authenticated engine obtains the existing
version/ACL-bound snapshot. ModelGateway builds the candidate-compilation context
from the actual authorized original texts and unchanged question. A JSON schema,
exact stable segment IDs and untrusted-source instructions accompany that data.
Only the existing built-in `OfflineModelPort` currently supplies model output.
Its response contains proposed typed interpretations, never a solver label,
answer, executable code or committed state. Ordinary answer calls retain their
existing wire contract. The durable reservation records this one offline attempt.

The pure compiler turns candidate trees into formulas. The actual old
`argument_readings.classify_reading` and `quantified_logic` algorithms compute
each reading in a bounded subprocess. The pure operator returns an OpResult and
candidate Delta; only the engine commits. AnswerAssembler consumes exact result
fields and checked countermodels. The existing claim reconstruction check rejects
altered values or answer text. Receipt, original candidate response, typed IR,
source bindings, profile and solver version remain inspectable by an authorized
caller. PARTIAL results persist and replay with their original status, without
sending again. Source changes and withdrawal of host access still invalidate
normal and cached delivery, including every derived receipt field.

## Representation and source alignment

Segmentation is mechanical, not a sentence-understanding algorithm. It preserves
all original Unicode, combining marks, whitespace and CRLF without normalization.
Every segment records original whole-text SHA256, source/version, character and
UTF-8 byte interval; its identity includes that provenance and interval. Question
segments have a different kind and cannot become source-root premises. Repeated
words at different positions do not share an ID. No old `NAME: I believe` text
rewriting, ASCII name filter or text-to-answer lookup is used.

The strict schema has explicit source-local entities, unary/binary predicates,
SOURCE_DISCOURSE/QUOTATION/HYPOTHETICAL/COUNTERFACTUAL/INTERPRETATION frames and
multiple candidate readings. Frame parents must be acyclic. Propositions retain
natural-language reading, typed AST, frame, source IDs, origin and alignment
references. Entity labels may be Chinese or multiword; stable semantic IDs map
to solver symbols, not the other way around. Same names in distinct sources do
not merge entities. Symbols do not assert distinct individuals: different FOL
constants may co-refer, which every generated scenario discloses. Cross-source
same-as inference, withdrawal and query dependencies remain S2.2.

Typed AST operations are atom, negation, conjunction, disjunction, implication,
equivalence, universal/existential quantification, and opaque meaning. Lexical
variable binding, predicate arity and exact field sets are checked. The grammar
cannot carry file paths as actions, imports, commands, network calls or arbitrary
Python. Opaque meaning stays in IR and prevents that reading from solving.
Cross-frame premises require a future explicit Bridge; the compiler does not
quietly combine them. Background priors/assumptions require an explicit assumption
list. Present frame-local results are conditional on that frame, never truth
about the actual world or private mental states. Time remains explicitly
unresolved; no source order or text date is silently promoted to event time.

Every source segment must be mapped or appear as unparsed. Omitted segments are
automatically retained as unresolved obligations; no source content is silently
discarded. This check is at declared segment granularity. It cannot detect a
candidate that cites a whole sentence but changes its meaning, misses a clause,
or invents a predicate. Alignment SUPPORTED is a model proposal, not proof:
`semantic_certified=false` and `candidate_completeness=NOT_ESTABLISHED` are
unconditional. CHALLENGED/UNRESOLVED alignment or incomplete source coverage
produces PARTIAL delivery. A deliberately wrong but structurally valid candidate
is retained as unverified in the regression suite. Independent semantic checking,
real multilingual extraction and semantic repair are still required by the full
plan; JSON validation is never credited for them.

## Actual reasoning and countermodels

For each executable reading the existing classifier checks premise consistency,
then entailment and refutation. Consistent readings can be True, False or
Uncertain; inconsistent premises never license arbitrary conclusions. Solver
UNKNOWN is distinct from semantic/logical uncertainty and remains unresolved.
Full-FOL equivalence uses Z3 after finite counterexample searches. A missing
finite countermodel does not establish validity. Full-FOL UNSAT is a conditional
solver result, not an independently checked proof object. Classification labels
must match the consistency/entailment/refutation check statuses before consumption.
There is no model-provided answer label and no branch based on fixture names.

Finite witnesses are independently evaluated again with the original premise
list and the correct original or negated query. Their original query truth values
retain polarity. A generated scenario maps domain elements, entity labels and
predicate extensions back to the source-local symbol map; rebuilding that model
must equal the checked model. This is a formal round trip, not a source quotation
or evidence that the proposed source interpretation was right. A full-FOL SAT
result without an available finite model never receives an invented scenario.
Disagreeing supplied readings yield READING_DEPENDENT/PARTIAL and no unique
unconditional answer. All retained readings and assumptions remain visible.

## Resource bounds, persistence and failures

SemanticProfile defaults to 8 readings, 18 entities, 26 predicates, 32 frames,
512 AST nodes per reading, depth 48, 100 ms per solver check, a 15-second wall
deadline, 12 CPU seconds and 768 MiB address space per worker. These are explicit
bounded engineering defaults, not cognitive capacity ceilings. The configuration
allows bounded increases (up to 64 readings); inherited parser symbol/node limits
are rejected explicitly, not truncated. Each reading has at most 16 premises;
the existing TaskRequest byte, formula and local-evaluation allowances still
apply. Candidate response and final answer must fit their existing output bound.
No persisted TaskRequest/BudgetSlice/SQLite schema fields change in this slice.

The fixed-purpose subprocess receives only formula JSON, with a sanitized
environment, OS CPU/address-space limits and parent wall timeout. A timed-out
worker is killed and reaped; missing resource-limit support fails closed. This
is not an arbitrary-code sandbox or a claim of OS network-syscall isolation.
The async engine runs this wait in a worker thread so ACL/source updates can
proceed while solving. Deadline/resource failures return safe diagnostics and
unknown completed-work accounting, not fabricated zero use. Actual completed
calculation is recorded before a later stale/ACL commit refusal.

Usage counts classification batches. A batch can perform up to 15 underlying
solver checks; the receipt labels that number an upper bound, not an observed
SMT-call count. A timed-out batch retains the mock attempt and reserved local
work. Durable request/lease/reservation, UNKNOWN holds, no-resend semantics and
source-free failure receipts remain the S1.2 mechanism. No parallel child can
write shared state from the subprocess. Schema-2 imported namespaces retain their
existing exact code-version fence across this runtime change; readonly rollback
and audit remain available, with no automatic reactivation.

## Evidence and remaining work

`tests/test_unified_s21.py` exercises Chinese conditional, negation, missing
antecedent and converse contrasts; English negation-scope ambiguity; quantifier
order with an independently evaluated two-element countermodel; eight unseen
propositional compositions against a separate Boolean oracle; same-name source
isolation; exact spans and Unicode; opaque/unparsed/frame/assumption boundaries;
malformed/executable trees and answer-label refusal; actual subprocess timeout
and reap; solver-unknown and unavailable-model paths; claim tampering; restart,
run/stream compatibility and fresh normal/cached ACL checks. Fixtures specify
interpretation input only. Real downstream outcomes are never stubbed except in
explicit failure-control tests for UNKNOWN or missing model materialization.

`scripts/witness_unified_s21.py` changes actual original Chinese source texts and
supplied candidate meanings, obtains actual True/False/Uncertain calculations,
then preserves two English ambiguity readings. It checks answer consumption,
finite scenarios, PARTIAL restart replay and stale-source refusal. It records
exact checked-out commit and all runtime file hashes. Current old behavior and
fixed historical identity partitions continue to execute unchanged; no old pin,
grant, score or test is rewritten. These are integration and regression evidence,
not an independent language benchmark, Base improvement, LIVE_FUNCTIONAL or
EFFECT_CONFIRMED. S2.2 continues with time, bridges, assumptions, identity and
revision; S2.3 supplies the broader dynamic protocol and scheduling contract.
