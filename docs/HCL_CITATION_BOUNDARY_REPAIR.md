# Three deterministic citation and admission boundary repairs

This source-only repair follows the independently reviewed policy clarification.
It changes two runtime functions, `audit_original_citations` and
`UniversalHCL.put_source`, while preserving all historical runtime/evidence pins.
The defects below were reproduced with authored, provider-free inputs. No paid
answer was rescored or replayed as accepted, and no provider call is authorized.

## 1. Overlapping original quotations were misclassified as unique

In `ha ha ha`, the quote `ha ha` starts at positions 0 and 3. The previous
non-overlapping search found only the first, so missing offsets could produce a
false unique-location claim and a deliverable UniversalHCL answer. Unicode and
whitespace-layout overlap had the same problem.

Location enumeration now uses an escaped lookahead and stops after the second
match, which is sufficient to reject ambiguity. It covers overlapping exact and
whitespace-layout candidates without building a list proportional to repetitions.
An exact supplied offset still disambiguates either occurrence. A wrong or missing
offset on repeated text rejects; a unique quote still relocates when its supplied
offset is wrong. Exact matches continue to take precedence over whitespace-only
alternatives, and the original/submitted text and location mode remain explicit.
No paraphrase, noncontiguous wording, lexical repair or semantic verification is
introduced. The strict citation field schema, including rejection of `end` and
other extra fields, is unchanged.

## 2. The shared reader audit omitted the answer string type

The shared audit checked `uncertainty` and `assumptions`, but not `answer`.
Consequently, the ordinary legacy reader could deliver a JSON object containing
`answer: null`, an array or another non-string value. UniversalHCL already had a
separate string check and was not bypassed by this defect.

The shared audit now requires all three prose fields to be strings. The existing
explicit cannot-support fallback remains when reader delivery fails; the original
raw output stays separately available and is never coerced or reclassified. This
adds no retry, model call or hidden rewrite. Empty strings remain structurally
valid; semantic adequacy is still unassessed.

## 3. Source admission disagreed with the final source-ID boundary

UniversalHCL accepted a 129-character source ID even though final original-source
review rejects IDs longer than 128 characters. A scripted valid flow consumed its
two phases before that deterministic frame rejection.

Admission now checks the existing final boundary first: a nonempty string of at
most 128 Unicode characters. It rejects an oversized ID before modifying source
state or invoking a backend. Exact 128-character IDs, including multibyte Chinese
and supplementary-plane emoji, preserve identity and normal revision behavior.
There is no truncation, alias substitution, byte-length or UTF-16 interpretation.
The final review bound itself is unchanged.

## Verification and limits

Eleven new authored tests cover missing/wrong overlap offsets, valid explicit
0/3 offsets, Unicode overlap, whitespace ambiguity, unique relocation, early
second-match termination, legacy non-string answers, unchanged raw rejection,
strict fields and 128/129-character admission/revision boundaries. Existing
citation schema and complete-frame budget tests continue to apply.

The new amendment imports every prior historical byte pin and validates consumed
archives. It reconstructs the exact previous whole-runtime digest by restoring
only the two reviewed file hashes, and separately verifies byte identity outside
the two scoped functions. Current witness imports advance; old reports, grants,
failed answers, executable packages and independent review artifacts do not.

The policy-only PR353 record accurately describes its own unchanged validator;
this later amendment explicitly changes the three boundaries described here.
Neither engineering result establishes live model compliance, semantic answer
quality or efficacy. The campaign remains eleven calls and US$0.69163776 retained
full reservations, with all completed sub-runs closed and no new paid sequence.
