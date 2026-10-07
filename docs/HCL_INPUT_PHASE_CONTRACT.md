# Explicit reader inputs and separate planning/final budgets

The [entry-routing smoke](HCL_ENTRY_VALIDATION_20261007_RESULTS.md) selected B01
without semantic candidates, produced no checked treatment, then spent its final
8,192-token/high-thinking allowance without a visible answer. This repair makes
input intent verifiable, lets strict callers stop before unnecessary final fees,
and separates the two phases' fixed completion configurations. It does not claim
that a model will choose faithful inputs or preserve every answer fact.

## Current model-planning contract

Every B01/C01/C02/C03 operation returned to UniversalHCL.answer must explicitly
choose input_mode:

- literal uses the complete original source through the existing native reader
  and forbids semantic_candidates. The mode label does not establish that the
  source has supported premises or that the result will contain checked treatment.
- semantic requires one to 24 faithful source-anchored semantic_candidates in the
  same first model response. All quote/offset anchors are checked before any
  operation dispatch. At most one bridge operation is allowed, as before.
- insufficient records that the planner cannot construct faithful supported input.
  It creates no native result or checked treatment. If no other operation actually
  returns a native result, final generation remains unavailable.

Other capabilities reject input_mode. A missing mode on these four families,
inconsistent mode/candidates, or invented quote is rejected rather than silently
interpreted as a valid current model plan. The source, existing literal parsers,
conditional translation semantics and real native operations remain unchanged.
Models still supply interpretations; no local code fabricates candidates or
certifies meaning from a mode label. Negation, attribution and time qualifications
remain subject to the existing conditional-state and source-authority rules.

Direct native APIs keep their existing literal/semantic input form, so a historical
argument can still be replayed without rewriting the original record. This does
not bypass the stricter current model-planning entry, which always requires modes.

## Strict evaluation before final dispatch

The optional caller argument required_checked_capabilities is an immutable tuple
of allowed capability IDs. When nonempty, at least one actual returned operation
must have executed=true and checked_treatment_present=true in that set before
final request construction or reservation. The model cannot configure this gate.
Failure preserves the selected plan, actual native outcomes and first-call receipt;
there is no final call, automatic replanning or retry. The test gate is a necessary
condition only: independent source-first review still decides relevance and quality.
Literal C02 now exposes the same checked-treatment metadata as its semantic path:
true only when the actual native payload contains checked explanation rows. Empty
results stay false; payloads, supporting claims and motive conclusions are unchanged.

The default empty tuple retains ordinary evidence-limited answers after an honest
native insufficient-evidence result. It does not require every natural-language
question to have checked treatment, and the gate never turns a failed or irrelevant
operation into successful HCL processing.

## Explicit phase configurations

The existing DeepSeek model/account port now fixes planning to 16,384 tokens with
high reasoning effort, and final answering to 16,384 tokens with low effort.
Thinking stays enabled for both. The original 36,000-byte complete-request ceiling,
full-source transport, citation audit, timeout and zero-retry requirements remain.

The [official Chat Completions contract](https://api-docs.deepseek.com/api/create-chat-completion/)
allows low/high/max effort; medium maps to high. Its unspecified thinking allowance
is 64K, while non-thinking defaults to 8K. These facts do not justify unbounded
completion or promise that low effort always finishes. The chosen final setting
reduces reasoning intensity and increases its fixed completion room; its effect
on accuracy, latency and failure rate requires new real validation under the
unchanged semantic acceptance rules.

Reservation and usage guards use each phase's actual serialized request and
16,384-token bound. At the existing peak CNY 9/M input and 27/M output rates, a
36,000-byte phase reserves at most CNY 1.109664; two phases total CNY 2.219328.
This conservative reservation is not a provider invoice or a spending grant.
An old 8K-final allowance cannot silently authorize the new request. All historical
paid executors, grants, results, cases and review bytes stay pinned and are replayed
at their exact closed runtime. Any new model call needs fresh bounded authorization.

Provider-free regressions cover malformed/omitted modes, supported literal input,
explicit insufficiency, exact source anchors, negation, genuine previous/current
argument replays, strict zero-treatment stops before final reservation, ordinary
limited answers, caller authority and per-phase wire/quote identity. Scripted
answers demonstrate control flow only. No provider request, recharge, hidden
reasoning disclosure, new adapter or formal I02-I06 completion follows from this
change.
