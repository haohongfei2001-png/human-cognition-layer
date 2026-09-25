# Human Cognition Layer

Human Cognition Layer (HCL) 是一个面向**复杂人类认知建模、状态更新与社会决策**的可迁移认知层研究项目。

项目的最终目标不是把某个 benchmark 调到更高分，也不是把输入分成几个类别，而是：

> **构造一个独立于底座模型的复杂认知模块，使不同 LLM 能更可靠地形成、维护、更新并使用关于人的结构化认知，从而在未见过的推理与交互任务上获得稳定提升。**

**Canonical live state:** [STATUS.md](STATUS.md)

## Research thesis

**The base model is replaceable. The cognition layer is the asset.**

研究成果应当是一个可复用、可迁移、能够真正增加能力的认知模块。

Benchmark / leaderboard 的角色是：

- 外部测量；
- 泛化检验；
- 研究认可渠道。

它们不是“什么是正确认知”的最终裁判，也不是模块设计的答案来源。

HCL 首先要求认知表示和更新本身在事实、信息边界、时间关系与证据范围上成立；对于不可直接观察的潜在心理状态，则要求不过度断言、保留真实不确定性，并尽可能用独立人类行为或其他有效证据校验。分数用于检验效用，不替代正确性判断。

因此本项目明确反对：

- 根据 leaderboard 错题逐条补 prompt 规则；
- 把 internal synthetic test 的满分当作研究有效性的证明；
- 把 SIMPLE / EPISTEMIC / CAUSAL_AMBIGUITY 分类本身当作研究贡献；
- 消费 fresh evaluation 后继续针对这些样本调参。

公开研究定位与 Phase-0 门禁见：

- [docs/RESEARCH_POSITIONING_V04.md](docs/RESEARCH_POSITIONING_V04.md)
- [docs/HCL_V04_PHASE0_RESEARCH_QUESTION_FREEZE.md](docs/HCL_V04_PHASE0_RESEARCH_QUESTION_FREEZE.md)
- [docs/HCL_V04_CAPABILITY_DEVELOPMENT_PLAN_V01_PUBLIC.md](docs/HCL_V04_CAPABILITY_DEVELOPMENT_PLAN_V01_PUBLIC.md)
- [docs/HCL_V04_CAPABILITY_DEVELOPMENT_PLAN_V01.md](docs/HCL_V04_CAPABILITY_DEVELOPMENT_PLAN_V01.md) — detailed review draft
- [docs/HCL_V04_PRO_CAPABILITY_ARCHITECTURE_REVIEW_PROMPT.md](docs/HCL_V04_PRO_CAPABILITY_ARCHITECTURE_REVIEW_PROMPT.md) — Pro review instructions
- [docs/HCL_V04_RESEARCH_PLAN_V01_PUBLIC.md](docs/HCL_V04_RESEARCH_PLAN_V01_PUBLIC.md) — historical/superseded
- [docs/HCL_V04_EVALUATION_EXPOSURE_REGISTER.md](docs/HCL_V04_EVALUATION_EXPOSURE_REGISTER.md)
- [docs/MODULE_FIRST_DOCTRINE.md](docs/MODULE_FIRST_DOCTRINE.md)

## Current phase

当前 canonical 阶段：

**HCL v0.6 fresh comparison staged; v0.7 intention runtime in provider-free development**

v0.5 保持冻结，作为显式 stance / revision / provenance / persistent-state 基础。v0.6 已经真正增加了一层人物信息视角与 belief evidence runtime，而不是继续只做 memory infrastructure。

当前已完成的 v0.6 cognition capability：

- 一阶人物信息视角；
- 有限二阶视角：A 有证据认为 B 接触过什么；
- self-report / narrator / third-party report / observed action 的 belief evidence 来源分离；
- CHARACTER_UNCERTAIN 与 SYSTEM_INSUFFICIENT 分离；
- 收到 challenge 不自动等于改变 belief；
- 明确 direct revision 才能 supersede 旧 belief；
- perspective-bounded downstream answer context。

第一次有效的外部 development utility check 使用 8 个此前未消费的 FANToM conversation，在同一 `deepseek-flash` 下比较 C / P / D：

- C direct：**4/8**；
- P thin perspective scaffold：**4/8**；
- D HCL v0.6：**6/8**；
- D 相对 P：**2 个独占修正，0 个退化**。

因此预冻结 directional gate **PASS**。这只是 n=8、单模型、development-only 的正向信号，不是外部 efficacy 或 leaderboard claim。

两类剩余抽象缺陷已经进入 v0.6.1 修复：

1. **隐式首次出现 / late-entry boundary**：模型知道未来人物名单时，不能把未来才出现的人追溯性地放进早期 listener；
2. **partial summary != precise knowledge**：听到相关主题或摘要，不等于知道一组更精确、更完整的复合信息。

