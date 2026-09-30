# HCL Assistant Product Master Plan

版本：Canonical 1.0 / 2026-09-30。性质：Owner 已决产品方向的正式采用；合入 main 生效。当前实时状态只在 STATUS.md，执行队列只在 DEVELOPMENT_PLAN.md；字段契约在 contracts/PRODUCT_CONTRACTS_V1.md。不得以聊天旧建议覆盖 GitHub current main。

## 1. Product North Star

> 用户首先感受到的是一个能持续理解背景、区分事实与解释、并在新信息出现后正确修订判断的 AI，而不是一个需要用户操作认知模块的分析工具。

产品定义：HCL Assistant 是一个能够持续理解上下文、区分信息与解释、随新信息修订判断的 AI 助手。用户自然地与它交流，HCL 在每次交互中管理相关上下文、认知状态与回答生成；Explain 和 Lab 提供按需的解释与检查能力。

这是产品目标，不是当前已验证效力。优先级：真实帮助与边界可靠性 > 正确持续上下文 > 自然可用体验 > 调试可观察性 > 展示复杂度。不会为维持 HCL 名称硬留无增益机制。

## 2. 固定产品原则

### P01 Assistant-first

Assistant 是第一层；Explain 是回答级按需依据；Lab 是高级研究/调试环境。三层共享同一 run 的真实记录。普通用户不创建 Case、不选择研究包、不配置 evaluation arm。默认正常聊天，无常驻右侧图谱，无前台 Base/HCL 开关。

### P02 HCL owns the answer flow

所有正式输入和生产回答都经过 Interaction Controller。Direct 也是 `input → HCL control → Direct decision → adapter/model or deterministic result → HCL-governed answer`。禁止从 UI/API 直达 provider 的隐藏生产旁路。Lab Base-only 是明确隔离的实验路径，不免除真实权限与费用控制，不自动回写生产记忆。

### P03 Always-on, not always-complex

每条用户消息、文件、引入的历史、来源、更正、假设都进入控制流程。每个相关变更被处理或明确标记未解析/未完成；不得声称未知输入已经全部语义理解。简单问题可 Direct，专门操作可为零。generic-only、unresolved、failed、cost-without-known-gain 均合法。始终在线不等于后台监视或无用户事件的持续付费分析。

输入变化与回答任务分开：`更正，昨天是 B 不是 A；2+2 等于几？` 必须先处理更正，再直接答算术。不能按最后一句绕开前面的状态变化。

### P04 Revisable persistent cognition

原始记录、当前背景、系统解释、假设、更正、撤回、历史状态、摘要/索引分别建模。模型过去生成的解释不能因为被保存、复述或摘要就升级成新的独立证据。重复、引用和衍生摘要保留共同来源根。

### P05 Internal rigor, natural output

内部维护证据、人物、时间、作用域、竞争解释及依赖；外部自然、简洁、有判断力。清晰主判断不等于强选真实动机；关键不确定性进入正文，技术细节进 Explain/Lab。不得因缺少直接自述一律禁止有据推断，也不得把可能解释说成心理事实。无校准不使用伪精确概率。

### P06 Honest activation and evidence

Selected、executed、result-produced、used-in-answer、cache-reused 分开记录。mock 不升级 live，接口通过不升级语言理解，代码正确性不升级 efficacy。产品控制层在线不代表所有研究机制已默认启用。

## 3. 用户价值与范围

优先任务：持续的人际/合作问题理解；长期目标、角色和价值讨论。支持逐步扩展至关系冲突、承诺误解、自我反思、小说人物、多方事件回顾、条件责任与概念分析。用户的感受应被尊重，但用户对他人动机的猜测不是客观事实。

有用结果可能是推断、重构问题、草拟沟通、确认关键缺口或选择不依赖读心的稳健行动。不是诊断别人、人格评分、统一信任值、永久人物画像或制造 AI 亲密依赖。

## 4. 产品分层与对象

前台：Conversation；一个可选的 Topic 容器（UI 可标为项目，不同时引入两套容器）；Files；相关时才出现的 People；可管理的 remembered context。

内部：Event、SourceVersion、ContextState、Interpretation、Snapshot、Run、OperationReceipt、Intervention、Revision、CapabilityManifest。Case 仅为 Lab 中可派生的分析对象，不是生产根对象。

