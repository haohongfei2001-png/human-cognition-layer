# HCL 当前状态

## 已批准设计

全系统整改v1.0及D1–D6推荐默认已被用户采纳。唯一规格、执行Manifest、Codex交接分别为 [docs/HCL_SYSTEM_REDESIGN_SPEC.md](docs/HCL_SYSTEM_REDESIGN_SPEC.md)、[docs/hcl_design_manifest.json](docs/hcl_design_manifest.json)、[docs/HCL_CODEX_HANDOFF.md](docs/HCL_CODEX_HANDOFF.md)。

## 当前实际状态

固化前main：`58bfa17aed8da5773714309173438796b33491ec`。认知源码树：`d3269730de701ec041cd4e5f256381d50263cf84`。

新方案：**DESIGNED / APPROVED_PLAN_NOT_STARTED**。本次只写文档；没有产生新的认知算法实现、真实模型功能或独立效果证据。下一实施起点是S1.1，等待owner后续Codex启动指令。

每阶段按DESIGNED、IMPLEMENTED_OFFLINE、INTEGRATED_OFFLINE、LIVE_FUNCTIONAL、EFFECT_CONFIRMED区别记录；离线检查不能升级为实模或effect。完整目标与全部M/S/T范围没有缩减。

## 历史证据边界

A–H有界建设、G-HC provider-free、G-ARCH局部架构/运行入口以及DRC、SID001、10月6–8日实验都按原版本、来源、执行、失败和费用范围保留；不能自动继承为新系统成熟。原状态全文见 [历史状态](docs/history/pre-redesign-20261012/STATUS.md)。历史原始报告、代码、模型输出、评分、runtime pins和closed grants没有修改。

#323–#325保持原状态，不在此次文档固化中合并/关闭，也不重启已消费实验。收费、部署和sealed访问授权均为零；本次设计批准不能复活旧授权。
