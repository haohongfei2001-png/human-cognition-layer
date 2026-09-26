# HCL v0.8 CAREBench Source-Grounded Development Utility v0.1

Status: **FROZEN PROVIDER-FREE PACKAGE / NO v0.8 PROVIDER CALL**

## Source and task

Use `zhaoyuesun/CAREBecnch`, `first_person.json`, pinned commit
`8b4135219d493c4aaa2474beeefed11779c66890`, SHA-256
`93b410dab0ea3f40796f6e02bf4cb8085898670a340fe2a6f10f154593d6d05c`.
The published file has 1,000 first-person records. Only the reviewed
`story_collection.final_scenario` is public task evidence. Cognitive responses,
emotion labels, ratings, persona, demographics, identity and chat history
never enter state/answer construction or automatic scoring.

Selection: `eval/v08/carebench_dev_selection_v01.json`, SHA-256
`65060aa1656dfd9fbc0a8a43fef7dfe406c0975aca4fda8f56ad531604314bbf`. Source narratives of
80..1,500 characters are deduplicated by exact narrative hash; eight are
selected by salted narrative-hash ordering (`HCL-V08-CAREBENCH-DEV-V01`). No
outcomes or annotation values informed selection. The manifest stores case
IDs, source-key hashes and narrative hashes rather than participant identity
or raw narrative text. Future separation must use narrative hashes and
source-key hashes across both first- and third-person files, not a split name.

The source-only sufficiency audit after runtime implementation found:

| Case | Public evidence suited to this development task |
|---|---|
| care-dev-01 | Reported pride and importance of another person's performance. |
| care-dev-02 | Reported distress, helping goal and limited ability to change another person's grief. |
| care-dev-03 | Reported anger/stress and competing obligations; supported desired outcome. |
| care-dev-04 | Reported discouragement/stress, helping goal and obstacles to obtaining information. |
| care-dev-05 | Family disagreement, reported mediator position, desired reconciliation and later resolution; outcome does not prove a new private feeling. |
| care-dev-06 | Reported sadness and goal to preserve understanding across disagreement. |
| care-dev-07 | Positive outcome coexists with reported doubt/unsettled feelings; success does not uniquely imply happiness. |
| care-dev-08 | Reported sadness/anger and another person's attributed feeling; subject boundaries matter. |

The eight stories are manually source-inspected, provider-unconsumed
**development** cases, not sealed efficacy data. No annotation values have
been inspected. They become development-consumed once provider execution
begins. No claim is made about unexpressed actual feelings or mental health.

## Frozen C/P/D comparison

All arms receive the same complete narrative, base-model alias
`deepseek-flash`, disabled thinking, seed 42, temperature zero, and 512-token
answer maximum. C is a strong source/evidence/uncertainty control. P adds a
thin appraisal reminder. D receives the candidate typed affect state plus
the same story. D semantic state is built before the explanation task is
released; the source actor is the anonymous first-person role `experiencer`,
not an identity extracted from demographic fields.

Answers contain up to four emotion claims with narrated time scope, up to
three appraisal claims, and uncertainty. Every claim needs an exact excerpt
and DIRECT/INFERRED/ATTRIBUTED strength. Multiple plausible feelings remain
allowed. One authored report is ingested as one source event; placeholder
time orders ingestion, not real-life events. This check does not separately
validate temporal segmentation or the goal-link mechanism.

## Predeclared diagnostic rubric and decision

Automatic checks validate answer format, exact quote anchoring, field caps,
source retention and operational limits. **There is no automatic private-
emotion accuracy or official CAREBench score.** Human annotation matching
would not establish entailment and is not performed.

Before aggregate comparison, mask arm identities and review all case answers:

1. Does each claimed feeling/appraisal follow from its quote and full source,
   with reported versus inferred versus attributed support preserved?
2. Are materially stated mixed feelings preserved within the common output
   budget, including positive outcomes with negative/uncertain feelings?
3. Is another person's report assigned to the correct subject, without turning
   action/expression or a favorable result into a unique direct feeling?
4. Are earlier/later feelings qualified rather than silently treated as current?

A material error is an unsupported direct mental claim, subject misattribution,
unsupported unique motive/emotion, or omission of the core explicitly stated
mixed pair within the shared capacity. Reasonable alternative hypotheses or
minor wording differences are not errors. Record ambiguous cases separately,
invalid answers and semantic failures; do not invent numeric emotion truth.
Disclose reviewer count, visible labels and whether aggregate scores were
seen. Single-agent review remains development diagnosis, not independent
human adjudication. Report paired material-error discordances, not only totals.

Continue toward a fresh comparison only if D has at least two P-error/D-
adequately-grounded cases, no more than one reverse case, and visible typed
source support causally consistent with those gains. If C/P is comparable or
cheaper without that increment, simplify and do not expand the typed affect
architecture against these cases. In all events, record cost and uncertainty.
Do not use future selected fresh outcomes for tuning.

## Separate bounded execution gate

This package makes zero provider calls until a separate owner authorization
covers this v0.8 check. The previous USD 0.50 authorization was expressly for
one v0.7 fresh pilot; it does not authorize a new v0.8 experiment. No new
account/credential purchase or LongMemEval execution is permitted.

Hard caps: semantic extraction 16 calls (one source plus at most one repair
for each case), C/P/D 8 each, **40 calls total**; 262,000 input and 112,000
output characters. Character-as-token peak planning bound USD 0.213.
Shared pre-request reservation/reported-usage ledger cap **USD 0.25**.
Missing usage or uncertain transport charges the full reservation and stops;
SDK retries are disabled. Actual invoice may differ from the peak-rated ledger.

`HCL_V08_CAREBENCH_DEV_COST_AUTHORIZED_USD` must be at least 0.25; it is
currently unset. `.github/HCL_V08_CAREBENCH_DEV_V01_TRIGGER` is absent.
The exact-parent trigger-only workflow permits the first cloud attempt only,
verifies source/selection and provider-free regressions before paid calls,
and archives partial consumed evidence. A failure is never relaunched as fresh.
Source text is not committed; repository evidence uses IDs/hashes and receipts.
