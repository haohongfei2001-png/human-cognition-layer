# Ordinary final-delivery diagnostics

## Change and limits

The next runtime adds `final_delivery_code` to the receipt returned by
`UniversalHCL.answer`. It records which existing final-output gate was reached.
It is populated by the actual ordinary runtime, not a detached diagnostic helper.

The codes contain no answer, source, planner output, exception text, parser
offset, field value or inferred model intention:

| Code | Meaning |
|---|---|
| `NOT_REACHED` | No final text returned successfully from the metered allowance. This does not mean that no backend invocation occurred. |
| `RETURNED_UNVALIDATED` | Final text returned, but validation did not finish at a categorized gate, including a subsequent source/support change or unexpected parser/auditor failure. |
| `JSON_INVALID` | The existing final JSON parse raised `JSONDecodeError`. |
| `SCHEMA_INVALID` | The existing top-level final-answer schema check rejected the object. |
| `ANSWER_BLANK` | The existing Unicode-whitespace nonblank guard rejected the answer. |
| `SOURCE_REVIEW_REJECTED` | The existing supplied-source audit or source-free empty-citation rule rejected delivery. This deliberately does not invent a finer citation diagnosis. |
| `DELIVERED` | The existing runtime delivery checks accepted the unchanged final text. This is not semantic certification. |

Every existing receipt field, acceptance/rejection predicate, ordering, final
prompt, answer byte string, citation check, source-currentness check, allowance,
reservation and retry behavior is preserved. In particular, JSON errors are
re-raised unchanged, so the existing generic failure classification remains.
No malformed output is repaired and no additional model call is made.

Only this fixed enum is content-free. The full receipt still contains private
fields such as `answer_raw`, sources and planning results; it is not a public
export. Existing public exporters and their authorized field whitelists remain
unchanged. A future public exporter would require its own reviewed scope.

This is a diagnosability change. It does not establish better final-answer
quality, higher delivery rate, module utility or HCL efficacy.

## Historical/runtime separation

The predecessor is immutable commit
`9c0fb6164860150a2d03c39f0804c51f9ba0c47f`, runtime
`90737b3ed772f65851553d8a673112eae50f2781185d8b5b4ccd127cdfb8663b`.

The new amendment pins the changed runtime file and restores its predecessor
hash to prove that no other runtime file or membership changed. It retains all
161 predecessor history pins and additionally pins the consumed G05/four-case
scripts, execution manifests, evidence, scores, frozen inputs, workflows and
closed grants, plus the predecessor nonblank record. Existing historical bytes
are never rewritten to match the new runtime.

Current ordinary regressions use the new validator; 11 witness scripts and 10
test files receive import-only retargets. The current-runtime CI validator
commands are retargeted. Consumed G05/four-case tests and their exact package
reconstruction run separately in a fresh detached worktree at the predecessor
commit. The replay invokes only fixed offline unittest modules, removes provider
credentials from the child environment and blocks socket connection/DNS entry
points. No historical executor CLI or live trigger is launched. Missing Git
history, altered preserved files, failed tests or nonzero/open grants fail the
check; they are not skipped.

The consumed G05 and four-case grant balances stay at zero. Original evidence,
the unavailable D01 output, locked scores and the 38/40 versus 30/40 historical
result are unchanged.

## Proven contract difference, deferred

Synthetic tests establish a contract difference, not the cause of historical
D01 failure. The ordinary prompt and source audit permit a citation object with
omitted `version`, a quote string with exactly one source, and `start: null`.
The frozen four-case canonical export rejects those forms. Ordinary empty
citation arrays also remain valid, while that trial explicitly requires a cited
answer for acceptance. Conversely, its export can retain `end` for an invalid
answer, while the runtime citation audit rejects that field.

These behaviors are preserved in paired regression tests. No export whitelist,
prompt, schema or score is adjusted here. No absent raw/private response is
reconstructed, and none of these synthetic cases is asserted to explain D01.

## Verification

- Paired tests load the exact predecessor `universal_entry.py` Git blob after
  checking its SHA256. Its dependencies are unchanged, enforced by the runtime
  amendment. They compare entire receipts after removing only the new field,
  plus exact prompts, raw answers, backend calls, journals, reservations and
  allowance closure state under an identical fixed ingestion clock.
- Cases cover every code, gate precedence, Unicode and JSON whitespace, duplicate
  JSON keys, nonstandard JSON constants, schema injection, source revision and
  withdrawal, unexpected parser/auditor errors, metering/journal failures, exact
  output bounds and the unchanged ordinary/export contract differences.
- Canary tests ensure exception text cannot enter the new enum or existing safe
  failure fields. Existing bounded raw-answer retention is not mislabeled as
  secret-free output.
- Mutation tests reject changes to preserved historical files, the new pin
  manifest, unrelated runtime files and runtime membership.

Run from the repository root:

```sh
python -m unittest tests.test_v1_final_delivery_diagnostics
python -m unittest discover -s tests -p 'test_v1*.py'
python -m scripts.development_final_delivery_amendment
python -m scripts.development_final_delivery_history
```

The full provider-free CI also runs its existing ordinary witnesses and earlier
runtime regression suites. Synthetic metering amounts are test fixtures, not
provider spending. This patch authorizes zero additional calls or budget.
