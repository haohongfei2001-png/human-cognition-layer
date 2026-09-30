# Product acceptance matrix

以下是待实现义务，不是已跑PASS。L0只检查规划、枚举、链接与边界。实施closure必须给command、SHA、fixture lineage、实际结果和限制。

| ID | 正向义务 | 负向义务 | 首包 |
|---|---|---|---|
| A01 | raw/source版本重启往返 | 错hash或截断仍标完整 | L1-01 |
| A02 | 幂等event/run | 同key异payload与半提交 | L1-01 |
| A03 | 有序state version | 旧标签页覆盖新更正 | L1-01 |
| A04 | 人物归属局部更正 | 全局同名合并 | L1-02 |
| A05 | 独立支持保留 | 撤回即否定/重复算独立 | L1-02 |
| A06 | absence依赖被新证据失效 | 只追正向引用 | L1-02 |
| A07 | event/record/receipt分开 | 迟到信息倒灌过去 | L1-02 |
| A08 | 假设分支 | 污染实际背景 | L1-02 |
| A09 | 临时正文不持久 | 日志/摘要/备份留副本 | L1-03 |
| A10 | stop/delete传播 | cache/Explain恢复删除内容 | L1-03 |
| A11 | 三套权限 | 文件扩权/cross-topic偷带 | L1-03 |
| A12 | 检索更正/挑战/反证 | 只支持旧结论 | L1-03 |
| A13 | 更正+2+2先更正 | Direct忽略前半条输入 | L1-04 |
| A14 | 每回答有controller receipt | 隐藏Base bypass | L1-04 |
| A15 | stream恢复/cancel/retry | 重复调用/过期覆盖 | L1-04 |
| A16 | clean chat/file/keyboard | 常驻Inspector/上传即理解 | L2-01 |
| A17 | 多轮自然修订 | 猜测固化为人格事实 | L2-02 |
| A18 | 未支持中文/指代unresolved | fixture冒泛化 | L2-02 |
| A19 | Explain当次依据可纠正 | 事后造理由/CoT泄漏 | L2-03 |
| A20 | Lab只读且Compare禁用 | 实验写生产/mock升级 | L2-04 |
| A21 | failure/unknown/cost记录 | 删除失败/未知成本填0 | L2-04 |
| A22 | 产品独立导出/运行 | research/确认/secrets导入 | L0-01及全部 |

## 原创轨迹规范

只用原创synthetic；记录source family、用途、预先固定的变化/不变义务。不得把研究失败题改名，不找外部题源。typed mock事件可在测试expected端存在，不能给未来真实模型充hidden gold。

轨迹一：合作不顺→主动联系→更正对方何时知情→撤回猜测。检查局部变化、旧视角、重复证据和无关目标。
轨迹二：临时安排变化→角色压力→较晚自述价值→撤回自述。检查context不变人格、expiry和目标。
轨迹三：同词不同reading→假设换判据→回实际讨论。检查fact/concept/value分离、假设不污染。

L4另用新的非确认材料测真实中文、多轮、合成/Explain忠实性、必要推断、反向伤害、普通任务非干扰与完整费用；不以偏好/长度/节点数/多拒答单独认定增益。
