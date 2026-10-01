# Preserve explicit hypothetical speech scope

The ordinary reader previously treated `In a hypothetical scenario, Eva said,
“I believe the gate is clear.”` as an actual reported public expression. The
counterfactual variant and an explicit imagined-conversation preamble behaved the
same way. This could also join a hypothetical plan to actual opportunity/belief
records. The source remained complete, but the derived state lost its qualifier.

The repair changes only `hcl/cognition/semantic.py` in the runtime. Existing
`CONDITIONAL_OR_EMBEDDED` scope now covers bounded, explicit hypothetical and
counterfactual prefixes and scene declarations. The existing checkers then leave
those expressions unsettled. No new ontology, instruction text or inference about
a person's private state is introduced.

## Source boundary

The source text and original offsets stay unchanged. A temporary narration view
excludes quoted, colon-format and script-format speech bodies before locating
scene cues. A character discussing an imagined conversation, or saying “In
reality” within one, cannot set the narrator's scene scope. Soft wraps retain the
same clause, and closing quotation marks do not terminate a coordinated turn.
Explicit narrator-level actual-scene resumption can restore ordinary quoted
speech handling without promoting earlier hypothetical speech.

This is bounded syntax handling. It does not resolve arbitrary discourse,
indirect scope, unreliable narrators, sarcasm or all ways of entering/leaving an
imagined scene. Existing conservative script-preamble handling remains unchanged.
Unmatched text stays available in the complete original source; a coverage limit
is not a claim that an event or motive is absent. Actual speech that discusses a
hypothetical example and reasonable real-world interpretations remain allowed.

## Evidence

`reports/HCL_QUALIFIED_SPEECH_SCOPE_WITNESS.json` records six newly authored
contrasts under the previous main runtime and the repaired runtime. The three
explicit hypothetical/counterfactual inputs stop producing actual checked
expressions. The ordinary statement and actual discussion controls retain their
speaker. Explicit resumption retains the actual later speaker alone. All six
sources remain complete and all preparations make zero extraction calls.

`tests/test_v1_qualified_speech_scope.py` covers source qualifiers, soft wraps,
coordinated speech, plan composition, quote/colon/script attribution, actual
resumption, revision invalidation, backend proposal validation and one raw-
preserving stub answer. Its thirteen tests invoke no model or provider transport.
The witness script can observe the same six cases on a chosen local runtime; it
does not perform semantic scoring or select cases by model outcomes.

Local validation passes 1,160 v1 tests, 176 historical regressions and all 36
consumed-archive tests. The existing current-runtime v21/v24 witnesses, runtime
amendment and compilation checks also pass. Exact-head hosted CI is recorded in
the pull request before integration.

## Historical and current evidence

The successor amendment pins the previous budget report and validator bytes.
Restoring only `semantic.py` from the certified v24 archive reconstructs the full
previous budget-runtime hash. This checks that every other runtime file, including
the merged final-input budget fix, is unchanged. Historical packages, runtime
pins, model outputs, grades and grants remain immutable.

This establishes source-scope correctness on explicit authored constructions. It
does not establish improved model answers, native-task utility, a version ranking,
general discourse understanding or a new paid-run authorization. Ordinary-source
reasoning and independent task evaluation remain the canonical next work.
