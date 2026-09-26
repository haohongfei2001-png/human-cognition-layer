# HCL v0.10 minimal conditional argumentation runtime

Status: provider-free candidate. No efficacy claim.

## Scope and API

`hcl/v10` accepts a complete directed attack graph explicitly supplied by the
caller: Argument nodes, Attack edges and an immutable ArgumentFramework.
Maximum 12 nodes, 144 edges. Arguments are atomic; the solver does not evaluate
premises, infer attacks from disagreement, decide source/value priorities,
learn motives or decide moral truth. It computes the published Dung formal
semantics conditional on a graph: grounded, complete, preferred and stable.

An accepted set attacks a node if any accepted member attacks it. A node is
defended when every attacker is attacked by the set. A complete extension is
conflict-free and equals the nodes it defends. Grounded is the least fixed
point, preferred extensions are maximal complete extensions, and stable
extensions attack every excluded node. Cycles are preserved. Grounded iteration
and every requested labelling are archived; no majority or probability is
assigned to extensions. IN/OUT/UNDEC are formal acceptance labels, not truth,
falsity or a person's belief. Stable semantics may have no extension; skeptical
and credulous queries then return null rather than vacuous acceptance.

`HCLV10Runtime` binds a framework to an existing EventRecord with explicit
`argumentation_scope=DECLARED_COMPLETE_ARGUMENTATION_FRAMEWORK`, exact argument/
attack source quotes and timezone-aware valid/recorded times. Source quotes
alone do not prove semantic entailment: caller/adapter assumptions must remain
visible. It reuses v0.6 source access/bitemporal views. A missing, private or
future graph supplies no framework/trace. It does not delete hidden attackers
and pretend the remaining graph is complete. ID collision fails atomically;
identical replay is idempotent. Separate snapshots are never silently merged,
superseded or used to revise a character's actual belief. There is no new
persistence, natural-language extractor, ASPIC+ priority semantics or PMPM logic.

## Independent correctness

Twelve runtime tests cover reinstatement, mutual and self attack, odd cycles,
multiple alternatives, stable absence, provenance/access/time boundaries,
atomic binding and detached contexts. All 512 three-node directed graphs are
compared against an independent three-valued legal-labelling oracle for complete,
grounded, preferred and stable semantics. Five utility tests verify static
source projection, independent generic execution, source-only query separation,
renamed graph family deduplication and strict answer structure. Existing v0.4–
v0.9 tests join these checks: 126 passed locally before source utility execution.
Synthetic correctness is not external utility or human-cognition efficacy.

The source audit follows correctness; its four public-author-example diagnostic
is documented separately. Full state/calculations/raw answers and exact inputs
will be retained. A wrong provider final answer cannot be rescued by a correct
trace or by relaxing the parser. No provider-backed evidence exists yet.
