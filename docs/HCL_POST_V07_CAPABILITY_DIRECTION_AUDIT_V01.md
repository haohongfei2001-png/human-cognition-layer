# Post-v0.7 Capability Direction Audit v0.1

Date: 2026-09-27. Decision: **v0.8 candidate = evidence-constrained affect and appraisal**.

v0.7 is frozen with SIMPLIFY; no SAGA tuning continues. This short audit
selects one next capability without ordering all later versions. Selection
is a research decision; a stable deficit of the current DeepSeek alias is
not yet demonstrated. The small external check must establish candidate
value over strong direct and simple prompting.

| Direction | Evidence, reuse and decision |
|---|---|
| Relationship/social cognition | [Recent multi-party relationship research](https://aclanthology.org/2026.iwsds-1.38/) reports weak model estimates against simple features. Actor/perspective assets transfer, but relationship identities need public-evidence sufficiency and corpus-access audit. Defer. |
| Emotion/affect | [CAREBench](https://arxiv.org/abs/2605.17176) studies appraisal reasoning, mixed feelings and experiencer/observer judgments; authors report process gaps even for GPT-5.2/Claude-Sonnet-4.6. Source access is verified and goal/perspective/time assets transfer. Select a small candidate, without treating ratings as unique mental truth. |
| Narrative/character understanding | Reuses existing assets, but another goal/perspective task risks extending the closed SAGA/FANToM direction. Keep as transfer context. |
| Moral/value cognition | Stance assets help, but norm agreement is not universal moral truth. No currently audited source qualifies a new mechanism over affect. Defer. |
| Conceptual cognition | Cross-task potential; no specific externally qualified HCL error family or task semantics established here. Avoid premature ontology. Defer. |
| Philosophical cognition | Multiple defensible interpretations leave the external utility criterion unresolved here. Defer architecture selection. |

The next capability distinguishes reported feeling, observable expression,
other-person judgment and plausible hypothesis. A small appraisal vocabulary
covers goal relevance/congruence, control, certainty and accountability.
Mixed feelings remain possible; a good/bad outcome never uniquely proves an
emotion. This reuses v0.7 goals and v0.6 perspective rather than building a
personality model or emotion taxonomy. Fixtures use published concepts,
not owner-private examples or unpublished mechanisms.

## Source audit after minimal implementation

The runtime and independent correctness were implemented before viewing
any CAREBench narrative. The source audit then verified:

- Code: `ZhaoyueSun/CAREBench`, commit `e388179414456bd057d4c9277975844353e73414`.
- Public ungated data: `zhaoyuesun/CAREBecnch` (upstream spelling), commit
  `8b4135219d493c4aaa2474beeefed11779c66890`.
- `first_person.json`: 1,000 records, SHA-256
  `93b410dab0ea3f40796f6e02bf4cb8085898670a340fe2a6f10f154593d6d05c`.
- Only `story_collection.final_scenario` reaches models. Cognitive responses,
  ratings, emotion labels, chat, identity, persona and demographics are withheld.
- [Data card](https://huggingface.co/datasets/zhaoyuesun/CAREBecnch): CC BY-NC-ND
  4.0; code: MIT. HCL stores hashes/IDs and research receipts, not raw
  narratives or redistributed derivative dataset copies.

Narratives were assembled with an LLM and reviewed by their experiencers.
Self-ratings and observer ratings remain reports/judgments, not unique
publicly entailed feelings. HCL therefore audits public support, attribution
and mixed-feeling preservation, not agreement with withheld private labels.
This is an adapted development task, not an official CAREBench score.

[GoEmotions](https://aclanthology.org/2020.acl-main.372/) is a secondary
expression source with reader annotations, not private-mind truth or evidence
of a current strong-model gap. Author/reader differences are documented by
[Uncovering the Limits of Text-based Emotion Detection](https://arxiv.org/abs/2109.01900).
[Context-to-appraisal research](https://aclanthology.org/2025.findings-acl.1359/)
also motivates this direction; single-emotion interpretations still need
source-sufficiency audit. Multimodal sources require a new adapter and defer.

Next: the eight-narrative C/P/D package in
`docs/HCL_V08_CAREBENCH_DEVELOPMENT_UTILITY_V01.md`. No model outcome on it
has been viewed; no v0.8 external utility is claimed.

## Development outcome (2026-09-27)

Run `36263323431` completed 8/8; the frozen diagnostic continuation criterion
was not met. v0.8 is frozen SIMPLIFY; see its final development closure.
This selection did not establish a stable current-provider gap.