v0.6.1 因此新增确定性的 participant-presence evidence floor，并把“精确知识需要所有 material details 有支持”写入 perspective semantic policy。后续 external harness 还会保存不含 benchmark 文本的 turn/speaker/listener access map，便于区分 access-state 错误和 downstream reasoning 错误。

完整记录：

- [docs/HCL_V06_MINIMAL_PERSPECTIVE_BELIEF_RUNTIME_V01.md](docs/HCL_V06_MINIMAL_PERSPECTIVE_BELIEF_RUNTIME_V01.md)
- [reports/HCL_V06_FANTOM_CPD_V01_REPAIR_CLOSURE.md](reports/HCL_V06_FANTOM_CPD_V01_REPAIR_CLOSURE.md)
- [docs/HCL_V06_PERSPECTIVE_BOUNDARY_REPAIR_V061.md](docs/HCL_V06_PERSPECTIVE_BOUNDARY_REPAIR_V061.md)

当前不会重跑这 8 个已消费 development conversation 来制造“修复后分数”。v0.6.1 先通过独立 provider-free correctness；之后新的外部 efficacy 必须使用新的 disjoint fresh selection，并加入 competent generic structured-state G。

LongMemEval 32-row package 继续冻结、未消费，不阻塞当前 human-cognition capability 路线。

新的 FANToM C/P/G/D fresh pilot 已冻结 32 条互不重叠的完整 conversation，
排除历史 80 条及上述 8 条 development 数据。G 保留完整事件、来源、时间、
普通听闻关系与不确定性，作为有竞争力的通用结构基线。当前只完成
provider-free package，**没有调用 provider，也没有 fresh 成绩**。
见 [pilot protocol](docs/HCL_V06_FANTOM_CPGD_FRESH_V01.md) 与
[case audit](reports/HCL_V06_FANTOM_CPD_V01_CASE_AUDIT.md)。

下一块真实 cognition capability 已开始：v0.7 Evidence-Constrained Intention
& Motivation。最小 runtime 区分明确意图、目标、行动、推测动机及他人归因，
并支持证据约束的修订、完成、放弃和未决状态。当前已通过 provider-free correctness，外部效用仍未验证；
事件级语义提取器只接受原始事件中的精确证据片段，并在无效输出时 fail closed；
见 [runtime contract](docs/HCL_V07_INTENTION_MOTIVATION_MINIMAL_RUNTIME_V01.md)
与 [external benchmark audit](docs/HCL_V07_EXTERNAL_BENCHMARK_AUDIT_V01.md)。

v0.6.1 已在 main `0bf56af7baf305ca3bebb9035c4a989794a50eb8` 完成 provider-free certification：
- runtime correctness run `36138966541` — **SUCCESS**；
- C/P/D provider-free run `36138966583` — **SUCCESS**。

本轮没有为了“修复后分数”重跑 8 个已消费 FANToM conversation；v0.6.1 的新增边界只通过独立 synthetic correctness 验证。

当前 gate：

**HCL_V06_V061_PERSPECTIVE_RUNTIME_FROZEN_NEXT_CAPABILITY_OR_FRESH_EFFICACY**

## Intellectual-property boundary

公开仓库只包含已决定公开的研究定位、实现、协议与实验结果。

未公开的 owner-originated conceptual examples、私有研究推演和拟作为后续研究成果组成部分的机制细节，不应在未获得明确授权前写入公开仓库。

## HCL v0.3 architecture

### 1. Frozen cognition state

每个输入都先构造结构化 cognition state。当前冻结模式包括：

- SIMPLE
- EPISTEMIC
- CAUSAL_AMBIGUITY

关键语义原则包括：

- world truth 与 agent knowledge 分离；
- 信息转移必须有 evidence bridge；
- 一阶信念与二阶信念分离；
- world-belief divergence 作为 epistemic state 处理；
- 保留真实竞争因果，不为方便强行消歧；
- 使用 minimal sufficient modeling；
- 不确定性和回答粒度必须与问题粒度匹配。

冻结契约：

- [hcl/v03/FROZEN_STATE_SEMANTICS.md](hcl/v03/FROZEN_STATE_SEMANTICS.md)
- [hcl/v03/state_schema.json](hcl/v03/state_schema.json)
- [hcl/v03/STATE_BUILDER_PROMPT.md](hcl/v03/STATE_BUILDER_PROMPT.md)

### 2. Always-on answer loop

回答链路当前为：

~~~text
Input
  ↓
HCL v0.3 cognition state
  ↓
Base-model draft
  ↓
HCL consistency / calibration check
  ↓
Final answer
~~~

checker 检查显式事实一致性、agent 信息可达性、一阶/二阶信念、错误消歧、过度不确定以及回答粒度。

实现：

