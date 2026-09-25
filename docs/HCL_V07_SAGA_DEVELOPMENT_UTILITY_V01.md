# HCL v0.7 SAGA C/P/D Development Utility Protocol v0.1

Status: **SOURCE SLICE AND PROVIDER-FREE PACKAGE FROZEN / NO v0.7 PROVIDER CALL**

## Purpose and source boundary

This is a small development check of evidence-constrained intention and goal
reasoning, not a fresh efficacy estimate. SAGA's original goals are distinct
crowd interpretations, often several for the same story. They are not unique
access to a character's private mental state. The check asks whether the
v0.7 evidence state helps a model distinguish directly stated goals from
plausible goals inferred from actions, while citing the public narrative.

Source: `saiumbc/SAGA` at `9c66afefb06b8bad77fc7f5913ddc8264a57c69b`,
`data/actual_test.jsonl`, SHA-256
`a00ed709011dfdcb2016b0bb25753eaca4445afdbf8ae87bf4b33c213e415764`.
The file has 219 annotation rows but only 81 unique story/participant groups.
The 12 development entries in `eval/v07/saga_dev_selection_v01.json` use
12 distinct story IDs, six with a directly narrated goal or proximal plan and
six where a goal must be inferred from behavior/context. Their manifest SHA-256
is `54fb8e5226e69d79f1667dcb0ab724ec75afbfd541c59d4099e16ca2ed14f0f3`.
Selection was manually audited for public source sufficiency; it is not a
random sample. SAGA goal labels were visible during source audit, so this
slice is strictly development evidence. No selected story ID may later enter
a v0.7 fresh pilot, including through alternate-story siblings.

The source tier refers to whether **any relevant goal or plan** is directly
stated in the five public sentences. It is not an assertion that the human
annotated `original_goal` is the only correct motive. SAGA's `goal_revision`
field rates proposed future plans and is not treated as direct proof that a
character revised their actual goal. Its hidden or crowd-judgment fields never
enter model state construction or answer prompts.

## Frozen arms and firewall

All arms use the existing DeepSeek credential, `deepseek-flash`, temperature
zero, disabled thinking, the same 256-token answer maximum and a shared JSON
answer schema: evidence class (`EXPLICIT`, `INFERRED`, `INSUFFICIENT`), candidate
goal and exact source quote. C receives the complete five-sentence story and
participant, with common evidence/uncertainty instructions. P receives the
same material with one thin action-versus-goal reminder. D receives the same
story plus v0.7 state: source-anchored intention/goal/action evidence,
provenance, status and bounded perspective. D's semantic state is built from
five reader-only narrator events before the highlighted participant/task is
released. The semantic adapter never sees SAGA labels, selected source tier,
answer fields or other benchmark metadata.

Narrated action is represented as action evidence with narrator provenance;
it cannot by itself establish private intention. Reader-only goal evidence can
inform the external system without entering the character's own perspective
view. Independent synthetic regressions cover both boundaries.

## Scoring and interpretation

The runner enforces JSON shape and exact source quote membership, and records
agreement with the manually audited source tier. **Tier agreement alone is not
goal correctness.** After a run, a blinded case audit must judge whether each
candidate goal is supported and whether uncertainty is calibrated, accepting
multiple plausible interpretations. Report paired C/P/D outcomes and every
invalid/unsupported answer; do not grade free-text goals by exact match to one
SAGA crowd label. The development slice may motivate a benchmark-independent
repair, but its exposed cases cannot become fresh evidence.

## Operational cap and one-shot rule

Maximum calls: semantic extraction 120 (five sentences, at most one repair
each), and C/P/D 12 each: **156** overall. Character caps are 665,000 input
and 136,000 output overall. Using peak no-cache input USD 0.30/M and output
USD 1.20/M, the character-as-token cap calculation is USD **0.3627**. A shared
pre-request reservation ledger additionally blocks requests before the
provider-rated amount could exceed USD **0.50**; missing usage or transport
uncertainty charges the full reservation and stops the run. No SDK retry.
These are operational safeguards, not an invoice guarantee if provider rates
change. The one-shot workflow additionally requires an exact-parent trigger
and first attempt, verifies the source digest, manifest and provider-free
tests, and requires a separately set authorization variable of at least
USD 0.50. The trigger is absent and the variable is unset. The prior USD 3.50
authorization covered only the completed v0.6 FANToM pilot, not this check.
No new account, credential or LongMemEval call is contemplated.

The result artifact will include source IDs/hashes, arm answers, state hashes,
repair counts, failures, model identities, calls, characters, wall time and
provider-rated cost. Raw SAGA stories and goal labels will not be committed to
the HCL repository. A partial run is marked consumed development evidence and
is not silently presented as a completed comparison.
