# HCL v0.7 SAGA Development Utility — Repair Closure

Status: **12/12 DEVELOPMENT CHECK COMPLETE / NO FRESH EFFICACY CLAIM**

## Evidence chain

- Frozen development manifest SHA-256:
  `54fb8e5226e69d79f1667dcb0ab724ec75afbfd541c59d4099e16ca2ed14f0f3`.
- Attempt 1 remains **PARTIAL_CONSUMED** in
  `reports/HCL_V07_SAGA_DEV_V01_ATTEMPT1_PARTIAL.md`: run `36164041203`,
  19 calls, USD 0.0024288 provider-rated peak-cost ledger. Its two completed
  cases were not merged into the repair run as independent observations.
- Repair trigger main: `b864905844186ea31816d3929f365cf088750384`.
- Repair run `36165111831`, first attempt, **SUCCESS**: 12/12 completed.
- Repair artifact ID `10877966052`; ZIP SHA-256
  `d9d1143151468b11fcf980f41d4f550369cebe3fb4545804a5513e8055e7af76`.
- All responses reported `deepseek-flash`. No answer JSON was empty or invalid.
  Three narrator-sentence semantic extractions remained invalid after one
  repair. They were recorded, their claims dropped, and their immutable source
  sentences retained. No false goal state was created from malformed output.

The 12 selected stories were manually source-audited development cases. Their
human goal labels are multiple interpretations, not unique private truth.
All selected story IDs are now provider-consumed development evidence and must
not enter any later fresh v0.7 set.

## Frozen automatic observation

The runner's predeclared automatic observation is agreement with the
source-audited distinction between a directly narrated goal/plan and a goal
inferred from behavior. This is narrower than goal correctness.

| Arm | Source-tier agreement | Directly narrated six | Inferred six |
|---|---:|---:|---:|
| C direct | 9/12 | 3/6 | 6/6 |
| P thin action/goal reminder | 12/12 | 6/6 | 6/6 |
| D v0.7 state | 9/12 | 4/6 | 5/6 |

Paired D versus P: D-only agreement **0**, P-only **3**, both **9**, neither
**0**. D versus C: **1/1** discordant, both **8**, neither **2**. P versus C:
P-only **3**, C-only **0**, both **9**. The sample is too small and manually
selected for a population estimate or efficacy claim; no p value is used to
promote the result.

The semantic adapter produced any structured evidence in only **2/12**
stories, with three persistent extraction failures across 60 source
sentences. D received the same complete story as C/P, so most D answers were
made with little additional extracted state. This run does not demonstrate
incremental utility of the v0.7 structured intention mechanism.

## Case-level source audit

An arm-masked review checked candidate goals and citations against the public
five-sentence narratives. The aggregate arm results were already known to the
reviewer, so this is a diagnostic review, not an independent blinded rating.
Raw stories and SAGA goal labels are not reproduced in this repository.

- `73a`: the quote directly states a desire to play; C and D classified the
  same supported goal as inferred. P classified it as explicit.
- `1054a`: C selected a plausible related goal inferred from behavior while
  an explicit desire appears elsewhere in the story. This is a priority
  difference, not an unsupported private-motive claim.
- `1180a`: C and D inferred a plausible repair goal from an explicitly stated
  proximal plan. P matched the source-tier label but called a different,
  unstated goal explicit. Source-tier agreement therefore overcredits P here.
- `346a`: D called a safety/sleep goal explicit from a sentence describing a
  belief and outcome; that quote does not directly state an intention. C/P
  treated the goal as inferred.
- `1444a`: all three inferred a plausible helping goal. D cited the action
  as well as the emotion; C/P cited only the emotion, a weaker standalone
  justification. This is a source-citation quality difference, not proof of
  D's structured state value.
- The remaining cases had plausible goals with exact source quotes. A quoted
  excerpt's exact presence was machine checked; whether it fully supports a
  particular inferred goal remains a human judgment.

The post-hoc audit is qualitative. It does not replace the predeclared tier
observation with a new numeric score chosen after viewing outcomes. P's 12/12
automatic agreement should not be called perfect goal understanding.

## Operational accounting

Repair run: **99 calls** (63 semantic, 12 each C/P/D), **153,394** input and
**8,600** output characters, **111.583** summed provider seconds. Peak-rate
provider-token ledger **USD 0.01055065**; conservative character-as-token
calculation **USD 0.056338**. Attempts 1 and 2 together charged **USD
0.01297945** to the peak-rate ledger, below the owner's cumulative USD 0.50
authorization. The repair variable was reset to zero after completion. These
figures are operational usage calculations, not a provider invoice.

## Development decision

**SIMPLIFY provisionally.** The thin P method was at least as useful as D on
the predeclared source-tier observation, while D's semantic state was mostly
empty and required 63 additional extraction calls. Use a concise
evidence/uncertainty instruction as the v0.7 comparison method. Retain the
typed runtime as auditable infrastructure, but do not expand or tune it on
these consumed SAGA stories. P's citation weakness and this one-model,
development-only sample prevent an external utility or broad human-cognition
claim.

Before any v0.7 fresh C/P/G/D test, freeze a disjoint story-family selection,
a competent generic structured G, a source-supported scoring protocol and a
separate capped provider authorization. LongMemEval remains sealed.
