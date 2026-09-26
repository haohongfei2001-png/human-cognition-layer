# HCL v0.7 Fresh SAGA C/P/G/D Pilot v0.1

Status: **FROZEN PROTOCOL / ONE FRESH RUN COMPLETE / NO FURTHER FRESH RELAUNCH**

## Question and frozen source

After the 12-story development check found no incremental D value over the
thin P method, this disjoint pilot asks whether a concise evidence/uncertainty
instruction remains useful on previously unexposed stories, and whether a
competent generic narrative structure G or the frozen v0.7 typed state D
adds anything. No method changes may be made after viewing fresh outcomes.

Source: `saiumbc/SAGA` at commit
`9c66afefb06b8bad77fc7f5913ddc8264a57c69b`, file
`data/actual_val.jsonl`, SHA-256
`f3b37c84526bba4ae74bec8991b2789d7a3b97d15c8ea8de565afa590f625ff7`.
The file has 106 annotation rows, 37 story/participant groups and 29 distinct
story IDs. It shares **zero story IDs** with the 219-row `actual_test.jsonl`
used for development, as verified at the pinned commit. The immutable
selection is `eval/v07/saga_fresh_selection_v01.json`, SHA-256
`d982e80a964d60b9c0dca06efaf05e322949bb9186748b13b0b7898db491d4e6`.
It contains 16 distinct complete five-sentence stories, eight with a
directly narrated goal or proximal plan and eight where a goal is inferred.
The selected story IDs are disjoint from all 12 provider-consumed development
story IDs. The source-sufficiency audit read only the public story sentences
and highlighted participant, not SAGA goal labels, model answers or outcomes.
Selection was manual, not random; results are a directional fresh HCL pilot,
not a population or leaderboard estimate.

SAGA crowd goal descriptions are not unique truth about a character's private
mind. The source tier is a manually audited distinction about what the public
narrative directly states. It is not full goal correctness. All future answer
evaluation must preserve alternate plausible goals and uncertainty; exact
string matching to one crowd goal is forbidden.

## Frozen arms and question firewall

All arms use `deepseek-flash`, temperature zero, disabled thinking, seed 42,
the same 256-token answer maximum, exact-source-quote JSON schema and the
complete five-sentence story.

- **C:** strong direct control with the common evidence/uncertainty instruction.
- **P:** same story and task, with the frozen thin action-versus-goal reminder
  from the development check. This is the provisional simple HCL method.
- **G:** a complete generic sentence timeline with actor-surface and entity
  mentions, source, time, event text, narrator provenance and uncertainty.
  It does not project goals, intentions or character beliefs. Every source
  event must survive; uncertain actor resolution is explicit rather than
  fabricated.
- **D:** the frozen typed v0.7 intention/goal state, preserving direct versus
  inferred evidence and perspective boundaries. Invalid semantic extraction
  remains recorded and fail-closed, while the original source sentence stays
  available. The same full story is supplied to the answer model.

G and D states are constructed from source sentences **before** the selected
participant/task is released. Neither state builder receives the source tier,
SAGA goal fields, outcomes or answer responses. G and D have equal source
access; P/C receive the same story. Provider model identities, all calls,
input/output characters, wall time, repairs, semantic failures, invalid
answers and state hashes are recorded.

## Scoring and interpretation

The predeclared automatic observation is agreement with the frozen public
source tier. Each nonempty answer must cite an exact source excerpt; invalid
JSON, missing quotes and malformed classes are recorded separately. A
case-level source audit must then examine whether the candidate goal really
follows from its quote and whether an `EXPLICIT` claim is warranted. The audit
must disclose whether raters saw aggregate results or arm identities. Report
paired P-versus-C/G/D and D-versus-G discordant counts; percentages alone are
insufficient. The small, one-model, source-selected pilot cannot establish
broad motivation or human-cognition superiority.

If P is comparable to G/D and adequately source-grounded, retain the simpler
method. If G clearly improves source-grounded outcomes, adopt the generic
structure. If D has a clear paired and causally interpretable increment,
reconsider its role. Do not tune on these cases after execution. A completed
pilot closes this SAGA direction for v0.7; a partial run remains consumed
evidence and is never relaunched as fresh.

## Operational authorization boundary

Hard call caps: semantic extraction 160 (five sentences, at most one repair
each), and 16 each for C/P/G/D, **224** overall. Component caps sum to
645,000 input and 148,000 output characters. At the official peak no-cache
Flash rates, a conservative character-as-token calculation is **USD 0.3711**.
The shared pre-request provider-token reservation and reported-usage ledger
enforces a separate **USD 0.50** operational cap. Missing usage or uncertain
transport charges the full reservation and stops. No SDK retry. These are
operational safeguards, not an invoice guarantee if provider pricing changes.

The separate owner authorization variable
`HCL_V07_SAGA_FRESH_COST_AUTHORIZED_USD` is **unset**, and the one-shot trigger
file is **absent**. The previous USD 0.50 authorization covered the completed
development check and its repair, not this fresh pilot. No new provider
account or credential may be purchased; LongMemEval remains sealed.

The provider workflow verifies an exact-parent, trigger-only, first-attempt
main commit; pinned source digest; immutable selection; and provider-free
regressions before any paid request. Artifacts store IDs, hashes, arm answers
and operational evidence. Raw SAGA stories and crowd goal text are not
committed to the HCL repository.


## Execution receipt (added after the frozen protocol)

The authorization boundary above describes the package at protocol freeze.
The owner separately authorized USD 0.50 on 2026-09-27. First-attempt run
`36260603724` completed 16/16 and the authorization variable was reset to zero.
The one-shot trigger is retained as historical consumed-run evidence. No
selection, mechanism, prompt or frozen score was tuned after outcomes. See
`reports/HCL_V07_INTENTION_MOTIVATION_FINAL_DEVELOPMENT_CLOSURE.md`.
