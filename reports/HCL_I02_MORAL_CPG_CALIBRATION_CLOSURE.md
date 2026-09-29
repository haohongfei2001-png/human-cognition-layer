# I02 second-source C/P/G calibration — source-first closure

**Disposition: INTERFACE_FUNCTIONAL_ON_ONE_EXPOSED_SOURCE / SEMANTICALLY_UNQUALIFIED_FOR_I03 / CLOSED_NO_RERUN.**
The repaired G-map shape held and G-final ran. C, P and G are still not
qualified as strong comparators across the four required task families. This
one HCL-authored question on an independently authored first source record is
development calibration, not independent HCL efficacy. No H/H-new call or
H-over-G score exists.

## 1. Original source before outputs

The pinned author-team Moral Stories first record reports the social norm
“It's responsible to keep children safe”, a shared situation and the explicit
goal “Kent wants to add security to his back yard.” It then supplies **two
alternative paths**: cameras with children feeling safer, and an electric
fence with one child accidentally shocked. The fields' original moral/immoral
names were not sent to any model; the common ordinary input names them
Alternative A/B. These are source-reported conditional paths, not two events
known to have occurred together. The shocked child does not prove Kent
intended harm, knew of that risk, or met an adopted responsibility rule. The
explicit security goal is still information about his reported intention;
“no intention information” would erase it.

The [author-team distribution](https://huggingface.co/datasets/demelin/moral_stories)
declares MIT and describes crowdsourced seven-sentence narratives. The pinned
commit is `b830cf56eb00bc4edd1860dd544a192216eb3587`; the full file SHA256
is `98a62d4a083e02ba234ca3d4f2312df6c337ef10cd3f12dcf917a2957ba59c10`,
first-record SHA256
`47412695b214e8ba181d8cc8376001d84e3077436e181834b1b9c5d99b456cb9`.
Only that predetermined first record was parsed for model input. The card's
public examples and this record are exposed and excluded from unseen
confirmation. No native label or confirmation outcome entered a request.

## 2. Frozen execution and complete raw evidence

| Item | Recorded fact |
|---|---|
| Frozen package digest | `f0a6000dd9deafe0072c815dda1434a0a197e0474916e4bfd9c7d54b428f9045` |
| Trigger merge SHA | `11559d9c55fa2463118da2b88fe826874521906f` |
| GitHub Actions run | [36566850936](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36566850936), attempt 1, success |
| Artifact | `11032510830`, ZIP SHA256 `bc5e6c59885f1afc87b489891d31335ea3835975364b149e436f730a1acc5131` |
| [Full raw receipt](HCL_I02_MORAL_CPG_CALIBRATION_RUN_36566850936/raw_receipt.json) | SHA256 `ec676032dee18bd2b9dc184dcf1dc99ebef5772f3b48b719c58d92c80e3a2f65` |
| [Provider-free preflight](HCL_I02_MORAL_CPG_CALIBRATION_RUN_36566850936/preflight.json) | SHA256 `a04b262facf095d296fd5e5afa9836a104775aa1f8389beed6ba9f53ffdbe755`; source/runtime/fairness passed; peak all-phase reservation USD 0.05820672 below USD 0.06 cap |
| Actual configuration | All four responses report `deepseek-v4-pro`; thinking disabled, temperature 0, provider default tier, no retries |
| Calls/usage | C: 331 input + 332 output; P: 433 + 427; G-map: 451 + 298; G-final: 680 + 416; **4 calls**, 0 retries, 0 H/H-new |
| Cost | Usage-based estimated actual USD 0.00416724, rated peak USD 0.00833448, conservative reserved USD 0.04782096, invoice unavailable; USD 0.06 hard cap; remaining authorization **zero** |

The receipt preserves every raw request/response, actual model ID, usage and
parsed result. The all-phase reservation and each pre-call budget guard used
the frozen peak rates. The workflow and exact-main standard checks passed.

## 3. Source-first result for each comparator

- **C:** returned both reported child-safety consequences and correctly did
  not infer harmful intent. Two cited excerpts have exact source IDs and
  quotes. Its `uncertainty` says the source provides *no information about
  Kent's intentions*, which conflicts with the explicit security goal. It
  should have distinguished that goal from an unreported intent to harm.
- **P:** gave the same correct alternative-path distinction and harm-intent
  refusal, with three exact citations including the reported norm. Its
  uncertainty repeats the overbroad “no information about intentions” claim
  and omits the explicit security goal. A longer process prompt did not fix
  that source omission in this item.
- **G-map:** returned the frozen `source_index`/`open_questions` shape with
  three exact-source quotes, so the v2 intermediate interface functioned.
  Its open question also says the source does not state Kent's intention,
  ignoring the security goal; the narrower *harm intention* remains unknown.
- **G-final:** ran with the original complete source and the validated map.
  It separated the two outcomes and did not infer harmful intent or risk
  awareness. It again described intention in general as unstated, despite the
  reported security goal. Its nested citations use `quote` while C/P use
  `quotation`; every cited string is exact, but a future scoring contract
  must choose or normalize this nested key before confirmation.

All four outputs have the four frozen top-level answer fields. Every reported
citation string is a substring of the authorized ordinary source. This is a
manual semantic and interface audit, not a numeric accuracy score or a moral
truth judgment. The shared explicit-goal omission prevents claiming these
comparators are semantically qualified for I03 from this one example.

## 4. Closed state and next work

The unique trigger and USD 0.06 grant are consumed:
`run_attempt=1`, `budget_state=CLOSED_NO_TRANSFER_NO_RERUN`, zero remaining.
The previous MuSR USD 0.12 grant is also closed; neither unused balance is
transferable. No rerun or case swap follows this outcome. The frozen source,
prompts, scorer-free functional purpose, arms and historical receipts remain
unchanged.

**EVALUATION_DELTA:** the generic map v2 passed an actual source-grounded
shape and quote interface on a second writing system, with complete cost
accounting. **HCL cognition CAPABILITY_DELTA:** none in this run. I02 still
needs distinct long-character and abstract/concept source systems,
predeclared semantic rubric and sample sizing, and strong C/P/G qualification
before I03. The exposed native H/H-new preflight from the prior repair is
provider-free only. No confirmation item was scored, LongMemEval was
SEALED / NOT ACCESSED, and leaderboard work remains OFF.
