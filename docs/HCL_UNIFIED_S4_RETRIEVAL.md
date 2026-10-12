# M10: bounded authorized retrieval and recorded evidence closure

This is an **INTEGRATED_OFFLINE_PARTIAL** increment of the approved S4/M10 plan.
It does not close M10, S4, T22, T24 or T27. All S1–S7 research goals remain.

## Actual path

`HCL.run` / `HCL.stream` accepts an `ExecutionIssue` containing a typed
`RetrievalIssue`. Its explicit `RetrievalQuery` has separate support, challenge
and alternative query texts, an optional current source scope, bounded hit/node/
character allowances, and optional immutable recorded evidence result IDs.
The host still supplies the authenticated principal; source text cannot grant
access or choose model credentials.

- `memory.retrieve` delivers an actual EvidencePacket and CoverageManifest.
- `logic.compare_semantic_readings` and `argument.evaluate` can consume that
  exact selected packet through the existing candidate compiler and real solver.
  The model receives selected original spans, question and coverage, not the
  entire source library. Required recorded closure is never silently truncated
  to make a model context fit; a packet that exceeds its capacity fails safely.
- Current source scope is selected by the retrieval query, not implicit request
  handle expansion. Ordinary non-retrieval goals retain their old handle rules.

`QueryStore` is a view over the existing SQLite StateStore, not another cognitive
state database. New revision-enabled source objects reference a rebuildable
mechanical region/token cache beside the original text and formal input. The
authoritative source object stays small; cached index objects are disposable,
and a missing/corrupt cache is rebuilt from the validated original. Migration
need not copy disposable caches; it must preserve every authoritative object. Old
objects remain unchanged and are indexed from their original bytes on demand.
SQLite events, content hashes, atomic object writes, owner fencing and the
existing QuerySnapshot/QueryDelta dependency protocol remain authoritative.

## Computation and boundaries

The index preserves exact original source/version/hash, character and UTF-8 byte
spans. Unicode words and CJK unigram/bigram tokenization are versioned. CJK runs
are recognized before Python's Unicode word categories: BMP ranges U+3400–4DBF,
U+4E00–9FFF, U+F900–FAFF and supplementary ranges U+20000–2FFFD and
U+30000–3FFFD. This mechanical range policy includes reserved code points without
claiming Unicode assignment or semantic knowledge. Other word categories follow
the interpreter's Unicode database. Tokenizer/index version 2 rebuilds version-1
caches from original text, without modifying those historical objects. Mechanical
regions do **not** infer chapter, topic, event or perspective boundaries.
Cache rebuilding occurs only after the namespace passes its exact runtime/control
gate; it does not authorize opening an older executable namespace without cutover.

Each of the three explicit query routes computes BM25 and normalized sparse
TF-IDF cosine over the authorized corpus, followed by reciprocal-rank fusion.
TF-IDF is a genuine corpus-derived vector calculation and a lexical baseline;
it is not a trained semantic embedding or proof of paraphrase recall. Route names
express search intent. A hit is not certified as support, contradiction or an
alternative explanation merely because that route retrieved it.

Current ACL filtering happens before source/index reads, candidate formation,
corpus statistics, length normalization, rank, counts and dependency identity.
An explicitly named inaccessible source is indistinguishable from a missing
source. Hidden documents do not affect visible scores, query tokens or counts.

The first recorded-graph adapter uses actual committed M13 argument objects:
source premises/rules, children, attacks (including priority-blocked attacks),
and same-conclusion alternatives. The generic closure also traverses all AND
members of every OR support group and recorded revision reasons. It repeatedly
reads newly discovered obligations and handles cycles. Missing nodes, unindexed
regions and resource frontiers are preserved, not interpreted as absence. The
M13 adapter does not manufacture revision-reason edges or support unimplemented
graph dialects.

The complete immutable result-ID list is explicit in the query. Automatically
including every future inference would make a retrieval result invalidate its
own input graph. Query-bound prior effects can be validated recursively, with a
safe depth bound; their original source/ACL dependencies must still hold.

The packet records original selected spans and recorded graph nodes/edges. Its
coverage records indexed scope, exact read regions, contiguous unread ranges,
unindexed ranges, missing dependencies and closure frontier. Recorded graph
closure is never semantic/world completeness or a whole-book reading claim.

## Dependency, result and recovery safety

The query token binds query texts, source scope and versions, tokenizer/index/
representation versions, selected results, corpus statistics inputs, full
recorded graph and unindexed coverage. Tracking only selected top-k positives
would miss newly arriving counterevidence. A new visible in-scope source therefore
invalidates a prior query even if it was not selected. An outside-scope source
leaves an explicitly restricted query intact. A hidden source leaves the visible
query intact. Current ACL epochs still conservatively invalidate old authority.