同名人物默认作用域内身份；跨 topic 合并必须有显式依据/确认，并可拆分。小说第一人称、引用、假设不能写成用户本人背景。

## 5. Product architecture

```text
Assistant Web UI
  ↓
Conversation API
  ↓
HCL Interaction Controller
  ↓
Scoped Context Builder
  ↓
Capability Scheduler
  ├ Direct
  ├ Generic
  └ Approved cognition operations
  ↓
Answer Synthesis / Explain Projection
  ↓
Model Adapter
  ↓
Provider
```

这是逻辑边界，不要求微服务。执行顺序细化：接受事件 → 识别/提交相关变更与失效 → 构造范围内上下文 → 按预算调度 → 准备有依据的回答 → 必要模型生成 → 有界检查与发布 → 保存同版本回答/Explain/receipt。Explain 是该 run 已记录依据的投影，不是预先知道模型结果或事后编造理由。

持久化贯穿：原始消息/文件；版本化事件账本；当前状态投影；解释支持/挑战关系；检索/摘要；不可静默覆盖的运行回执。删除政策优先于永久留存，不能用审计要求阻止用户删除。

Controller 负责秩序、权限、版本、选择和资源；不自称万能语义 oracle。研究 Python runtime 保持可替换，通过版本化薄接口接入，不在产品仓库复刻研究机制。

## 6. Routing 与状态责任

路由：DIRECT、CONTEXT_ASSISTED、SELECTED_COGNITION、BOUNDED_RESPONSE、CLARIFY、BLOCKED。blocked 只在无法安全完成时使用；可答部分尽量保留。状态、路由、运行结果独立字段。未选择操作不表示相应世界事实不存在。

不按关键词强制心理分析。判断当前任务、相关上下文、现有证据、能力适用范围、语言覆盖及资源。最小充分操作集合；多解释有限、证据无增量即停止。所有中间模型调用经过计量 adapter。

权限/范围不能确认时不 fallback 到失控 Base。专门操作失败时可基于有效来源生成有界回答，但必须记录失败和未覆盖范围。重试是新 attempt，不改写旧失败。

## 7. 长期对话是一等能力

同一 conversation 延续；用户指定 Topic 内跨对话延续；跨 topic 默认关闭，后续仅显式选择内容。当前背景与历史观点分开，短期情绪/期限目标可过期，未决承诺和问题可继续。

检索不只找支持旧结论的记忆：旧判断连同更正、挑战、撤回、身份更正和关键反证进入候选闭包。摘要是可重建派生物，不是新来源；原文变更使相关摘要和缓存失效。未检索/未解析不等于不存在。

时间至少区分 event/story time、person receipt/learned-at、disclosure、recorded-at；没有依据保留未知/偏序，不按上传时间制造人物获知时间。

新证据可以修正现在对过去的重建；不能把今天获知的信息塞回当事人过去的视角，也不能改写旧回答当时的输入记录。相同事实的多个独立支持可保留，撤回一条不自动全删；新增信息也可能影响原先基于缺失证据的判断。

## 8. Answer 与 Explain

正文优先实际问题；若有依据给主判断和关键条件，可用一个有用行动收束。不得每次机械列状态表，不隐藏改变建议的实质不确定性。

合成只使用当前有效 context、明确 operation outputs 及其允许的一般表达。不得新增未记录的人物心理/动机/价值事实；新假设要先登记为系统解释并保持可检查身份。Direct 一般知识/算术不是人物事实写入，也不是必须先存所有世界知识。

Explain 默认不触发模型调用；展示当时记录的依据、关键条件、其他解释、缺口及会改变判断的信息。旧回答用当时记录；按新信息重新分析是新 run。不得展示或保存私有 chain-of-thought 为产品 Inspector 内容。

## 9. UX 与 MVP

默认：左侧新对话/历史/Topic，中间聊天，右侧不存在。回答级引用、Explain、更多。Explain 轻量抽屉；Lab 经 Advanced 或回答更多进入。用户随口更正即可，不要求表单标注心理真相。

Must Have：normal chat；streaming/stop/retry；always-on Controller；conversation persistence；Topic scope；text/file context；信息与解释区分；correction/retraction；state invalidation；natural synthesis；Explain；memory/privacy；delete/stop using；minimal receipt；failed/unresolved handling。

