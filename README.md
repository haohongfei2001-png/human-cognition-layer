# Human Cognition Layer

HCL 为基础模型增加按需的人类认知支持，帮助理解人物信息、信念、视角和有来源的心理证据。**基础模型可以直接做好时，直接回答。** 简单提示足够时不调用复杂机制；精确计算采用通用工具；专门认知机制只保留得到增量证据支持的部分。

当前阶段：**HCL Long-Horizon Capability Growth — Wave D**。A01–A05 共享证据、普通语义入口、解释修订和保留能力垂直整合已通过正确性验证；B01 已实现有作用域的高阶信念归因；B02 已实现三人差异化交流/接触视图；B03 已区分人物修订与分析者纠正旧记录；B04 已实现转述来源归组与有界高阶查询；B05 已完成分人物局部更新与概念/责任检查整合，Wave B 正确性构建完成；C01 已实现目标/计划/机会的有来源联结；C02 已实现带前提与反证的竞争行动解释；C03 已区分人物信念下的计划支持与声明模型条件；C04 已实现目标相关评价与有来源的重新评价；C05 已把行动时信念/计划与条件解释联结，后来的信念和评价分开；D01 已区分条件承诺、接收、接受、撤回和履行报告；当前唯一 `NEXT_READY` 为 **D02 bounded mutual understanding and repair**。POST-CG05 review 和全部历史 evidence disposition 保持原分类；EG01-A 的通用 semantic/native-entry 工作吸收到 Wave A，independent qualification 与 serious efficacy validation 后移到 G-ARCH 之后。唯一实时状态见 [STATUS.md](STATUS.md)，完整长期架构与 41 包路线见 [HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md](HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md)，live 队列见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)。

- [普通人物问题与叙事入口](docs/HCL_V1_PERSON_QUESTION.md)：有来源、时间、访问与局部修订边界；单次回答，默认零提取调用。
- [夜间 source-first closure](reports/HCL_NIGHT_CAPABILITY_CLOSURE.md)：实际能力变化、证据限制、两个 deferred 冻结包。
- [可执行 capability registry](docs/HCL_V1_CAPABILITY_REGISTRY.md)：核心、可选结构、通用工具、停用研究资产。
- [Router / context / answer API](docs/HCL_V1_COGNITION_ROUTER.md)：确定性最小路由、有访问和时间边界的上下文、单次底座模型调用。
- [Long-Horizon Capability Master Plan](HCL_LONG_HORIZON_CAPABILITY_MASTER_PLAN.md)：canonical 最终 capability architecture、Levels、Waves A–H、41 个 work packages、G-HC/G-ARCH、serious evaluation、cross-model、optimization 与 leaderboard phase。
- [Live development plan](DEVELOPMENT_PLAN.md)：只保存当前 wave、执行队列、superseded policies 与 `NEXT_READY`。
- [CG-04 比较协议](docs/HCL_CG04_EXTERNAL_DEVELOPMENT_PROTOCOL.md)：四个合成开发案例、五臂、零重试、USD 0.30 单次授权已消费并关闭；旧预算不转移。
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

- [CG04 source-first closure](reports/HCL_CG04_EXTERNAL_DEVELOPMENT_CLOSURE.md) / [CG05 source-first closure](reports/HCL_CG05_EXTERNAL_DEVELOPMENT_CLOSURE.md)：两项 RETAIN 仅为 HCL-authored development evidence，独立外部泛化尚未建立；预算和 trigger 均关闭。

- [POST-CG05 capability gap review](reports/HCL_POST_CG05_CAPABILITY_GAP_REVIEW.md)：当前新增机制证据不足以选择 CG06，下一项为已保留能力的独立外部泛化接入；首次零调用原问题检查0/8有专门 treatment，未创建付费包。


## Long-horizon development policy

The architecture-building main line is now Wave A through Wave H. Correctness,
safety and integration smoke tests allow dependent development to continue, but
do not establish external efficacy. Per-capability mandatory provider-backed
five-arm validation, per-capability benchmark search and the old two-unvalidated-
candidate ceiling no longer block architecture growth.

After H05, G-ARCH is a mandatory gear shift into Serious Independent Evaluation:
independent generalization → strong-base/P/G/H comparison → cross-model transfer →
optimization → Authoritative Leaderboard Target Audit → final leaderboard push.
No provider spending, LongMemEval access or benchmark-specific runtime logic is
authorized by this policy change.

共享来源修订入口见 [A01](docs/HCL_WAVE_A01.md)：实际更新相关信念/词义比较，保留无关状态；仅 correctness evidence，普通入口仍限旧语法。最新 owner 默认授权允许现有 provider 基础设施内必要且有记录的正常开发调用；不重新开启历史已消费 grant。

[A02–A03 普通文本与解释修订](docs/HCL_WAVE_A02_A03.md)：明确自述与不确定、含糊指代分支、反证传播及局部撤回；可替换提取器的开放候选不因 JSON 或引用正确而获得语义事实地位。

[A04–A05 共享材料与保留能力](docs/HCL_WAVE_A04_A05.md)：原文→有来源的语义候选→保留检查器→依赖比较→一次最终回答输入。新路径保留原文、内部格式和条件假设的区别；旧冻结实验仍在历史边界回放。

[B01 高阶认知对象](docs/HCL_WAVE_B01.md)：区别人物对他人信念的归因与对方自己的表态，保留内外层否定、听闻/理解/知识主张及私人信念假设的边界。

[B02 交流与信息路径](docs/HCL_WAVE_B02.md)：公开/定向发送不等于收到，收到不等于理解或相信；提取前选择可见文本，保留迟到接触与早期快照的区别。

[B03 修订与获知时间](docs/HCL_WAVE_B03.md)：后来纠正旧记录可修订当前对过去的解释，但不污染当时可得的证据；人物明确修订仍需同一人物的早期支持。

[B04 转述来源与冲突](docs/HCL_WAVE_B04.md)：复制不增加独立支持，人物明确不确定与系统缺证分开，高阶归因不脱离原来的说话者与模态。

[B05 分人物整合与局部修订](docs/HCL_WAVE_B05.md)：只修改 Noor 的接触记录，会更新其高阶比较、概念和条件责任检查；Mira 与 Kai 的实际输入保持不变。

[C01 目标、手段与计划](docs/HCL_WAVE_C01.md)：目标不自动选定计划；有来源的选定计划与机会可支持继续推进；放弃目标会改变依赖它的检查，结果不反推意图。

[C02 竞争行动解释](docs/HCL_WAVE_C02.md)：行动时无知可削弱知情型解释，不能自动证明其他动机；多个有来源目标可以并存，缺证与否定证据分开。

[C03 信念、计划与声明模型](docs/HCL_WAVE_C03.md)：人物信念可支持模型条件不成立的计划，不能据此说人物明知不可行；换计划不自动改变价值。

[C04 评价、感受与重新评价](docs/HCL_WAVE_C04.md)：混合目标评价不等于实际情绪；目标更新和明确重新评价分开，表情与旁人判断不升级为真实感受。

[C05 行动解释与评价整合](docs/HCL_WAVE_C05.md)：纠正行动前信念会改变计划依赖的解释，后来获知不倒填过去，也不自动推断情绪。

[D01 条件承诺生命周期](docs/HCL_WAVE_D01.md)：条件未知、条件不成立、未收到条件和主动撤回分别解释；后来的接收不倒填早先期待。
