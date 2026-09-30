# HCL Assistant Live Development Plan

Canonical product policy: [Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md). Live facts: [STATUS](STATUS.md). Package detail: [L0–L2](docs/L0_L2_WORK_PACKAGES.md). Machine mirror: `control/plan.json`.

**NEXT_READY: L1-01_EVENT_SOURCE_STATE_LEDGER**（L0 setup merge/exact-SHA check 是前置条件）。

## Live queue

| ID | 交付 | 依赖 | 当前状态 |
|---|---|---|---|
| L0-01 | canonical product contracts + execution setup | owner adopted direction | CANONICAL; merge/check required |
| L1-01 | event/source/state ledger | L0-01 | NEXT_READY |
| L1-02 | revision, dependency invalidation, historical state | L1-01 | WAITING_DEPENDENCY |
| L1-03 | privacy, expiry, scoped retrieval and counterevidence | L1-02 | WAITING_DEPENDENCY |
| L1-04 | always-on Controller, run/stream lifecycle, mock adapter | L1-03 | WAITING_DEPENDENCY |
| L2-01 | desktop chat, Topic, files, streaming controls | L1-04 | WAITING_DEPENDENCY |
| L2-02 | multi-session synthetic cognition + natural synthesis | L2-01 | WAITING_DEPENDENCY |
| L2-03 | Explain, correction and memory/privacy UX | L2-02 | WAITING_DEPENDENCY |
| L2-04 | Lab shell + integrated L2 acceptance/handoff | L2-03 | WAITING_DEPENDENCY |

九包是行为闭环，不是九个 PR 指标；可以合并相邻稳定切片，不按字段碎分 PR。

## Later gates

L3 REAL_RUNTIME_INTEGRATION：物理独立仓库 + I06 disposition + pinned permitted artifact/interface + explicit execution budget/access。未具备不得接真实 HCL。

L4 PRODUCT_MULTI_TURN_VALIDATION：独立于 I02–I06 confirmation 的新材料；覆盖中文、迟到信息、修订、Explain 忠实性、普通任务非干扰、memory 污染和完整费用。

L5 EVIDENCE_DRIVEN_OPTIMIZATION：保留实用路径，删除/简化无收益复杂度；不为排行榜修改产品机制。

## 执行规则

本轮 setup 只完成 L0，随后停止。后续产品 Work 在 L1/L2 依赖满足时自主推进实现、测试、修复、PR 与合并。修改 live queue 同时更新 STATUS 与 control/plan.json，不把每日状态写进 Master Plan。每次以实际 main、head CI、receipt 为准；不更新根目录研究控制面。
