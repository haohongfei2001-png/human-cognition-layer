# Canonical HCL Status

## Current phase

**POST-CG05 REVIEW COMPLETE; CG03/04/05 DEVELOPMENT-ONLY RETAIN; INDEPENDENT GENERALIZATION PREPARATION; NO CG06**

This file is the single live status. Historical statuses, gates, budgets and always-on policies are superseded; their complete record remains at [pre-v1 main c6b0eca](https://github.com/haohongfei2001-png/human-cognition-layer/blob/c6b0eca63295166ce4b2fb6984911b94ec90e349/STATUS.md). Current remote main and exact-SHA CI remain the code facts.

## Canonical policy

Capability growth is the development main line: **real human-cognition capability growth > external validation > leaderboard**. Base model first. Use the minimum evidence-grounded capability set only when needed. A simple prompt or generic exact tool is preferred when sufficient. Specialized mechanisms require incremental evidence. No automatic action-to-motive/emotion, narrator-to-character, exposure-to-revision, or computation-to-world-truth promotion. The owner-authorized frozen CG04 and CG05 comparisons are both consumed and closed. All grants are zero; no paid run, rerun or budget transfer is currently authorized. The canonical execution plan is [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

## Engineering state

**V1-00 through V1-08 COMPLETE / PROVIDER-FREE CERTIFIED.**

- PR #112: executable registry with 22 capabilities and inactive-capability rejection. Registry main `d7ef836dd0dc8ebd409f2bc92f218b1e6caf24aa`, exact-main run 36346501198 PASS.
- PR #113: deterministic router, sparse context, unified evidence hierarchy, minimal answer execution, generic tools, cost classes and import boundary. Runtime main `9070bbcf518b5aa69b92502949998413e0960d1d`, exact-main run [36347078900](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36347078900) PASS.
- Certification receipt correction: the v1 workflow now explicitly checks out the PR head and records the actual checkout SHA separately from GitHub's synthetic PR merge-event SHA. Earlier PR-associated runs were merge-candidate checks; exact-main runtime evidence remains valid. Final corrected exact-head/main receipts are emitted by CI.
- **42 v1 + 176 frozen v0.4–v0.10 provider-free tests = 218 PASS**. All six existing exact-main workflow groups passed. No historical benchmark/provider experiment was rerun.
- An integration test exposed hidden proposition names in zero-support historical belief estimates; v1 removes them without changing the frozen v0.6 runtime or weakening the test.
- V1-09: two-source public qualification audit completed, including eight source-only DREAM dialogue families. **No qualified integrated selection**; no frozen fresh/paid C/P/G/H package. Source exposure and candidate limitations are recorded in the protocol.

Runtime: `hcl/v1`; [inventory](docs/HCL_V1_CAPABILITY_REGISTRY.md); [router/API](docs/HCL_V1_COGNITION_ROUTER.md); [source audit and evaluation design](docs/HCL_V1_INTEGRATED_EVALUATION_PROTOCOL.md); [handoff](reports/HCL_V1_INTEGRATION_FINAL_CLOSURE.md); [runtime receipt](reports/HCL_V1_PROVIDER_FREE_CERTIFICATION.json).

The answer adapter performs one model call; default v1 schedules zero extraction calls. Optional capability packages may use an explicitly opted-in semantic-preparation adapter call, recording its input, output and cost separately. Optional typed context requires validated upstream semantic evidence; access metadata is not automatically mined from prose. The deterministic bilingual router has finite vocabulary; injected historical state is caller-managed. This is a working foundation, not external efficacy. The final handoff commit's exact SHA, counts and CI receipt are also emitted by the v1 workflow artifact for that commit, avoiding a self-referential static SHA in this file.

## Historical capability dispositions

| Asset | Disposition |
|---|---|
| v0.4/v0.5 | frozen evidence/provenance, actor/time, stance/revision/persistence foundation; no synthetic tuning |
| v0.6 | RETAIN perspective/belief; fresh C/P/G/D 11/19/22/30 of 32, D-only/G-only 8/0; consumed, no rerun |
| v0.7/v0.8 | SIMPLIFY, optional typed evidence/audit context; SAGA/CAREBench closed |
| v0.9 | generic exact causal computation development signal only; source-scoped assumptions |
| v0.10 | generic exact argumentation non-fresh development signal only |
| quantifier/witness/alternative reading | conditional correctness tools; no external semantic superiority |
| Circa/CLASH/TORQUE/FOLIO | frozen SIMPLIFY/no increment/inconclusive dispositions; consumed families closed |
| LongMemEval | SEALED / DEPRIORITIZED; 32 rows untouched, no trigger/read/consume/reinterpret/delete |

Historical closure reports under `reports/` remain unmodified. No benchmark, paid workflow, authorization variable, credential, private thought material, plan or account was changed in this round.

## Current capability-growth work

The previous `HCL_V1_INTEGRATED_SOURCE_QUALIFICATION` remains a useful **external-validation backlog**, but it is no longer the sole development blocker. The main line now follows [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

**CG01-A — IMPLEMENTED.** Generic `why` / `为什么` no longer activates intention by itself. READER_ANALYSIS / CHARACTER_PERSPECTIVE / OBSERVER_ABOUT_TARGET are explicit in the v1 request, plan and answer context.

**CG01-B — IMPLEMENTED.** The bounded `hcl/v1/cg01.py` checker tests source, action time, perspective availability, explicit knowledge/goal/opportunity conditions, contradiction and local revision. Unknown conditions remain unknown.

**CG01-C — PROVIDER-FREE IMPLEMENTED; EXTERNAL INCREMENT UNPROVEN.** A conservative ordinary English narrative path prepares finite candidates without caller-entered mental state and preserves actual source, perspective, candidate, condition and final-message content in debug receipts. The grammar is deliberately bounded; unrecognized cases fail closed. See [implementation limits](docs/HCL_CG01_IMPLEMENTATION.md).

**CG01-CERT — PROVIDER-FREE CERTIFIED.** PR #117 exact head `b0fbca3df69eec36d16a8a0616caca36d2f99dc0`, [run 36388937743](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36388937743); merged code tree on main `9c28284c4fe2935adbc5ddb6ade92ae9f063d014`, [run 36389075682](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36389075682). Both receipts record 59 v1 tests + 176 frozen historical regressions = **235 PASS**, provider calls/spend 0, and LongMemEval sealed. All six exact-main workflow groups passed. This certifies correctness, not external benefit.

**CG01-D — EXECUTED ONCE:** four source-audit-exposed cases from two public-domain story families, with C/P/G/H/H-new arms, exact source digest, scorer, 24-call maximum and USD 0.75 owner-authorized hard cap. See [protocol](docs/HCL_CG01_EXTERNAL_DEVELOPMENT_PROTOCOL.md), [package](reports/HCL_CG01_EXTERNAL_PACKAGE.json) and [raw receipt](reports/HCL_CG01_EXTERNAL_RUN_36392929956.json).

**CG01-E — SIMPLIFY / CLOSED.** [First-attempt run 36392929956](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36392929956) used all 24 calls, returned 20 answers, and recorded USD 0.05900004 as a conservative peak-price cost upper bound. All four semantic preparations failed exact source-span validation; H had no checked candidate, and H/H-new final messages were identical in every case. P scored 2/4 strict valid-and-status-matched responses against H 1/4; this tiny, source-audit-exposed probe cannot estimate broad efficacy. The ordinary-text route has no demonstrated specialized increment and remains opt-in; use the simpler P path for this task class. The deterministic checker remains available for validated typed evidence. Checker efficacy is inconclusive because the paid H arm never exercised it. See [source-first closure](reports/HCL_CG01_EXTERNAL_DEVELOPMENT_CLOSURE.md).

The generic provider-free repair now aligns only unique whitespace variants to exact source spans, rejects unanchored events and dependent claims, uses source order, and preserves paid extraction output/cost on validation failure. These prospective fixes do not change the consumed run. No rerun or new paid package is authorized; the unused grant is closed at zero. LongMemEval remains sealed.

CG-01 remains **SIMPLIFY / CLOSED** for ordinary-text use; its deterministic checker remains optional for source-validated typed evidence, with specialized efficacy inconclusive because the paid H arm never exercised it.

## Active capability-growth work

**CG-02 — SOURCE-FIRST INCONCLUSIVE / CLOSED FOR THIS DEVELOPMENT PACKAGE.**

Canonical contract: [docs/HCL_CG02_CAPABILITY_CONTRACT.md](docs/HCL_CG02_CAPABILITY_CONTRACT.md).

CG-02 targets a new social-cognition capability: preserve what a proposal, request,
acceptance, refusal, conditional commitment or withdrawal actually expressed;
track which conditions each participant could access; compare participant
expectations; and explain bounded misunderstandings without automatically
inferring deception, betrayal, trust change, relationship status or moral blame.

Execution order:

- **CG02-A** — v1 operation/routing surface;
- **CG02-B** — grounded social-act and condition checker;
- **CG02-C** — participant expectation/misunderstanding comparison;
- **CG02-D** — bounded ordinary-text semantic preparation;
- **CG02-CERT** — provider-free certification and regressions;
- **CG02-E** — provider-free freeze of C/P/G/H/H-new external package.

The CG-01 lesson is now a hard validation gate: no paid authorization request is
valid unless provider-free preflight proves the selected H cases actually execute
the CG-02 treatment and that H/H-new final inputs differ because of that
treatment.

The A-D implementation adds the explicit v1 social route, source/time/access
checker, participant expectation comparison and a narrow provider-free
ordinary-dialogue path. See [implementation and limits](docs/HCL_CG02_IMPLEMENTATION.md).
PR [#121](https://github.com/haohongfei2001-png/human-cognition-layer/pull/121)
exact head `54bc3e99a4850ba2dabe525020747e730957982d`,
[run 36399944493](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36399944493),
and merged main `ec02f8e5b8056dfb28e329afc0c2e834fefee7a8`,
[run 36400034483](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36400034483),
both record 93 v1 + 176 frozen historical = **269 provider-free PASS**,
the same runtime digest, zero provider calls/spend and LongMemEval sealed.
The other five exact-main workflow groups also passed. This certifies
correctness and treatment presence, not external efficacy.

CG02-E freezes [four public HCL-authored development dialogues and all five
C/P/G/H/H-new inputs](reports/HCL_CG02_EXTERNAL_PACKAGE.json), with
[protocol and score rule](docs/HCL_CG02_EXTERNAL_DEVELOPMENT_PROTOCOL.md).
All four H cases passed source, checked-act, checked-expectation, H-state,
H-new-ablation and final-input-difference gates without provider calls.

The provider contract was subsequently corrected before any paid execution:
CG-02 now reuses the repository's existing `DEEPSEEK_API_KEY`,
`deepseek-v4-pro` / `DeepSeek-V4-Pro-0813`, thinking disabled and JSON
response mode. The superseded `gpt-6-sol` / new-`OPENAI_API_KEY` assumption
must not be executed. No new account, credential or provider is required.
Using the same repository-frozen conservative DeepSeek peak-price basis as CG-01,
20 calls at the frozen per-call bounds have a worst-case rated ceiling of
**USD 0.2517504**, within the unchanged proposed **USD 0.30 hard cap**.

A dormant one-shot DeepSeek workflow remains for historical reproducibility,
with its grant reset to zero and the trigger removed. The single authorized
CG-02 run is consumed; no rerun is authorized.

Provider refreeze PR #123 merged as `1c08a059815a82c7eea0804212e2ce74c50c5084`.
Its exact-head provider-free checks passed before merge. The first merge-push CI
attempts failed during dependency installation before any HCL test executed;
this was CI transport/dependency failure rather than capability evidence.
Follow-up main `86e1db9ecdb908cbe67bc561b878a0d37e4cb819` completed the
provider-free certification with successful [v1 run 36410904352](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36410904352).

Owner-authorized DeepSeek [run 36413088075](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36413088075)
used the exact frozen package and all 20 C/P/G/H/H-new calls once, with no
retry and no LongMemEval access. All four H cases passed treatment-presence
preflight. [Full raw receipt](reports/HCL_CG02_EXTERNAL_RUN_36413088075.json)
records 13,353 input and 1,648 output tokens, actual model IDs, raw API
requests/responses, scores and usage. Conservative rated cost was USD
**0.02415204** versus the USD 0.30 hard cap; the usage/time-based provider
price estimate was USD **0.01125938**, not a verified invoice. Artifact ID
10966520253; receipt SHA-256
`ca271347f343647f190d2c9ba55140865421ff13d79aaebdd46250b308e9b972`.

The [source-first Phase E closure](reports/HCL_CG02_EXTERNAL_DEVELOPMENT_CLOSURE.md)
selects **INCONCLUSIVE**. Strict exact-field scores were H 24/28, H-new 9/28,
P 7/28 and G 9/28, but the P/G task inputs omitted several required enum
values that H's checked context supplied. The small HCL-authored synthetic set
therefore does not establish a qualified specialized increment. No case, gold,
prompt, scorer or treatment was changed or rerun. CG-02's deterministic checker
remains an optional source-valid correctness component; external utility remains
unresolved. This is development evidence only, not fresh/independent evidence.

The current engineering milestone is:

**NIGHT-INTEGRATION-09 — lossless shared preparation/access metadata**

CG-02's one-time authorization, budget and trigger are closed. The next
capability-first package is responsibility-structure explanation, selected from
`DEVELOPMENT_PLAN.md` section 8 and bounded by
[the CG-03 contract](docs/HCL_CG03_CAPABILITY_CONTRACT.md). CG03-A–D provide a
typed operation, five source/time/access factor checks, conditional evaluation
under caller premises and a conservative exact-line prose path. Claims remain
claims; third-party attribution, later knowledge, contested evidence and
unmet conditions cannot silently become intention, responsibility or moral
truth. [Implementation limits](docs/HCL_CG03_IMPLEMENTATION.md) are explicit.
**CG03-CERT passed:** exact PR head `086fdbd819174505eb862e466177a5b90669b358`
([run 36421176120](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36421176120))
and merged main `2aeda0188eb64728735e3cd6c0b049f9ed329e6e`
([run 36421279622](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36421279622))
each passed 111 v1 + 176 historical tests with the same runtime digest, zero
provider calls/spend and LongMemEval sealed. [Certification receipt](reports/HCL_CG03_PROVIDER_FREE_CERTIFICATION.json).

**CG03-E — RETAIN / CLOSED, DEVELOPMENT EVIDENCE ONLY.** Owner authorized the
frozen package on `main@1c784d87c104e5a0056eddfa92bd7862133c59bc` once. [Run
36427668859](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36427668859)
executed 20 DeepSeek calls with zero retries. Every preflight passed again and
all inputs matched package SHA-256
`e76c0fa13bc9c9f4f9c1de9f5986791621e3cd6e9bbdcf0f7d018463d00876e8`.
[Full raw receipt](reports/HCL_CG03_EXTERNAL_RUN_36427668859.json) records
22,464 input / 1,857 output tokens, actual model IDs, raw requests/responses,
scorer results and H/H-new treatment receipts. Conservative rated cost:
**USD 0.03700620** under USD 0.30; usage/time/cache-based estimate:
USD 0.01768646, not a verified invoice. Artifact ID 10972111450; ZIP SHA-256
`cf7601f702564dca780e9ad4c679cb9b0b8cbdddd3174d5d4340ef6f3816faaf`.

[Source-first closure](reports/HCL_CG03_EXTERNAL_DEVELOPMENT_CLOSURE.md) selects
**RETAIN** for the explicit optional checker: H 28/28 versus P 21/28, G 20/28,
H-new 23/28, with substantive time/attribution/premise safeguards and ablation
support. H costs 4.34x P; this does not meet the eventual typical-cost maturity
target or justify default activation. Four HCL-authored synthetic cases provide
**development evidence only**, never independent/fresh external efficacy or
broad moral cognition. The grant is closed at zero, trigger removed and automatic
paid triggering disabled; no rerun or budget transfer is authorized.

The next capability from section 8 is **CG-04 contextual value conflict and
preference**, with [bounded contract](docs/HCL_CG04_CAPABILITY_CONTRACT.md).
Execute A → B → C → D → CERT → E provider-free: actor/role/context-bound
preferences, explicit conditions, scope-local revisions and unresolved conflict;
no global fixed weights or inferred lasting values from observed choices.

Leaderboard selection remains deferred until the maturity gate in
`DEVELOPMENT_PLAN.md` is met. Historical CG-01 provider charge remains bounded
by **USD 0.05900004** on conservative published peak all-cache-miss rates; no new
CG-02 provider spend is authorized. LongMemEval remains fully sealed/deprioritized.

**CG04-A–D / CERT — provider-free certified.** [PR #135](https://github.com/haohongfei2001-png/human-cognition-layer/pull/135)
exact head `ca6f36434275b97b9ed15aaba3f1423f33ed8aa2`
([run 36430264670](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36430264670))
and main `88b5cfbefaae51793998a9e2685e11f30a22a241`
([run 36430479680](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36430479680))
both passed 142 v1 + 176 historical = **318 tests** with runtime digest
`b700aaef4a27d6beda7b4abd79b6801d29947583adaa1dc00ca45b3f50ccd006`,
zero provider calls/spend and LongMemEval sealed. All six head/main workflow
groups passed. [Certification receipt](reports/HCL_CG04_PROVIDER_FREE_CERTIFICATION.json).

The operation checks complete-line source/actor/authority, role/context-bound
conditions, attribution, explicit same-condition-domain local revisions and
unresolved pair/cycle conflict. A bounded ordinary-text path records actual
preparation/state/final messages without extraction calls. Source claims do not
prove lasting values, sincerity or moral truth; choices do not create preferences.
[Implementation limits](docs/HCL_CG04_IMPLEMENTATION.md) remain explicit.

**CG04-E — frozen provider-free proposal.** [Protocol](docs/HCL_CG04_EXTERNAL_DEVELOPMENT_PROTOCOL.md)
and [package](reports/HCL_CG04_EXTERNAL_PACKAGE.json) fix four public
HCL-authored synthetic development cases with identical task/output vocabulary
across C/P/G/H/H-new. All four treatment-presence preflights pass, and final
H/H-new inputs differ solely by the executed checked state. The frozen package
SHA-256 is `0ffcfdfae3d9d5130c96205f2247991d1d88a872edbb144b701ad01da3202ce9`.
Existing DeepSeek infrastructure is reused; no API/account/credential/plan is added.
The new proposal is 20 calls maximum, zero retries, thinking disabled, 512 output
tokens, provider default tier, conservative reservation **USD 0.29543184** and
proposed **USD 0.30 hard cap**. The workflow grant is **0**, with no trigger;
no CG-04 paid run is authorized. Historical unused budgets do not transfer.
Implementation, certification and freeze are complete; only a separately
owner-authorized paid comparison remains. Any result is development evidence only.


## Authorized unattended night — 2026-09-28

**NO-BLOCKING-OWNER-GATE**: new spending stays unauthorized. A completed
provider-free capability whose only remaining step is paid validation is frozen
as **READY / DEFERRED_OWNER_AUTHORIZATION**; continue independent implementation.
One active writer, one coherent PR; exact-head CI → merge → exact-main CI.

CG-04 remains **IMPLEMENTED_UNVALIDATED / READY / DEFERRED_OWNER_AUTHORIZATION**.
No independent CG-04 grant exists. Package bytes/hash, sources, gold, prompts,
scorer, arms and treatment remain unchanged at
`0ffcfdfae3d9d5130c96205f2247991d1d88a872edbb144b701ad01da3202ce9`.
Frozen replay uses certified `main@018afbc93c645975d7f6f1077c8c8380635d9f2f`;
current-runtime regression separately requires every frozen case's actual input
and checked treatment to remain identical. Latest runtime is not silently
substituted into a future paid run. Proposal: 20 calls/0 retries/USD 0.30,
reservation USD 0.29543184; grant 0, trigger absent, calls/spend 0.

**CG05-A–D — IMPLEMENTED_UNVALIDATED**. CAPABILITY_DELTA: distinguish local
social-concept meanings by speaker/context, check source properties and explicit
counterexamples, retain multiple readings and scope-local revision. Ordinary
text reaches actual final cognition state without hand-entered mental state or
provider extraction. [Contract/brief](docs/HCL_CG05_CAPABILITY_CONTRACT.md).
Certification and fair five-arm freeze are complete; paid validation is deferred. These
are the only two active unvalidated candidates. Afterwards the unique next
implementation task is retained-capability integration and context/cost
reduction, not a third module. CG-02 remains closed INCONCLUSIVE and CG-03 remains
development-only RETAIN. New provider calls/spend tonight: **0 / USD 0**.
LongMemEval: **SEALED_NOT_ACCESSED**. No owner input is needed for this work.


**CG05-CERT — PASS / E — READY / DEFERRED_OWNER_AUTHORIZATION.**
PR #137 exact-head run [36435067793](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36435067793)
and exact-main c7593bc run [36435439212](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36435439212)
both passed 347 tests with runtime digest
`4760aeb40ed6103c78efb844ee491c32451333158d5bd9bb532c3e8708fd473a`.
All six workflow groups passed at both SHAs. E freezes four synthetic cases and
fair five-arm actual messages; every treatment-presence gate passes.
Package SHA-256 `9ade82883d7dd954b3b092af7b4501b679ca950bf0ca432f108bd35a29400dc7`; proposal
20 calls/0 retries/USD 0.30; conservative reservation USD 0.29537640.
[Protocol](docs/HCL_CG05_EXTERNAL_DEVELOPMENT_PROTOCOL.md). Frozen runtime replay
uses certified c7593bc and frozen builder hashes. No grant or trigger exists.

Two pending candidates: CG-04 and CG-05, both IMPLEMENTED_UNVALIDATED. Do not open
CG-06. **Unique next implementation task:** lossless context compaction so more
source-grounded cognition fits a bounded final-answer context, preserving all
actor/time/access/uncertainty and premise distinctions. Default/frozen inputs
stay unchanged; compact output is explicit and round-trip auditable. Then
cross-capability composition/semantic preparation. No owner input needed.
Night provider calls/spend remain 0 / USD 0; LongMemEval remains sealed.


**CG05-E freeze merged / exact-main PASS.** PR #138 head
4eabf2656d1ee52ece5d793de183eaac7aeb47f7 (run 36436266252) and main
5a7b2ddf84bfa2fe0b91076f78dfb3e67e966cb0 (run 36436527346) each passed
175 v1 + 176 historical = 351 tests; all six workflow groups passed.
[Freeze receipt](reports/HCL_CG05_FREEZE_CERTIFICATION.json).

**NIGHT-INTEGRATION-01 — implemented; certification in progress.**
CAPABILITY_DELTA: source-grounded checked cognition can fit a context budget
that previously refused it. Explicit lossless source/case references and shared
provenance columns preserve every factor, premise and uncertainty; hidden or
redacted references cannot be resurrected. Twelve CG03/04/05 inputs round-trip
exactly and complete input bytes fall 8.33%, including codec policy. No token,
billed-cost or model-utility claim. Defaults and every frozen input stay equal.
[Implementation](docs/HCL_V1_CONTEXT_COMPACT.md).
CG02 registry metadata now says INCONCLUSIVE_CLOSED, matching its existing
closure; it is not counted as a pending new candidate. New calls/spend: 0/USD0.
After exact-head/main CI the unique next implementation is source-projected
cross-capability composition, not a third module. No owner decision required.


**NIGHT-INTEGRATION-01 — exact-head/main CERT PASS.** PR #139 head c443051,
run 36437324076; main 4725466e719320e88c97b3286e89ede22475dc79,
run 36437814406. Both passed 183 v1 +176 historical =359 tests and all six CI
groups. [Receipt](reports/HCL_NIGHT_CONTEXT_CERTIFICATION.json).

**NIGHT-INTEGRATION-02 — implemented; CERT in progress.** CAPABILITY_DELTA:
one ordinary source now reaches one final answer with actual scoped preference,
concept and conditional responsibility checks together, preserving each operation's
uncertainty and refusing cross-operation promotion. One adapter answer, zero
extraction; ten composition tests, including private typed views and local revision.
A source grammar collision exposed a real preparation defect: context conditions
were parsed as concept usage and concept revisions as malformed preferences.
Generic domain separation is repaired; every frozen default input/treatment
remains identical. [Implementation](docs/HCL_V1_COMPOSITION.md).
After exact-head/main CI, the unique next implementation is bounded, explicitly
source-grounded semantic preparation/access integration for existing operations,
without inferred private state or a third unvalidated module. Provider calls/spend
remain 0/USD0, LongMemEval sealed, no owner-only development blocker.


**NIGHT-INTEGRATION-02 — exact-head/main CERT PASS.** PR #140 final head
f2754c8 (run 36438705568), main 27695beeeba7fda9d55eacea54d4e2ad139a58e8
(run 36438969596): 193 v1 +176 historical =369 PASS, same runtime digest,
all six workflow groups passed. [Receipt](reports/HCL_NIGHT_COMPOSITION_CERTIFICATION.json).

**NIGHT-INTEGRATION-03 — implemented; CERT in progress.** CAPABILITY_DELTA:
ordinary source with exact narrated delivery clauses can now support character/
observer preference and concept composition without caller-entered access state.
Reported exposure remains distinct from belief/understanding/world truth. Missing
or ambiguous access stays unknown; later receipts cannot enter earlier event or
record views. Source anchors and public/receiver promotion are checked. Twelve
new boundary/ordinary-composition tests; default frozen cases remain identical.
[Implementation](docs/HCL_V1_NARRATIVE_ACCESS.md). CG01 registry now records its
existing SIMPLIFY_CLOSED, retaining optional typed checker efficacy as inconclusive;
CG02 INCONCLUSIVE_CLOSED and CG03 development-only RETAIN are unchanged.

After exact-head/main CI the unique next implementation is lossless pooling of
repeated source records in composed final input, preserving operation access links
and complete cognition under a tighter budget. No third candidate, new paid run,
credential, source hunt or owner-only blocker. Night calls/spend: 0/USD0; sealed
LongMemEval not accessed. Night remains ongoing.


**NIGHT-INTEGRATION-03 — exact-head/main CERT PASS.** PR #141 head d9a1412,
run 36439907605; main 73eca3f0183b2ec9c3055896fc3d3bb875fb6dea,
run 36440392096. Both 205 v1 +176 historical =381 PASS, same runtime digest;
all six workflow groups passed. [Receipt](reports/HCL_NIGHT_ACCESS_CERTIFICATION.json).

**NIGHT-INTEGRATION-04 — implemented; CERT in progress.** CAPABILITY_DELTA:
the complete three-operation cognition context fits a tighter budget through
lossless source storage pooling. Per-operation source IDs, actor/event/record
scope and access links stay unchanged. Seven new useful/private/time/tamper/
budget tests; complete integrated input bytes shrink 4.91% including policy,
with no billed-token or model-efficacy claim. [Implementation](docs/HCL_V1_COMPOSED_SOURCE_POOL.md).
Default frozen CG04/05 inputs and engineering hashes remain identical.

After exact-head/main CI, preserve deferred-package reproducibility across current
main and frozen-runtime checkouts, then continue source-validated preparation and
composition of retained v0.6 belief/perspective. This is the unique next existing-
capability integration path; no third candidate or new paid validation. Night
provider calls/spend remain 0/USD0, LongMemEval sealed, no owner-only blocker.


**NIGHT-INTEGRATION-04 — exact-head/main CERT PASS.** PR #142 head d0922bb,
run36440860812; main1482c876924bad226d37c5f901241ee743c5c345,
run36441173090. Both212 v1 +176 historical =388 PASS, matching runtime digest;
all six groups PASS. [Receipt](reports/HCL_NIGHT_SOURCE_POOL_CERTIFICATION.json).

**NIGHT-FREEZE-COMPATIBILITY — dormant execution repair.** CG04 control/main
and actual frozen execution checkouts are explicitly separated; a future grant
must bind exact certified runtime018afbc/package0ffcfdf and no migration occurs.
All source/gold/prompts/scorer/arms/treatment/helpers are unchanged. Original
preflight executes at the frozen checkout. Grant0/baseUNAUTHORIZED/no trigger,
no dispatch/call. Executed guard tests reject default budget, latest-runtime
replacement, retry and missing unique trigger. This preserves reproducibility,
not a new capability delta or outcome. Immediately next implementation is source-
validated ordinary belief preparation/composition using RETAIN v0.6, without
exposure-to-belief or reported-belief-to-knowledge/world truth promotion.
Night remains ongoing, two pending candidates only, calls/spend0/USD0,
LongMemEval sealed, no owner-only development blocker.


**NIGHT-INTEGRATION-05 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: ordinary source self-report/denial/uncertainty/attribution and
local revision now enter RETAIN v0.6, alongside existing concept/preference state
in one actual final answer input. Exposure is not acceptance, indirect attribution
is not private belief, source belief is not knowledge/world/moral truth. Revision
anchors obey actor/context/access/event/record scope; absent anchors do not create
old state. No third capability candidate or paid package is added.
Twelve new tests + existing regressions pass locally:226 v1; CI runs176 historical
checks too. Prior PR143 exact-main1aab093238900a0ffc4f25bd62db1e6b1fa1a9be,
run36442402242 records390 PASS; both applicable workflow groups PASS.
CG04/05 package bytes remain frozen/deferred. Provider calls/spend tonight0/USD0;
LongMemEval SEALED. Immediately after exact-head/main CI, implement a small
source-scoped composition comparison between expressed belief and local concept
criteria, preserving disagreement/uncertainty without inferring shared meaning,
private intention, correctness of the belief or moral truth. This is the unique
next existing-capability integration task; no third candidate or owner paid gate.


**NIGHT-INTEGRATION-05 — exact-head/main CERT PASS.** PR144 head47f0006,
run36443534792; maina6df973cac86041644de8aaf0a2adcfc40c1adfa,
run36443654867. Both226 v1 +176 historical =402 PASS, same runtime digest;
all six groups PASS. [Receipt](reports/HCL_NIGHT_BELIEF_CERTIFICATION.json).

**NIGHT-INTEGRATION-06 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: explain a same-actor/context/item/term expressed belief's
consistency, difference or unresolved relationship with local source criteria,
with both evidence bases. No belief-to-truth, definition-to-shared-meaning or
moral/private-intention promotion. Later properties/definitions or indirect
reports cannot move the original self-report's time. Eleven new tests, including
actual final messages, private hidden properties and backdated records.
CG04/05 remain the only implemented-unvalidated candidates, READY/deferred;
provider calls/spend tonight0/USD0, LongMemEval SEALED.
After exact-head/main CI, the unique next implementation is a bounded ordinary-
question entrypoint that selects existing belief/concept preparation and composed
comparison from explicit actor/context/item/term question semantics, without
caller-entered mental state, extra extraction or an added candidate. Ambiguous
questions must refuse structured analysis and preserve authorized reader source.


**NIGHT-INTEGRATION-06 — exact-head/main CERT PASS.** PR145 headbbe49e7,
run36444353205; mainb29bb01a1c64c06352032bc3480c0ddb6f99e3b8,
run36444505097. Both237 v1 +176 historical =413 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_COMPARISON_CERTIFICATION.json).

**NIGHT-INTEGRATION-07 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: ordinary explicit person/context questions select retained
belief and existing local-concept preparation/comparison, without caller-entered
correct mental state or operation flags. Source alone supplies belief/meaning;
unsupported questions refuse structured analysis, preserve authorized reader
source only, and never transfer it into a private fallback. Bounded English/
Chinese task grammar, request-local state, one final answer/zero extraction calls.
Twelve new tests; all frozen default inputs unchanged. CG04/05 are the only two
IMPLEMENTED_UNVALIDATED deferred candidates, calls/spend tonight0/USD0,
LongMemEval SEALED. After exact-head/main CI the unique next implementation is
source-order snapshot support for these ordinary questions, preserving what was
supported before later belief/meaning revisions or later exposure. Explicit
statement order is not a calendar-time or real receipt claim. No third candidate,
new provider call, benchmark/source hunt or owner gate.


**NIGHT-INTEGRATION-07 — exact-head/main CERT PASS.** PR146 final head9c55a57,
run36445515626; mainea68db6a9082dbb2cd1ca1be902565c4a27a21da,
run36445717940. Both249 v1 +176 historical =425 PASS, matching runtime digest;
all six groups PASS. [Receipt](reports/HCL_NIGHT_QUESTION_CERTIFICATION.json).

**NIGHT-INTEGRATION-08 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: explicit ordinary earlier questions prepare only authorized
source prefixes, preserving earlier belief/meaning/access before later revision
or exposure. Future malformed semantic lines cannot poison the valid earlier
scope. Selected/original source hashes are audited, future-source digest absent
from final input. Statement order is not calendar or verified receipt time.
Invalid/nested/conflicting scopes reject whole-reader fallback; state+scope budget
is checked. Ten new meaningful tests; default frozen inputs stay identical.
CG04/05 remain the two deferred implemented-unvalidated candidates. Calls/spend
night0/USD0, LongMemEval SEALED. After exact-head/main CI, unique next work is
lossless reduction of repeated shared policy/preparation metadata in composed
final input, preserving every actor/source/time/access/uncertainty decision and
all actual-state decoder checks. No third candidate or paid authorization gate.


**NIGHT-INTEGRATION-08 — exact-head/main CERT PASS.** PR147 head0ba6f64,
run36446430437; mainba0f4803b6e8d0d6c5a242d459748f5c8992c6b4,
run36446683994. Both259 v1 +176 historical =435 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_SOURCE_ORDER_CERTIFICATION.json).

**NIGHT-INTEGRATION-09 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: complete checked operation states fit a tighter total context
budget through lossless per-stage preparation defaults and one shared access
policy. Every source/actor/time/access/failure/uncertainty decision survives exact
decoding; nonzero/missing/different-typed counts stay literal. Oldv1 decoder format
remains accepted, invalid defaults fail closed. Seven new tests; full current
suite266 v1, CI adds176 historical. Four-input complete-byte audit is committed;
no token/cost/model utility extrapolation. Default frozen inputs stay unchanged.
After exact-head/main CI, unique next implementation is ordinary explicit belief/
conditional-responsibility composition with caller-scoped normative premises,
using only retained v0.6 and development-only RETAIN CG03. Keep knowledge,
foreseeability, control, intention and the caller premise separate from belief or
outcome. Reuse existing checker/ordinary preparation, no third candidate, moral
ontology or new paid run. CG04/05 stay deferred/unvalidated, calls/spend0/USD0,
LongMemEval SEALED; no owner blocking gate.


## Authorized continuous integration queue — NI-10 through NI-14

Owner-authorized continuation is registered in
[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md), section 15. After NIGHT-INTEGRATION-09
exact-head/main certification, the unique provider-free queue is:

`NI-10 belief + conditional responsibility`
→ `NI-11 multi-source local revision`
→ `NI-12 perspective contrast`
→ `NI-13 bounded multi-event narrative integration`
→ `NI-14 ordinary-question robustness + integrated closure`.

This queue does not authorize a third capability candidate, paid/provider
execution, new credential/account/permission, benchmark or leaderboard search,
LongMemEval access, or alteration of frozen/consumed evidence. CG04/CG05 remain
implemented-unvalidated and deferred. Ordinary engineering failures are not owner
gates; repair them and continue. External-only gates are recorded and bypassed
for dependency-safe provider-free work. Do not create filler work merely to fill
time; stop only when this queue is complete or all remaining work is genuinely
owner/external/prohibited.


**NIGHT-INTEGRATION-09 — exact-head/main CERT PASS.** PR148 head8382dd1,
run36447628980; main90e98075123969df59e523da72a6f619cd08e374,
run36447975654. Both266 v1 +176 historical =442 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_SHARED_PREPARATION_CERTIFICATION.json).

**NIGHT-INTEGRATION-10 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: ordinary explicit questions compose RETAIN v0.6 expressed belief
and development-only RETAIN CG03 conditional responsibility, from ordinary source
and explicit caller normative requirements. Fix incidental planned/control/etc
belief/meaning/property words becoming responsibility factors or action/outcome.
Explicit negative control stays separate from unknown knowledge/foreseeability/
intention. Caller FOCAL_EPISODE scope binds action/outcome plus required factor
sources; all relevant privacy/time guards remain. Thirteen new tests and actual
private-view messages committed. All four consumed CG03 default cases unchanged;
CG04/05 frozen inputs/helpers unchanged. Calls/spend tonight0/USD0, LongMemEval
SEALED, no third candidate or historical efficacy upgrade.
After exact-head/main CI, continue NIGHT-INTEGRATION-11: multi-source local
revision composition under section15, with explicit source authority/identity/order,
source-bounded before/after state and complete provenance. No third candidate or
new paid call; ordinary source-grounding repairs stay within this integration line.


**NIGHT-INTEGRATION-10 — exact-head/main CERT PASS.** PR150 headeb66f990,
run36451333022; main1f5a9273e14ad0240c794c4fe55f1fa413569ab3,
run36451451272. Both279 v1 +176 historical =455 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_BELIEF_RESPONSIBILITY_CERTIFICATION.json).

**NIGHT-INTEGRATION-11 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: one ordinary question over2–4 explicitly authorized source
records preserves before/after belief, local meaning, access and conditional
responsibility. Explicit source paths never become calendar/verified receipt
claims; later content/exposure never backfills an earlier snapshot. Incomparable
branches have no merged winner; unrevised opposite source assertions remain
unresolved. Every visible operation/event keeps exact record/statement bindings
through existing lossless encoding. Invalid/missing authority/order and total
budget overflow refuse complete-library fallback. Ten new meaningful tests,
actual compact/private/conflict inputs;289 v1 locally PASS. No third candidate,
new paid call or evidence upgrade; CG04/05 unchanged/deferred, night0/USD0,
LongMemEval SEALED. After exact-head/main CI, immediately NI-12: explicit two-
participant perspective contrast under DEVELOPMENT_PLAN section15.


**NIGHT-INTEGRATION-11 — exact-head/main CERT PASS.** PR151 head3a50a158,
run36452293275; main5e58b99025604ee0fffaaf7553cee055259ab4b5,
run36452455568. Both289 v1 +176 historical =465 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_SOURCE_REVISION_CERTIFICATION.json).

