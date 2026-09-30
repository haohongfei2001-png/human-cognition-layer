# Stable Product Contracts v1

状态：ADOPTED_INTERFACE / NOT_RUNTIME_IMPLEMENTATION。字段是产品契约，不是研究Python API的别名。机器枚举与必需字段在catalog.json，候选能力在capabilities.json。L1必须验证行为，不以字段存在代替语义正确。

## C00 Common envelope

每个对象：schema_version=1.0、opaque id、server-owned tenant_id、created_at。版本对象有integer revision>=0。时间为带时区ISO8601；未知语义时间保留null/偏序，不用入库时间补造事件或人物获知时间。ID不是权限凭据。

破坏含义需要major version及迁移；新增optional字段可minor。旧run保留schema/runtime/config身份。客户端提供的tenant、verified、activation不具有验证权力。

## C01 Interaction Controller Contract

唯一生产入口handle_interaction(request)。API只认证、解析、限额并调用Controller。生产model adapter必须持server-issued run authorization；无frontend-to-provider路径。

Request必需字段：
- event：UserEvent；message/upload/revision/control/retry，原始内容或授权source ref，正文不是控制指令。
- scope：server tenant_id、conversation_id、topic_id(nullable)、branch_id、perspective_id(nullable)。
- expected_state_version：integer>=0，乐观并发，不可last-write-wins丢更正。
- allowed_memory_scope：TEMPORARY/CONVERSATION/TOPIC/EXPLICIT_CROSS_TOPIC；服务端验证，文件无扩权权力。
- source_refs：source_id/version/content_sha256列表；旧版本不能绕过新撤回。
- model_resource_policy：model/adapter、call/token/cost/latency limits、retry policy；L0–L2 max_provider_calls=0。
- idempotency_key：绑定tenant+conversation+规范化payload hash。

Result必需字段：run_id、state_version_before/after、accepted_change_ids、invalidated_state_ids、selected_context、route、selected_capability_ids、answer_preparation(nullable)、explain_projection(nullable)、operation_receipts、run_receipt、unresolved_updates、errors。

route为DIRECT/CONTEXT_ASSISTED/SELECTED_COGNITION/BOUNDED_RESPONSE/CLARIFY/BLOCKED。先处理输入变化，再决定回答任务；更正+算术不能跳过更正。无法解析的更新保留unresolved，不声称任意文本已全部理解。

同key同payload返回同event/run；同key异payload返回409；显式retry新attempt但不重复input/revision。expected version不符409且无部分写入。合法事件提交后模型失败，事件保留，回答标失败，不回滚已确认更正。发布前再检查最新权限/stop-using；旧回答不能覆盖新状态。未知transport结果记UNKNOWN，不盲重试。

## C02 Context Contract

ContextRecord字段：record_id、tenant_id、conversation_id、topic_id?、branch_id、kind、content、subject_refs、source_refs、origin、epistemic_status、valid_time、recorded_at、disclosure_time?、person_access_events、retention_policy、reuse_policy、provenance_roots、support_groups、challenges、assumptions、read_dependencies、revision、lifecycle_status。

kind严格区分：
- USER_REPORTED_EVENT：用户报告的事件，不自动认证世界事实。
- USER_GUESS：用户解释/猜测，重复不升级。
- CHARACTER_SELF_REPORT：人物何时向谁表达；表达不等于私人真相。
- THIRD_PARTY_REPORT：保留转述链，不抹掉中间归属。
- SYSTEM_INTERPRETATION：有前提、反证、替代的系统解释，不是新独立来源。
- HYPOTHETICAL：分支条件，不写回实际世界。
- CONDITIONAL_RULE：给定/明确采用/来源报告的条件规则，保留origin/applicability。
- CORRECTION：指向旧记录的更正事件，不覆盖历史字节。
- RETRACTION：撤回支持，不断言原命题为假。

用户自报感受按体验尊重；对他人动机仍保持解释身份。kind含糊保留候选与UNRESOLVED，不强选确定类别。

