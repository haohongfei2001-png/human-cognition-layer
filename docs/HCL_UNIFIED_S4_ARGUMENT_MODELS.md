# S4 work in progress: executable structured argument models

This increment starts the approved S4/M13 argument mechanism on main
`8e25a2c91dba20aea2f0128069b9ca7df69a724b` / PR #430. S3 continues in parallel.
It does not close M13, S4 or any full acceptance family. M10–M14, M03–M09,
S1–S7, P01–P38, T01–T32 and all original research and migration exits remain
unchanged. In particular, a finite argument solver does not replace conceptual
feedback, reflective equilibrium, literary understanding or ethical judgment.

## Actual entry and source boundary

The same HCL run/run_sync/stream engine accepts an ExecutionIssue goal
`argument.evaluate`. A source-anchored `argument-model-1` LocalModel is compiled
from proposed scoped literals, strict/ordinary premises, strict/defeasible rules,
explicit priorities, assumptions and questions. The proposal cannot contain
acceptance labels, attack/defeat matrices, preferred extensions or precomputed
critical edits. No new persistent dataclass or alternate runtime is introduced.

Ordinary source and question text are retained exactly. Every premise, rule and
priority requires authorized source spans; question spans cannot become facts.
Duplicate IDs/fields, foreign anchors, invalid Unicode, undeclared undercut rule
names, priority cycles and unaccounted source material fail safely. Explicit
unmodeled fragments remain in the result and keep it partial. Competing models
have separate source/model/frame scope identities; their proofs cannot mix.
The proposal's `source_id` is its namespace source and must itself have an actual
item/query anchor. It is not attribution of every fact to that one source.
Legitimate multi-source models retain host-created exact segment bindings
(source/version/digest/character and byte ranges), actual input source versions,
and each literal/premise/rule/priority/query record's anchors. Each proof retains
the union of the premise/rule/literal spans it used. Priorities and opposing
proofs remain separate acceptance dependencies in the full model records. The
compact delivery retains these bindings and names all actual input sources;
secondary-source ACL revocation also blocks replay. An unmodeled-only namespace
source does not satisfy the anchoring requirement.

Model assumptions propagate into every constructed proof, in addition to each
premise/rule's own conditions. Withdrawal actually removes dependent arguments.

The installed model port still injects test reconstructions. These are unverified
interpretations of source, not demonstrated open reconstruction or premise-truth
judgments. A source quote and an executable argument are not philosophical truth.
All final claims retain this conditional boundary and NOT_ESTABLISHED candidate
completeness. M04 discovery and M12 concept suppliers are not replaced by mocks.

## Structured arguments, attacks and defeats

`operators/argumentation.py` constructs rooted finite proof trees. An argument
retains its conclusion, top rule/premise, child proofs, complete subargument set,
root premises, rules, priority bases and assumption environment. Its identifier
binds those actual contents, not just a candidate's name. Rootless support cycles
do not produce arguments. The current construction explicitly excludes proof
paths that repeat a rule or conclusion; excluded circular fragments are reported
and keep the integrated answer partial rather than claiming unrestricted proof
completeness. This is a finite acyclic-proof scope, not every possible logic.
The durable and compact results always retain acceptance_scope, fixed-point
iterations and excluded_circular_rules, including empty/not-computed values.
The answer states the acyclic and declared-edit scope and names excluded rules;
a COMPLETE query inside that scope cannot imply unrestricted completeness.

Attacks are computed from scoped contraries and explicit rule applicability:
- undermining targets an ordinary premise;
- rebuttal targets a defeasible conclusion;
- undercutting targets a named defeasible rule.

An attack on a subargument propagates to all of its superarguments. Attack and
defeat are separate. An explicit acyclic strict-priority relation may block
undermining/rebuttal under the declared last-link-style comparison; it never
blocks an undercut. Unknown/incomparable priorities are not broken by ID order.
Strict contradictory roots are preserved as a visible inconsistent core. No
explosion rule is added, and the integrated result remains partial.

The chosen lifting of item priorities is an explicit versioned local semantics,
not a claim to implement every structured-argumentation framework or universal
rationality postulate. Strict premises/rules are assumptions of the proposed
model, not source assertions that the system has independently proved true.

## Acceptance and genuinely computed critical changes