- [hcl/v03/answer_loop.py](hcl/v03/answer_loop.py)
- [hcl/v03/backends.py](hcl/v03/backends.py)
- [hcl/v03/ANSWER_LOOP_PROTOCOL.md](hcl/v03/ANSWER_LOOP_PROTOCOL.md)

### 3. Decision Policy for interactive action

SOTOPIA 等交互环境中，HCL cognition state 后增加 Decision Policy，将“知道什么 / 不知道什么 / 存在哪些可能性”进一步映射成更合适的行动策略。

这一步是为了解决早期实验暴露出的一个真实问题：认知判断本身可以是谨慎且正确的，但如果缺少行动策略，最终行为可能变得过度被动、低信息或低推进。

## Current evidence

以下数字是研究证据，不是最终产品能力声明。

### State fidelity

最终 fresh 18-case freeze holdout：

- raw: **17 / 18**
- mode accuracy: **94.4%**
- uncertainty accuracy: **94.4%**
- schema validity: **100%**

唯一 raw failure 经审计被判定为 fixture-design 问题；历史原始分数保持 17/18，不做事后改分。

### Answer checker

fresh adversarial checker suite：

- raw: **11 / 12**
- revision-family hit rate: **100%**
- final-check pass rate: **100%**

结论：**HCL v0.3 answer checker gate PASSED**。

### SOTOPIA-Hard

固定 diagnostic slice（10 settings）在 Decision Policy 修复前：

- control mean overall: **2.7429**
- HCL mean overall: **2.7000**
- paired mean delta: **-0.0429**

该结果没有显示 aggregate improvement，并暴露了 knowledge acquisition、financial/material 与 goal 推进方面的问题。

Decision Policy 修复后的 fresh holdout（此前未使用的 Hard ordinals 10–19）：

- control mean overall: **2.4714**
- HCL + Decision Policy mean overall: **2.8857**
- paired mean delta: **+0.4143**
- improved / tied / worsened: **7 / 1 / 2**

这是**鼓舞性的 fresh-holdout signal**，但不是最终 efficacy claim：n=10、每个 arm 单轨迹，并且使用自定义 DeepSeek partner/evaluator，不与官方 leaderboard 直接可比。

完整实验记录、run id、adjudication 与最新 repeat 状态见 [STATUS.md](STATUS.md)。

## Benchmarks

### CogToM

CogToM 现在是 diagnostic/regression instrument，而不是项目当前阶段本身，也不被视为不可质疑的人类心智真值。

官方上游评测代码固定到 commit：

`28c6781b6ea7d7ef7d491f61adc18f076f8b993c`

代表性 200-group baseline 覆盖 46/46 subcategories，mean group accuracy 为 96.0%。历史 HCL v0.1/v0.2 结果保留用于回归和方法诊断。

### SOTOPIA-Hard

SOTOPIA-Hard 是当前主要的方法验证环境。当前流程强调：

1. 诊断集与 fresh generalization holdout 严格分开；
2. 决策策略修改后不得再把已看过的设置当 fresh evidence；
3. 正向单次结果必须经过 predefined repeats / seeds；
4. 稳定后再做 cross-base-model transfer。

## Research discipline

- Benchmark 原题与标准答案不得作为训练数据。
- 可以根据 benchmark 暴露的**抽象 failure mode**设计独立 synthetic fixtures。
- raw score、失败案例和事后 adjudication 必须分别保留，不做 post-hoc 改分。
- 不因为 HCL 某次表现更差就静默绕过 HCL；回退本身是诊断信号。
- fresh holdout 一旦消费，就不能继续作为调参后的 fresh generalization evidence。
- 所有实验应记录模型、prompt/协议版本、seed、benchmark slice、上游 commit 与运行环境。
- API key、私密数据、本地 `.env` 和凭据不得提交到仓库。
- 在 repeated holdout 与 cross-base transfer 之前，不启动模型训练。

## Historical CogToM runner

CogToM baseline/diagnostic runner 仍可用于回归：

~~~bash
export DEEPSEEK_API_KEY="..."
python scripts/run_cogtom_baseline.py --model deepseek-flash --limit 20 --language zh
~~~

正式/较大样本运行可按实验配置调整模型与 limit。运行结果应作为实验 artifact 保存，具体当前 workflow 与状态以 [STATUS.md](STATUS.md) 和仓库 Actions 配置为准。

## Current route

```text
HCL v0.3 baseline (FROZEN)
→ HCL v0.4 minimal persistent cognition runtime
→ correctness / revision semantics
→ long-horizon bounded-context capability test
→ independent transfer validation
→ frozen unseen external evaluation
→ cross-base-model transfer
→ recognized benchmark / leaderboard evidence
→ training / adapters only if the evidence justifies them
```

当前原则是：**先形成研究机制，再让榜单证明它；不让榜单错题反向定义认知模块。**

不要从 README 推断某个实验仍在运行或已经结束；**实时执行状态始终以 [STATUS.md](STATUS.md) 为唯一事实源。**
