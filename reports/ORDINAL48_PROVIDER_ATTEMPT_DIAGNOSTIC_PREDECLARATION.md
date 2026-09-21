# Ordinal 48 Provider-Attempt Metadata Diagnostic Predeclaration

Status: **DIAGNOSTIC ONLY — NO BEHAVIOR REPAIR**

## Motivation

Consumed diagnostic run `35585685155` reproduced the ordinal48 frozen
Decision Policy failure twice.

The dominant wrapper-level result was empty final content. However
`OpenAICompatibleBackend.complete()` internally performs up to four provider
requests per wrapper call, and the existing observer sees only the returned
string. It cannot identify why the provider-level final content is empty.

## Fixed execution

Use the same consumed setting and boundaries:

- environment ordinal: `9`
- combo ordinal: `3`
- expanded ordinal: `48`
- seed: `42`
- HCL treatment only
- model/provider: `custom/deepseek-flash@https://api.deepseek.com`
- existing DeepSeek credential only
- pinned SOTOPIA commit unchanged
- same-provider evaluator repair unchanged
- maximum two episode attempts, stop after first success
- existing four provider attempts per backend `complete()`
- existing three Decision Policy JSON attempts
- temperature/max_tokens/prompt/model/seed unchanged.

This is already-consumed diagnostic evidence, not fresh evidence or holdout
completion.

## Provider-attempt observer

Add an opt-in runner-only wrapper enabled only by
`HCL_PROVIDER_ATTEMPT_DIAGNOSTICS=1`.

For each of the backend's existing provider requests it may record only:

- provider attempt ordinal within the current backend call;
- requested max_tokens and temperature;
- finish_reason;
- final content byte count + SHA256;
- reasoning-content byte count + SHA256 when the response exposes a separate
  reasoning field;
- refusal byte count + SHA256 when exposed;
- prompt_tokens / completion_tokens / total_tokens;
- reasoning_tokens when exposed;
- transport-exception outcome without exception text.

It must not record prompt text, response text, reasoning text, refusal text,
persona, transcript, credentials or provider exception text.

## Transparency requirement

The provider-attempt wrapper must preserve exactly:

1. the same maximum four provider requests;
2. the same request arguments/model/seed;
3. immediate return on the first non-empty final content;
4. final empty return after four empty final contents;
5. original exception identity and propagation;
6. no retry caused by observer/sink failure.

Synthetic no-network tests must compare wrapped and unwrapped transport
semantics before any real diagnostic replay.

## Interpretation target

The replay is intended to distinguish, without exposing content:

- `finish_reason=length` with substantial reasoning usage and empty final
  content;
- `finish_reason=stop` with empty content;
- empty final content accompanied by separate reasoning content;
- provider usage anomalies;
- provider transport exceptions;
- non-empty malformed final content.

No behavior-bearing repair is authorized until this metadata is collected and
audited.