origin为direct_user/uploaded_source/system/tool；只有认证用户控制命令可调整允许的记忆范围。tool结果仅对声明条件负责。

support_groups是OR-of-AND组；一组共同必要，多组替代。provenance_roots去重原始来源家族；摘要、复述、同文镜像不增加独立证据；rootless cycles不成立。read_dependencies包括读过的来源集合、版本及absence query，保证新增反证也触发失效。

epistemic_status：REPORTED/CONDITIONAL_SUPPORT/CHALLENGED/CONFLICT/UNRESOLVED。lifecycle_status：ACTIVE/STALE/SUPERSEDED/RETRACTED/STOPPED/DELETED。运行成功不是语义真。

SourceRef：source_id、version>=1、sha256、exact span(start inclusive/end exclusive)或message/line locator；程序核验位置，近似引用不充exact。source原文版本与parse版本分别存储。权限过滤先于提取/检索/模型。

ContextSelection：scope、state_version、source_versions、record_ids、correction_ids、challenge_ids、retraction_ids、assumptions、missing_scope、coverage、content_digest、policy_revision。coverage为FULL_WITHIN_DECLARED_SCOPE/PARTIAL/UNAVAILABLE；上传成功不是理解完整。

检索旧判断必须带有效更正、挑战、撤回及来源状态闭包。超限不只留支持，扩大可靠重算范围或明确有界拒绝。cache key含tenant/topic/perspective/time/policy/state/source/runtime/query/model/config。

## C03 Revision Contract

RevisionCommand：action、target_ids、expected_state_version、reason(nullable)、new_content/source_refs(按action)、effective_time(可未知)、request_actor、idempotency_key。目标含糊澄清，不改所有同名对象。

ADD：增加来源/记录，检查旧结论和absence dependencies，不强行覆盖。
CORRECT：旧记录有误，创建successor/source version；历史可回看，现行依赖失效。
RETRACT：撤回支持，保留关系；不是否定；独立支持仍可保留。
SUPERSEDE：从有依据的effective time起新状态替代旧状态；旧时段保留，不自动表示过去记错。
HYPOTHETICAL_BRANCH：从snapshot分叉，不并入实际背景。
STOP_USING：立即禁止目标及可恢复其内容的派生物进入后续context；原文仅在用户仍允许历史保存时保留，Explain受当前权限约束。
DELETE：删除正文及可恢复派生物/索引/cache；只留必要无正文tombstone。备份恢复必须重放删除，不复活人物印象。

RevisionReceipt：new_state_version、changed_ids、invalidated_ids、recomputed_ids、reused_ids、unchanged_checked_ids、not_evaluated_ids、unresolved_ids、deletion_status。未检查不等于不变；语义相同不等于未重算。先保守失效实际读依赖，再重算，不承诺最优细粒度。ACL撤回优先历史回放；旧答案不重写，更新是新run。

## C04 Answer Synthesis Contract

AnswerPreparation：snapshot_id、valid_context_refs、operation_output_refs、main_judgment(nullable)、claim_bindings、alternatives、material_uncertainties、assumptions、forbidden_promotions、response_intent、length/style_policy、coverage、resource_remaining。

只用当前有效context和显式operation outputs。Direct算术/一般知识可受控生成，不表示必须先保存所有世界知识；不得借此新增未记录的人物心理/动机/价值事实。新的解释先登记SYSTEM_INTERPRETATION并按同一来源约束检查，再以假设表达，否则删除主张。

先给可支持的实用判断，不强选真实原因。会改变结论/行动的material uncertainty进入正文；次要技术细节进Explain。不可机械输出全状态，也不可一律拒绝推断。

AnswerRecord：answer_id、run_id、snapshot_id、text、claim_bindings、citation_refs、material_uncertainties、coverage、published_at、status。引用/格式检查不是语义真理。历史答案不自动变supporting evidence，后续引用保留SYSTEM origin。

## C05 Explain Projection Contract

输入只接受该answer/run已记录的claim_bindings、context/operation refs、版本与policy，不重调用模型猜当时理由。

