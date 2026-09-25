# HCL v0.6 Minimal Perspective & Belief Runtime Closure

Status: **IMPLEMENTATION COMPLETE / PROVIDER-FREE CERTIFIED / EXTERNAL EFFICACY NOT YET ESTABLISHED**

## Runtime commit and certification

Runtime merge:
- main commit: `9d632cfeea469555ef2896740fa43ed99aa467bc`
- merged PR: #56

Provider-free certification:
- PR exact-head run: `36125213746` — **SUCCESS**
- main exact-head run: `36125320225` — **SUCCESS**

Both runs completed:
- Python compile for `hcl/v06`;
- v0.6 capability correctness suite;
- frozen v0.5 current-stance regression;
- v0.5 semantic-runtime regression.

No provider-backed benchmark call was made.

## Capability added

The new runtime implements:

1. **First-order character information perspective**
   - character-visible events are bounded by actor / recipient / observer / public access;
   - reader-only narrator evidence is not leaked into character-visible context.

2. **Bounded second-order perspective**
   - supports what A has evidence that B could access;
   - does not recurse arbitrarily.

3. **Belief-evidence provenance**
   - SELF_REPORT;
   - NARRATOR_ASSERTION;
   - THIRD_PARTY_REPORT;
   - OBSERVED_ACTION;
   - INFORMATION_EXPOSURE for challenge receipt.

4. **Distinct epistemic states**
   - CHARACTER_UNCERTAIN;
   - SYSTEM_INSUFFICIENT;
   - AFFIRMED / DENIED / SUPERSEDED / CONFLICT.

5. **Belief revision semantics**
   - receiving counterevidence does not automatically erase or suspend an existing belief;
   - explicit direct revision may supersede a prior proposition;
   - indirect reports and actions remain indirect rather than becoming private-belief truth.

6. **Perspective-bounded downstream answer context**
   - separates target-visible world/information evidence from external HCL evidence about the target's belief;
   - narrator knowledge may establish a reader-level belief estimate without becoming character-visible world evidence;
   - second-order answering keeps observer-visible belief evidence separate from what the observer can establish the target had access to.

## Important v0.5 relationship

v0.5 remains frozen.

This milestone does not reinterpret or rewrite historical v0.5 results. In
particular, v0.5 `REVISION_EXPOSURE` behavior remains part of the frozen
explicit-stance state machine. v0.6 introduces a separate belief semantics so
that an information challenge is not automatically treated as a psychological
belief change.

## What is now established

Established:
- the new mechanism exists as executable code;
- its information-boundary and belief-revision invariants pass provider-free
  correctness tests;
- frozen v0.5 stance/semantic tests still pass.

Not established:
- that v0.6 improves FANToM or any external benchmark;
- that the semantic extractor is sufficiently accurate on open narrative text;
- that the capability transfers across model families;
- that this minimal mechanism outperforms a thin prompt scaffold or competent
  generic structured state;
- broader emotion, motivation, relationship, moral, literary or philosophical
  cognition.

## Next step

The next step should be a **small external utility check**, not additional
architecture expansion.

Use the already frozen eight unconsumed FANToM development conversations to
compare:
- C: strong direct reasoning;
- P: thin perspective scaffold;
- D: this frozen minimal v0.6 runtime.

The goal is to determine whether D fixes real information-perspective / belief
errors beyond a thin scaffold. If D does not add value, simplify or revise the
mechanism before expanding into further human-cognition capabilities.

A competent generic G remains important for the later efficacy stage, but does
not need to block the first bounded C/P/D utility check.

LongMemEval remains frozen and unconsumed.

**Current gate: HCL_V06_MINIMAL_RUNTIME_COMPLETE_EXTERNAL_CPD_UTILITY_CHECK_NEXT**
