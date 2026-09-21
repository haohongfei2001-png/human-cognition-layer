# Ordinal 48 Provider-Attempt Diagnostic Result

## Boundary

This is a diagnostic replay of already-consumed expanded ordinal `48`.

It does **not**:
- complete the original 8/10 holdout;
- restore freshness;
- provide an efficacy result;
- change frozen HCL behavior.

Predeclaration:
`reports/ORDINAL48_PROVIDER_ATTEMPT_DIAGNOSTIC_PREDECLARATION.md`

## Canonical run

- run: `35588167021`
- launch commit: `1409f159c57fdb1aab4f959b7e4a2a405c48228b`
- artifact: `10634471138`
- artifact SHA-256:
  `2f17a73edb80bf65ef947691d173309ffbccd0c39cfc9ceb27902546f92d537d`
- setting: environment ordinal `9`, combo ordinal `3`, expanded ordinal `48`
- seed: `42`
- treatment only
- attempts executed: **2 / 2**
- final episode outcome: **failure**
- both attempts reproduced the exact frozen RuntimeError:
  `HCL decision policy returned no valid JSON after 3 attempts`

The workflow is green because diagnostic evidence was collected and passed
privacy/integrity checks. It does not mean ordinal 48 passed.

## Aggregate provider-attempt evidence

Across both bounded episode attempts:

- Decision Policy wrapper events: **14**
- underlying provider-attempt events: **37**
- provider attempts with non-empty final content: **7**
- provider attempts with empty final content: **30**
- transport exceptions: **0**

For **all 30** empty-final-content provider attempts:

- `finish_reason = "length"`
- `content_bytes = 0`
- `completion_tokens = 4096`
- `reasoning_tokens = 4096`
- separate reasoning content was present, typically about 15.7–17.9 KB
- requested `max_tokens = 4096`

For all observed successful non-empty provider attempts:

- `finish_reason = "stop"`
- final content was non-empty
- reasoning token use remained below the 4096 ceiling
- observed reasoning-token counts ranged approximately **1537–3443**
- observed total completion-token counts remained below 4096.

No provider-attempt event ended in a transport exception.

## Episode attempt 1

The first two Decision Policy backend calls succeeded:

- backend call 1:
  - `finish_reason=stop`
  - content: 1356 bytes
  - reasoning: 3184 tokens
  - completion: 3557 tokens
- backend call 2:
  - `finish_reason=stop`
  - content: 1611 bytes
  - reasoning: 3443 tokens
  - completion: 3865 tokens

Then the failing Decision Policy invocation exhausted all three outer JSON
attempts.

For backend calls 3, 4 and 5:
- each backend call made all four allowed provider requests;
- every provider request ended `finish_reason=length`;
- every provider request consumed exactly 4096 reasoning/completion tokens;
- every provider request returned **0 bytes final content**.

Therefore the failing turn produced **12 consecutive provider completions** in
which the entire 4096-token output budget was consumed by reasoning and no
final-answer content was emitted.

Classification:
**reasoning-output-budget exhaustion**

## Episode attempt 2

The same failure class reproduced.

Several early Decision Policy calls succeeded with `finish_reason=stop`.
At the failing region:

- multiple backend calls again produced four consecutive
  `finish_reason=length` / 4096-reasoning-token / 0-content responses;
- one backend call recovered on its third provider attempt with
  `finish_reason=stop`, reasoning 2533 tokens and non-empty final content;
- later backend calls again exhausted the complete 4096-token budget as
  reasoning on all four provider attempts.

The episode still terminated with the same frozen no-valid-JSON RuntimeError.

Classification:
**reasoning-output-budget exhaustion**

## Root cause

**ROOT CAUSE CONFIRMED: the Decision Policy completion budget is too small for
the provider's default thinking mode on this late-turn context.**

The current transport gives Decision Policy:

`max_tokens = 4096`

DeepSeek thinking mode emits reasoning separately from final `content`, but the
generated-token budget includes the reasoning process. In the reproduced
failures the model reaches exactly 4096 reasoning/completion tokens with
`finish_reason=length`; final content is therefore empty.

This explains why:

- the parser sees no JSON object;
- the backend retries four times;
- the outer Decision Policy retries up to three times;
- the same failure can persist despite healthy credentials and transport;
- provider routing repair does not resolve ordinal 48.

The earlier single non-empty/non-parseable wrapper observation is real historical
diagnostic evidence, but it is not the dominant reproduced failure. Provider-
attempt replay establishes output-budget exhaustion as the repeated structural
cause.

## External API consistency check

Current DeepSeek API documentation states that:

- thinking mode is enabled by default;
- reasoning is returned separately as `reasoning_content`;
- `max_tokens` bounds generated completion tokens;
- `finish_reason="length"` means generation hit the configured output/context
  limit;
- when `max_tokens` is omitted, the provider default in thinking mode is much
  larger than this project's explicit 4096 cap.

The telemetry is therefore consistent with documented provider semantics.

## What is ruled out

The reproduced primary failure is **not** explained by:

- missing OpenAI credentials;
- same-provider routing failure;
- a network/transport exception;
- HCL state-semantic corruption;
- an Action Checker failure;
- a single stochastic malformed JSON response;
- insufficient retry count as the primary mechanism.

Increasing retry count at the same 4096-token cap would simply repeat a failure
mode already observed across many provider attempts.

## Minimal repair candidate

The narrowest behavior-preserving candidate is:

> increase **Decision Policy only** from `max_tokens=4096` to a bounded
> `max_tokens=8192`.

Keep unchanged:
- model/provider/endpoint/key;
- thinking mode;
- seed;
- prompt and Decision Policy semantics;
- outer three JSON attempts;
- inner four empty-content attempts;
- HCL cognition state;
- Action Checker;
- all other backends.

Why 8192:
- it is the smallest simple doubling of the exact exhausted ceiling;
- it preserves the provider's existing reasoning behavior rather than reducing
  reasoning effort or disabling thinking;
- it remains far below the provider's normal thinking-mode output allowance;
- it can be independently gated before any external validation.

This is a **candidate**, not an authorized runtime change.

## Cost boundary

Changing 4096 to 8192 increases the maximum billable output-token envelope.

The existing implementation can issue up to 12 provider requests for one
Decision Policy `build_plan` failure:
- 4 provider attempts per backend call;
- 3 outer Decision Policy JSON attempts.

Therefore a 4096→8192 change can raise the theoretical worst-case generated-
token ceiling for a single failing `build_plan` from 49,152 to 98,304 output
tokens, although successful calls return early and the observed repair may
reduce repeated failed calls in practice.

Per the project execution authority, this is a **cost-boundary change** and must
not be enabled without owner authorization.

## Required validation after authorization

If the owner authorizes the bounded output-budget amendment:

1. freeze a v0.2.1a amendment with only Decision Policy output budget changed;
2. add no-network forwarding tests for exactly 8192 on Decision Policy only;
3. rerun all existing independent Decision Policy synthetic suites;
4. rerun Action Checker regression;
5. run SOTOPIA custom-agent smoke;
6. replay consumed ordinal 48 only as diagnostic evidence to verify the failure
   class is removed;
7. only after those gates decide whether any new external validation is
   methodologically justified.

Do not start a new holdout merely because ordinal 48 diagnostic replay succeeds.