**NIGHT-INTEGRATION-12 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: ordinary English/Chinese questions compare two independently
source-projected participant views of one claim. Public declarations/nonpublic
exposure, direct self-report, indirect/narrator attribution, character uncertainty
and missing system evidence stay separate. Shared source availability never
creates shared acceptance; observer views exclude unauthorized private reader
material. Exact statement/event/record scopes and whole-budget refusal preserve
both views together. Ten new tests and actual final-input receipts;299 v1 locally
PASS. CG04/05 remain the two deferred candidates; no new paid call/ontology or
historical evidence upgrade, night0/USD0, LongMemEval SEALED. After exact-head/main
CI, immediately NI-13 bounded multi-event narrative integration using a minimum
question-justified set of existing operations, under section15.


**NIGHT-INTEGRATION-12 — exact-head/main CERT PASS.** PR152 head7e3f8fdd,
run36453086517; maindca3d064f564db9653675cd4e2a1e680895a5b45,
run36453234208. Both299 v1 +176 historical =475 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_PERSPECTIVE_CONTRAST_CERTIFICATION.json).

**NIGHT-INTEGRATION-13 — IMPLEMENTED; correctness certification pending.**
CAPABILITY_DELTA: an ordinary compound question over a short explicitly event-
sectioned narrative follows real local belief/meaning/role-preference revisions,
with before/after checked state and exact event/source bindings. Select only the
requested2–3 existing operations; absence remains unresolved, choice never supplies
preference/intention. Earlier event selection excludes future malformed semantic
content/revision/access. Event order is not calendar/verified receipt; private
projection and whole-budget refusal remain enforced. Ten new tests, actual
current/early/minimum-operation inputs;309 v1 locally PASS. No new cognitive
candidate, paid call or history upgrade; CG04/05 still deferred, night0/USD0,
LongMemEval SEALED. After exact-head/main CI, immediately NI-14 ordinary bilingual
question robustness and source-grounding repairs, then integrated closure under
section15. No owner blocking gate.


