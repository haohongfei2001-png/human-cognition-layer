# Human Cognition Layer

HCL 为基础模型增加按需的人类认知支持，帮助理解人物信息、信念、视角和有来源的心理证据。**基础模型可以直接做好时，直接回答。** 简单提示足够时不调用复杂机制；精确计算采用通用工具；专门认知机制只保留得到增量证据支持的部分。

当前阶段：**HCL Capability Growth；CG-03 单次开发比较按 RETAIN 收口（仅 development evidence），CG-04 已冻结并 deferred；CG-05 也已实现、认证和冻结；夜间继续已有能力集成与上下文成本改善（provider-free）**。CG-02 的一次性开发比较已按 INCONCLUSIVE 结案；v1 integration foundation 已完成。唯一实时状态：[STATUS.md](STATUS.md)，长期执行计划见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。

- [可执行 capability registry](docs/HCL_V1_CAPABILITY_REGISTRY.md)：核心、可选结构、通用工具、停用研究资产。
- [Router / context / answer API](docs/HCL_V1_COGNITION_ROUTER.md)：确定性最小路由、有访问和时间边界的上下文、单次底座模型调用。
- [Capability Growth development plan](DEVELOPMENT_PLAN.md)：真实能力增长优先于外部验证；当前工作包为已有能力集成；CG-04/CG-05 两个候选的付费验证均 deferred。
- [CG-04 比较协议](docs/HCL_CG04_EXTERNAL_DEVELOPMENT_PROTOCOL.md)：四个合成开发案例、五臂、零重试、USD 0.30 未激活提案；旧预算不转移。
- [CG-04 实现及边界](docs/HCL_CG04_IMPLEMENTATION.md)：有条件的显式偏好、局部修订与未解决冲突；普通文本入口零提取调用。
- [CG-04 capability contract](docs/HCL_CG04_CAPABILITY_CONTRACT.md)：角色、情境、条件和局部偏好冲突；不建立全局价值权重。
- [CG-03 capability contract](docs/HCL_CG03_CAPABILITY_CONTRACT.md)：在显式规范前提下区分因果贡献、知识、可预见性、控制与意图。
- [CG-03 实现及边界](docs/HCL_CG03_IMPLEMENTATION.md)：来源、时间、访问与规范前提分离；保守文本入口。
- [CG-03 开发比较协议](docs/HCL_CG03_EXTERNAL_DEVELOPMENT_PROTOCOL.md)：四例五臂、公平输出格式、treatment-presence 和已消费的单次比较规则。
- [CG-03 source-first closure](reports/HCL_CG03_EXTERNAL_DEVELOPMENT_CLOSURE.md)：H 28/28、P 21/28、G 20/28、H-new 23/28；仅四个合成开发案例，授权和 trigger 已关闭。
- [CG-02 capability contract](docs/HCL_CG02_CAPABILITY_CONTRACT.md)：社会承诺、期待与误解的最小能力边界、阶段和 treatment-presence gate。
- CG-01 的一次性开发验证和结案见 [报告](reports/HCL_CG01_EXTERNAL_DEVELOPMENT_CLOSURE.md)。
- [集成评估来源审查与设计](docs/HCL_V1_INTEGRATED_EVALUATION_PROTOCOL.md)：保留为 external-validation backlog；不再阻塞新 capability implementation。
- `hcl/v1` 不导入 benchmark runner，不自动提取私人心理状态，不调度额外模型提取调用。

```python
from hcl.v1 import HCLCognitionLayer, CognitionRequest

# 可替换为调用者自行管理的真实模型接口；此例不调用 provider。
layer = HCLCognitionLayer(lambda messages: '可用证据不足。')
answer = layer.answer(CognitionRequest('Alice 知道什么？', target_actor='Alice'))
```

Perspective/belief 是目前最强的专门认知资产：历史 fresh C/P/G/D 为 11/19/22/30 of 32，D-only/G-only 8/0，但仅是一模型的小规模证据。Intention/affect 保留为可选、有来源的结构；因果、论证、形式验证和多解读证书是条件计算工具。未提供验证后的语义证据时，字段保持空值，不自动生成动机或情绪。详见 API 文档。

此前 v1 foundation 轮次的 42 项 v1 集成与 176 项历史回归共 **218 项测试通过**，合并后六组 CI 全绿；执行证据见 [closure](reports/HCL_V1_INTEGRATION_FINAL_CLOSURE.md)。该轮只执行无需 provider 的验证。所有旧预算关闭；已消费样本不重跑；LongMemEval 32 行继续 sealed/deprioritized。CG-01 的单次授权开发验证另见本页下方报告。正确性测试通过不等于外部效用已经证明。

