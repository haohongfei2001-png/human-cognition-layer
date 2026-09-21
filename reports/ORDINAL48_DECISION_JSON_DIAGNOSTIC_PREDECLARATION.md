# Ordinal 48 Decision-JSON Bounded Diagnostic Replay Predeclaration

Status: **DIAGNOSTIC ONLY — CONSUMED SETTING, NOT FRESH EVIDENCE**

## Purpose

Determine whether the preserved ordinal 48 failure

`HCL decision policy returned no valid JSON after 3 attempts`

can be classified with the already-certified content-free Decision Policy
observer.

This replay is not a new holdout and cannot repair, complete, rescore, or
promote the original 8/10 post-repair holdout.

## Fixed setting

Before execution:

- original holdout run: `35523303566`
- environment ordinal: `9`
- combo ordinal: `3`
- expanded ordinal: `48`
- generation seed: `42`
- treatment only: `HCLSocialAgent`
- model/provider: `custom/deepseek-flash@https://api.deepseek.com`
- existing `DEEPSEEK_API_KEY` GitHub secret only
- pinned SOTOPIA commit: `a0aaafb440e570e5e61b7c44a44e5e417c545383`
- same-provider output-repair patch: applied exactly as certified
- `HCL_DECISION_DIAGNOSTICS=1`

No control arm is replayed because control already completed in the consumed
holdout and is irrelevant to identifying the treatment Decision Policy
serialization failure.

## Retry boundary

The diagnostic reproducer mirrors the historical episode retry ceiling:

- maximum **2 treatment episode attempts**;
- each HCL Decision Policy call retains the frozen internal maximum of
  **3 JSON attempts**;
- if an episode attempt succeeds, stop immediately;
- no extra seed, temperature, token limit, prompt, retry, or model change.

This is diagnostic replay of consumed evidence, never fresh evidence.

## Frozen behavior

The workflow must prove byte-level Git diff absence since the certified freeze
anchor `f6e591db8d22ae0e2175769852a1a8aa9c3e106a` for:

- `hcl/v03/decision_policy.py`
- `hcl/v03/action_checker.py`
- `hcl/integrations/sotopia_agent.py`

The diagnostic observer itself is off by default and is already certified not
to alter provider call count, return value, exceptions, normalization, seed or
retry behavior.

## Allowed evidence

For each Decision Policy provider call, retain only:

- attempt number;
- call ordinal within that episode attempt;
- requested max_tokens;
- temperature;
- outcome:
  - `accepted_object`
  - `empty`
  - `no_parseable_object`
  - `transport_exception`
  - `observation_unavailable`
- response byte count when available;
- response SHA256 when available.

For episode-level outcome retain only:

- success/failure;
- exception class;
- whether the exact frozen no-valid-JSON RuntimeError occurred;
- HCL turn count on success.

Do **not** retain:
- prompt text;
- response text;
- parsed decision fields;
- persona names or transcript;
- credentials;
- provider exception text;
- SOTOPIA reward/evaluator result as efficacy evidence.

## Interpretation

Possible outcomes:

1. three Decision Policy calls are `empty`:
   classify an empty-output family for that episode attempt.
2. three calls are `no_parseable_object`:
   classify a non-empty malformed/unparseable-output family.
3. a `transport_exception` occurs:
   classify transport/provider failure, without exposing provider error text.
4. all Decision Policy outputs are accepted and the episode succeeds:
   historical ordinal 48 failure is **not reproduced** under this bounded replay;
   exact original cause remains unresolved.
5. accepted Decision Policy objects occur but episode fails elsewhere:
   ordinal 48 replay failure is not the frozen Decision Policy JSON failure.

No behavior repair is authorized by this predeclaration. If a behavior-bearing
repair becomes justified, it must start a new amendment and repeat independent
synthetic + integration smoke gates before any external validation.
