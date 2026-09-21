# v0.2.1 holdout failure and same-provider repair

Baseline main: `cbf8987459ace8bbcbd3f5c5ab2426b298a73701`.
Original completed/failure run: [35523303566](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/35523303566).

## Preserved outcome

Eight of ten predeclared pairs completed. Ordinal 48 (job 106111025178)
returned invalid HCL decision JSON after three attempts. Ordinal 88 (job
106111025125) returned an OpenAI missing-key AuthenticationError. Aggregate job
106124671375 failed. There is no valid complete-holdout efficacy conclusion.
The predeclared seed42/combo3/ordinals8,18,28,38,48,58,68,78,88,98 remain intact.
All attempted combinations are consumed diagnostic evidence. Existing run
artifacts and failures are preserved; no selective rescore or replay occurred.

## Routing audit and repair

Pinned upstream `a0aaafb440e570e5e61b7c44a44e5e417c545383` normalizes a custom
source model to `openai/deepseek-flash` but defaults malformed-output repair to
`gpt-5-mini-2025-08-07`. Its repair helper also drops base_url and api_key.
The earlier forwarding-only patch was incomplete: it could send a DeepSeek key
with an unrelated repair model. It is superseded by this guarded patch.

The repository evaluator now explicitly selects the normalized original model.
The pinned patch forwards the original endpoint/key in both parser branches,
and rejects an alternate model/provider identity before repair dispatch for a
custom source. Native providers retain native credential resolution. Source
hash verification refuses upstream drift; reapplying the exact patch is a no-op.
No actual credentials are logged or read by the tests. No new OpenAI credential,
permission, model, temperature, retry budget or benchmark seed is introduced.

The three frozen behavior files remain byte-identical to `f6e591db8d22ae0e2175769852a1a8aa9c3e106a`.
The original workflow applies the patch on a future explicitly triggered run;
this change does not touch the holdout trigger and does not rerun the slice.
Only the evaluator/plumbing changes; the missing-key error is consistent with
this verified fallback defect, but the original run has no complete traceback
proving the exact ordinal88 call chain. We do not claim to repair ordinal48.

## Verification and limits

Local prior AST mock evidence confirmed the dropped routing arguments.
The new integration gate imports the actual pinned SOTOPIA implementation and
exercises malformed generation -> repair -> Pydantic parse, plain parser,
alternate-model rejection, failure retry count, native routing and the actual
HCL evaluator binding. Provider completion calls use synthetic mocks; no private
benchmark or paid model call is made. Remote gate result is pending publication.

The repair can close as infrastructure engineering after exact-head CI; the
original incomplete holdout and HCL efficacy remain unresolved. A future replay
must be separately declared diagnostic/consumed, preserve every attempt, and
must not claim independent fresh evidence.
