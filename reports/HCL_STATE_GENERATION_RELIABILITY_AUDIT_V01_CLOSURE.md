# HCL State-Generation Reliability Audit v0.1 — Closure

## Decision

**STATE JSON RELIABILITY DEFECT ESTABLISHED**

The predeclared defect threshold was met decisively before the workflow timeout.

## Canonical run

- workflow: `HCL State-Generation Reliability Audit v0.1`
- run: `35685106840`
- launch commit: `8c3141f2256ed954d523bed3a9e63364ef03fbff`
- terminal result: **CANCELLED by 120-minute job timeout**
- zero-provider preflight: **PASS**
- HCL behavior freeze: **PASS**
- audit protocol freeze: **PASS**
- artifact upload: **not reached**
- persisted summary artifact: **none**

The lack of an uploaded artifact is a workflow-completeness limitation, not a
failure of the predeclared defect criterion. The job log itself contains the
content-free per-case status lines emitted by the frozen runner.

## Observed execution before timeout

The workflow completed **22 of 24** synthetic cases before cancellation.

Observed terminal per-case classifications:
- success: **4**
- `state_json_exhaustion`: **18**
- `backend_or_other_exception`: **0**
- not reached before timeout: **2**

Every observed `state_json_exhaustion` case exhausted exactly **3 HCL-level
state-generation attempts**.

Observed by stratum:
- short / simple: 0 success, **4 state_json_exhaustion**
- short / recursive: 1 success, **3 state_json_exhaustion**
- medium / simple: 0 success, **4 state_json_exhaustion**
- medium / recursive: 2 success, **2 state_json_exhaustion**
- long / simple: 1 success, **3 state_json_exhaustion**
- long / recursive: 0 success, **2 state_json_exhaustion**, 2 not reached

The runner reached `sgr_long_recursive_02` and was cancelled before the final
two long/recursive cases.

## Predeclared gate

The audit predeclared:

- at least 2 distinct `state_json_exhaustion` cases ->
  state-generation JSON reliability defect established;
- at least 2 distinct `backend_or_other_exception` cases ->
  backend/transport/other reliability defect established.

Observed:
- distinct state-json exhaustion cases: **18**
- backend/other exception cases: **0**

Therefore:

**predeclared interpretation =
STATE_JSON_RELIABILITY_DEFECT_ESTABLISHED**

This conclusion is monotonic with respect to the two unobserved cases: the
threshold was exceeded by sixteen cases before timeout, so completing the final
two cases cannot invalidate the established JSON defect.

## Relation to Hi-ToM v0.1

Hi-ToM v0.1 had:
- 60 selected rows;
- 36 completed paired rows;
- 24 persisted `RuntimeError` failures;
- efficacy not evaluable.

Those consumed Hi-ToM artifacts did not persist exception text and therefore
could not prove the exact RuntimeError cause.

This independent synthetic audit now reproduces the abstract failure class
without using any Hi-ToM content:
- frozen real `HCLAnswerLoop.build_state()`;
- frozen real DeepSeek backend;
- repository-owned synthetic inputs;
- repeated exhaustion after three unparseable state-generation attempts.

This establishes that the HCL state-generation JSON path has a genuine,
repeatable reliability defect.

It does **not** prove that every one of the 24 Hi-ToM RuntimeErrors had the same
cause. That claim remains unsupported because the Hi-ToM artifacts did not
persist the needed exception detail.

## Timeout interpretation

The audit job timed out because 24 cases were executed serially and many cases
required three provider-backed state attempts.

The timeout prevented:
- final two synthetic cases;
- post-run artifact validation;
- artifact upload.

The timeout does not authorize treating runtime duration as a separate
provider/transport defect. No `backend_or_other_exception` was observed in the
22 completed cases.

A future regression workflow should be structured to finish reliably, for
example by bounded sharding or per-call timeout, without changing the semantic
test cases or the defect criterion.

## Repair authorization boundary

This closure authorizes a **separate independent repair round** for the abstract
state-generation JSON reliability defect.

The repair must not:
- use consumed Hi-ToM content;
- tune against Hi-ToM outcomes;
- weaken the always-on HCL doctrine;
- change HCL v0.3 cognition semantics unless separately justified;
- silently bypass state generation.

A valid repair should target only the abstract reliability mechanism, such as:
- structured-output enforcement where supported;
- robust generic JSON extraction/recovery;
- bounded retry/fallback behavior;
- transport/request timeout so one provider call cannot stall the audit;
- content-free diagnostic preservation.

Any repair must first pass:
1. zero-provider unit tests for JSON/retry/fallback invariants;
2. the same independent synthetic reliability suite;
3. existing HCL state-fidelity regressions;
4. existing answer-loop/checker regressions;
5. the prior independent output-interface audit.

Only after those gates pass may new external evidence be consumed.

## Claim boundary

Supported:
- a repeatable HCL state-generation JSON reliability defect exists under the
  frozen DeepSeek-backed HCL v0.3 state builder.

Not supported:
- Hi-ToM efficacy gain or regression;
- attribution of all 24 Hi-ToM RuntimeErrors to this exact cause;
- provider/transport defect;
- cross-base transfer;
- HCL 1.0 certification.