**NIGHT-INTEGRATION-13 — exact-head/main CERT PASS.** PR153 headdafb4d23,
run36453917674; mainf7acf1e9386f19d357b407bcec216af6e8901292,
run36454160591. Both309 v1 +176 historical =485 PASS, matching runtime digest;
both applicable groups PASS. [Receipt](reports/HCL_NIGHT_NARRATIVE_EVENTS_CERTIFICATION.json).

**NIGHT-INTEGRATION-14 — IMPLEMENTATION COMPLETE / INTEGRATED PROVIDER-FREE CLOSURE.**
CAPABILITY_DELTA: one ordinary bilingual entrypoint prepares existing single/
combined person cognition, authorized source revisions, two participant views and
multi-event state without internal operation selection or caller mental-state
gold. Fix reproduced Chinese routing and nested-decoder failures. CG03 full-source
subject/predicate/polarity guards prevent wrong-person/quote/hypothesis promotion;
explicit FOCAL_EPISODE literal references prevent unrelated object/outcome factors
or opposite actions supporting the focal episode. Missing links/polarity remain
unknown, no world/ontology bridge. Positive/negative direct and explicit indirect
claims stay distinct; historical default cases remain identical.

Eighteen new meaningful tests;327 v1 +176 frozen historical =503 local PASS;
five actual local adapter/input probes cover the full NI10–14 line. Delivery is
accepted only with this runtime's exact PR-head/main CI PASS artifacts; the final
canonical GitHub handoff records the actual SHAs, run IDs and artifact digest.
[Integrated closure](reports/HCL_NIGHT_INTEGRATED_CLOSURE.json),
[source-first closure](reports/HCL_NIGHT_CAPABILITY_CLOSURE.md).

