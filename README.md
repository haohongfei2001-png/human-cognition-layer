# Human Cognition Layer

HCL 为基础模型增加按需的人类认知支持，帮助理解人物信息、信念、视角和有来源的心理证据。**基础模型可以直接做好时，直接回答。** 简单提示足够时不调用复杂机制；精确计算采用通用工具；专门认知机制只保留得到增量证据支持的部分。

当前阶段：**Serious Independent Evaluation，I02 来源及比较臂资格审查**。Waves A–H 完成 provider-free 正确性构建；G-ARCH 经一次有界真实普通输入运行，通过架构与入口准备门槛，原始回执及限制见 [source-first closure](reports/HCL_G_ARCH_ENTRY_CLOSURE.md) 和 [gate](docs/HCL_G_ARCH_GATE.md)。I02 的[普通叙事信息状态 v2 接入](docs/HCL_I02_INFORMATION_STATE_V2_REPAIR.md)已在公开校准案例上通过无 provider 的 H/H-new treatment-presence 和公平性检查；早期 C/P/G 校准曾因 G-map 格式失败，后续 ACL v8 开发运行通过接口但语义资格仍未确立。这尚未证明独立泛化或强模型增益。当前按 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) 和 [I01 evaluation contract](docs/HCL_I01_EVALUATION_CONTRACT.md) 做独立来源与公平比较资格审查。LongMemEval 保持封存，leaderboard 尚未启动。

