# I02 — source-first semantic scorer v1

Status: **PROVIDER-FREE SCORER INTERFACE FROZEN / NO CONFIRMATION SOURCE OR OUTCOME INSPECTED**.
The [machine-readable rubric](../reports/HCL_I02_SEMANTIC_SCORER_FREEZE.json)
and [executable validator](../scripts/serious_eval_semantic_score.py) fix
eight general dimensions and weights before independent confirmation. They
apply to the same four-field open answer contract for C/P/G/H. This is an
evaluation instrument, not a model prompt or an HCL cognition mechanism.

The source auditor first writes a case manifest from authorized original
sources alone. Each obligation records an exact source quotation, a semantic
question and whether the output should **state**, **qualify** or **avoid** a
claim. The manifest binds to the rubric hash and declares that no arm output
was seen. A different reviewer then sees the original source and an opaque
output ID, not an arm name, and marks every obligation satisfied, violated or
unresolved with a reason and an exact output excerpt where applicable. The
scorer validates source quotations, citations (accepting the historical
`quote`/`quotation` variants), complete reviews and arithmetic. Missing or
unresolved items earn zero; a violated weight-three boundary makes an answer
ineligible. Citation fabrication makes scoring fail closed.

The exposed Moral Stories calibration showed why **supported goal** and
**unproved harmful intent** need distinct review items. A correct refusal to
infer harmful intent cannot erase the source's explicitly reported goal.
Other fixed dimensions cover actor/time/access, alternative paths,
counterevidence, conditional norms, concept scope and precise uncertainty.
The synthetic tests demonstrate one ordinary source with alternate plans:
preserving a stated safety goal scores differently from omitting it, while
inventing harmful intent is a critical failure. They also check fabricated
source or output quotations, arm-name leakage and incomplete reviews.

The code **does not determine semantic truth** and a Boolean declaration
cannot prove that a human auditor was blind or worked before outputs. I03
needs an auditable independent source-audit workflow, reviewer blinding,
calibration, sample-size and model-family freeze. A source-specific manifest
must never enter any model input. No C/P/G/H provider call, confirmation
outcome or LongMemEval row was used here. Historical frozen prompts, runtime,
receipts and dispositions remain unchanged.

**EVALUATION_DELTA:** I02 can now compute a consistent, fail-closed score from
blinded source-first reviews, including a distinct penalty for omitted
explicit facts and critical unsupported private-state upgrades. **HCL answer
CAPABILITY_DELTA:** none; I02 is measuring the completed architecture.

**NEXT_READY:** qualify independent source diversity and a protected
confirmation split before any I03 comparison. Do not select cases because H
appears to win or reuse either spent C/P/G calibration grant.
