# HCL 单一正式执行计划索引

本文件是索引，不是另一套开发计划。技术语义以批准规格为准，阶段、验收、切片与状态以 manifest 为准，操作流程由 Codex 交接规定。

- [完整批准规格](docs/HCL_SYSTEM_REDESIGN_SPEC.md)
- [唯一阶段、验收与状态注册表](docs/hcl_design_manifest.json)
- [Codex 实施入口](docs/HCL_CODEX_HANDOFF.md)

固定依赖：**S1 → S2 → {S3 ∥ S4} → S5 → S6 → S7**。不得缩减 M01–M16、S1–S7、T01–T32；文学/哲学/伦理不是可选附件。

当前：**DESIGN_APPROVED / IMPLEMENTATION_NOT_AUTHORIZED**。本次仅文档专用 PR；未获进一步批准不修改认知运行时代码、不收费、不部署。PR 合并本身不启动研发。

获得后续实施批准后，唯一下一切片是 **S1-A**，详见 manifest.execution_slices 与交接 §11。S1/S2 必须交付真实可执行纵向路径而非无限基础设施；S3/S4 按 manifest.parallel_contract 并行，相关算法真实接入后才结案。

探索性机制必须在原定建设阶段完成算法研究、实现、正向推断、修订和下游消费；结构与接口测试不能代表认知功能完成。普通缺陷在现有条目内修复，不重复制订总体计划。

## 被替代的历史执行规则

[旧计划完整快照](https://github.com/haohongfei2001-png/human-cognition-layer/blob/58bfa17aed8da5773714309173438796b33491ec/DEVELOPMENT_PLAN.md)仅为原时点历史。其 NEXT_READY、A–H 完成标签、G-ARCH 和旧 I02/DRC 队列不再决定新开发顺序。原始结果、来源、运行时、CI 与已消费 grant 保持不变。
