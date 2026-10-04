# Nonblank final-answer delivery guard

The ordinary `UniversalHCL.answer` entry could report
`ANSWERED_WITH_EXPLICIT_LIMITS` even when the final JSON answer field was empty or
contained only whitespace. Real native execution and valid source quotations did
not make that response a delivered answer. The regression was reproduced on the
adopted C02 runtime before this repair, with zero provider calls.

The entry now checks for a nonblank answer after the existing output-schema and
size checks. Empty strings and Unicode whitespace-only strings return
`NONBLANK_FINAL_ANSWER_REQUIRED` and are not exposed as a delivered `answer`.
The original bounded `answer_raw`, native results, successful call reservations
and usage remain intact. No replacement answer, trimming, retry or extra provider
phase is introduced. The final prompt also asks for an explicit evidence
limitation when appropriate instead of an empty field.

Whitespace follows Python's Unicode-aware `str.strip()` definition. The check
does not mutate the text. CJK, emoji, combining characters and valid content with
surrounding whitespace remain byte-preserving through the JSON response. This is
a presence check, not a relevance, readability or semantic-quality classifier.

The existing source-citation validator and low-level quote-location audit are
unchanged; a nonblank answer still fails delivery if its citations are invalid.
Historical outputs are not rescored. Native parsers, capability coverage, model
configuration, token bounds and all historical grants remain unchanged.

Five targeted regression methods cover empty/ASCII/Unicode/bounded-large blank
answers, source-free native preparation, unchanged nonblank Unicode output,
citation rejection and the real metered interface with a fake SDK. The baseline
produced eight failing assertions; the repaired cases pass without a network or
provider call. They establish delivery-boundary behavior only. Real-model answer
quality and private-result readback remain separate readiness requirements.