- [I02 普通 reader 全来源传递 v6](docs/HCL_I02_READER_SOURCE_CARRY_V6.md)：认知准备不再替代原始来源；保留 observer/access 边界与完整长度限额，原生选择题探针归开发证据、排除确认；旧付费运行按原认证版本重放，零新调用。
- [I02 原生隐私概念开发校准收口](reports/HCL_I02_IRIE_PRIVACY_CPG_CLOSURE.md)：四次调用、零重试、估算 USD 0.06977652；C/P/G 开发者匿名诊断各 7/7，未证明独立泛化或 H 增益；预算关闭、来源暴露排除，继续 I02。
- [I02 可达 Git 历史暴露门禁 v6](docs/HCL_I02_REACHABLE_HISTORY_SCREEN.md)：已删历史来源仍可被拦截；实际 KPU 负例命中三处，LongMemEval 对象只据元数据跳过，仍需独立来源与比较臂资格。零调用。
- [I02 来源论点普通入口 v5](docs/HCL_I02_READER_ARGUMENT_ENTRY_V5.md)：修复短文本中公开论点比较被通用拒绝的问题；来源和题目完整进入最终输入，仍未证明专门机制或答案增益。开放教材候选已开发暴露、权利待核查，不作未见确认；零调用。
- [I02 匿名评审 v2 交接](docs/HCL_I02_BLIND_REVIEW_V2.md)：揭盲前强制完整剩余断言审查；真实 ACL 回执完成无 provider 流程验证，尚无独立语义评审。
- [I02 剩余断言审查补充](docs/HCL_I02_RESIDUAL_CLAIM_AUDIT.md)：可审计预设义务外的无依据严重断言；仅评估接口改进，不提升历史分数或独立证据。
- [I02 ACL C/P/G v8 一次性开发校准结案](reports/HCL_I02_ACL_ETHICS_CPG_V8_CLOSURE.md)：四次原生推理调用与精确引文接口通过，零重试，估算 USD 0.02662506／峰时 USD 0.05325012；合成开发来源不能证明独立泛化或 HCL 增益，盲式语义比较尚未合格，授权已关闭。
- [I02 ACL v8 开发者匿名语义审查](reports/HCL_I02_ACL_CPG_V8_DEVELOPER_REVIEW/CLOSURE.md)：冻结四项来源优先义务下，C/P/G-final 分别为 6/8、7/8、8/8；审查者也是实现者，不能视为独立盲评或跨任务比较臂资格。
- [I02 ACL 教学摘要开发来源](docs/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.md)：固定外部作者 CC BY 合成摘要及来源优先义务；C/P/G 普通输入无 provider 门禁通过，H 实际直通；整套作者／模板不能算未见确认。
- [I02 来源优先盲评交接](docs/HCL_I02_BLIND_REVIEW_PACKET.md)：真实原始回执可生成匿名答案包，完整复核后才揭示比较臂；尚无独立盲评或效力结论。
- [I02 强比较器 v8 候选](docs/HCL_I02_STRONG_COMPARATOR_V8.md)：C/P/G 原生推理和引文接口已在一条合成开发题上运行；跨任务语义能力与独立来源仍未合格。
- [I02 受限覆盖报告](docs/HCL_I02_RESTRICTED_COVERAGE_REPORT.md)：可执行校验器如实报告少于四任务／三来源体系的目录，同时保留完整成熟度门槛；不开放 provider 输入或声称效力。
- [I02 完整来源输入覆盖](docs/HCL_I02_LONG_INPUT_COVERAGE.md)：25 篇固定长故事均超过 H 普通入口长度上限；将拒绝记为观察结果，不截短来源或宣称合格样本。
- [I02 EPC 工程伦理开发筛查](docs/HCL_I02_EPC_GLASS_SCREEN.md)：独立作者的原生伦理题有来源和许可回执，但 H 普通入口直通模型、无认知机制处理；已暴露材料不作独立确认。
- [I02 QuALITY 有界来源筛查](docs/HCL_I02_QUALITY_BOUNDED_SCREEN.md)：外部文章与人工题的许可有直接来源；固定开发文章九题仍不足以证明深层概念任务适配，已读来源纳入暴露边界，不送模型。
- [I02 叙事来源边界](docs/HCL_I02_NARRATIVE_SOURCE_BOUNDARY.md)：NarrativeQA 开发题和教学模块已读材料纳入暴露记录；教学模块的人物状态表及示例回答不得作为普通来源输入，尚无合格独立案例。
- [I02 G 中间证据边界 v4](docs/HCL_I02_G_WORKSPACE_V4_BOUNDARY.md)：比较臂的引用图只允许来源 ID、原文引用和未决问题进入最终模型输入；仍待真实模型语义校准。
- [I02 通用 G 工作区 v5](docs/HCL_I02_GENERIC_WORKSPACE_V5.md)：补上有版本的引文记忆、暂定证据关系和回答步骤；不改变 C/P 或历史运行，仍待真实模型语义校准。
- [I02 EPC C/P/G v5 一次性开发校准收口](reports/HCL_I02_EPC_CPG_V5_CLOSURE.md)：3 次调用、零重试；G-map 达到冻结输出上限并截断，G-final 未运行，G 语义未合格。原始回执已保存，授权关闭；H 未运行，不计独立确认。
- [I02 G v6 紧凑通用比较器](docs/HCL_I02_GENERIC_WORKSPACE_V6.md)：对 G 的来源索引与中间输出加上可执行界限；保留完整原文与 C/P 输入。后续 KPU 开发运行的 G-map 引文超过冻结单行长度，G-final 未调用，语义仍未合格。
- [I02 G v7 通用证据工作区](docs/HCL_I02_GENERIC_WORKSPACE_V7.md)：在整体输出界限和逐条准确来源校验下容纳较长完整引文，保留 C/P、公平普通输入及历史 v6 结论；仅 provider-free，尚无新模型语义证据。
- [I02 KPU C/P/G v6 开发校准收口](reports/HCL_I02_KPU_CPG_V6_CLOSURE.md)：独立作者 CC BY 案例的一次性运行用去 C/P/G-map 三次调用；G 引文真实但全部超过冻结单行长度，G-final 未调用，P 引文格式也未过 scorer。原始回执已保存，授权与 trigger 关闭；案例只作开发证据，不作独立确认或 HCL 效力证据。
- [I02 来源权利与隐私筛查 v3](docs/HCL_I02_RIGHTS_PRIVACY_SOURCE_SCREEN_V3.md)：两个已暴露来源系统被明确拒绝，新增独立于历史冻结包的 URL、许可与隐私门禁；没有合格确认案例或新调用。
- [I02 已暴露来源指纹 v4](docs/HCL_I02_EXACT_SOURCE_FINGERPRINT_V4.md)：KPU 已消费原文即使用镜像 URL 和新作者／模板 ID 也不能进入独立确认；不改历史冻结包，仍须单独做完整来源资格审核。
- [I02 开放教材有界筛查](docs/HCL_I02_OER_BOUNDED_SCREEN.md)：SQuALITY、TRU/Rebus 与 Ethics Bowl 案例的具体许可、任务适配和已读暴露分别记录，尚无合格独立样本。

