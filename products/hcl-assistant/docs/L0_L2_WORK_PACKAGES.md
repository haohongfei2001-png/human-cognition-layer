# L0–L2 coherent work packages

总计9包：L0一包、L1四包、L2四包。ID与machine plan一致；包是行为闭环，不是PR数量指标。依赖版本与执行命令由实施包固定，普通实现决策无需再问Owner。

## L0-01 — Canonical contracts and execution setup

Delta：产品方向、接口、范围、隔离、验收和Work队列进入GitHub main。
Dependencies：Owner已决Assistant-first指令。
Scope：产品Master Plan、STATUS、DEVELOPMENT_PLAN、AGENTS、contracts、docs、planning checker/tests、专用workflow；无runtime/UI。
Acceptance：九包/唯一NEXT_READY一致；六项stable contracts完整；provider-free checks通过；仅产品边界与专用CI新增；合并后exact-SHA核验。
Negative tests：拒绝PENDING_I06生产激活、隐藏Base bypass、CoT日志许可、未知/重复NEXT_READY、缺少契约/文件、越界路径、mock/live伪标签。
Persistence/revision：只定义，尚未实现；规划本身版本化，无伪造数据结果。
Evidence：CANONICAL_DESIGN；setup checks不是cognition实现。当前执行者合并核验后停止。

## L1-01 — Event/source/state ledger

Delta：创建对话/Topic，持久保存消息与文件版本，重启可重建同一状态。
Dependencies：L0-01合入与exact-SHA planning pass。
Scope：apps/api、packages/store/contracts、migrations、tests/persistence。Python模块化API、SQLite初始backend，store可替换；添加依赖/lockfile，不要求托管服务。
Acceptance：tenant/conversation/topic IDs、source/parse versions、event history、state projection、idempotency、optimistic version；同key同payload不重复，异payload409；崩溃无半条记录或错配状态；原文/hash往返一致。
Negative tests：跨tenant/topic引用、错版本、重复retry、source与parse错配、半提交、同名人物全局合并。
Persistence/revision：事件和版本原子提交；未实现revision明确拒绝，不靠覆盖旧文本临时实现；测试DB不入Git。
Evidence：NOT_IMPLEMENTED；完成只记PROVIDER_FREE_IMPLEMENTED，不记语义理解或效力。

## L1-02 — Revision and historical dependencies

Delta：更正/撤回/替代/假设分支驱动相关状态失效，保留独立支持和历史。
Dependencies：L1-01。
Scope：packages/context/revision、migrations、tests/revision。
Acceptance：C03全部action分开；OR-of-AND依赖、来源家族去重、unknown/partial-order时间、历史查询、人物归属更正、absence dependencies；输出changed/recomputed/reused/unchanged_checked/not_evaluated。
Negative tests：撤回即否定、迟到信息倒灌人物过去、摘要自我支持、rootless cycle、撤一个支持全图失效、假设污染主分支、未检查标unchanged、source改变仍复用stale answer。
Persistence/revision：transaction revision receipt；历史source与现行解释分开；重放一致，并发冲突409；记录保守重算范围，不承诺最优增量。
Evidence：NOT_IMPLEMENTED；typed authored events验证算法，不声称自动中文分类。

## L1-03 — Privacy, expiry and correction-aware retrieval

Delta：背景使用范围可控；检索不漏已知更正/反证/撤回；stop/delete有效。
Dependencies：L1-02。
Scope：packages/policy/retrieval/store、tests/privacy；无真实数据/云凭据。
Acceptance：三套权限；TEMPORARY/CONVERSATION/TOPIC，未实现cross-topic则拒绝；临时正文无持久副本；STOP_USING立即过滤；DELETE清理source/summary/index/cache，仅留无正文tombstone；restore模拟不复活删除；expiry不生成事实否定。
Negative tests：文档授权memory write、读者权限当人物知情、topic越界、旧Explain泄漏删除内容、撤回证据通过摘要复活、只检索支持、cache绕过最新policy。
Persistence/revision：当前权限优先历史snapshot；summary/index可重建且有lineage；级联不误删独立支持。
Evidence：NOT_IMPLEMENTED；需要存储/重启测试，不以UI开关代替权限。

## L1-04 — Always-on Controller and run lifecycle

