# S2.2: persisted scoped revision under candidate interpretations

This is the approved S2.2 **offline integration** slice, based on main
`9c739f3d65ac3d49277e6cb4001d904304e8dd9f` / PR #427. It implements the joint
loop in the formal plan: late evidence and withdrawal change relevant support;
independent support and unrelated people remain; newly relevant evidence
invalidates a conditional absence result; old recorded-cutoff views remain
separate. All M01–M16, P01–P38, T01–T32, the 61 migration rows and S1–S7 retain
their approved scope. No full acceptance family or stage is closed.

The extraction port is still an explicitly injected `OfflineModelPort`. Its
JSON proposes source-bound atoms, scopes, temporal relations, identities and
assumptions. No fixture supplies computed support, solver results or an answer.
Actual kernels compute the values consumed by the answer. This does not
establish open-language extraction, source-faithful semantic interpretation,
candidate completeness, real-model functionality or effectiveness.

## Entry and actual execution

`HCL.run`, `run_sync` and `stream` accept `RevisionIssue`, a typed extension of
the unchanged `Issue` contract, with kind `revision.evaluate` and optional
`known_at`. It requires an explicitly revision-enabled durable store. There is
no separate unauthenticated query endpoint or implicit schema upgrade.

The engine obtains an ACL-bound `QuerySnapshot`, reserves the ordinary durable
model call, and sends only the requested original sources, unchanged question,
exact segments and the candidate contract through `ModelGateway`. It compiles
strict candidate JSON, stores source-index interpretations with every source
actually exposed to that call, binds retrieval and absence dependencies, runs
`RevisionOperator`, then commits its `QueryDelta`. `AnswerAssembler` consumes
actual signed support bits, query metadata and computed revision fields. The
ordinary result-field reconstruction and fresh delivery checks still apply.

The candidate syntax admits finite signed atoms and explicit grounded AND/OR
rules. This is a support/revision representation, not a replacement for S2.1's
existing quantified FOL and independently checked finite countermodels. It does
not infer a complete logic program or a character's private belief from prose.
The gateway does not yet supply an automatically aligned catalog of other
stored meanings; cross-source references are explicit fixture proposals checked
against the authorized registry. Automatic reference discovery is not proven.

The formal plan's responsibilities are implemented as follows, without empty
facades: `kernel/truth.py` owns rooted support and incremental revision;
`kernel/temporal.py`, `scope.py`, `identity.py` own scoped obligations;
`kernel/dependencies.py` owns pure index/query contracts;
`memory/sqlite_store.py` owns transactional indexing/history validation;
`operators/revision.py` composes these mechanisms as the pure `OpResult` producer.
These cover the listed `kernel/revision.py` / `memory/index.py` responsibilities;
the approved deliverable and exit conditions are not changed by file layout.

## Rooted support and revision

A support contains both a set of assumptions and original evidence-root IDs.
Conjunction unions them; disjunction retains independent alternatives. Minimal
assumption environments are exposed without erasing independent provenance.
Unsupported cycles cannot manufacture support. Explicit nogoods remove only
incompatible environments. Positive and negative claims are independent bits;
both supported does not produce arbitrary conclusions. Neither supported does
not prove either polarity false.

Rules have nonempty premises and one scoped conclusion. Direct reports and
explicit interpretation assumptions create original evidence roots. Checked
fact/Bridge/default seeds refer back to original roots; derived seeds cannot
make a self-supporting provenance cycle. Derived seeds inherit every original
root's assumption environment even if their explicit local assumption list is
empty. Root-assumption activation changes invalidate dependent seeds during
incremental revision. Time constraints, clock mappings, identities and Bridges
likewise inherit their evidence roots' environments. An incompatible joint
time/root environment remains unresolved and cannot license a watched absence.
A source version or interpretation
change changes its root identity. Equal names never merge source-local entities.

`TruthKernel.revise` computes dirty reverse closure across the old and new
programs, changed assumptions, dependent derived seeds and prior unexplored
frontier. It retains unaffected labels and hashes. The integration additionally
compares typed claim/scope/perspective hashes. The tests withdraw one of two
independent supports, then both, while preserving an unrelated source's support
and semantic hash. The final truth recomputation set excludes that unrelated
claim. The complete pipeline still performs bounded base/temporal computation;
this is not a claim that every pipeline operation touches only affected nodes.

## Time, perspective and explicit Bridge

Event time, agent access, record-publication time, narrative order and concept
validity use distinct axes. Exact rational difference constraints with a
strictness bit compute relative ordering. Original-edge witness paths are
summed independently before consumption. A cross-axis, cross-scope or
cross-agent relation needs an explicit evidenced clock mapping. Publication or
narrative order never silently becomes event/access time. Independent clock
components are separate; a conflict in one cannot poison another, and an
inactive connecting relation does not join them.