Only CG04/CG05 remain implemented-unvalidated, both frozen/deferred. CG01 SIMPLIFY,
CG02 INCONCLUSIVE/CLOSED, CG03 development-only RETAIN, v0.6 bounded historical
RETAIN; no independent/fresh or broad capability upgrade. Calls/spend during this
night0/USD0; no grant, trigger, credential/account/plan/budget transfer; LongMemEval
SEALED. All section15 implementation and reproduced integration failures are
closed subject to exact CI, not a claim every conceivable future integration is
finished. Unique next implementation task: **NONE_QUEUED_PROVIDER_FREE_AFTER_NI14
EXACT_MAIN_CI**. Do not create filler or a third unvalidated large candidate.
Future work needs a concrete dependency-safe task recorded in the canonical plan;
new paid validation remains deferred without blocking already-available work.
No owner-only decision is required for this delivery. The night closure condition
is two pending candidates plus completion of all currently queued/identified
provider-free integration/correctness work, not waiting for paid authorization.

## Current serial authorization (supersedes prior deferred execution only)

Owner baseline main 1185b981 authorizes CG04 once, then CG05 once only after CG04 closure, zero grant, removed trigger and exact-main CI. Sources, gold, prompts, scorer, arms, treatment and budgets remain frozen. CG04 runs certified 018afbc; CG05 will run certified c7593bc. Each has an independent USD 0.30/20-call/0-retry/512-token cap. Both retain synthetic development-only evidence scope. Freeze metadata stays immutable; separate control grants carry authorization. Post-CG05 gap review precedes any new capability; no automatic CG06. LongMemEval SEALED.

