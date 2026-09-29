# I02 — complete-source ordinary-input coverage

**Status: provider-free negative coverage finding / no qualified case.**
The [machine receipt](../reports/HCL_I02_LONG_INPUT_COVERAGE.json) pins the
SQuALITY v1.3 dev file by SHA256 and records only document character counts.
No question, reference answer, story prose or gold was displayed for this
audit. The 25 nonempty dev documents range from 22,559 to 38,795 characters.
The present `CognitionRequest(..., narrative=complete_source)` rejects every
one at its 16,000-character input gate. The candidate C/P/G builder accepts
the same complete sources under its 64,000-character gate. This is a
structural entry result, not a model comparison or proof that SQuALITY items
fit I01's long-character task family.

The [executable audit](../scripts/i02_input_coverage.py) checks that C, P and
G-map receive identical complete ordinary input, tries the actual H entry,
and records either the actual final input hash or the rejection reason. A
rejection is an **observed H outcome**, never a basis to remove a long case
after seeing H behavior. The synthetic tests cover a complete short source,
a >16,000-character source, and an attempt to relabel refusal as acceptance.
They do not qualify a source or a model. G-final still needs a real, charged
map call and is not exercised by this coverage audit.

The frozen I01 question explicitly counts inability to parse an ordinary
question as an outcome. F05/H05 support bounded dated, typed narrative forms,
but cannot be substituted for arbitrary complete literary prose without a
new, disclosed input method. This work does not change the frozen HCL runtime
or truncate the source. A future repair needs a versioned runtime amendment
and provider-free full-source/treatment checks before confirmation; historical
results stay attached to their original runtime. A fair evaluation may record
H refusal and C/P/G answers on a qualified long case, with coverage and reverse
harm reported, rather than silently shrinking the source or task.

**EVALUATION_DELTA:** input coverage failure is visible and machine checked.
**HCL answer CAPABILITY_DELTA:** none. **Qualified independent cases:** 0.
**Provider calls/spend:** 0 / USD 0. **LongMemEval:** sealed, untouched.

**NEXT_READY:** genuinely unexposed source/question qualification and semantic
comparator calibration; preserve this length boundary in every later case
receipt. Do not sample down to make H look eligible.