- [普通人物问题与叙事入口](docs/HCL_V1_PERSON_QUESTION.md)：有来源、时间、访问与局部修订边界；单次回答，默认零提取调用。
- [I02 C/P/G 一次性校准结案](reports/HCL_I02_CPG_CALIBRATION_CLOSURE.md)：3 次调用后 G-map 格式失败，G-final 未运行；完整 raw receipt 已保存，授权关闭，不测 H 增益。
- [I02 第二来源 C/P/G 校准结案](reports/HCL_I02_MORAL_CPG_CALIBRATION_CLOSURE.md)：Moral Stories 首条开发样本完成四次调用；G-map v2 接口通过，但比较臂遗漏明确的安全目标，语义资格未通过。授权关闭，不调用 H/H-new，不声称独立效力。
- [I02 来源优先语义评分 v1](docs/HCL_I02_SEMANTIC_SCORER.md)：冻结通用评审维度、原文引文校验与盲评计分接口；不自动判定语义真伪，也不代表 HCL 答案能力或独立效力提升。
- [I02 来源暴露边界](docs/HCL_I02_SOURCE_LINEAGE.md)：MuSR、Moral Stories 及五个历史用过的来源体系不能换行号进入独立确认集；仍需完整历史审计，尚无合格确认案例。
- [I02 通用比较臂 v3](docs/HCL_I02_CPG_V3_REPAIR.md)：P/G 的来源清单把明确目标与未知的伤害意图分开；保留 C 和共同输入。仅无 provider 正确性，尚未确认模型表现。
- [I02 FairytaleQA 元数据候选](docs/HCL_I02_FAIRYTALE_METADATA_CANDIDATE.md)：按固定目录规则锁定一条较长外部故事及专家问题；后续已做盲式版本及题型标签核对，正文、题目和答案文本均未展示，不可送模型。
- [I02 盲式版本核对](docs/HCL_I02_FAIRYTALE_BLIND_PROVENANCE.md)：已证明候选故事全文标准化后连续匹配固定 Gutenberg 版本；只输出哈希和统计，没有展示正文或查看问题答案，案例仍未合格。
- [I02 FairytaleQA 题型元数据核对](docs/HCL_I02_FAIRYTALE_QUESTION_TAG_AUDIT.md)：固定题目文件仅统计出版社标签；61 题中 6 题为总览，且没有总览人物／感受标签。长篇人物发展任务适配尚未证明，未查看题目或答案文本，案例仍不合格。
- [I02 FairytaleQA 标注来源与许可边界](docs/HCL_I02_FAIRYTALE_ANNOTATION_RIGHTS.md)：固定作者仓库对专家标注和根目录 Apache 2.0 许可的原始证据；provider 处理地点、题目语义及任务适配仍未核实，不开放模型输入。
- [I02 FairytaleQA 章节跨度核对](docs/HCL_I02_FAIRYTALE_SECTION_SPAN.md)：六个总览题均只标注相邻附近两章，最大跨度为 43 章中的 2；该预选来源不符合当前长篇人物发展任务的元数据资格，不据此换题或声称 HCL 效力。
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

[D02 有限相互确认](docs/HCL_WAVE_D02.md)：原话、回述、确认及各自接收链分开；后来澄清不会自动更新另一方，也不产生无限共同知识。

[D03 竞争交流解释](docs/HCL_WAVE_D03.md)：假话不自动等于欺骗；信念、知情报告、目标、遗漏与信息需求分别检查，真话也可保留条件性的隐瞒疑点。

[D04 误解因素与解释修订](docs/HCL_WAVE_D04.md)：接收、条件、局部词义和角色期待分别保留；明确的新期待更新解释，但不重写原承诺或自动恢复信任。

[D05 多方计划与有限授权](docs/HCL_WAVE_D05.md)：分别保留各人的计划、同意和接收；来源规则下的授权不自动转授，也不产生全知的群体人物。

