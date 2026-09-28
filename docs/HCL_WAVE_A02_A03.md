# A02–A03 — Ordinary source candidates and revisable interpretations

## Positive capability deltas

**A02:** ordinary dialogue can bind “I” to its explicitly named speaker, distinguish
an affirmative expression from expressed uncertainty/denial, and preserve multiple
possible referents for “She”. Caller input is an ordinary question plus authorized
text, not operation flags or correct mental states. Source-order relations remain
separate from event chronology. Entity identity stays source-local.

**A03:** a counterstatement can contest an interpretation and its dependent
conclusions; withdrawing that support restores the surviving interpretation.
Other persons and clean alternative support remain unchanged. Original source
history is never rewritten into a different event or private belief.

## Working paths

- `prepare_semantics(query, tuple[AuthorizedText], ...)` and workspace
  `prepare_semantic` feed the same evidence core. Visibility/time projection
  happens before the optional backend sees text. Structure, exact quote location
  and semantic support are independently reported. Ambiguous duplicate quotes
  require a valid offset; malformed batches do not partially add interpretations.
- The local adapter recognizes bounded named reported speech/colon dialogue and
  first-person belief expressions. A replaceable `complete_json` backend may
  propose general events/relations, but valid JSON and exact citations still leave
  those proposals `UNVERIFIED_CANDIDATE` unless the bounded local semantic check
  independently matches. No caller-supplied “verified” flag is accepted.
- `assess_positions(core, semantic_result)` consumes bound literal propositions,
  constructs source-local public-expression interpretations and challenges their
  settled readings with incompatible explicit expressions. It does not merge
  matching names across documents or resolve ambiguous pronouns by gender guesses.
- `assessment.messages(core, query)` emits the **current** support/challenge/
  alternative closure and positions as actual answer-adapter inputs. Withdrawn
  roots are marked inactive; unsupported interpretations remain audit history.
- Core replacement records explicitly mean analyst interpretation revision, not
  that a character changed their mind. A replacement depending solely on the
  retired interpretation is rejected. Rootless and mutual-challenge cycles terminate.

## Witness and verification

[A02 reproducer](../scripts/witness_semantic_entry.py) / [receipt](../reports/HCL_WAVE_A02_WITNESS.json):
Mira affirms, Noor is explicitly unsure, “She” remains Mira/Noor alternatives.
Changing Mira's source expression changes only her signal; no private truth is
inferred. [A03 reproducer](../scripts/witness_interpretation_revision.py) /
[receipt](../reports/HCL_WAVE_A03_WITNESS.json): Mira's affirmative and negative
expressions are challenged; withdrawing denial restores affirmative support,
while Noor's state is identical. Both before/after actual final inputs are saved.

Fourteen A02 and eight A03 tests cover unit correctness, negative inference,
composition, ordinary-input smoke and relevant regression. They include renamed
speakers/paraphrases, hidden-source non-interference, future/unknown time rejection
before backend calls, conditional speech, alternative supports, local retraction,
explicit replacement, source preservation and bounded failure. Full v1 and 176
historical regressions are required by the exact-head/main CI. CI reproduces all
three A01–A03 witnesses and uploads them with its exact-SHA receipt.

## Evidence and limits

CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN. No real provider calls
or spend. Replay adapter invocation counts are **not** paid/provider counts.
Broad extraction, cross-document identity and broad language efficacy remain
unverified. Source syntax cannot establish sincerity, private belief, knowledge,
world truth or moral truth. The local parser is a bounded fallback; arbitrary
backend proposals cannot bypass semantic qualification. Retained v0.6/CG03/04/05
shared material consumption is the next package, A04. Historical paid receipts,
dispositions and frozen runtimes remain unchanged; LongMemEval stays sealed.
