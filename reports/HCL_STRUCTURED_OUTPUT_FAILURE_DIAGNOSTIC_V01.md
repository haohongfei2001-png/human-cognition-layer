# HCL Structured-Output Failure Diagnostic v0.1

Status: **PREDECLARED / DIAGNOSTIC ONLY / NO REPAIR**

## Trigger

HCL state-JSON reliability repair v0.1 failed its frozen 24-case validation:

- success: 8 / 24;
- state_json_exhaustion: 16 / 24;
- backend/other exception: 0;
- all state attempts used provider-native JSON mode;
- across failed cases, 27 attempts were empty and 21 were non-empty but not
  accepted as a JSON object.

The v0.1 artifacts intentionally did not persist provider finish metadata or
response text, so the failure classes cannot yet be distinguished.

## Frozen implementation under diagnosis

The diagnostic observes the failed v0.1 repair candidate exactly:

- HCL state semantics remain frozen;
- state schema remains frozen;
- STATE_SYSTEM remains frozen;
- model: deepseek-flash;
- endpoint: existing DeepSeek endpoint;
- seed: 42;
- temperature: 0;
- state max_tokens: 8192;
- response_format: {"type": "json_object"};
- backend non-empty retry budget: 4 provider calls per HCL attempt;
- HCL state retry budget: 3 HCL attempts.

No HCL behavior code is modified by this diagnostic.

## Fixture boundary

Use the exact same 24 repository-owned synthetic fixtures from
eval/answer_loop/state_generation_reliability_v01.json.

No fixture wording, stratum, or ordering changes are allowed.

No Hi-ToM, FANToM, SOTOPIA, or other consumed external benchmark content may
be used.

## Exact request reproduction

For each synthetic case, reproduce the current state-generation request:

1. frozen STATE_SYSTEM;
2. the same synthetic user input;
3. the same state-only suffix used by HCL;
4. on HCL retries 2 and 3, the same invalid-JSON retry suffix;
5. same model/provider/seed/temperature/max_tokens;
6. same JSON response_format;
7. same backend behavior: retry up to 4 provider calls while content is empty;
8. same HCL behavior: retry up to 3 HCL attempts if no JSON object is parsed.

The diagnostic may call the provider directly only to retain response metadata
that the production backend currently discards.

## Content-free provider-call metadata

For every provider call, persist only:

- case ID and frozen stratum metadata;
- HCL attempt ordinal;
- provider-call ordinal within that attempt;
- request duration in milliseconds;
- finish_reason;
- content_is_none;
- response byte length;
- stripped response byte length;
- response SHA-256 when content exists;
- empty_after_strip;
- full-response JSON syntax validity;
- JSON top-level type when syntax-valid;
- current HCL extract_json() object-parse outcome;
- structural booleans: starts/ends with object brace, contains code fence;
- prompt_tokens, completion_tokens, total_tokens;
- provider exception class, if a call raises.

Do not persist synthetic input text, prompt/messages, response text, parsed JSON
body, HCL state, credentials, or exception text.

## Diagnostic categories

Each provider call is classified as one of:

- provider_exception
- empty_length
- empty_stop
- empty_other_finish
- valid_json_object
- valid_json_nonobject
- embedded_object_recoverable
- nonparseable_length
- nonparseable_stop
- nonparseable_other_finish

Empty means stripped response length is zero.

## Interpretation

This diagnostic does not pass or fail a repair.

It must report counts by provider-call category and finish_reason; empty versus
non-empty counts; JSON top-level types; HCL case success/exhaustion counts;
token usage and duration by category; and stratum breakdown.

Evidence relevant to a later v0.2 repair includes:

- finish_reason=length concentration among nonparseable calls: truncation or
  output-budget mechanism;
- finish_reason=stop with syntax-valid non-object JSON: top-level-shape issue;
- finish_reason=stop with malformed non-empty content: provider-format or
  recovery issue;
- empty responses, especially with finish_reason=length and high completion
  token usage: documented JSON-mode whitespace/empty-output mechanism.

No repair v0.2 is authorized until this diagnostic closes.

## Execution

Use 6 shards x 4 frozen cases, max parallelism 3, then aggregate.

All 24 cases must terminate for the canonical diagnostic result. Workflow
success means evidence collection succeeded, not that HCL passed reliability.

## Claim boundary

This diagnostic may identify content-free provider/output mechanisms associated
with the state-generation reliability defect.

It does not establish external benchmark efficacy, semantic quality of generated
cognition states, cross-base transfer, or HCL 1.0 certification.
