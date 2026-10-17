# M06 → M08 → M05: bounded character-relative causal appraisal

Status: **INTEGRATED_OFFLINE** for the explicit finite increment only. Original
requirements: P10, M08 §1–4, T10 and the S3 integration obligation in
`HCL_SYSTEM_REDESIGN_SPEC.md`. Full M08, M09, S3 and S4 remain open.

## Contract and compatibility

`affect.evaluate` accepts the additive `hcl-affect-candidates-2` candidate and
executes `affect-model-2` / `s3-finite-affect-2`. Each v2 episode adds
`attributions`; an empty list asserts no implemented attribution for that episode.
The v1 candidate, context wire, operator output, ordinary answer and nested
relationship/literature paths retain their previous representation. The installed
provider remains `OfflineModelPort`; the unchanged v1 context is deliberately not
presented as automatic v2 extraction. No paid provider, new credential, sealed
input or new service is used.

Each source-anchored bridge specifies:

- Episode-local ID, goal, exact actor and episode time, and an explicit attributed
  `event_id` resolving to the same mental timeline at or before the episode.
  Event identity and event time remain part of appraisal semantics. A declared contributor
  (source-local actor ID or null for a non-person cause). Contributor identity is
  supplied by the source hypothesis, never inferred from a causal equation.
- Cause variable, distinct actual/contrast Boolean values, and outcome value.
  These are factual tests, **not observations** and not presumed knowledge.
- Explicit Boolean atom/polarity projections from M03 to causal variables,
  including the target. Unmapped variables stay latent. Cause and target differ.
- One or more same-model M06 structural references, each with a nonempty
  source-anchored `available_when` conjunction over M03 atoms. This is a proposed
  character-access mechanism, not proof that the person knows the true theory.
  The M06 model `source_event_id` separately resolves its theory-declaration source
  in the same timeline; it need not equal the attributed event. A future theory
  source is unavailable until its own time, even if a gate says true. It may be
  included in an earlier bridge only as an unavailable alternative, allowing a
  later unchanged `NEW_INFORMATION` mechanism to consume it without backfilling.
- A cumulative per-bridge world-evaluation bound in 0–4096, further restricted by
  the remaining shared local budget. Existing M03/M05/model/schema caps remain.

The compiler rejects foreign identities, times, structures and atoms, tautological
self-target interventions, invalid polarities, unbound condition IDs, mismatched
goals and computed appraisal inputs. `NEW_INFORMATION` preserves bridge identity,
structures, gates, mapping, contrasts and all prior goal/coping mechanisms; only
its required episode-time binding changes. An analyst may propose a new reading
using `ANALYST_REINTERPRETATION`, which never establishes character reappraisal.

## Actual computation and epistemic boundaries

1. The existing M03 event mechanism supplies the actual actor-view at the episode
   time. Reception, understanding and acceptance remain separate; earlier views
   are never recomputed using a later report. System ACL is checked independently.
2. Preserve the joint actor-world projection over both observation and gate atoms.
   Deduplicate only equivalent projections, never infer probability from counts.
   A world with no available structure remains unresolved even if another world
   has identical causal observations and an available structure.
3. Call the existing M06 `evaluate_counterfactual` for each retained accessible
   structure/projection. Its factual abduction uses **only** the actor projection.
   The analyst query's `observations`, `interventions` and result values do not
   supply or repair the character's beliefs. The declared structure is explicitly
   bridged rather than imported as omniscient character truth.
4. Classify each paired factual/intervened trace under the **same exogenous
   background**:
   - `OUTCOME_UNESTABLISHED`: the target does not match the tested outcome.
   - `CAUSE_NOT_ACTUAL`: the target matches but the tested cause value does not.
   - `CONTRIBUTES`: the tested cause and outcome match and the contrast changes
     the target.
   - `NO_BUT_FOR_DIFFERENCE`: the tested cause/outcome match but this contrast does
     not change the target. This is not a general finding of no causal role.
   - Missing structure, inconsistent observations or an uncomputed frontier adds
     `UNRESOLVED`; it cannot certify any negative conclusion.
5. Union all retained worlds and structures. No majority rule, favored-model
   selection, pseudo-probability or certainty from an explored prefix is allowed.
   A determinate M06 target value alone is insufficient for determinate attribution.
6. An attribution condition names its bridge and goal. Its three-valued result
   enters the existing competing emotion mappings and coping priority adjustment.
   Unknown conditions preserve both adjustment branches. Their actual utilities
   are passed to M05, producing real Q values, feasibility and conditional next
   appraisals; coping is never claimed to have occurred.

