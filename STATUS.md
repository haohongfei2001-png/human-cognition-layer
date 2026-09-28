# Canonical HCL Status

## Current phase

**HCL-CG-04 — Contextual Value Conflict and Preference (A–D implemented; CERT next)**

This file is the single live status. Historical statuses, gates, budgets and always-on policies are superseded; their complete record remains at [pre-v1 main c6b0eca](https://github.com/haohongfei2001-png/human-cognition-layer/blob/c6b0eca63295166ce4b2fb6984911b94ec90e349/STATUS.md). Current remote main and exact-SHA CI remain the code facts.

## Canonical policy

Capability growth is the development main line: **real human-cognition capability growth > external validation > leaderboard**. Base model first. Use the minimum evidence-grounded capability set only when needed. A simple prompt or generic exact tool is preferred when sufficient. Specialized mechanisms require incremental evidence. No automatic action-to-motive/emotion, narrator-to-character, exposure-to-revision, or computation-to-world-truth promotion. No new paid experiment is authorized; all historical budgets are closed. The canonical execution plan is [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).

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

**CG04-CERT — provider-free contextual-preference certification**

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

CG04-A–D are now implemented with an explicit v1 operation, complete-line source
validation, role/context-bound conditions, attributed reports, explicit local
revision, unresolved pair/cycle conflict and a bounded ordinary-text path.
[Implementation limits](docs/HCL_CG04_IMPLEMENTATION.md) and debug/ablation
boundaries are explicit. 23 targeted CG-04 checks and all 141 v1 tests pass
locally at zero provider calls; exact PR-head/main certification is pending.
No external utility claim or new paid authorization follows.
