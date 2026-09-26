# HCL v0.7 Intention & Motivation Final Development Closure

Status: **FROZEN / SIMPLIFY / SAGA DIRECTION CLOSED**

## Execution and immutable receipt

On 2026-09-27 (Asia/Shanghai), the owner authorized a separate USD 0.50
fresh SAGA pilot. Trigger-only PR #78 merged as main
`37c3939a4cd3ca177a6c20fcca01fd53fc966d4b`. The frozen code package had
already passed exact-main checks at `42f95450061da8b1c54a7205b62fb66f55e4c3ed`.

[Run 36260603724](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36260603724)
completed **SUCCESS**, first attempt, 16/16 stories. Its workflow rechecked
the exact-parent trigger, pinned source digests, entire-split story-ID
separation, selection identities and provider-free regressions before calls.
Artifact ID `10911849154`; downloaded ZIP SHA-256 matches GitHub's digest:
`6113bd11212f57b91c6eab3587da0f31ea847984220c9dc0fef1f402c7f3ad76`.
The structured receipt is `reports/HCL_V07_SAGA_FRESH_V01_RECEIPT.json`.

All 16 selected story families are now HCL provider-consumed. Selection was
manual and source-only, not random. No further run on these stories is fresh.
LongMemEval remains sealed and untouched. The fresh authorization variable
was reset to zero after completion; the historical one-shot trigger is retained.

## Frozen automatic observation

This observation is **source-tier agreement**, not full goal correctness.
The predeclared labels distinguish direct narrative goal/plan evidence from
inferred goals. A matching tier can accompany an unsupported candidate goal.

| Arm | All 16 | Explicit tier, 8 | Inferred tier, 8 | Invalid answer JSON |
|---|---:|---:|---:|---:|
| C, strong direct/common evidence instruction | 14 | 7 | 7 | 0 |
| P, thin extra reminder | 14 | 7 | 7 | 0 |
| G, complete generic chronology | 14 | 8 | 6 | 0 |
| D, typed intention state | 15 | 8 | 7 | 0 |

| Pair, A versus B | A-only agreement | B-only agreement | Both | Neither |
|---|---:|---:|---:|---:|
| P versus C | 1 | 1 | 13 | 1 |
| P versus G | 2 | 2 | 12 | 0 |
| P versus D | 0 | 1 | 14 | 1 |
| D versus G | 2 | 1 | 13 | 0 |
| D versus C | 2 | 1 | 13 | 0 |

These small discordant counts do not establish a stable mechanism increment.
No significance-driven expansion, post-hoc replacement score or label tuning
was performed.

## Case review and causal limits

The reviewer inspected all answers with method identities shuffled separately
per case, before looking at aggregate tier scores. Frozen tiers remained
visible. Notes were saved before unmasking, SHA-256
`1a1cba24ffbd7bc67132e1cad71ec1a42759f5afb2ffec486e04e75b2b2c6ff3`.
This was one agent's diagnostic review, not independent human adjudication;
answer style could reveal method identity. The following maps the saved
observations back to C/P/G/D. Raw narratives are not reproduced here.

| Case | Source-grounding diagnosis |
|---|---|
| 52a | All four recognize the directly narrated business desire. |
| 757a | All four use the narrated relaxation need as a proximal goal; need versus desire remains a conceptual qualification. |
| 649a | All four recognize a directly narrated voting decision. |
| 1501a | C/P underclassify the direct request; G/D recognize its explicit communicative goal. All candidates are plausible. |
| 826a | All four ground the candidate in the narrated doll desire. |
| 445a | All four ground the investment goal in a narrated wish. |
| 1294a | All four ground the archery goal in a narrated desire. |
| 709a | All four ground the lifting aim in directly narrated trying. |
| 184a | All four propose a plausible sharing goal. The frozen inferred tier is debatable because a narrator purpose phrase can also directly express a proximal aim. |
| 544a | P/D promote a conditional reward offer to an explicit private goal; C/G preserve inferred status. |
| 910a | All four propose a plausible inferred performance goal. The outcome quote alone does not entail the prior plan; the full narrative supports a candidate explanation. |
| 190a | All four infer a reasonable hosting goal from the invitation and full occasion context; the short quote alone omits part of that context. |
| 121a | All four propose a reasonable dinner goal without claiming that changing the action proves goal revision. |
| 1339a | C/P/D preserve a permissible eating hypothesis; G unnecessarily abstains. Abstention does not mean the participant has no goal. |
| 1372a | C calls display behavior an explicit goal, an interpretive boundary. P/G offer plausible later bird-care goals. D adds an unsupported exclusion of hatching/raising intent without distinguishing the earlier episode from later care; its tier agreement hides this problem. |
| 793a | G promotes narrated worry to an explicit performance goal under the frozen policy; C/P/D keep an inference. The worry/goal boundary remains interpretive. |

The frozen score is retained unchanged, including cases with debatable tier
boundaries. Directly narrated purpose, need, desire and request are not
interchangeable measurements of a single hidden motive. Alternate plausible
goals must remain allowed; one crowd annotation is not private mental truth.

D produced any semantic evidence in **5/16** stories, one evidence row each.
Three sentences failed both extraction attempts; their source text survived
and no semantic claim was created. All 80 source events survived. The sole
D-over-P tier win, 1501a, had **zero** D semantic evidence. Both D-over-G tier
wins, 1339a and 793a, also had zero D semantic evidence. Thus the comparative
observation cannot be causally attributed to the specialized intention
projection. There was no ablation; serialization or generic prompting may
account for these readout differences. D's unsupported exclusivity in 1372a
also prevents interpreting 15/16 as 15 correct goal explanations.

## Operations and cost

Every response reported the alias `deepseek-flash`, with temperature 0,
thinking disabled, seed 42 and the same 256-token answer maximum. The alias
is not an immutable checkpoint identifier; no cross-date checkpoint equality
with the development run is claimed.

| Component | Calls | Input chars | Output chars | Peak-rated ledger USD |
|---|---:|---:|---:|---:|
| C | 16 | 12,158 | 2,414 | 0.00171660 |
| P | 16 | 13,598 | 2,453 | 0.00179580 |
| G | 16 | 56,813 | 2,498 | 0.00622920 |
| D answer | 16 | 32,097 | 2,483 | 0.00298302 |
| D semantic construction | 83 | 145,870 | 4,615 | 0.00801949 |
| Total | 147 | 260,536 | 14,463 | **0.02074411** |

Provider wall time summed to 119.15549 seconds. D construction plus answer
cost USD 0.01100251 versus P's USD 0.00179580. The ledger uses provider token
usage and conservative peak rates, rechecked against
[official DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/)
on 2026-09-27; it is not the provider invoice. All frozen caps were respected,
with no SDK retry, transport failure, invalid answer or budget failure.

## Final decision

**SIMPLIFY** the v0.7 operational method to the already tested common
source-evidence and uncertainty instruction with the complete narrative.
P's added reminder has no observed net advantage over the strong C control;
it is optional, not a proven increment. Neither G nor D warrants added cost
or architecture as the default on this evidence.

Keep the typed intention/goal runtime, provenance, revision, perspective and
fail-closed infrastructure for audit and future integration. Its provider-free
correctness is distinct from demonstrated downstream utility. Do not expand
or tune it against the consumed SAGA stories. The pilot does not test all
runtime transitions or establish broad motivation understanding.

The development check and this fresh pilot now close v0.7's SAGA direction.
Continue with a short capability-direction audit, choose one evidence-grounded
next capability, and implement provider-free correctness before external
utility validation. No LongMemEval execution or v0.8/v0.9 sequence is implied.