输出：answer_id、run_id、snapshot_id、known_information、judgment_basis、alternative_explanations、uncertainties、key_premise、discriminating_information、source_links、recorded_at、redactions。每项指向记录，未记录理由省略/标未记录。

旧Explain使用当时依据，不用今天证据洗白旧答案；新分析是新run；当前权限/删除可返回REDACTED/UNAVAILABLE。不展示或存储私有chain-of-thought/raw reasoning为产品思维过程。

## C06 Capability Manifest Contract

稳定capability_id不绑定研究包编号。每项必需：capability_id、contract_version、supported_input、language、scope、output_objects、limitations、runtime_implementation、i06_disposition、product_activation_policy、evidence_status。尚未接入runtime=null，语言空数组表示未认证覆盖；planned_languages不是实测语言支持。

Disposition：PENDING_I06/RETAIN/SIMPLIFY/GENERICIZE/DISABLE/REPLACE/INCONCLUSIVE。
Activation：MOCK_ONLY/DISABLED/EXPERIMENTAL/SCOPE_DEFAULT。DISABLE不得active；PENDING_I06不得production active；RETAIN仍需产品范围/语言/适配验证。selected/executed/output/used/cache分别记录。不兼容语义需major版本，不因实现替换重命名一切。

## C07 Run / operation / stream / cost

RunReceipt：run_id、attempt_id、parent_attempt_id?、surface(ASSISTANT/LAB)、controller_receipt_id、snapshot_id、state_versions、source/config/runtime hashes、mode(MOCK/REAL)、route、capabilities、operations、outcome、usage、errors、started/finished_at。

Outcome：COMPLETED/PARTIAL/UNRESOLVED/FAILED/REFUSED/CANCELLED/UNKNOWN。gain_assessment默认NOT_ASSESSED，有执行不表示有收益。OperationReceipt：operation_id、capability_id?、input_versions、read_dependencies、output_ids、status、cache_status、model_calls、usage_refs。

每次调用记录provider/model/request_id、input/output/reasoning token(未知null)、cost amount/currency/source、latency、finish_reason、timeout/cancel。mock provider_calls=0，不能将adapter invocation算paid。真实费用未知不能填0，估算与账单分离，不保存hidden reasoning正文。

Stream：run.accepted、state.committed、operation.completed、answer.delta、answer.completed、run.failed、run.cancelled；seq单调，含run_id/state_version。last-event-id只重放，不重触发模型。结构化state只在完整验证后提交，不把半段JSON当人物状态。

## C08 API surface

POST /v1/conversations；POST /v1/topics；POST /v1/conversations/{id}/events（消息/更正/控制均入Controller）；GET /v1/runs/{id}/events；POST /v1/runs/{id}/cancel；POST /v1/runs/{id}/retry；POST /v1/sources（上传注册无正文赋权）；GET /v1/answers/{id}/explain；GET /v1/context；delete/stop-using提交RevisionCommand。

400格式、401/403权限、409version/idempotency、413输入范围、422无法处理语义、429quota。系统失败不得伪装成功。分页opaque cursor，读取按当前权限/reuse过滤。

## C09 Memory and privacy

TEMPORARY：正文不进持久索引/日志/备份；L1进程内临时store，重启丢失要明示。CONVERSATION仅本会话；TOPIC仅显式成员；EXPLICIT_CROSS_TOPIC后期逐项授权，L1/L2拒绝未实现扩权。

真实tenant access、人物perspective access、persistence/reuse独立。文件/tool只有数据权力，不能memory-write或改policy。stop/delete涉及摘要、embedding、缓存、分支与Explain导出。未来provider日志保留由实际政策披露，不承诺无法执行的远端删除。

## C10 Research import gate

L0–L2无研究Python import，无provider transport。L3只接approved artifact、exact digest/interface/disposition/limitations，无confirmation/eval/sealed资产。普通输入接入、合成忠实性、中文多轮验证分别记录，不继承研究效力标签。
