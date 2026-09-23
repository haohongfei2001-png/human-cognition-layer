# HCL v0.4 Perspective-Safe Correction Action v0.1 — Controlled Diagnostic Closure

Verdict: **INTERNAL DIAGNOSTIC COMPLETE / STRUCTURED GROUNDING FAILED / NO INCREMENTAL UTILITY / NOT PROMOTED**

## Frozen boundary and exact evidence

- The independent six-case synthetic fixture was sealed before provider use at SHA-256 `f76844dac359059e0ffd14f69f4ef8d0f18a84878f915640b5f460b8cc3cd3b8` under `docs/HCL_V04_PERSPECTIVE_SAFE_ACTION_V01_CONTRACT.md`.
- The exact experimental head `bd7cecfd2567b2497156ee2770c4fa4bac7369cc` ran the provider-free preflight and one existing-model `deepseek-flash` C/D/E pass. [Diagnostic workflow 35900191714](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/35900191714) succeeded as an execution job. Its `result.json` artifact SHA-256 is `d3b4d9ac21a8ceb118fecbb4507dfcb10f7b22d89cc5ca0eb3962333c0c89ae9`; the artifact preserves every synthetic prompt and response, per-case state and action rationale. The workflow success is **not** a semantic PASS.
- No external benchmark row, owner-private example, new provider/model, cross-model paid experiment, training, publication, or runtime promotion was used.

| Arm | Safe action | Calls | Input characters | Output characters | Schema repairs |
|---|---:|---:|---:|---:|---:|
| C — full-history structured reconstruction | 5/6 | 12 | 47,780 | 10,378 | 0 |
| D — persistent structured updates | 5/6 | 23 | 88,354 | 26,247 | 0 |
| E — direct full-history reasoning | 6/6 | 6 | 14,828 | 1,498 | 0 |

All action IDs stayed within the four frozen options. The fixture/gold separation preflight passed; no scoring key was included in model prompts. The synthetic scoring key measures safe action under explicit fixture evidence only, not real human belief.

## Semantic audit

All six C final states, all 17 D sequential updates, and all 18 action rationales were reviewed against the visible raw-event chronology. State citations used fixture event IDs, and `OTHER_UNKNOWN` remained present. The material failures are:

1. `science_fair_title_disputed`: C and D treated Paz's receipt of the **old approved title** as support for receipt of the **current replacement correction**, although the only replacement came from an unsigned draft and the curator explicitly said no replacement had been approved. Both chose `ASK_CONFIRMATION` instead of the frozen safe action `VERIFY_SOURCE`. This is a source-authority and correction-identity failure, not merely a wrong option ID.
2. `film_credit_later_revision_unconfirmed`: D continued to mark `ACCEPTED_CURRENT` as `SUPPORTED` from Rae's acceptance of **Marin** after the later **Marina** correction was delivered without a reply. D chose the safe action `ASK_CONFIRMATION`, but its state violated the frozen rule that acceptance of an earlier revision does not establish acceptance of a later one. The older assertion was not revised correctly.
3. In D's early updates for `makerspace_rule_acknowledged`, the original 10:00 instruction was described as a “current correction” before the 11:00 correction existed. This shows the target's correction identity was not consistently grounded throughout incremental maintenance.
4. E chose all six safe actions, but its final `film_credit_later_revision_unconfirmed` rationale called “receipt/acceptance” unconfirmed although delivery of the latest correction was explicit. Acceptance alone was unconfirmed. E's action result is stronger here, but its rationale is not a perfect perspective-state certification.

The C and D structured arms **fail the grounded-state gate**. Their 5/6 action scores cannot be reported as HCL capability success. E is a cheaper, stronger action baseline on this bounded synthetic set, with the noted wording error; six cases do not establish broader transfer or real-world cognition quality. D has no utility or cost advantage over E.

## Closure and next boundary

The experimental implementation, frozen fixture, and raw artifact remain for audit; do not merge them into main or tune/rerun these six cases as fresh evidence. Main HCL runtime remains unchanged. A future internal capability question must have a separately frozen, independent contract and fixture; any new external benchmark, cross-model paid experiment, model training, owner-private material, or public release needs its own authorization and gate.
