# Offline diagnostic export and review binding

The [current runtime diagnostics](HCL_PLAN_DIAGNOSTICS_AND_BINDINGS.md) expose
safe failure codes and stages. This separate offline version carries them through
the actual deterministic fake transport, UniversalHCL, durable receipt, public
projection and review identity check. It creates no paid package, grant, marker,
SDK client, account query or live execution route. Historical frozen files and
the runtime remain unchanged.

The runner accepts only its exact FakeClient type, with bounded fixed response
strings. An ordinary client or a subclass with an offline flag is refused before
package verification or output creation. Its snapshot binds the new implementation
files, pinned read-only helper files, current runtime, original packet and exact
requests. Archived budget and native-check mechanisms are reused as reference
code, without adopting old approval or grant authority. Simulated usage and full
holds remain distinct from actual spend, which is zero.

## Diagnostic preservation

Immediately after UniversalHCL returns, the runner obtains the existing safe
code/stage projection and persists it before native capture can fail. Public
records require the nullable orchestration_failure field. A null means no failed
runtime receipt was captured, not successful treatment. The field admits only
the exact primitive-string code/stage pair recognized by the runtime helper.
Missing fields, extra keys, unknown strings, containers and spoofed string
subclasses are rejected. Later capture failure has a separate fixed enum.

Malformed JSON and a valid empty plan therefore remain distinct after receipt
reload and export. Planning validation, entry refusal, insufficient native
treatment and subsequent failure stages remain distinguishable. Closing an
interrupted process preserves already recorded diagnostics and conservative
holds; a process dying before runtime return cannot acquire an invented diagnosis.

The public projection excludes full planner replies, hidden reasoning, provider
envelopes and raw exception text. Complete synthetic sources and source-validated
native arguments remain where the existing evidence contract requires them;
diagnostic privacy never justifies dropping source text. All operations and
canonical actor offsets must come from the runtime. Exporters do not repair
arguments or turn unresolved processing into checked treatment.

## Two separate checks

validate_review_binding checks exact protocol, package, runtime, packet and
evidence identities. The complete evidence hash covers diagnostics and native
records. This identity check can accept a correctly bound failed or unavailable
record; it is not semantic approval.

validate_phase1_gate separately requires complete delivery, actual relevant
checked treatment, the bounded native evidence with matching source/version,
runtime, arguments, results, receipt and counts, plus every original semantic
requirement. The caller must separately supply the original saved receipt and
native capture. The gate checks that receipt's hash and reproduces the public
projection from those originals, requiring exact equality before semantic checks.
Missing, empty, substituted or extra native evidence cannot be made successful by
supplying a rehashed affirmative fixture. Offline, zero-spend and no-certification
flags are fixed values at their respective boundaries.

The original saved artifacts are the caller's trust anchor. These checks do not
authenticate arbitrary replacement files supplied by an adversary as originals,
or turn a synthetic affirmative review into an independent semantic judgment.
The frozen historical failure is not reinterpreted by these new offline schemas.

## Verification and limits

Run the dedicated provider-free suite with:

```sh
python -m unittest tests.test_hcl_offline_diagnostic_export_v1 -v
```

The tests use real runtime execution and durable receipt reload. They cover all
eight diagnostic stages, process exits before/after runtime return, capture/export
interruptions, primitive-enum attacks, evidence tampering, correct failure closure,
canonical unique-quote offsets, source boundaries and complete 36,000-byte requests.
Synthetic affirmative review fixtures test control flow only. They are not
independent semantic judgments or owner permission.

Planning remains 16,384/high and final answering 16,384/low. No extra planning,
retry, fallback, second case or live call is introduced. The earlier real failure's
precise cause remains unknown. This establishes an offline diagnostic path, not
model compliance, general reliability or I02-I06 completion. Any later real study
still requires its own exact implementation/request/review freeze and new bounded
owner approval; none is created by this change.

## Current ordinary-request preflight

`scripts/hcl_offline_diagnostic_preflight_v1.py` reuses this runner and exporter
against the original, already exposed October 8 flute smoke. Its separate offline
[manifest](../scripts/hcl_offline_diagnostic_preflight_v1.json) pins the original
packet/rubric, current runtime, implementation helpers,
complete request and phase configuration before fake transport or output creation.
It reads the existing source packet without duplicating or rewriting its text.
The current complete planning request is 28,333 UTF-8 bytes, below the unchanged
36,000-byte limit; planning remains 16,384/high and answering 16,384/low.

Fixed injected failure controls exercise one returned planning response, preserved
safe code/stage, a closed planning hold, and no final reservation or dispatch.
The preflight reloads the saved receipt and native capture independently, then
requires their fresh export to match the supplied public evidence before checking
review binding. It writes the safe public diagnosis before requiring a complete
native capture. A receipt explicitly recording post-runtime capture failure may
bind with no native artifact; a declared capture whose file is missing, malformed
or replaced retains the diagnosis but rejects the source binding. A JSON-null file
cannot stand in for an uncaptured artifact. Source, runtime, request, configuration
or original-evidence drift must fail closed. These controls are simulations with zero actual spend;
their review fixtures do not claim an independent semantic judgment. A correctly
bound failed record still cannot pass the separate semantic success gate.

Run the current-request checks with:

```sh
python -m unittest tests.test_hcl_offline_diagnostic_preflight_v1 -v
```

This preflight covers retention of a diagnostic that the runtime actually returns.
It cannot reconstruct the old real run's lost reason, invent a diagnosis before
runtime return, or demonstrate that a future model will select useful operations.
Any future live integration must reuse this preservation order and bind its own
reviewed implementation, exact requests and trusted original artifacts; its live
transport and authority are not created here. New paid calls and public evidence
require their own bounded approval. Historical packets, results and grants remain
unchanged.
