# Universal final citation contract

## What changes

`UniversalHCL.answer` now sends an explicit-object citation contract in its actual
final-generation request and verifies that shape before the existing source audit:

- Every citation is an object with `source_id`, integer `version`, and `quote`.
- The only optional field is `start`. If present, it is a nonnegative integer,
  never a boolean or null, measured in Unicode characters.
- The model must copy source identity/version from the actual supplied source.
  Quote strings, omitted versions, and null offsets are no longer delivered by
  this entry. Extra fields, including `end`, are still rejected.

The generation prompt, rejection gate and strict consumer now agree on the
previously inconsistent shapes. A shape failure has
`source_review.status = INVALID_EXPLICIT_CITATION_SHAPE` and retains the existing
`SOURCE_REVIEW_REJECTED` final-delivery code. No answer, citation, source identity,
version or offset is filled, dropped, wrapped or rewritten. The unchanged raw
response remains only in the existing bounded private receipt; this is not a
new public exporter or permission to disclose that receipt.

Successful shape validation still must pass the existing source identity,
version, quote/location and currentness audits. This does not make an invented
quotation valid. Existing unique-quote offset relocation and whitespace-layout
matching remain explicit in the audit and unchanged; the new shape contract does
not claim stronger lexical or semantic certification.

## Deliberate scope boundaries

The ordinary entry still allows an empty citation array for an explicit evidence
limitation. A source-free analysis still requires it. The historical four-case
comparison separately requires a cited answer, so its `accepted` predicate still
rejects an empty array. That is a declared task-level difference, not an excuse to
invent citations. The comparison exporter and acceptance code are unchanged.

The separate legacy `answer_reader_entry` policy has exactly its previous string
value and behavior. The meaning/provenance/inference instructions are shared
unchanged; only `UniversalHCL` uses the new explicit-object shape instructions.
No parser, capability routing, model/token setting, retry, repair, grant or live
provider execution is added. The complete new prompt is included in the existing
context and metered request accounting rather than truncated or uncharged.

## Evidence and history

Baseline: `2fe35047ffb42327eb72817769300dfaecdeeda3`. Only
`hcl/cognition/reader_entry.py` and `hcl/cognition/universal_entry.py` change within
the runtime. The new amendment restores precisely those two predecessor file
hashes to verify all other runtime membership and bytes, and retains the complete
previous history/consumed-execution pin checks plus the prior diagnostic amendment.

The current diagnostics regression remains active against the current runtime.
Its paired baseline advances to the immediate predecessor and permits only the
explicit prompt prefix, declared shape-refusal metadata and the newly rejected
legacy shapes to differ. Raw output, actual source data, native results, call
counts, synthetic reservations and journals are still checked. The old test
files also execute unchanged in a credential-free, network-blocked worktree at
the exact predecessor. The existing consumed G05/four-case replay still runs at
its own exact older runtime. Neither history is rewritten to pass the new code.

The new synthetic end-to-end test port reads the actual final-generation request,
checks the new policy, and returns explicit citations using the supplied source
identity/version. The same unchanged raw string must then pass the real runtime,
the frozen strict `final_fields` consumer and its `accepted` source audit. Cases
cover one/multiple sources, source version 2, Unicode/repeated quotations,
malformed types/fields, stale or invented source facts, existing citation bounds,
empty-array differences and exact/one-character-short context budgets.

These are deterministic engineering tests. They establish contract consistency,
not that a real model now complies more often or answers better. Historical D01's
missing noncanonical output is still unavailable, its precise cause is still
unknown, and the locked Base 38/40 versus HCL 30/40 result is unchanged. No paid
evaluation or reexecution has occurred or is authorized by this change.

## Provider-free checks

```
python -m unittest tests.test_v1_explicit_citation_contract tests.test_v1_final_delivery_diagnostics tests.test_v1_answer_citation_contract
python -m unittest discover -s tests -p 'test_v1*.py'
python -m scripts.development_explicit_citation_amendment
python -m scripts.development_explicit_citation_history
python -m scripts.development_final_delivery_history
```

The existing full provider-free CI and witness suites remain required for the
exact candidate commit. All consumed provider grants remain closed at zero.
