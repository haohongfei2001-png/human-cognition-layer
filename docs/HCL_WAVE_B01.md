# B01 — Distinct epistemic objects and bounded nested attribution

**CAPABILITY_DELTA:** from an ordinary reported conversation, HCL can now compare
“Mira believes Noor believes p” with Noor's own denial of p, while retaining who
is attributing which attitude. Outer denial and inner denial produce different
results. Withdrawing Noor's evidence invalidates the comparison and Noor's
interpretation, not Mira's independent report.

`prepare_epistemic(workspace, ordinary_question, source_ids=(...))` reuses A02
source binding. A bounded ordinary question selects a holder path; the entry
constructs nested `MentalProposition` objects only within a declared depth budget
(default 3, maximum 4). This is a tree operation and a real two-source-expression
join, not an access-intersection label. `bundle.messages` carries the actual
current query projection, attribution comparison and evidence channels.

The operators remain distinct: belief, exposure claim, understanding claim,
knowledge claim and third-party reported attribution. Bare speech produces a
public expression only. An explicit self-belief report can support a **conditional
private-belief hypothesis**, carrying an unverified sincerity assumption and a
separate scope; it never establishes the person's private belief. “I know p” does
not prove p. Hearing that Noor believes p does not become Mira believing Noor
believes p. First-person reference inside a nested quoted clause stays bound to
the actual quoted speaker, not automatically to the immediately enclosing holder.

Outer `DENY/UNCERTAIN` blocks inner projection; neither is converted into the
inner person's denial/uncertainty. Third-party attribution stays under its
reporter's scope. Same names across documents are not implicit aliases. Ambiguous
or indefinite speakers, conditional speech, hidden sources and over-depth
expressions remain unresolved rather than becoming unsupported mental facts.

[Reproducer](../scripts/witness_epistemic_objects.py) /
[receipt](../reports/HCL_WAVE_B01_WITNESS.json) saves before/after actual final
inputs. Fifteen targeted tests cover positive nested joins, query selection,
renaming/paraphrase, modal separation, polarity scope, negative inference, hidden
source non-interference, depth limits, withdrawal composition and historical
boundary reuse. Full v1 and 176 historical regressions remain exact-head/main CI
requirements; the new witness is included in the same exact-SHA artifact.

**State:** CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN.
No provider calls/spend. Local speech/modal grammar remains bounded; ordinary
parser operation is not broad language efficacy or independent evidence.
Historical dispositions are unchanged. **NEXT_READY: B02** differentiated
communication/access updates, followed by B03–B05 under the canonical dependency
plan. No benchmark/source hunt or per-package paid comparison is required.
