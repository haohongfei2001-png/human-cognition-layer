# Canonical HCL Status

## Current phase

**HCL-CG-01 — Perspective- and Choice-Constrained Character Explanation**

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

The answer adapter performs one model call; default v1 schedules zero extraction calls. CG-01 may use one explicitly opted-in semantic-preparation adapter call, recording its input, output and cost separately. Optional typed context requires validated upstream semantic evidence; access metadata is not automatically mined from prose. The deterministic bilingual router has finite vocabulary; injected historical state is caller-managed. This is a working foundation, not external efficacy. The final handoff commit's exact SHA, counts and CI receipt are also emitted by the v1 workflow artifact for that commit, avoiding a self-referential static SHA in this file.

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

**CG01-C — IMPLEMENTED_UNVALIDATED.** A conservative ordinary English narrative path prepares finite candidates without caller-entered mental state and preserves actual source, perspective, candidate, condition and final-message content in debug receipts. The grammar is deliberately bounded; unrecognized cases fail closed. See [implementation limits](docs/HCL_CG01_IMPLEMENTATION.md).

**CG01-CERT — PROVIDER-FREE CERTIFIED.** PR #117 exact head `b0fbca3df69eec36d16a8a0616caca36d2f99dc0`, [run 36388937743](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36388937743); merged code tree on main `9c28284c4fe2935adbc5ddb6ade92ae9f063d014`, [run 36389075682](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36389075682). Both receipts record 59 v1 tests + 176 frozen historical regressions = **235 PASS**, provider calls/spend 0, and LongMemEval sealed. All six exact-main workflow groups passed. This certifies correctness, not external benefit.

**CG01-D — provider-free package frozen:** four source-audit-exposed cases from two public-domain story families, with C/P/G/H/H-new arms, exact source digest, scorer, masked audit rubric, 24-call maximum and USD 0.75 proposed hard cap. No paid call has been made. See [protocol](docs/HCL_CG01_EXTERNAL_DEVELOPMENT_PROTOCOL.md) and [package](reports/HCL_CG01_EXTERNAL_PACKAGE.json).

The bounded C/P/G/H/H-new external development package is frozen. Do not make paid calls without separate owner authorization.

All provider-free CG-01 implementation, regression, source/package, scorer, ablation and metering work is complete. The sole next step is the owner-authorized paid external development comparison. The frozen handoff is: two story families / four source-audit-exposed cases from Project Gutenberg eBook 10483 (source SHA256 `14eef73227e014591aff4bf6bc217e6d030fa6daaf429742c0f6501172f5bb8e`, catalog public domain in the USA); DeepSeek API `deepseek-v4-pro`, non-thinking JSON; C/P/G/H/H-new; 4 preparation + 20 answer calls maximum; 16,000 input and 2,000 output tokens per call; USD **0.75 hard cap** using peak all-cache-miss pricing; deterministic status/quote checks plus masked source-first semantic audit. The expected evidence value is to falsify unsupported explanation claims and test whether any H gain over P/G disappears in H-new. Four cases cannot establish broad efficacy. No paid call has yet been executed.

The current engineering milestone is:

**HCL_CG01_EXTERNAL_VALIDATION_AUTHORIZED_EXECUTION_PENDING**

Owner approval for this exact USD 0.75 package was received on 2026-09-28. The one-time cloud workflow and durable receipt are being prepared; no provider call has yet been made. Historical budgets do not transfer.

Leaderboard selection is explicitly deferred until the maturity gate in `DEVELOPMENT_PLAN.md` is met. Provider spend this round: **USD 0**. LongMemEval remains fully sealed/deprioritized.