The computed result carries the exact retrieval projection. The controller
compares it to the actual QuerySnapshot before accepting the effect. Positive
and query dependencies propagate into the same strict commit guard and durable
ledger. Final claims consume exact stored result fields and preserve retrieval
scope/frontier qualifications. Cached delivery rechecks current dependencies and
ACL after leaving the older WAL view.

A pure retrieval commit race can locally refresh and recompute the dependent
query within the existing shared step/local-work budget, without any model call.
A changed input to a compiled semantic proposal cannot silently reuse that old
proposal for newly read text: it fails stale and requires a new authorized task
or a future explicit recompile operation. Already returned calls are not blindly
resent. Computed/committed checkpoints reuse exactly accepted effects; UNKNOWN
call accounting keeps the existing conservative semantics.

Preparation is bounded to 1024 sources, 8 Mi characters, 65,536 indexed regions,
8192 recorded graph nodes and eight nested query-dependency levels. Per-query
packet bounds are independent of model/delivery capacity. Existing task storage
and source-byte limits still apply. Local-evaluation accounting records the
retrieval-result operation separately from indexed-region/visited-node counts;
these counts are not measured wall-clock cost or a calibrated token estimate.

Repeated ancestors in recorded dependency DAGs share immutable projections only
within the same SQLite transaction, principal, session/version/ACL/rule and write
generation. A memoized subtree retains its longest height: a shallow earlier hit
cannot let a deeper path bypass the eight-level bound. Every final fresh delivery
transaction computes its own authorization/projections. Preparation is also
bounded across the entire transaction to 64 uncached projections, 32 Mi scanned
source characters, 262,144 indexed regions, 4096 evidence rows and 32,768 graph
nodes. Exhaustion reports `RETRIEVAL_PREPARATION_BOUND`, never successful absence
or semantic completeness. The initial search participates in these same bounds.

A synthetic two-wide shared-ancestor DAG at levels 0–5 originally performed
2/6/14/30/62/126 projections including its separate delivery check. It now performs
2/4/6/8/10/12; one short-source development measurement changed level 5 from
approximately 0.34s to 0.05s. These are measured engineering examples, not claims
of constant latency, general semantic recall or full T27 scale acceptance.

## Actual checks and remaining work

Tests include exact Unicode offsets, cache rebuild identity, independent dense
TF-IDF comparison, AND/OR/challenge/alternative/revision traversal, cycles and
frontiers, current ACL before scoring, unread-source membership invalidation,
restricted-scope noninterference, WAL late revocation, run/stream, restart,
computed/committed recovery and a real commit race. An injected conditional FOL
interpretation consumes a remote packet from a long source; added counterevidence
changes the actual solver result. A separately executed M13 argument result feeds
its actual attack graph into retrieval. These supplied ASTs are port fixtures,
not semantic-extraction oracles presented as learned capability.

Development measurements on synthetic 99,991- and 999,982-character sources
completed ordinary retrieval in approximately 0.9s and 13.2s in this workspace,
with three delivered regions and zero model calls. They are engineering
measurements, not the full natural-text/independent-recall/scale acceptance suite.

The next M10 work remains substantive: semantic/event/topic/perspective indexing,
active query synthesis and missing-region rereading, all-domain packet consumers,
concept-change invalidation, historical retrieval selection and memory-layer
policies, independently evaluated natural long-text counterevidence recall, and
privacy erasure. ACL revocation is implemented; it is **not physical erasure**.

Current events can contain source identities and full query text; old checkpoints,
failed branches, calls and migration packages can retain content outside final
answer dependencies. Erasure needs exact artifact lineage, durable tombstones,
non-replayable accounting, governed event redaction and resumable file/WAL cleanup.
Deleting a source row or unlinking current objects alone would be unsafe and is
not offered as an erasure API in this increment. Implementation and tests for
that work use disposable synthetic stores. No real user/production content was
erased, and no claim is made about external backups or previously delivered data.

## Qualified relationship predecessor and historical eligibility

The predecessor allowlist additionally includes exact published M09 main
`d30e8cbba5e51d7c2b8191c21cb8969370880408`, with 190 runtime Python files and
code hash `70ca9691b43d0873e0078e707ce70cfe6109a5eff2b852984755e4c2e3446021`.
The original 189-file M09 pin, tests and immutable objects are retained. The
complete existing migration suite executes both actual runtimes independently;
the added pin is not an assertion that their behavior is interchangeable.

`test_unified_relationship_qualification_upgrade` creates actual old 189-file
executions in disposable schema 3/4 namespaces. It covers definite and
unknown fulfillment across completed, RETURNED, computed and committed states.
On current delivery, known results remain valid, old unsafe accepted numerical
effects fail qualification, and RETURNED candidates can be genuinely recomputed
under the new rules without another send. Reopen/stream, completed old task and accepted-object
immutability, fresh-request corrected recomputation and current ACL are checked.
No historical posterior is rewritten or merely relabeled. All earlier retrieval
limits, exact pins and existing tests remain in force.
