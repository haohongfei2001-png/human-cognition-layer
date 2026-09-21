# Ordinal 48 Decision-JSON Diagnostic Replay Result

## Boundary

This is a diagnostic replay of an already-consumed setting.

It does **not**:
- complete the original 8/10 holdout;
- create fresh evidence;
- produce an efficacy score;
- change frozen HCL behavior;
- authorize a new holdout.

Predeclaration:
`reports/ORDINAL48_DECISION_JSON_DIAGNOSTIC_PREDECLARATION.md`

## Canonical diagnostic run

- run: `35585685155`
- launch commit: `8dfe862613213933983f4f8c20ae7363e1738732`
- artifact: `10632519832`
- artifact SHA-256:
  `b84b469181f1ab1048ee15d739b849253fd335d0859fbd622c09ff07b2a55750`
- workflow: **SUCCESS as diagnostic collection**
- setting: environment 9 / combo 3 / expanded 48
- seed: 42
- treatment only
- model/provider: `custom/deepseek-flash@https://api.deepseek.com`
- attempts executed: **2 / 2 maximum**
- final episode outcome: **failure**
- exact frozen RuntimeError reproduced in both attempts:
  `HCL decision policy returned no valid JSON after 3 attempts`

A green workflow here means metadata was collected and passed privacy/integrity
checks. It does not mean the episode passed.

## Raw metadata

### Episode attempt 1

Decision Policy wrapper events:

1. accepted object — 1333 bytes
2. accepted object — 1707 bytes
3. **empty — 0 bytes**
4. **empty — 0 bytes**
5. **empty — 0 bytes**

The final three policy attempts were all empty, so the exact invalid-JSON
RuntimeError was raised.

Classification: **empty-output family**

### Episode attempt 2

Decision Policy wrapper events:

1. accepted object — 1502 bytes
2. accepted object — 1421 bytes
3. **empty — 0 bytes**
4. accepted object — 2263 bytes
5. **empty — 0 bytes**
6. **non-empty but no parseable object — 1333 bytes**
7. **empty — 0 bytes**

The final three policy attempts were:
`empty -> non-parseable non-empty -> empty`.

Classification: **mixed invalid-output family**

No Decision Policy diagnostic event in either attempt was a
`transport_exception`.

No prompt, response text, transcript, persona, credential or evaluator score
was stored in the diagnostic artifact.

## Important transport-layer implication

The current observer wraps `OpenAICompatibleBackend.complete()`, not each
underlying provider request.

That backend itself performs:

- up to **4 provider completions** for one `complete()` call;
- it returns immediately on the first non-empty content;
- if all four provider completions have empty content, it returns the final
  empty string.

Therefore:

- each wrapper event classified `empty` proves **four consecutive underlying
  provider completions with empty final content** for that Decision Policy
  attempt;
- episode attempt 1 ends with three empty wrapper events, therefore at least
  **12 consecutive underlying provider completions with empty content** at the
  failing turn;
- episode attempt 2's final failed Decision Policy call contains two empty
  wrapper events (at least 8 underlying empty completions) plus one non-empty
  1333-byte output that did not parse as an object.

This makes a simple one-off parser glitch or missing provider credential an
insufficient explanation.

## What this does and does not establish

Established:

1. ordinal 48's Decision Policy JSON failure is reproducible under the same
   consumed setting / seed / provider and frozen HCL behavior;
2. the dominant observed failure mode is provider-facing **empty content**;
3. at least one retry can also return non-empty but structurally unparseable
   content;
4. no transport exception was observed by the current wrapper;
5. the same-provider SOTOPIA evaluator repair is orthogonal to this Decision
   Policy failure.

Not yet established:

- provider `finish_reason`;
- whether an empty `content` carried model reasoning in a separate field;
- provider token usage on each underlying completion;
- whether the underlying response ended by length, stop, filtering, or another
  provider-specific reason;
- exact raw text of the non-parseable response (intentionally not collected).

## Next diagnostic target

Do **not** increase retries or alter prompts yet.

The next minimal step is provider-attempt-level, content-free observability for
Decision Policy only. For each of the backend's existing 1..4 underlying
provider completions, record without changing behavior:

- provider attempt ordinal;
- `finish_reason`;
- final-content byte count/hash;
- reasoning-content byte count/hash when exposed by the provider response;
- prompt/completion/total token counts when available.

The observer must preserve:
- exactly the current four-attempt backend loop;
- the outer three-attempt Decision Policy loop;
- model/provider/endpoint/key;
- seed/temperature/max_tokens;
- returned content and exceptions;
- frozen HCL behavior.

Only after this metadata distinguishes the empty-output cause should a
behavior-bearing amendment be considered.
