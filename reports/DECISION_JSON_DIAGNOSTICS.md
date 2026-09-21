# Decision JSON failure diagnostics

Execution: HCL-JSON-DIAGNOSTICS-20260921-aem01.
Base main: e57039c5565f5c8313557d03dccca44a00fbef86.

## Observed gap

Original holdout35523303566 job106111025178 reports ordinal48 failed with
`HCL decision policy returned no valid JSON after 3 attempts`.
Its preserved log does not distinguish empty output from a non-object or
unparseable response and records no provider finish reason. No exact cause,
truncation diagnosis, or efficacy conclusion follows from that message alone.
Ordinal88 routing repair remains separately certified; original8/10 is incomplete.

## Bounded implementation

An optional runner-only transport observer is enabled by
`HCL_DECISION_DIAGNOSTICS=1`. It wraps only the Decision Policy backend after
seed42 has been assigned; cognition/action checking retain their original backend.
The default is off. No workflow enables it or launches a benchmark in this change.

It records call ordinal, requested max_tokens/temperature, output byte count,
SHA256 and one coarse result (accepted object / empty / no parseable object).
A transport exception records only that fact. It never emits the request,
response text, parsed fields, credentials, provider error text or persona.

Every call forwards exactly once, returns the identical original object and
propagates the original exception. Observation/sink failures cannot trigger a
retry or replace the outcome. Frozen normalization, prompt, seed and three-attempt
limit remain unchanged; no provider credentials are introduced or read by the observer.

An accepted object means the unchanged extractor found a dictionary; it does not
mean the decision is correct or satisfies an experimental promotion gate.
A no-parseable-object observation cannot prove truncation. Provider finish reasons
are unavailable through the current backend interface and remain unobserved.

## Validation and boundary

Synthetic tests exercise actual HCLDecisionPolicy and the actual runner factory,
with fake transports and agent profiles: exact forwarding, original return/error,
three invalid outputs, unchanged retry messages/normalization, sink failure,
metadata-only output, default-off and decision-only opt-in. Existing same-provider
integration tests remain required. No SOTOPIA dataset, model call or holdout replay
is part of this certification.

The three frozen behavior files are byte-identical to the prior certified baseline.
This is observability plumbing permitted by the freeze; it neither fixes ordinal48
nor releases the incomplete efficacy gate. Any later replay must be separately
recorded as already-consumed diagnostic evidence, never fresh evidence. No new
holdout, seed or product/credential boundary is authorized by this document.

## Published certification

PR2 candidate `ac95f4f33e65d5cf6ca2e10051f9f33aa352bd04` passed run
`35558285692` and independent read-only review. Runtime main
`88a6322ea5f32afa437cece39665e20110e016c0` passed exact-main run
`35558532085`: both sets of 6 tests and the frozen-behavior comparison.
Links: [PR2](https://github.com/haohongfei2001-png/human-cognition-layer/pull/2),
[main certification](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/35558532085).
This final documentation records that runtime certification without creating
a recursive requirement to certify a later documentation-only commit.
