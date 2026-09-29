# H01 — Query-directed planner

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.

**CAPABILITY_DELTA:** The same ordinary authorized source now takes different
execution paths according to the user's actual question. A single narrator
fact query returns only exact source reports with no specialized cognition
operation. A concept question uses G03; an opposed-speaker question uses the
G03→G04 dependency chain; an explicit one-factor hypothetical uses
G03→G04→G05. The planner executes those existing operations, saves their
actual cognition state for the final model and refuses a complex question if
its required operation, depth or branch budget is insufficient. It does not
stack every module on every question.

`QueryDirectedWorkspace` uses one versioned, access-controlled source domain.
It selects source-local speakers, an explicit known-at timestamp or line-prefix
cutoff from the ordinary question, and records declared versus used depth,
branch, operation and provider-call budgets. Provider-call budget is zero in
this provider-free adapter. The simple path preserves exact narrator quotes,
source spans and versions; no match means only no *selected* report, not world
absence. Complex paths reuse G03–G05 rather than building another ontology.
The G03 extension surfaces active local criteria even when no item application
is present, enabling an actual “what does this person mean?” answer path.

The planner recognizes deliberately bounded question forms. Unsupported or
ambiguous questions, unbound/later speakers, unavailable source/time, excess
reports, and inadequate budgets fail explicitly. Source correction or access
change invalidates saved final model input. The planner never infers a private
mental state or moral truth from a selected source statement. It is
provider-free replay evidence, not broad natural-language routing efficacy.

The [ordinary witness](../reports/HCL_WAVE_H01_WITNESS.json) shows all four
paths over the same text and their actual final model messages. Twelve
targeted tests cover positive routing, simple path, negative inference,
ordinary time selection, source-prefix noninterference, budgets, access and
correction. Full v1 and historical regressions remain required at exact head
and main. Provider calls/spend: zero. LongMemEval sealed. NEXT_READY: H02
finite rival explanations and discriminating evidence retrieval.