A temporal record has versioned publication time, proposed event time and
explicit per-agent access time. Selection chooses the newest record at the
cutoff **before** event/access filtering: a correction cannot resurrect an older
version just because the correction is outside the requested event view.
Unknown ordering, missing receipt or temporal conflict stays unresolved. A
later publication does not backfill earlier character access. Later evidence
explicitly supporting an earlier receipt can revise the current reconstruction;
the old recorded-cutoff reconstruction and old actual task result remain intact.

A cognitive perspective includes an optional story-agent ID, nested path, query
time and proposed observation/belief models. It grants no system permission.
The present Bridge checks source/target scope, viewpoint correspondence,
predicate and polarity preservation, every argument's identity mapping,
relative-time mapping, live assumptions/evidence and target-agent receipt for
every material source root. Identity and temporal proof dependencies enter the
result support. Internal program-lineage roots remain in proof/ACL dependencies,
but are not treated as fictional narrative reports requiring impossible receipt
records. A rule-derived claim can project when its actual material reports meet
all receipt obligations. Pure metadata/default support cannot project into a
character view without material evidence. This does not assert that the character
understands or believes the formal rule. Alternative valid receipts remain usable even if another alias
was received too late. Identity retraction removes the projection while leaving
its original source report available.

This establishes only conditional information projection. Private belief,
understanding, higher-order mental-state truth and arbitrary nested-viewpoint
projection are not inferred. Different nested paths remain unresolved. Full
hypothesis-world enumeration is not implemented: a temporal proof or conflict
that combines a declared nogood becomes `HYPOTHESIS_BRANCHING_UNEXPLORED`.
These limits remain visible rather than being reported as definitive negatives.

## QueryDependency and conditional absence

A source-local candidate index records exact source/version, typed program,
queryable claim metadata and mechanical coverage. Index format/version is bound
into snapshots and commits. Exact filters are allowlisted (`kind`, `agent_id`,
`message_id`, `interval_id`, `scope_id`, `claim_id`, `entity_id`). Stable qualified
IDs preserve source-local identity. Claim entity filters must agree with the
claim's actual arguments.

`QueryDependency` binds query parameters, index version and the digest of the
actual authorized matches, coverage and selected source-history view. Query
validation runs at snapshot validation, commit, reservation, send transition,
response persistence, task finish and cached delivery. Fresh delivery leaves
the earlier WAL snapshot before rechecking. A concurrent newly pending source
invalidates cached absence even without changing any old positive read-set.

A default watches actual supported matching claim records. Mere row existence
is not receipt support. Missing/uncompiled sources and mechanically incomplete
programs remain pending; they cannot establish absence. Only complete bounded
indexed coverage with no supported match licenses an explicitly assumed,
conditional indexed-absence support. Its receipt includes the actual query
dependency. A new relevant source first invalidates that result; after real
identity/time/Bridge computation supports the receipt, the default is rebutted.
Unrelated fully compiled evidence can preserve the semantic conclusion hash.
Cyclic negative/default dependencies and unresolved search remain partial.

This is not a closed-world claim about reality or a proof that extraction found
all relevant meanings. All indexes have `semantic_certified=false` at result
level and candidate completeness remains `NOT_ESTABLISHED`. A structurally
valid wrong interpretation can still produce a conditional result.

## Two historical views and current permission

`known_at` is an authenticated session-event revision cutoff. Each source
version records its **first** content-publication event; later ACL updates of
the same version do not move that clock. Hash chains, immutable same-version
objects and the current source projection are verified. Source-version selection
happens before index selection. `indexed_at` is separate: a source-local
interpretation compiled later may reconstruct what the old source said, but
cannot use later source versions or other later inputs of its extraction call.
Uncompiled historical material stays pending until explicitly compiled against
that historical source binding.

A fixed-cutoff reconstruction is distinct from replay of an actually stored
old `TaskResult`. Neither rewrites the latter. `RevisionIssue.known_at` is part
of the exact task fingerprint, so changing it cannot replay another request's
result. Source-only historical selectors are explicit typed dependencies;
ordinary positive version maps retain exact-current-version semantics.

System ACL is always current, including historical reconstruction, replay,
previous-result comparison and rollback views. Every index keeps **all** actual
model-input dependencies, even when it cites just one source. Source spans do
not prove that a model output was uninfluenced by other private inputs. Index
inspection filters those dependencies before reading source-bearing objects.
A shared public/private extraction cannot leak private text through its public
index. Denied results rebuild a source-free receipt; own-task reservation usage
remains visible without leaking other principals' calls.

## Explicit side-copy schema cutover