## CG04 source-first paid closure / current serial task

Run36463463452, frozen runtime018afbc and package0ffcfdfa, 20 calls/0 retries, C26/P23/G25/H28/H-new26 of28. RETAIN_DEVELOPMENT_ONLY, bounded optional applicability/unknown-condition protection; no independent or fresh evidence. Raw requests/responses, usage, final inputs, treatment preflight and artifact hashes preserved. Conservative USD0.03948384, published-rate estimate USD0.016720352, invoice unavailable. Grant0, trigger deleted, unused money extinguished. Only CG05 remains implemented-unvalidated. Immediately after this closure exact-main CI, activate and execute CG05 once with its independent USD0.30 authorization and certified c7593bc runtime. No new samples/reruns; LongMemEval SEALED.

CG04 closure PR157 merged bc51049, all six exact-main groups PASS, 329 v1+176 historical. CG04 workflow disabled, grant0 and trigger absent. CG05 now has its separate single-run grant and hash-pinned transport adapter; full cognition runtime remains certified c7593bc, frozen builders/scorer/messages unchanged. [CG04 closure certification](reports/HCL_CG04_CLOSURE_CERTIFICATION.json). After exact-main CG05 activation CI, create one unique trigger; source-first closure follows immediately.

## CG05 source-first paid closure / current task