[E01–E02 关系证据与冲突修复](docs/HCL_WAVE_E01_E02.md)：领域、方面和方向不混合；失败不自动归咎于恶意，收到道歉不自动表示原谅。

### I02 author-original concept source boundary

The [OBP author-original metaethics source audit](docs/HCL_I02_OBP_METAETHICS_SOURCE_AUDIT.md)
now clears a complete CC BY 4.0 author section and its native question 10 for
**development calibration only**, after resolving the whole chapter’s quotation
and family-news boundary. Exact PDF reconstruction and three source-first
obligations distinguish a reported error theory from moral truth and approval
of theft. C/P/G keep complete equal inputs; actual H is direct with no specialized
treatment. This developer source audit is not independent human review, a hard
item certificate, model-semantic qualification or H efficacy. v9 excludes the
exposed OBP author/writing system from confirmation. Zero provider calls/spend;
confirmation source count remains zero. Continue protected disjoint source and
comparator qualification without paying to retest this already verified input path.


### I02 protected original-narrative candidate

The [protected original Gilman narrative candidate](docs/HCL_I02_GILMAN_PROTECTED_SOURCE_SCREEN.md)
pins the complete 31,497-character original English body and a new ordinary
question, without NarrativeQA questions/gold or implementer-visible story text.
Limited US/China/UK original-prose term review is separate from semantic fit;
there is no worldwide rights claim. A scoped cloud workflow applies existing
current-HEAD reachable-history and snapshot screens after exact-byte reconstruction.
No H entry, runtime repair, provider input or paid call is allowed by this package.
Even a clean history receipt only makes source-first holder review ready; confirmation
qualification, task difficulty and model competence remain unresolved. Zero calls/spend.


### I02 protected source-holder audit freeze

The [v3 native long-input interface closure](reports/HCL_I02_SOURCE_HOLDER_V3_CALIBRATION_CLOSURE.md)
is **INCONCLUSIVE_INTERFACE_CONTRACT_FAILURE**, run 36708265295 on main
`881628ff37411e934e87409acaa776bb419b9845`: complete JSON/finish stop and literal
source anchors, but all five expectation fields were prose, failing the strict
STATE/QUALIFY/AVOID enum. **1 call / 0 retries**, usage/clock estimate
**USD 0.02909676**, peak rated USD 0.05819352; invoice unverified. Raw receipt,
usage, hashes and diagnostics preserved; grant zero and trigger disabled, no rerun.
The future-only typed v4 prompt contract clarifies fields without coercing old
answers or changing the frozen receiver. 33 provider-free tests pass; v4 live
behavior unverified. Authored repetitive fixture does not establish literary
semantics, independent review, comparator qualification or H efficacy.
Unique next task: distinct protected source/task qualification using the typed
contract and source/rights/exposure gates; do not rerun consumed fixtures or
Gilman/James. I02 remains NEXT_READY; historical dispositions unchanged.

The [v3 long-input interface calibration freeze](docs/HCL_I02_SOURCE_HOLDER_V3_LONG_CALIBRATION.md)
uses a **new authored 81,243-character / 804-line fixture**, complete ordinary
question/input and native high thinking with line references. Expected literal
anchors remain outside model input. **1 call / 0 retries / new USD 0.38 cap**,
16,384 output tokens, conservative peak reservation USD 0.36697320; no ceiling
escalation, old-source reopening or historical budget transfer. 0 calls at freeze.
Thirty provider-free tests passed at freeze; the closure above supersedes readiness.
any result is interface-only, never independent source, literary semantics,
old-source failure repair, comparator competence or H efficacy proof.

The [complete James source-audit closure](reports/HCL_I02_JAMES_HOLDER_CLOSURE.md)
is **INCONCLUSIVE — incomplete output at 16,384 tokens**, run 36704349775:
**1 call / 0 retries**, usage/clock estimate **USD 0.04721376**, peak rated
USD 0.09442752; invoice unverified. Raw receipt, metadata, control audit and
hashes are preserved; grant zero, trigger closed, no rerun or arm calls.
With two monolithic source audits incomplete, **SIMPLIFY_INTERFACE** before
further source swaps/spending: provider-free v3 retains the complete original
source and binds source/question hashes while resolving deterministic line ranges
locally, rather than making the reviewer reproduce exact quotes. 25 correctness/
boundary/revision/composition/historical checks pass; the 80,958-character long
witness reconstructs exactly. No live-capacity/cost/semantic improvement is proved.
Historical next task was the v3 calibration; it has now been consumed and closed
as above. Continue distinct I02 source/comparator qualification without reopening
Gilman or James.
No new H capability/efficacy, confirmation qualification or historical disposition change.

