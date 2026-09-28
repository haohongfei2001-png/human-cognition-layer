# Retained v0.6 ordinary belief preparation

## Small falsifiable brief

Failure: existing ordinary composition preserved concept/preference state but had
no committed belief evidence. The final model had to reconstruct belief from raw
text, and could conflate a definition, received information or another person's
report with a private belief.

Simplest alternative: the base model with the existing evidence-bounded policy.
The new opt-in preparation converts complete source assertions into event-local
payloads checked by the unchanged RETAIN v0.6 validator/runtime. It is request-
local integration, not a third capability candidate or a new external claim.
Simplify/remove the preparation if supported expressions cannot stay source-bound,
or a future separately authorized comparison shows its context cost adds no
benefit over the simpler policy. No paid comparison is scheduled here.

**CAPABILITY_DELTA:** HCL can now prepare explicit self-reported belief, denial,
character uncertainty, indirect attribution and local revision from ordinary
text, and combine that state with existing concept/preference/responsibility
operations in one final answer input. The distinction between belief and received
information survives actor, time and access projection.

## API and grammar

`CognitionRequest(..., target_actor='Alice', narrative=text, belief_analysis=True)`
uses the existing `perspective` and `belief` capabilities. `evidence=` may instead
supply timed raw EventRecords; it supplies source/access, not correct mental
state. Ordinary text uses line order and cannot claim calendar cutoffs.

Complete bounded English examples:

```
Alice: In team, I believe proposal is fair.
Alice: In team, I do not believe proposal is fair.
Alice: In team, I am unsure whether proposal is safe.
Alice: In team, I now believe proposal is unfair instead of proposal is fair.
Bob: In team, Alice believes proposal is fair.
Narrator: In team, Alice believes proposal is fair.
```

Context/item/term labels are literal source names, preserving case and scope;
no synonym, negation-opposite, shared-meaning or world-truth inference. A belief
that an item is fair does not establish moral fairness or a normative premise.
Third-party reports remain indirect. Narrator assertions remain source assertions
about belief, and do not enter character information unless explicit access
permits. Exposure creates no acceptance, uncertainty or revision.

At most24 source events,8 assertions,8 proposition labels,4 actors,2 contexts.
Partial, embedded, ambiguous or actor-mismatched belief expressions fail closed
for the semantic package, while authorized reader source remains available.
No extraction provider is called: a source-bound local adapter passes prepared
payloads through the unchanged v0.6 semantic validator. Historical injected
persistent runtimes are rejected on this opt-in preparation path.

Explicit revisions require an earlier affirmed self-report from the same actor,
context and proposition within the current access/time/record scope. If that
anchor is absent or hidden, the new explicit self-report remains evidence without
manufacturing a superseded old state. Other actors/contexts stay independent.

Private prose views use `narrative_access=True` and the existing exact narrated
exposure clause; unmentioned access stays unknown. Receiving the sentence is a
reported exposure, not a verified receipt or proof of believing it.

`prepare_composed_answer` accepts2–3 distinct operations including this retained
belief preparation. All share exact source, focal actor, observer, time and
perspective. One answer adapter call receives all prepared states; zero extraction
calls. Source pooling and lossless context compaction remain optional. Complete
belief revisions are foreign-domain source for concept/preference parsers and do
not erase their valid state. Malformed own-domain syntax is still rejected.

## Evidence and limits

Twelve new provider-free tests check actual transmitted state, ordinary/private
composition, actor/source binding, time/record cutoffs, uncertainty, exposure,
indirect reports and local revision. All existing frozen CG04/CG05 inputs and
engineering helper hashes remain identical. See the committed integration example
`reports/HCL_NIGHT_BELIEF_PREPARATION_RECEIPT.json` and exact-SHA CI artifacts.
These certify engineering correctness only, not new external efficacy. v0.6
retains its historical bounded evidence; CG03 remains development-only RETAIN;
CG04/CG05 remain the two IMPLEMENTED_UNVALIDATED deferred candidates. No new
provider call, spend, budget, trigger or LongMemEval access.