Run36464819798, frozen runtimec7593bc/package9ade8288 and pinned adapter8a539144, 20 calls/0 retries, C21/P23/G21/H28/H-new23 of28. RETAIN_DEVELOPMENT_ONLY, bounded local criteria/uncertainty/counterexample protection; no independent/fresh evidence. Full raw requests/responses/usage/scorer/treatment and artifact hashes preserved. Conservative USD0.04263072, published-rate estimate USD0.018375456, invoice unavailable. Grant0, trigger deleted, workflow disabled, unused money extinguished. Zero pending candidate slots. Total newly authorized calls40, rated USD0.08211456, estimates USD0.035095808, budgets independent and now closed. LongMemEval SEALED. After exact-main closure CI, perform POST-CG05 CAPABILITY GAP REVIEW before creating any new contract/module; no automatic CG06 or leaderboard.

## POST-CG05 canonical handoff / current next task

CG05 closure PR159 merged b31d8c29f64e5a2b1d62462de0ff58729b743ac9; all six exact-head/main groups PASS, 332 v1+176 historical=508. CG04/CG05 both consumed and closed, workflow disabled/cap0, triggers absent. [CG05 certification](reports/HCL_CG05_CLOSURE_CERTIFICATION.json). [Short gap review](reports/HCL_POST_CG05_CAPABILITY_GAP_REVIEW.md) and [complete disposition/accounting inventory](reports/HCL_POST_CG05_CAPABILITY_DISPOSITIONS.json).