The [complete James development narrative audit freeze](docs/HCL_I02_JAMES_DEVELOPMENT_SOURCE_AUDIT.md)
pins **80,958 characters of complete original author prose**, preserving CRLF and
excluding the nonauthor transcription/contact note. Two interior lines were
accidentally displayed in a legacy-boundary check: **the whole author/system is
development-exposed**, excluded from confirmation by v10. Do not call it unseen.
A new ordinary person/self/other/counterfactual question receives source-only
review, no arm or H outcome: **1 call / 0 retries / new USD 0.32 cap**, 16,384 native
reasoning/output tokens, peak reservation USD 0.30622680. 0 calls at its historical freeze; the closure above supersedes execution readiness.
No Gilman rerun or source shortening; no confirmation or H efficacy promotion.
Continue I02 long-narrative comparator/source qualification.

The [OBP native concept C/P/G closure](reports/HCL_I02_OBP_METAETHICS_CPG_CLOSURE.md)
records **C/P/G-final 7/7** on the three frozen obligations plus developer residual
review: this local question is saturated. Run 36701264145 completed **4 calls /
0 retries**, usage/clock estimated **USD 0.02631310**, peak rated USD 0.05344284;
invoice unverified. Raw requests/responses, model, usage, cost, opaque reviews and
source-first scores are preserved; grant zero, trigger closed, no rerun.
**H/H-new 0; H efficacy NOT TESTED**. This is implementer-reviewed development
calibration, not independent review, confirmation or broad comparator qualification.
Continue I02 protected independent source qualification; no historical disposition changes.

The [native OBP concept C/P/G calibration freeze](docs/HCL_I02_OBP_METAETHICS_CPG_CALIBRATION.md)
uses the unchanged exposed author-original unit and native question, with obligations
frozen before outputs. Existing DeepSeek/high native reasoning, 16,384 output tokens
per phase, **4 calls / 0 retries / new USD 0.35 cap**; peak whole-phase reservation
USD 0.33817872. No old grant transfer, Gilman rerun, H calls or confirmation claim.
No call at the historical freeze; the closure above now supersedes execution readiness;
this answers a distinct concept-comparator qualification question in I02.

The [protected source-holder audit closure](reports/HCL_I02_GILMAN_HOLDER_CLOSURE.md)
is **INCONCLUSIVE — OUTPUT_CEILING_BEFORE_JSON**: run 36698203458 made exactly
one DeepSeek call, zero retries, exhausted 8,192 completion tokens and returned
no final JSON. Peak rated and usage/clock estimated cost: **USD 0.04445892**;
invoice/holiday adjustment unverified. Raw binary receipt, metadata and control-only
provenance are preserved; the grant is zero and the trigger is closed. No H/C/P/G
call, source semantic verdict, confirmation qualification or H efficacy follows.
The generic future-source capacity gate is provider-free and does not authorize
or migrate this consumed run. Continue I02 source/comparator qualification.

The [one-call protected source-holder audit freeze](docs/HCL_I02_GILMAN_SOURCE_HOLDER_AUDIT.md)
was ready at its historical freeze; the closure above supersedes execution readiness. The prior main source screen
found no overlaps across 2,774 reachable text blobs / 1,337 snapshot files while
skipping sealed objects. A separately frozen **source-only** automated review
uses existing DeepSeek, high thinking, max 8,192 output tokens, **1 call / 0 retries /
USD 0.18 cap**, worst peak reservation USD 0.13181784; no old budget transfer,
H/C/P/G comparison or confirmation qualification. Raw source/quotes stay in a
separate role-withheld artifact; only structural/provisional/usage/cost metadata
crosses to the implementer. Judge independence, semantic truth and difficulty
remain unverified. No call has executed at this freeze. Continue I02; no owner
permission request is needed under the current normal-cost autonomy policy.

