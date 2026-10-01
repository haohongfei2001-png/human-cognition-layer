# Keep embedded scene cues out of outer narration

A source-first authored probe found an inherited scope defect in the ordinary
quoted-speech path. After an explicit imagined-scene declaration, a bracketed
stage direction or fenced example saying `In reality,` could promote subsequent
imagined speech to an actual public expression. Conversely, an embedded example
saying `This scene is hypothetical.` could suppress subsequent actual speech.
This is a derived-state error even though the original source stayed intact.

A shared scene-cue function now admits declarations and transitions only outside
bracketed directions and fenced examples. It uses the existing offset-preserving
narration view, which already excludes quoted, colon-format and script-format
speech. Bracket and fence characters spoken by a character therefore cannot
change the embedding of later narration. Both the speech and narrator-report
paths use the same cue admission rule. All source text remains available to the
answer path, with no rewriting or truncation.

## Evidence and boundaries

Seven original synthetic contrasts reproduce the previous behavior at exact main
`e4230dd46a47ecdc0940f168bbae36b3149968c6`. Two embedded actual cues cease promoting
imagined speech; two embedded hypothetical declarations cease suppressing actual
speech. Ordinary, imagined and real-resumption controls keep their prior result.
The witness verifies the previous semantic source hash. Six regression tests also
cover later real transitions, source revision invalidation and spoken delimiters.
No external benchmark items or model outputs were used to construct these cases.

The successor runtime amendment pins the previous narrator report and validator,
reconstructs its full runtime digest and retains all earlier speech/budget/v24
validation. The earlier narrator witness still compares its original baseline;
only its current-runtime validation entrypoint advances. Historical witness and
amendment report bytes remain unchanged. No assertion or historical gate is removed.

Independent source review found no blocking issue in the quoted-speech scope.
The narrator-report path retains its older conservative raw-prefix hypothetical
scan; this is not universal normalization of all embedded narration.

Local validation passes 1,178 v1 tests, 176 historical regressions and 36
consumed-archive tests. Exact-head hosted CI is recorded separately in the PR.

This does not interpret arbitrary stage directions, discourse, escaped Markdown
or every quotation convention. It establishes only these bounded scene-scope
contrasts. A source-relative expression still does not prove the speaker's private
belief or world truth. No new prompt instruction, semantic ontology, provider,
paid run or benefit claim is introduced. SID001 is consumed and closed; final
confirmation and LongMemEval protections remain in force.
