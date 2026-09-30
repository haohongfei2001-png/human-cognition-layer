# HCL Assistant — Product Control Plane

这是 HCL Assistant 的 canonical 产品应用边界，不是研究运行时，也不是已上线产品。

**产品：Assistant → 按需 Explain → 高级 HCL Lab。所有生产回答由 HCL Interaction Controller 管理。**

## Work 从这里开始

1. 阅读 [STATUS](STATUS.md)、[DEVELOPMENT_PLAN](DEVELOPMENT_PLAN.md)、[AGENTS](AGENTS.md)。
2. 阅读 [Product Master Plan](HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md)。
3. 按 [稳定契约](contracts/PRODUCT_CONTRACTS_V1.md)、[工作包](docs/L0_L2_WORK_PACKAGES.md) 和 [验收矩阵](docs/ACCEPTANCE_MATRIX.md) 执行唯一 NEXT_READY。
4. 检查 remote main、产品目录变更和相关 PR。只在本产品边界工作，不运行研究工作流。

当前是 **L0 canonical / L1–L2 development-ready**；L1/L2 尚未实现。合入 main 且 exact-SHA planning 检查通过才视为 L0 setup 完成。产品基础设施、mock 和真实认知效力是不同状态。

## 仓库边界

目标独立仓库名：`haohongfei2001-png/hcl-assistant`。本轮未创建该仓库：当前 GitHub connector 没有建仓 action，备用终端额度暂停。没有复用其他不相关仓库。

当前 adopted 承载位置：`human-cognition-layer/products/hcl-assistant/`，使用独立产品控制面、无研究依赖的检查和可独立导出的目录。**这不是已完成物理分仓或 repository ACL 隔离。** L1–L2 只允许 synthetic/provider-free 开发；真实用户数据、provider 凭据、公开部署及 L3 接入在物理分仓前禁止。

研究根目录的 STATUS / DEVELOPMENT_PLAN / Master Plan 继续只控制研究线；本目录不 supersede 研究 I02–I06。隔离与迁移规则见 [边界决策](docs/BOUNDARY_AND_ISOLATION.md)。

## 初始结构

- `contracts/`：稳定产品契约与 capability manifest。
- `control/`：机器可读 live queue；不存用户数据。
- `docs/`：工作包、UX、验收、隔离与只读研究基线。
- `apps/`：未来 Web/API；L0 仅目录说明。
- `packages/`：未来 controller/context/store/adapter；L0 不实现运行时。
- `scripts/`、`tests/`：仅 provider-free planning/setup 验证。

检查（在本目录或导出的独立目录内）：

```sh
python3 scripts/check_planning.py
python3 -m unittest discover -s tests -v
```

Hosted CI：`HCL Assistant Planning`。它按 exact SHA 仅物化产品子树，不 checkout 研究正文；输出 exact SHA、产品内容 digest 和测试结果。不访问 provider 或继承研究凭据。检查通过不是 persistent cognition 已实现或 HCL efficacy 证明。
