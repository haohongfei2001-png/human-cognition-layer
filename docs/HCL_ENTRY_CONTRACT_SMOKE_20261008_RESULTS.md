# Executable-entry smoke stopped before native execution

The [one approved October 8 smoke](HCL_ENTRY_CONTRACT_SMOKE_20261008.md)
ran once on the executable-entry runtime. One planning response returned, but no
accepted nonempty plan reached native dispatch. There was no final reservation,
request or answer. The exposed regression failed and all remaining authority
closed. This does not establish accurate operation selection or useful treatment.

The complete planning request was exactly 28,338 bytes, SHA256
`947e2de2c71bd542cf877b45ea5dea85aeb08023393214bfe08e4bc2c8bf1913`.
It retained the original question, full source and code-owned source/version
entry contract. The response reported finish_reason=stop, 5,911 prompt tokens,
10,676 completion tokens, 10,168 reasoning tokens and 2,219 visible characters.
Token usage is provider-reported; visible characters are measured from returned
content. No internal reasoning text is retained here.
The planning response was below the 16,384-token allowance. This evidence does
not support a token-limit or transport-failure explanation.

The public arm status is BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE.
The frozen exporter combines multiple safe failures into that class and does
not retain the precise validation code. Empty accepted-selection and native
records cannot reveal the model's intended operations. Under the frozen normal
control flow, plan parsing/validation failure and a valid empty plan are both
compatible with this record. A native adapter failure is not established: the
normal adapter rejection path would preserve the selected operation and outcome.
The exact rejected field, anchor, capability and model rationale remain unknown.

## Original evidence and independent review

- [Run 37717484248](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37717484248),
  attempt 1, workflow 377987939. M `b370e651b9e612f1138a4d27e14ade58a95fad25`
  has sole parent G `bc7cb0c5554f751b8299c7f451469bb2589a8fc9`; E is
  `0355622680cc4551e0d820f86c83c74c3ef60bff`.
- Runtime SHA256 `50e62d02790f165d1d73fc3275fc6f795da7582b9f81143eaa7aa69806660d16`.
  [Frozen package](../.github/frozen/hcl-entry-contract-smoke-20261008/package.json)
  canonical SHA256 `cb2ea842c2869cd233a80bcb9716efe94cf4181ee2af080b06cdbbfb489d89e2`.
  The source, question and original ten-obligation/four-smoke rubric are unchanged.
- Artifact 11524333170, 3,356-byte ZIP, SHA256
  `90bbb10d01744397575558e23c79f263d8fdd19c5bd4fda3d3a19ac25668c30a`, verified
  against GitHub metadata before extracting its sole named public JSON.
- [Original public evidence](../reports/HCL_ENTRY_CONTRACT_SMOKE_20261008_1_PUBLIC_EVIDENCE.json),
  raw SHA256 `7457af2769c5d4dc00b99c550173e9e4518e28cc9e0e69846da2029accbeb13a`,
  canonical `cf08729d0d273411ebd26a3497e07689fbe19d02db4f1d698de45428928ffa1b`.
  Its single bounded synthetic native record has zero operations and source,
  projection and receipt bindings. CAPTURED/VALIDATED describes that empty
  capture's integrity; it is not evidence of native processing. Likewise, avoiding
  listed blockers with no accepted operations does not establish correct routing.

The [independent source-first review](../reports/HCL_ENTRY_CONTRACT_SMOKE_20261008_1_SOURCE_REVIEW.json)
has overall_pass=false. All ten obligations and four smoke checks explicitly
say NOT_EVALUABLE_NO_FINAL. Their false booleans mean not demonstrated; they do
not assert that a nonexistent answer was semantically incorrect. No semantic
answer score is reported. Relevant real native treatment is absent. End-to-end
source and native-policy preservation remain unproved because no native/final
composition occurred; planning source/request integrity was separately verified.
The exact frozen gate rejects the receipt with
PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED, including with a fabricated
affirmative review. The final 16,384/low configuration remains untested.

## Cost and closure

One real call used **CNY 0.341451 at the prechecked peak-rate estimate**, not an
invoice: `(5911 * 9 + 10676 * 27) / 1000000`. The conservative full hold was
CNY 1.109664; the exact-request reservation was CNY 0.971748. Neither is a claimed
provider charge. The [new grant](../.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_1_GRANT.json)
is CLOSED_NO_TRANSFER_NO_RETRY with zero remaining call or spending authority.
Its original READY canonical SHA256
`3c4202973be714e7af1adf6594bdd6900823c74511fd078bf5e1e70a79e557b7` remains at M.
The unused second call and remaining ceiling cannot fund another attempt. There
is no second stage. The 600-second stage and 180-second request/dispatch bounds
remained in force, without a calendar cutoff. The run lasted about 138.82 seconds.

The owner separately approved publication of this budget record, marker, PR
descriptions and closure at 02:00:48 UTC. That permission did not reset the
00:10:20 experiment approval, call count or CNY 2.30 ceiling. No account balance,
credential, full planner reply, internal reasoning or private user data is included.

Workflow success means bounded execution and approved export completed. The
experiment remains a failed exposed regression, with no Base comparison,
unseen-case evidence, general benefit claim or formal I02-I06 advancement.

## Next free work

Keep the original failure immutable. Preserve code-owned failure enums and
orchestration stages in future diagnostic records, without copying provider
text. Any interface repair must follow a reproducible general input-contract
defect and preserve source, version, native-treatment and final-delivery gates.
No specific model mistake can be reconstructed from the missing diagnostics.
No further paid attempt is authorized by this closeout. It changes no runtime,
frozen package, earlier grant/report, launch marker or HCLA component.
