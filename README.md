# Human Cognition Layer

HCL 为基础模型增加按需的人类认知支持，帮助理解人物信息、信念、视角和有来源的心理证据。**基础模型可以直接做好时，直接回答。** 简单提示足够时不调用复杂机制；精确计算采用通用工具；专门认知机制只保留得到增量证据支持的部分。

当前阶段：**HCL v1 Cognition Integration Foundation**。唯一实时状态：[STATUS.md](STATUS.md)。

- [可执行 capability registry](docs/HCL_V1_CAPABILITY_REGISTRY.md)：核心、可选结构、通用工具、停用研究资产。
- [Router / context / answer API](docs/HCL_V1_COGNITION_ROUTER.md)：确定性最小路由、有访问和时间边界的上下文、单次底座模型调用。
- `hcl/v1` 不导入 benchmark runner，不自动提取私人心理状态，不调度额外模型提取调用。

```python
from hcl.v1 import HCLCognitionLayer, CognitionRequest

# 可替换为调用者自行管理的真实模型接口；此例不调用 provider。
layer = HCLCognitionLayer(lambda messages: '可用证据不足。')
answer = layer.answer(CognitionRequest('Alice 知道什么？', target_actor='Alice'))
```

Perspective/belief 是目前最强的专门认知资产：历史 fresh C/P/G/D 为 11/19/22/30 of 32，D-only/G-only 8/0，但仅是一模型的小规模证据。Intention/affect 保留为可选、有来源的结构；因果、论证、形式验证和多解读证书是条件计算工具。未提供验证后的语义证据时，字段保持空值，不自动生成动机或情绪。详见 API 文档。

本轮只执行无需 provider 的集成与历史回归。所有旧预算关闭；已消费样本不重跑；LongMemEval 32 行继续 sealed/deprioritized。集成外部评估先审查来源，不自行启动付费实验。正确性测试通过不等于外部效用已经证明。

历史研究、实验结果和当时的 always-on 架构记录完整保留在 [pre-v1 README](https://github.com/haohongfei2001-png/human-cognition-layer/blob/c6b0eca63295166ce4b2fb6984911b94ec90e349/README.md)、[历史 STATUS](https://github.com/haohongfei2001-png/human-cognition-layer/blob/c6b0eca63295166ce4b2fb6984911b94ec90e349/STATUS.md) 与现有 `docs/`、`reports/`。它们不是当前 v1 激活政策。