Default `StateStore.sqlite(path)` still creates schema 1. `revision=True` creates
schema 3 only for a new store; existing schema 1/2 requires
`RevisionCutover.upgrade(source_path, destination_directory, principal)`.
Revision-enabled stores require a version-bound control record. Schema 4 also
retains the imported namespace control and original quarantine package. Existing
codec type fields and ordinary dependency/fingerprint bytes are unchanged.

Upgrade requires the authenticated owner of every session and a supported exact
predecessor bundle. It verifies old hash chains, all projected rows and referenced
objects, then creates a WAL-safe SQLite side-copy under the old writer lock.
It copies original events, tasks, calls, result objects and hashes without
rewriting their meanings. A fsynced intent binds source/target/schema/code/index
versions and a verified checkpoint. The unpublished copy is not executable: revision control binds its one final
published database path, and the ordinary store refuses a staged/relocated path.
A unique preparation directory receives a durable ownership marker before it
becomes the reusable stage, so an initial marker-fsync failure cannot strand
recovery behind an unowned stage.
The source is terminally fenced before target activation and atomic directory
publication; downtime is preferable to two live writers. Only deployment/control
metadata changes in the old database, so the whole old DB is not claimed to be
byte-identical. Original domain rows and objects remain identical.

Recovery uses that exact intent and checkpoint. A pre-fence interruption leaves
the old store as sole writer and can rebuild a changed old prefix. Post-fence
recovery cannot choose another destination, release a budget hold or resend an
unknown call. Concurrent same-target recovery is idempotent; different-target
competition yields one target and one refusal. A terminal-source write lock
serializes the complete activation/publication/receipt tail, and each persisted
file uses a unique temporary name. `SEND_STARTED`/`UNKNOWN`, unknown
usage, owners and leases are retained. No abandoned-owner inference is automatic.

Rollback is terminal read-only on the target; it never reactivates the old
writer. The new ledger remains available for authorized audit. Original-content
views check current target permissions, including quarantined import sources,
and repeat the check outside the content-reading WAL transaction. Object/fsync/
rename failures are safe storage diagnostics and recoverable without double send.
Unknown schema/control versions, corrupt objects and projection drift are rejected.

## Bounds and evidence

Default truth bounds are 256 claims/roots, 512 rules, 256 assumptions, 64 support
alternatives and 100,000 work units. The integrated compiler uses explicit higher
bounded profiles: at most 16 source programs, 512 claims/roots/rules, 64 points,
512 temporal constraints, 256 identities, 64 Bridges and 32 defaults. Derived
truth roots cap at 4,096. Temporal closure has 300,000 relaxations; identity
queries share 100,000 total edge visits and cache exact pair queries. Bridge
combinations, supports and proof lengths are bounded. Actual local-evaluation
and byte budgets apply; partial output records the last **executed** graph,
not a newly proposed but uncomputed one.

Index scans cap at 10,000 rows; history/cutover validation caps at 100,000 events,
4 MiB per object and 128 MiB copied content. These are declared bounded engineering
profiles, not S6 scaling claims or cognitive ceilings. Search exhaustion remains
an unexplored frontier and never justifies certainty or a missing-evidence default.

`tests/test_unified_s22*.py` cover the actual kernels, transactional persistence,
cutover crashes/competition, ACL races and full engine contrasts. Independent
oracles include 1,920 assumption assignments across 120 random truth graphs,
512 derived-root environment/retraction combinations, 125 finite temporal
systems, all 64 four-entity identity graphs, and 32 unseen
end-to-end graph compositions. Fixtures change proposed meanings; actual kernels
and downstream answers change from those meanings rather than matching samples.
`scripts/witness_unified_s22.py` binds actual temporal/identity/default/replay
results and consumed fields to the precise commit and runtime hashes. The
original 1,643 legacy test IDs and 60 diagnostic checks continue through their
existing current/historical partitions, without relaxing any old identity guard,
pin, assertion or current-runtime refusal of historical authority.

Next is the approved S2.3 bounded dynamic operation/feedback/context/recovery
slice and common S3/S4 interface freeze. Full S1/S2 real-model functionality and
all later research/effectiveness requirements remain open. Provider calls,
provider spend and sealed-content reads in this slice are zero.

## Independent-review regressions

The first fixed candidate `68ab2f9` passed its initial focused/legacy checks but
independent review found five real composition/recovery defects: omitted root
assumptions (including incremental withdrawal), executable unpublished stage,
concurrent same-target publication, initial stage-marker fsync recovery, and
rule-derived evidence being mistaken for an unreceivable metadata report. New
regressions reproduced all five before correction; those failures are not
counted as passing evidence. The final regression methods retain those exact
contracts and add valid/invalid temporal/identity/Bridge/default contrasts.
A publication-rename fault test now targets the final destination explicitly
so it still fails after the old writer fence rather than at the newly added
earlier staging-directory rename. Original publication/hold assertions remain.