Delta：每个生产模拟输入先处理变更/范围，再回答；stream/cancel/retry有同版本回执。
Dependencies：L1-03。
Scope：packages/controller/adapter、apps/api、tests/controller/transport；mock adapter only。
Acceptance：C01/C07/C08；Direct/context/mock-selected/unresolved/failed同入口；更正+算术先更正；budget和snapshot固定；断线只重放；模型失败不丢输入；过期输出不能覆盖新状态。
Negative tests：UI/API直调adapter、无controller receipt回答、半JSON提交、重连重复调用、未知transport无限retry、权限变更后继续输出、预算0调用真provider。
Persistence/revision：event与run分离；cancel保留已提交修订；seq唯一；failed不冒COMPLETED。
Evidence：NOT_IMPLEMENTED；完成为MOCK_CONTROLLER_FUNCTIONAL，不是HCL live。

## L2-01 — Desktop Assistant shell and text/file flow

Delta：用户能创建/恢复对话、选Topic、上传文本、发送/停止/重试，默认干净聊天。
Dependencies：L1-04。
Scope：apps/web TypeScript/React、API client、styles、browser tests；走mock API，不是静态截图。
Acceptance：无HCL toggle/Compare/常驻Inspector；可折叠左栏，可读正文；TXT/Markdown/paste及原文定位；keyboard/focus/error/empty；刷新恢复；文件/长度限制如实；真实浏览器走通关键mock流。
Negative tests：上传即完整理解、重复发送、取消后拼旧流、topic错用、引用错版本、fixture心理gold喂作用户输入、截图冒交互。
Persistence/revision：乐观UI和server version reconcile；失败输入可恢复；不以localStorage敏感正文作旁路。
Evidence：NOT_IMPLEMENTED；MOCK_UI_FUNCTIONAL，browser coverage单列。

## L2-02 — Multi-session synthetic cognition and natural synthesis

Delta：多轮/多日synthetic情境延续背景、区分猜测/报告、处理迟到信息并自然回答。
Dependencies：L2-01。
Scope：packages/mock-runtime/synthesis、synthetic scenarios、integration tests；不import研究代码。
Acceptance：至少三类原创轨迹：合作信息差、目标角色、概念价值；更正+无关问题；明确scripted/mock extraction；任意未支持输入unresolved；结果从真实状态/fixture读出，不只硬编码截图；answer与registered claims一致。
Negative tests：重复猜测增独立支持、自述变真理、系统解释变原始证据、一次行为写永久人格、数字伪校准、题号路由冒泛化。
Persistence/revision：同Topic跨conversation继续；event/record time分离；关键反证进入context；summary重建保留provenance。
Evidence：NOT_IMPLEMENTED；SYNTHETIC_REPLAY_ONLY，全局mock标识，语义泛化NOT_TESTED。

## L2-03 — Explain, correction and memory controls

Delta：用户可查看真实关键依据，以轻量动作纠正人物/时间/猜测或停止使用。
Dependencies：L2-02。
Scope：apps/web Explain/context management、packages/explain、API projections、browser tests。
Acceptance：Explain绑定answer/run/snapshot；只显示记录，默认0模型调用；删除后redact；新判断新run；纠错不填JSON；临时/topic/stop/delete与后端一致。
Negative tests：旧答案用新资料补理由、隐藏来源/CoT泄漏、展开收费调用、UI删但索引留存、否认猜测仍写回、技术不确定性淹没正文。
Persistence/revision：旧answer不改但标过期；新解释关联新版本；历史遵从当前policy。
Evidence：NOT_IMPLEMENTED；mock来源/绑定忠实性，不是语义judge真理。

## L2-04 — Lab shell and integrated L2 handoff

Delta：高级用户查看真实mock run/context/operations；Assistant多轮闭环可复现，准备但不进入L3。
Dependencies：L2-03。
Scope：apps/web advanced/lab、只读run API、tests/e2e、L2 closure；不建完整research dashboard。
Acceptance：默认无实验arm；Lab只读，Base compare入口disabled且说明L3后许可；Direct/generic/mock-selected/failed清晰；验收矩阵逐项实际结果，不漏失败；停止于I06/分仓/真实接入gate。
Negative tests：Lab写生产state、mock换live标签、cache费用当总成本、研究分数当产品效力、越界访问、L2完成自动启真provider。
Persistence/revision：run/version/usage全链回放；导出无秘密和已删正文；断线/权限变化一致。
Evidence：NOT_IMPLEMENTED；完成为L2_MOCK_PRODUCT_VERIFIED_WITH_LIMITS；L3真实接入/中文真实泛化/efficacy仍NOT_TESTED。