历史研究、实验结果和当时的 always-on 架构记录完整保留在 [pre-v1 README](https://github.com/haohongfei2001-png/human-cognition-layer/blob/c6b0eca63295166ce4b2fb6984911b94ec90e349/README.md)、[历史 STATUS](https://github.com/haohongfei2001-png/human-cognition-layer/blob/c6b0eca63295166ce4b2fb6984911b94ec90e349/STATUS.md) 与现有 `docs/`、`reports/`。它们不是当前 v1 激活政策。


## Completed capability-growth package

**HCL-CG-01 — Perspective- and Choice-Constrained Character Explanation**

The implemented objective was to move beyond storing what a character knew or believed:
HCL should be able to check whether an explanation of a character's action depends
on knowledge, explicit goals or available choices that were actually supported at
the action time, and revise only the affected explanation when later evidence
changes those conditions.

Implementation order and stop rules are canonical in [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md).
Leaderboard work is deferred until the recorded maturity gate is met.

CG01-A/B/C now have a provider-free implementation: explicit reader/character/
observer modes, source- and time-scoped explanation conditions, local revision,
and an ordinary-text path with auditable final cognition context. See
[implementation and limits](docs/HCL_CG01_IMPLEMENTATION.md). The capability is
provider-free correct but has **no demonstrated external increment**. The
one-time [CG-01 external development package](docs/HCL_CG01_EXTERNAL_DEVELOPMENT_PROTOCOL.md)
ended in **SIMPLIFY** for ordinary-text use: all four semantic preparations
failed source-span validation, so H/H-new did not exercise the checker.
The [closure report](reports/HCL_CG01_EXTERNAL_DEVELOPMENT_CLOSURE.md)
preserves the distinction between failed end-to-end use and inconclusive
checker efficacy.


## Completed CG-02 development package

**HCL-CG-02 — Social Commitment, Expectation and Misunderstanding**

CG-02 aims to distinguish what a proposal/request/acceptance/conditional
commitment actually expressed from what different participants had evidence to
understand or expect. It reuses v0.6 perspective/access boundaries and must not
become a trust score, relationship graph, personality model or moral-blame
classifier.

The canonical scope and execution order are in
[docs/HCL_CG02_CAPABILITY_CONTRACT.md](docs/HCL_CG02_CAPABILITY_CONTRACT.md) and
[DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md). Its one-time DeepSeek comparison
passed treatment-presence preflight and is closed as **INCONCLUSIVE** after
[source-first review](reports/HCL_CG02_EXTERNAL_DEVELOPMENT_CLOSURE.md).

The source-grounded A-D runtime path is described in
[docs/HCL_CG02_IMPLEMENTATION.md](docs/HCL_CG02_IMPLEMENTATION.md). It checks
explicit conditions, source access and reported expectations; its ordinary-text
grammar is narrow and fails closed. The [frozen five-arm package](reports/HCL_CG02_EXTERNAL_PACKAGE.json)
and [full raw receipt](reports/HCL_CG02_EXTERNAL_RUN_36413088075.json) are
preserved. The next implementation package is
[CG-03 responsibility-structure explanation](docs/HCL_CG03_CAPABILITY_CONTRACT.md).

- [CG-05 capability contract](docs/HCL_CG05_CAPABILITY_CONTRACT.md)：按说话者和语境检查局部定义、适用条件、反例与修订；零新增付费调用。

- [无损 cognition context 压缩](docs/HCL_V1_CONTEXT_COMPACT.md)：保留完整来源与检查结果，在同一 context budget 下容纳更多已检查信息；默认冻结输入不变。

- [同一来源的 capability composition](docs/HCL_V1_COMPOSITION.md)：偏好、局部概念和条件责任检查一起进入一次最终回答，各自保留来源与不确定性。

- [显式叙事 access 准备](docs/HCL_V1_NARRATIVE_ACCESS.md)：从来源明确记录的接触句进入角色／观察者视角；接触不等于相信或理解。

- [组合来源池](docs/HCL_V1_COMPOSED_SOURCE_POOL.md)：来源投影后只压缩重复存储，保持每项操作的 access 链接；更紧预算下仍保留完整检查。

- [普通文本接入已 RETAIN 的 belief/perspective](docs/HCL_V1_BELIEF_PREPARATION.md)：区分明确自述、间接归因、角色不确定和信息接触，并与已有能力合成一次回答输入；未新增外部效用证据。

- [普通问题入口](docs/HCL_V1_PERSON_QUESTION.md)：明确的中英文问题选择已有 belief／词义准备与来源比较，不需手工输入正确心理状态；含糊任务保留为未决。
