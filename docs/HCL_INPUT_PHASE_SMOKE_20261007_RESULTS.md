# Input-phase smoke stopped before final generation

The [single approved input-phase smoke](HCL_INPUT_PHASE_SMOKE_20261007.md) ran
once on the explicit-mode runtime. It failed to obtain relevant checked native
processing. The new strict gate stopped before reserving or sending a final
request. This demonstrates that stopping control; it does not demonstrate useful
selection or end-to-end reliability.

The model selected B01 with input_mode=literal and no semantic_candidates, B02,
and D02. Actual B01 and B02 readers executed but returned checked_treatment_present
false. D02 rejected the unchanged source. The exact planning request contained
both code-owned B02/D02 source/version blockers; neither hint was omitted for
capacity. Source IDs, a mode label and a completed reader invocation did not
create the missing typed premises or satisfy the frozen relevant-treatment gate.

Only planning was called. It returned finish_reason=stop, 6,511 prompt tokens,
5,589 completion tokens, provider-reported reasoning_tokens=5,256 and 1,505
visible content characters. Its complete request was 31,035 bytes, below the
unchanged 36,000-byte ceiling. The run took approximately 43.85 seconds. There was
no final reservation, request, response or answer. The new final 16,384/low setting
therefore remains untested by this run; there is no evidence of a final-token
failure or success here.

## Original evidence and independent review

- [Run 37683890181](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37683890181),
  attempt 1, workflow 377801912. M `1615a5e649032d8227c46fa3e6cc3f97cff59bf7`
  has sole parent G `f93a110056016de60933cc94cbdd90fd82162e55`; E is
  `d47936f4c410ce9ff9dee6ef32c7068b25c23330`.
- Runtime SHA256 `112cfcd6749bd5c4216aaf580ad3608da85bda5d4d5bc017ebb04ade27aa8e7f`.
  [Frozen package](../.github/frozen/hcl-input-phase-smoke-20261007/package.json)
  canonical SHA256 `24134c0d0c78e22a1a2c3c4df3779fcd8944571831efeda0689c7ee327c62548`.
  The original source, question and rubric remain byte-identical.
- Artifact 11509668898, 5,343-byte ZIP, SHA256
  `cbda36700ce90f8a5090b53ac321bdacf535e83254fe0e6b44999a08057dbd04`, verified
  against GitHub metadata before extracting the sole named public JSON.
- [Original public evidence](../reports/HCL_INPUT_PHASE_SMOKE_20261007_1_PUBLIC_EVIDENCE.json),
  23,275 bytes, raw SHA256
  `e446487a54bc186df89dd1d27488259691fbfc54ef319c8d98a34dbfbf1c87c6`, canonical
  `2cccb0186a25cb4ccc967587be6355e6dab7f650b69860a0e4b4b419e216e1b4`.
  The bounded native record retains all three actual argument/result objects,
  including the rejected operation, with source, projection and receipt bindings.
  No replacement candidates, planner reply or internal reasoning are published.

The [independent source-first review](../reports/HCL_INPUT_PHASE_SMOKE_20261007_1_SOURCE_REVIEW.json)
has overall_pass=false. All ten obligations and four smoke checks are explicitly
not evaluable because no final exists; they are not invented incorrect-answer
findings. The existing frozen RELEVANT_REAL_NATIVE_TREATMENT_ABSENT tag describes
the observed unchecked native outcomes, not an answer contradiction. End-to-end
source and policy gates remain unproved because final delivery never happened;
planning source integrity, exact request identity and native publication/replay
binding were independently verified. The exact frozen validator rejects this
receipt with PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED.
Review raw SHA256 `7c30b3216a5408e49715647107a451e395e5ed221b5a8cf1560343cabfa58b62`,
canonical `8e975646b91e997d62316e6567feee12cf3b6d8a9c149e0df0b1aef3b430dde7`.

## Cost and closure

One real call used **CNY 0.209502 at the prechecked peak-rate estimate**, not a
verified invoice: `(6511 * 9 + 5589 * 27) / 1000000`. The conservative full hold
was CNY 1.109664, not a claimed provider charge. The
[new grant](../.github/HCL_INPUT_PHASE_SMOKE_20261007_1_GRANT.json) is
CLOSED_NO_TRANSFER_NO_RETRY with zero remaining call or spending authority. Its
original READY canonical SHA256
`9cea04f8df923839fabf04b0084743bbf00eb6ae8792fd76410f6c1c7fe47f95` remains at M.
The unused second call and remaining ceiling cannot fund another attempt. There
is no second stage. The original 600-second stage and 180-second request/dispatch
bounds remained in force, without a calendar cutoff.

Workflow success means the bounded execution and approved export completed.
The experiment remains a failed exposed regression, with no Base comparison,
unseen-case evidence, general benefit claim or formal I02-I06 advancement.

## Next free repair

Provider-free reconstruction matches the actual complete planning-request hash.
The current plan validator requires a consistent explicit mode, but still accepts
literal mode without proving that the source has the corresponding literal
premises. Source-entry blockers are separate observations rather than enforced
selection constraints. These are observable interface limitations; one response
does not establish why the model chose those operations or that a shorter prompt
would improve it.

Next work will expose code-generated executable entry/mode contracts and enforce
only proven necessary source conditions. Faithful semantic input remains the
model's responsibility, and ordinary evidence-limited answers remain possible.
Positive and negative cases must preserve valid literal, semantic and honest
insufficiency paths across source versions. Earlier rejection alone cannot count
as improved selection. No new paid run is authorized by this closeout, which
changes no runtime, frozen package, prior grant/report or HCLA.