These are finite **but-for contrast** explanations conditional on proposed
character beliefs and models. Overdetermination can return
`NO_BUT_FOR_DIFFERENCE` despite a meaningful causal role. `CAUSE_NOT_ACTUAL` is
relative to the character-view candidate; neither label establishes reality,
knowledge, innocence, blame, intention, control or actual emotion. Historical
cause control is explicitly not inferred. Existing goal-specific coping control
remains a separate M05 calculation. Normative and identity dimensions remain
`NOT_MODELED`. Emotion labels and mappings remain challengeable hypotheses.

The projected atoms are source-declared event-specific beliefs at appraisal time,
not an automatic snapshot of objective values at the historical event time.
A later physical device state must not silently stand for its earlier cause;
validating that semantic alignment remains open. Event IDs alone do not solve it.

Reappraisal compares event/target/cause/contributor identities, status and possibilities,
not episode timestamps, source/result IDs, world IDs or solver work. Full immutable
provenance remains available separately. Unrelated goals and evidence-only changes
are not reclassified as appraisal changes.

## Verification, recovery and concrete effect

The ordinary answer consumer reconstructs M03 views, projects gates/observations,
reruns M06 and verifies every retained trace/case and union, then recomputes the
mapping, coping branches and M05 results. V2 additionally verifies shared work
conservation across mental batches, views, per-goal planning, causal evaluation,
coping and reappraisal comparison. The actual nested mental operation is replayed
under the remaining budget rather than trusting its self-reported batch charge.
UNCOMPUTED rows cannot carry unverified causal
conclusions. Source versions and current ACL remain required for every delivery.

The original synthetic witness holds damage, goal consequences and action graph
fixed. Before B receives the correction, its conditional valve contribution
supports a distress candidate and a safety-focused coping model:

- Priorities safety=3/4, duty=1/4; M05 Q(cross)=-5/2, Q(wait)=-1/2; best=wait.
- After actual accepted receipt, the tested valve cause is absent in B's updated
  view; the candidate changes and the adjustment no longer applies.
- Priorities safety=1/4, duty=3/4; Q(cross)=5/2, Q(wait)=1/2; best=cross.

This change is an effect of the declared experimental coping hypothesis, not a
claim that a human would choose this risky action. Cutting M06 consumption leaves
both coping branches unresolved; cutting the attribution-conditioned M05
adjustment removes the initial wait prediction. Unreceived, misunderstood,
untrusted and late messages do not make the same update; analyst corrections do
not enter character observations. Unknown causes, conflicting structures and
budget frontiers retain competing interpretations and actions.

Exact predecessor recovery executes **PR451 main
`04174fc512cb3979c38d2ba398257e32dd46fee8`**, tree
`69eb56b723adad0e095615c93cddcb7b0699c731`, with only its 242 inventoried Python
runtime files. Bundle:
`01c1235d8defd15328ad4d02a104a7777dc62ed6b6c4193e396ee91683fe93bd`.
Real schema 3/4 v1-affect and v3-literature tasks cover completed, RETURNED,
UNKNOWN, computed and committed seams. Old context/proof/answer/claim bytes stay
unchanged, old writers are fenced, UNKNOWN is not resent, and ACL withdrawal
blocks previously completed delivery. This is not a regenerated approximation of
predecessor results.

Evidence entrypoints:

- `tests/test_unified_causal_affect.py`: independent Boolean enumeration through
  the formal entry, hand-computed Q, late/other-actor isolation, confounding,
  overdetermination, unknown/gate/structure/work boundaries, source/ACL, edge
  ablations, certificate tampering, run/stream and durable seams.
- `tests/test_unified_causal_affect_upgrade.py`: exact PR451 process and both
  persisted schemas, old v1/v3 claims and all recovery seams.
- `scripts/witness_unified_causal_affect.py`: 14 original-source compositions,
  actual consumers, run/stream, no-resend replay and ACL denial. Every invocation
  records the exact checked-out HEAD and runtime hash.
- The unchanged complete applicable suite and prior 28 witnesses, plus the new
  witness, are required on the final published HEAD. Focused development checks
  do not substitute for that release evidence.

Open obligations include richer/non-but-for actual causation, open causal belief
extraction and validation, semantic emotion mapping validation, normative/identity
appraisal, calibrated dynamics, broader coping search and complete M08/S3/S4.
No stage exit, live-model gain or open-world completeness is claimed.