No evidence currently isolates an unmet new human-cognition mechanism from ordinary preparation/integration limits. Do not create CG06. Independent generalization of retained v0.6/CG03/CG04/CG05 is the next evidence step. Zero-provider unchanged-native-question replay of eight previously source-exposed, never provider-consumed DREAM families gives0/8 specialized treatments; all safely refuse unsupported query scope. This is not model scoring, evidence of a base-model failure, fresh selection or proof that all DREAM is unsuitable. No paid external package is qualified/armed. Raw corpus stays outside repository under its non-commercial research license. [Actual readiness receipt](reports/HCL_POST_CG05_NATIVE_READINESS.json).

**Unique next implementation task: EG01-A_SOURCE_FIRST_NATIVE_SEMANTIC_PREPARATION_AND_TREATMENT_QUALIFICATION_OF_RETAINED_CAPABILITIES.** Work on generic native-task/source actor/time/access preparation and an independent source-first family whose unchanged task actually uses retained capabilities; no gold/manual psychology, benchmark-specific rule or new ontology. New provider execution requires a separate later grant; none is requested/armed now. Existing paid packages are terminal consumed records, not pending proposals. Total this authorization40 calls/0 retries, rated USD0.08211456, rate estimate USD0.035095808, invoice unknown, no budget transfer. Candidate slots0. LongMemEval SEALED, leaderboard OFF, owner-only decision currently NONE.
