# HCL State-JSON Reliability Repair v0.1 — Closure

## Decision

**REPAIR FAILED**

Provider-native JSON mode alone does not repair the independently established
HCL state-generation reliability defect.

## Canonical validation

- workflow: `HCL State-JSON Reliability Repair v0.1 Validation`
- run: `35695318437`
- launch commit: `a8788e2ee9a190e1b9ffc84e21580ad8a324b1bd`
- terminal result: **FAILURE**
- preflight: **SUCCESS**
- all 6 validation shards: **SUCCESS as evidence collection**
- aggregate: **SUCCESS**
- predeclared repair pass gate: **FAIL**
- summary artifact: `10682620073`
- summary digest:
  `sha256:9612c98b22472c3c1427fa3126c2e1ac6ed60687252a01499419b368cba41efb`

## Frozen repair

The candidate repair:
- added provider-native `response_format={"type":"json_object"}` only for HCL
  state generation;
- kept ordinary draft/check/revision completion in text mode;
- kept HCL v0.3 state semantics, schema and STATE_SYSTEM unchanged;
- kept the HCL-level retry budget at 3;
- used the exact same 24 independent synthetic reliability fixtures.

## Result

Across all 24 frozen synthetic cases:
- success: **8 / 24**
- failure: **16 / 24**
- `state_json_exhaustion`: **16**
- `backend_or_other_exception`: **0**
- all observed state attempts used structured JSON mode: **true**
- repair pass: **false**

By stratum:
- short/simple: 0/4 success
- short/recursive: 1/4 success
- medium/simple: 0/4 success
- medium/recursive: 3/4 success
- long/simple: 4/4 success
- long/recursive: 0/4 success

The predeclared pass gate required:
- 24/24 success;
- 0 state JSON exhaustion;
- 0 other exception;
- structured mode on every state attempt.

The candidate therefore fails decisively.

## Content-free attempt diagnosis

Across the 16 failed cases:
- 48 HCL-level state attempts total;
- all 48 used structured JSON mode;
- **27 attempts returned empty content**;
- **21 attempts returned non-empty content that still was not accepted as a
  JSON object**;
- no backend exception class was observed.

All 16 failed cases exhausted exactly 3 HCL-level attempts.

This establishes that enabling provider-native JSON mode is insufficient by
itself.

The evidence identifies two runtime phenomena that require independent,
content-free diagnosis:
1. empty structured-mode responses;
2. non-empty but non-parseable structured-mode responses.

The persisted artifacts intentionally do not contain response text, so the
second class cannot yet be subdivided into truncation, malformed syntax,
prose/code-fence wrapping, or another structural failure.

## Relation to the original audit

Original frozen audit before repair:
- 22 cases reached before timeout;
- 4 successes;
- 18 state-json exhaustion failures.

v0.1 repair validation:
- all 24 cases completed;
- 8 successes;
- 16 state-json exhaustion failures.

This suggests a bounded reliability improvement is possible, but the strict
repair gate is not close to satisfied and no repair-success claim is allowed.

## Next methodological gate

Do not consume new external benchmark evidence.

Before proposing repair v0.2:
1. preserve the v0.1 failure as historical evidence;
2. run a **content-free structured-output failure diagnostic** on independent
   synthetic inputs;
3. record provider response metadata sufficient to distinguish:
   - empty content;
   - finish reason / truncation;
   - response byte length;
   - JSON parse outcome;
   - provider request/response exception class;
   without persisting response text;
4. determine whether max-token exhaustion or another provider-side condition
   explains the non-empty non-parseable class;
5. only then predeclare a minimal repair v0.2.

Consumed Hi-ToM content remains forbidden for diagnosis or tuning.

## Claim boundary

Supported:
- provider-native JSON mode alone is insufficient;
- the state JSON reliability defect remains active;
- both empty structured responses and non-empty non-parseable responses occur.

Not supported:
- exact textual cause of non-parseable outputs;
- Hi-ToM efficacy;
- provider/transport defect;
- HCL 1.0 certification.
