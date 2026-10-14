# M14: exact bounded conditional weight domains

Status: **INTEGRATED_OFFLINE_PARTIAL**. Formal scope remains
`HCL_SYSTEM_REDESIGN_SPEC.md` M14 computation §3/§5, output value sensitivity,
and rational interval/sensitivity analysis (§implementation), T17/T18. This is
an additive finite executable slice, not full M14/S4, moral truth or live effect.

## Explicit v5 contract

`hcl-judgment-candidates-5` / `judgment-model-5` contains unchanged v1 `models`
and 1–4 `weight_domains`. Each domain names its exact source/model/decision/
framework and a source-qualified origin and segment references. Its target
framework explicitly retains `weights: null` / `PARETO`; the domain separately
declares `EXPECTED` or `MAXIMIN`. No representative point is substituted into
that fixed model. v1–v4, ordinary PARETO, `critical_retractions`, persistent-1/2,
proof-capsule-1 and pinned original commitment meanings retain their old semantics.

A domain has 1–4 dimensions, nonnegative rational weights with sum exactly one,
and at most 16 rational linear `LE`, `LT`, or `EQ` constraints. Each constraint
has a unique ID, all dimension coefficients, rational right hand side and actual
framework source anchors. Coefficients inherit the existing finite rational
bounds. Empty, lower-dimensional, open and closed domains are all explicit.
The compiler binds host session/principal, source versions/full source hashes,
frame, actor, time and target identity. Reconstructed origins never authenticate
user adoption. Domain proposals contain no scores, winners or coverage claims.

## Real computation and proof

The one ordinary runner and store invoke the actual shared M03/M05/M07/M13
computation once. Facts, action opportunities, commitments, hard norms, and
joint M13 preferred extensions are never synthesized independently for weights.
Each branch uses its actual jointly feasible/permitted outcomes. A weight
cannot compensate a violated or unresolved hard duty.

Eliminate the final normalized weight and arrange every nonconstant rational
score-difference hyperplane. Incremental `<`, `=`, `>` splits enumerate all
nonempty cells, including every lower-dimensional tie. Exact strict
Fourier–Motzkin elimination yields a rational primal witness or a nonnegative
linear-combination contradiction. An algebra-only verifier checks every such
certificate. The split tree records all three children and their nonempty/empty
proofs, providing exact feasibility, boundaries, disjointness and full coverage.
No floating point, fixed grid, random sample, external optimization service or
production recommendation call is used as a mathematical oracle.

Inside a cell every relevant score sign is fixed. EXPECTED requires one actual
explicit joint probability scenario (or one retained actual state). MAXIMIN
first scalarizes every actual joint scenario, then takes each action's minimum;
its point-specific scenario Pareto filter excludes maximin-tied but dominated
actions. Worst-scenario switches are retained. Numeric dimension losses/gains,
hard exclusions and joint branch dissent remain visible in final claim fields.
Two-weight cells are additionally merged into maximal intervals with identical
recommendations; all exact open/closed endpoints and ties are retained. Higher-
dimensional output exposes the exact linear cells, not just a list of winners.

For X=(10,0), Y=(6,6), Z=(0,10), the solver derives
`[0,2/5): Z`, `{2/5}: Y,Z`, `(2/5,3/5): Y`, `{3/5}: X,Y`, `(3/5,1]: X`.
On `[9/20,11/20]`, Y is uniquely robust. The whole simplex has no robust winner.
For A=(10,0)/(0,10), B=(4,4)/(4,4), MAXIMIN recommends A on the **closed**
interval `[2/5,3/5]`: B is tied in the worst scenario at each endpoint but
strictly dominated in another actual scenario. An empty domain never produces
vacuous robust or possible recommendations.

## Quantifiers, bounds, unknowns and delivery

`robust_recommended` means membership in the recommendation set for **every**
weight in the nonempty domain and every completely computed joint norm branch.
`unique_robust_recommended` additionally requires the same singleton throughout.
`possible_recommended` is the union of exact cells across complete branches.
Incomplete upstream knowledge/norm applicability or argument enumeration blocks
these global claims. Local complete cells and pending feasibility certificates
remain conditional candidates; no empty-intersection convention certifies them.
Different declared frameworks/domains remain separate analyses.

One local allowance meters program validation reservation, constraint generation,
hyperplane construction, strict feasibility elimination, sign enumeration,
comparison and primal/dual verification. Inputs too large to verify within that
allowance return `WEIGHT_VALIDATION_FRONTIER` before full replay. After successful
binding, exhaustion retains the conditional frontier. At most 256 cells and a
bounded per-branch proof are retained; the existing 4 MiB final audit cap and
128 MiB migration cap are unchanged. Full deterministic replay verifies actual
result fields and metadata before current-ACL checked delivery. This cache is
never an authorization token; stale source versions and revoked secondary
sources remain blocked. UNKNOWN send reservations never resend themselves.

## Exact predecessor and equivalent-cost regression

The sole added predecessor pin is shipped main
`0d025dfc733b72a7515c2516ee231ed04936453d`, tree
`0a38795bd7df646cdd3210bf8b8de55442171fbb`, 233 inventoried `hcl/**/*.py` files,
code hash `ceb99bffedbc109a038973fae8258c8a202d52abbd30ab556902ce78e7b1d5fc`.
All older pins remain. Independent old processes, not current runtime objects,
create schema-3/4 stores with v1/v2/v3 and v4 min/ties/nochange/PARTIAL at
completed/returned/UNKNOWN/computed/committed seams. Real v3 capsule-1 adoption
and two-subscriber successors cover completed/computed/committed, original task
and object bytes, expected-head CAS, zero resend, current ACL/erasure and old
writer terminal fences. The new persistent fixtures use three positive examples,
both counterexamples, five candidates and a unique two-pattern minimum at every
seam; the older full fourteen-candidate matrix remains unchanged.

To keep the full unchanged regression and extra predecessor coverage within the
existing 60-minute job, migration can reuse **successful structural decoding of
identical complete bytes only within one `_upgrade` call**. Every stage still
rechecks files, sizes, symlinks, current hashes, database events/projections,
governance, ACL, erasure and fences. Legacy root bytes are decoded and semantically
validated every time. No decoded mutable object, source authorization or proof
judgment is cached. The byte set is bounded at 128 MiB, cleared in `finally`, and
never survives a crash/retry or different migration. Changed bytes or failed
validation cannot hit it. Cache/no-cache performance and equivalence are checked
separately, without reducing historical or new-pin coverage or increasing CI
parallelism, timeout, provider access or spend.

Tests: `test_unified_weight_region_math`, `test_unified_weight_regions`,
`test_unified_weight_region_upgrade`, `test_unified_migration_decode_cache`.
The independent continuous rational-breakpoint oracle derives all crossings and
open intervals; full runner tests exercise three-dimensional delivery, provenance,
fixed upstream values, hard obligations, budgets, tampering, stream/reopen,
recovery and current access. `witness_unified_weight_regions` binds the exact
checked commit and runtime source hashes to computed final fields. No live model,
sealed content, paid service, automatic preference inference or adoption is used.
