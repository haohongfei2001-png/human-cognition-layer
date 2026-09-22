# HCL Structured-Output Failure Diagnostic v0.1 — Closure

## Decision

**OUTPUT-BUDGET EXHAUSTION MECHANISM ESTABLISHED**

The content-free provider diagnostic completed all 24 frozen synthetic cases and
identified a single dominant execution mechanism behind the failed v0.1 repair:
the provider almost always consumes the full 8192 completion-token budget and
terminates with `finish_reason="length"` before returning a usable state JSON.

## Canonical run

- workflow: `HCL Structured-Output Failure Diagnostic v0.1`
- run: `35702581717`
- launch commit: `cace86e54a33a93ab763489ea898e4be5def1617`
- terminal conclusion: **SUCCESS**
- preflight: **SUCCESS**
- diagnostic shards: **6 / 6 SUCCESS**
- aggregate: **SUCCESS**
- summary artifact: `10685496277`
- summary digest:
  `sha256:98596af2cf71216d5dea8753adc54525ac57488479540b19fcff966b156743a3`

Workflow success means evidence collection succeeded; it is not an HCL
reliability pass.

## Case-level result

Across the same 24 frozen repository-owned synthetic cases:

- case success: **2 / 24**
- case failure: **22 / 24**
- `state_json_exhaustion`: **22**
- provider-exception cases: **0**

By stratum:
- short/simple: 0/4 success
- short/recursive: 0/4 success
- medium/simple: 0/4 success
- medium/recursive: 1/4 success
- long/simple: 1/4 success
- long/recursive: 0/4 success

The diagnostic run is observational and is not compared as an efficacy result
against the prior repair run because provider sampling/runtime behavior can
vary between runs.

## Provider-call result

Total bottom-level provider calls: **191**

Categories:
- `empty_length`: **149**
- `nonparseable_length`: **40**
- `valid_json_object`: **2**
- all other categories: **0**

Finish reasons:
- `length`: **189**
- `stop`: **2**

Therefore:
- **98.95%** of provider calls ended by output-length exhaustion;
- every failed/non-usable provider call ended with `finish_reason="length"`;
- both usable provider calls ended normally with `finish_reason="stop"`.

## Token-budget evidence

For all 189 `finish_reason="length"` calls:

- completion_tokens: **8192 / 8192 / 8192** (min / median / max)

For the 149 empty-length calls:
- completion_tokens: exactly **8192** on every call;
- response bytes: exactly **0** on every call.

For the 40 nonparseable-length calls:
- completion_tokens: exactly **8192** on every call;
- response bytes: 30 to 10621;
- median response bytes: 3520.5.

For the 2 valid JSON-object calls:
- finish_reason: `stop`;
- completion_tokens: 6825 and 7888;
- response bytes: 6649 and 6893.

This establishes that the current state-generation request is not primarily
failing because the parser rejects otherwise complete output. It overwhelmingly
fails because the provider reaches the configured completion-token ceiling
before producing a complete usable JSON object.

## Empty-output interpretation

The diagnostic also explains the previously observed empty structured-mode
responses:

- all **149** empty provider calls ended with `finish_reason="length"`;
- all consumed exactly **8192 completion tokens**;
- none ended with `stop`.

Thus the empty-output class is part of the same output-budget exhaustion
mechanism, not an independent zero-byte transport exception.

The current diagnostic did not persist provider reasoning-token subfields.
Therefore it does not establish whether the consumed completion budget was
spent on hidden reasoning, whitespace, another provider-internal token class, or
a combination of those mechanisms.

## Non-empty malformed interpretation

All **40** non-empty but non-parseable calls also:

- ended with `finish_reason="length"`;
- consumed exactly **8192 completion tokens**.

Therefore the evidence supports truncation as the direct structural reason that
these outputs were incomplete.

There is no evidence in this run for:
- malformed output ending normally with `stop`;
- syntax-valid non-object JSON;
- parser-recoverable wrapped JSON;
- provider exception failures.

## Consequence for repair strategy

Repair v0.2 should target the output-budget / generation-efficiency mechanism,
not generic parser broadening.

A valid v0.2 design must be separately predeclared before implementation.

Candidate mechanisms that may be investigated without changing cognition
semantics include:
- reduce the state-output verbosity while preserving the frozen semantic fields;
- use a provider capability or model mode that constrains hidden reasoning /
  token expenditure if available and independently justified;
- increase the state completion budget only if the provider/model supports a
  larger bounded limit and cost/runtime implications are predeclared;
- split state construction into bounded structured stages only if semantic
  equivalence can be demonstrated.

Do not simply increase retries: repeated calls currently reproduce the same
budget-exhaustion mechanism at high cost.

## Frozen boundaries

This closure does not authorize:
- changing HCL v0.3 cognition semantics;
- changing the state schema;
- weakening always-on HCL;
- tuning against consumed Hi-ToM / FANToM / SOTOPIA rows;
- consuming new external benchmark evidence;
- declaring the v0.1 repair successful.

## Next gate

Before repair v0.2 implementation:

1. predeclare an output-budget-focused repair design;
2. preserve state semantics and schema unless separately justified;
3. add zero-provider tests proving semantic/schema invariants;
4. validate on the same independent 24-case synthetic reliability suite;
5. require 24/24 state-generation success and zero runtime failures before
   broader regressions;
6. only after repair reliability and regression gates pass may fresh external
   evidence be consumed.

## Claim boundary

Supported:
- the failed v0.1 repair's dominant state-generation failure mechanism is
  completion-token budget exhaustion at 8192 tokens;
- empty and non-empty malformed outputs are both associated with the same
  `finish_reason="length"` mechanism in this diagnostic;
- generic parser broadening is not supported as the primary next repair.

Not supported:
- the internal reason the provider consumed 8192 completion tokens;
- external benchmark efficacy;
- cross-base transfer;
- HCL 1.0 certification.