Grounded acceptance is the least fixed point of the defense characteristic
operator over the actual defeat graph. It is not rooted support, vote counting,
a chosen winner, or the intersection of preferred extensions. The output retains
IN/OUT/UNDEC labels and the fixed-point iterations. A query separately reports
accepted support and accepted contrary support, including neither/both cases.

Optional preferred-extension computation enumerates finite admissible sets and
checks actual set-maximality. Until enumeration is complete, it returns only
explicit admissible witnesses and a frontier; it cannot certify preferred or
skeptical acceptance. Work and witness storage are bounded. An independent
three-valued complete-labelling oracle checks all 530 directed graphs of one to
three nodes, including self attacks, against both grounded and preferred results.
The four-node counterexample with empty grounded extension but a nonempty
intersection of preferred extensions is retained.

A requested critical-retraction search removes only named hypothetical premise
or rule items. It never modifies original source. It reruns argument construction,
attacks, defeat and grounded acceptance for every smaller edit subset before
returning a minimum-cardinality witness. Its scope is the declared finite edit
set and the query's support/opposition pair; it is not global minimality across
arbitrary reinterpretations, priorities or concept edits. Search exhaustion is
unknown, not evidence that no important change exists. Two independent supports
require two removals in the corresponding oracle, rather than a greedy claim.

## Delivery, resources and old-state preservation

The operator returns an actual InferenceResult/Delta through the frozen common
protocol. The controller alone commits. Full proof/attack/defeat/search objects
remain in the durable result. Final delivery consumes exact query values,
labels, conditions and computed critical edits, and checks that claimed accepted
proof IDs really have IN labels and the requested scoped conclusion. It cannot
substitute an injected acceptance answer or reuse an uncommitted operation.

Compilation currently bounds four models, 128 literals, 64 premises, 64 rules,
128 priority edges and 16 queries per model. Runtime proof count is 256 with
100,000 explicit solver work units per batch. Preferred search additionally has
24 arguments and 256 stored maximal-so-far admissible witnesses; a frontier is
visible when these limits bind. Critical search is limited to 12 explicitly
selected premise/rule IDs and its own bounded recomputation work. The shared
execution budget counts solver batches; their internal bounded loops are not
misreported as one CPU instruction. This is not S6 scale or latency acceptance.

The existing shared call/byte/output budgets, unknown-send holds, committed-
operation hashes, immutable snapshots, source read sets and fresh ACL delivery
checks remain active. RETURNED candidate recovery reuses the response without a
new send. Late revocation clears argument content and all projections, including
on cached stream replay. Old argument data is not silently imported as true.

Side-copy migration adds only the exact published S3 finite runtime hash
`5087d2f8bb75441bd176fa715f50fcb46709d877e23322d7ecf0765b9fc39ee8`
from its 173 inventoried runtime Python files. Earlier S2.2/S2.3 allowlist entries
stay exact. Real old-runtime tests retain the codec bytes, events, effects,
completed finite/FOL/mental results, RETURNED/UNKNOWN and computed/committed
checkpoints. Unknown calls do not resend or lose holds; old writers are fenced;
source/ACL history remains authoritative. No old authorization or pins change.

## Evidence and remaining full obligations

`tests/test_unified_s4_argumentation.py` and `test_unified_s4_engine.py` cover
independent finite graph oracles, subargument attacks, priorities, undercuts,
actual critical edits, ordinary-input integration, changed assumptions/priority,
unrelated conclusion preservation, scope isolation, inconsistent strict cores,
resource frontiers, source anchors, actual claim consumption, recovery and ACL.
`test_unified_s4_upgrade.py` uses a real fixed predecessor projection.
`scripts/witness_unified_s4.py` records exact head/runtime hashes, actual argument
values and consumed answer fields under contrasting source interpretations.

Full M13 still requires its M06/M12 countermodel/concept links, broader genuine
counterexample/model edits and reflective-equilibrium mechanism with consistency,
coverage and edit costs. M04 is the single shared residual-guided supplier; its
absence is not disguised as a fixture implementation. S4/M10 external-memory
query closure, M11 literary/formal effects, M12 concepts/analogy/induction and
M14 feasibility/Pareto/framework/responsibility remain required. Full S3, S5's
five-domain chain, S6 scale, real-model ordinary-input functionality and S7's
independent confirmation remain open. Provider calls/spend and sealed reads are
zero; no service, credential or historical grant is created or expanded.
