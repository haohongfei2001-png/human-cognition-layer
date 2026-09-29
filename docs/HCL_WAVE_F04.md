# F04 — Competing character development explanations

## CAPABILITY_DELTA

Given a dated ordinary narrative in which the same named person is reported to
change an action, HCL can now return several source-anchored, simultaneous
explanations instead of labelling the person as having “grown,” “declined,” or
changed character. The positive witness preserves five distinct candidates:
new reported information, an explicit reported goal revision, an explicit
contextual preference revision, reported role pressure, and an explicit report
of audience-directed words. Each candidate has its own exact sources, date
boundaries, and one shared F03 closure that includes all recorded rivals. No
candidate is selected as the true cause.

The simplest alternative is to send the whole chapter to the base model with a
request to compare explanations. A serious independent evaluation after G-ARCH
must establish whether the source/time constrained mechanism adds value.

## Mechanism and limits

`compare_character_development` reads one authorized F02 `NarrativeTimeline`
chapter at a specified system-record and disclosure cutoff. It requires exactly
two opposite reports of the same action on distinct declared story dates. It
does not use source line order to invent temporal order; same-day factor/action
ordering is unresolved. The F02 parser now preserves dated action and role
records with exact source spans. F01 speech references remain available for
speech; action and role records are not mislabelled as F01 speech events.

F04 recognizes only explicit bounded report forms. Knowledge claims require a
matching earlier “did not know” and later “now know” self-report; a separate
“still want” report can show a stated continuing goal without proving a private
goal. Goal/value changes require an explicit old report and an explicit
“instead of” revision in the same actor and, for values, the same role/context.
Role pressure requires a reported appointment before a matching self-report of
pressure. Audience strategy requires an explicit self-report of what was told
to a named listener and why. Behaviour alone, later knowledge, a third party’s
report or a role title alone never creates an inferred motive.

The output is an analyst's conditional comparison of source reports, not a
character's private knowledge, actual preference, deception, moral character,
world action or causal proof. Names are source-local; no cross-chapter alias is
assumed. An older analyst snapshot remains valid after a later correction, but
current access revocation prevents its final input from exposing the source.
The full recorded candidate closure is carried into the actual final model
input; source completeness outside that closure is not claimed.

## Verification

Fourteen F04 tests cover the ordinary positive five-way comparison, source
citations and full rival closure, later-knowledge non-backfill, same-day
ordering, action-only refusal, multiple-action ambiguity, actor boundary,
missing role appointment, unsupported goal/value changes, source revision and
ACL revocation, cross-source non-aliasing, candidate budget refusal, and F02 source-span integration. The
ordinary witness records the actual final model messages in
`reports/HCL_WAVE_F04_WITNESS.json`. Full v1 and 176 historical tests run in
exact-head/main CI.

State: **CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.
Provider calls/spend: zero. LongMemEval sealed. NEXT_READY: F05 long narrative
integration and provider-free scale smoke.