L1/L2 仅文本/Markdown/TXT 与 synthetic 数据；可靠解析前不承诺 PDF/DOCX 全格式。来源范围可见，上传成功不等于已完整理解。进入真实用户阶段前需实际认证、备份/删除政策与数据安全验收；L1/L2 使用隔离测试身份，不宣传生产认证。

Lab shell：run、context/state、实际 capability execution、Base comparison 入口。比较入口 L2 明确 disabled/no-provider；不建完整 dashboard。P/G/ablation、真实公平比较和成本效力分析均属后期 Lab。

Later：native mobile、macOS native、voice、social、avatars、agent marketplace、心理诊断、人格评分、3D graph、全局永久第三方画像、无请求后台付费认知。

## 10. Privacy 与隔离

三个独立边界：account data permission、人物/故事 perspective access、persistence/reuse permission。临时对话不进持久检索/日志正文；conversation-only 与 Topic scoped 可控；跨 Topic 不自动扩大。

外部材料没有 memory-write、permission-expansion 或 system-policy 权限。stop using 立即阻止未来使用且传播到摘要/缓存；delete 清理来源和派生数据，允许保留无正文的删除回执，不能遗留可恢复人格印象。

采用 docs/BOUNDARY_AND_ISOLATION.md。产品不读取 confirmation source/gold/artifact/credential，不按确认失败调 prompt，不把确认材料改名 Demo，不读取或复制 sealed LongMemEval。产品反馈不得修改 frozen evaluation。必要问题在新的原创非确认材料复现。

## 11. L0–L5

L0：本 Master Plan、稳定契约、控制面、工作包、provider-free setup 检查。
L1：持久化、修订、权限、检索边界、Controller lifecycle；不实现真实研究语义。
L2：完整 synthetic/mock Assistant、Explain、纠错、文件和 Lab shell。
L3：I06 后固定 runtime/interface/digest，按处置与接入验证启用能力。
L4：新的非确认材料上的多轮、中文、更正、迟到证据、合成忠实性、延迟、成本和记忆污染验证。
L5：保留实际有用路径，简化/删除无收益复杂度。

L0–L2 共九个 coherent packages，详见 docs/L0_L2_WORK_PACKAGES.md。研究仍为 I02 → I03 → I04 → I05 → I06；L0–L2 不需要它先给出阳性结果。L3 不能以 I06 完成自动代替产品级验证。

## 12. 激活与处置

产品 capability identity 不绑定 B03/E05/H04。Manifest 分别记录 input/language/scope/output/limitations/runtime/disposition/activation。

RETAIN：限定范围启用；SIMPLIFY：替换简实现；GENERICIZE：保留实用通用路径、不冒称专门增益；DISABLE：新运行停用；REPLACE：新实现/版本接管；INCONCLUSIVE：不强行正面或负面归因，默认不作为生产已验证能力；PENDING_I06：仅候选。

旧回执保留原版本身份；迁移不得把历史 mock 变成 live。无专门操作仍可有产品价值，但不能由 always-on 包装推出更强认知。

## 13. 命名与开发默认

产品文档名 HCL Assistant，前台短名 HCL；高级环境 HCL Lab；示例体验 Cognitive Playground。未完成商标/域名审查，不为命名停工。

L1 默认 Python 模块化 API/Controller 与 SQLite 持久化测试实现；L2 TypeScript/React Web 客户端，通过 HTTP/SSE 接口，不从 UI 直接调用模型。版本、lockfile 和具体工具在各实施包中选定并记录；不引入托管数据库、部署平台、云凭据或付费依赖以解锁 mock。可替换 store/model 接口为后续部署留余地，不造通用平台。

## 14. 成功与停止标准

完成声明范围的正向可用行为，以及人物/来源/时间/权限/版本负面测试；从普通输入到最终记录可追踪；失败、未决、未介入如实保留。Schema/test PASS 只证明被检查的条件。

合并通过的 L0 planning/setup 后，本轮执行者停止。下一位产品 Work 从 L1-01 接管；可按依赖连续推进 L1/L2，不每包问 Owner。遇真实外部权限/凭据/许可/异常费用门槛 defer 并推进独立任务；L2 全部完成而 L3 条件不具备时停止，不制造 filler。
