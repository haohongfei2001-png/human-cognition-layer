# Boundary decision and research isolation — ADR 001

## Adopted decision

长期采用研究仓库 `human-cognition-layer` 与产品仓库 `hcl-assistant` 分离。研究负责 cognition runtime/evaluation/evidence/I02–I06；产品负责 UI、API、Controller product layer、persistence、Explain、Lab 和产品测试；以 versioned permitted runtime artifact 接入。

当前工具事实：已列出本连接可见仓库，没有适合复用的 HCL Assistant 仓库；GitHub connector 无 create-repository action；备用 Remote Desktop 调用明确因月度额度暂停，未重试或重连。未创建新仓库。

为完成 owner 允许的 planning/application-boundary 交付，当前 canonical 放在 `products/hcl-assistant/`。根研究控制面不改动。产品可独立构建，不导入研究模块。**同仓目录不是物理仓库/ACL 隔离，不能宣称已完成。**

## Enforced now versus planned

现在可验证：只新增产品文件与产品专用 workflow；planning CI 仅获取指定产品树的 blobs（无研究正文 checkout）；验证进程无 provider/eval 凭据；synthetic 之外无输入；结构验证阻止越界链接与不允许的状态声明。

仍未建立：独立仓库 ACL、生产身份/存储权限、网络 sandbox、真实数据隐私认证、真实语义增益。只读内容过滤和 AGENTS 规则不是密码学访问控制。

L1/L2 允许 mock/provider-free 工程。涉及真实用户数据、provider 凭据、公共部署或 L3 的包必须先物理分仓，不得以本 ADR 代替该 gate。

## Allowed share

只允许 runtime version、稳定 interface、capability disposition、limitations、经批准的通用实现改进。L0 不复制任何研究源代码或数据；研究 baseline 仅保存提交/路径/hash 与范围结论。

禁止 confirmation source/gold、受保护 artifacts、eval credentials、封存 LongMemEval，禁止从已消费/确认案例导入示例、同构改名材料或针对 outcome 调 prompt。产品 feedback 与 frozen evaluation 单向隔离；只向研究治理提交用新原创材料重现的通用问题，不直接改其冻结契约。

## Build/data/process boundaries

产品目录有自己的 docs、contracts、tests、store（未来）、lockfiles（实施时固定）。所有数据与 cache key 包含 tenant/conversation/topic/perspective/policy/version；Lab arm store 与 Assistant store 不互相写入。

产品 workflow contents:read，无研究 secrets，无 pull_request_target，无 paid/workflow-dispatch 研究动作。只 materialize product tree 并验证 blob hash；拒绝 symlink/submodule/path traversal。获取 tree metadata 不读取其他树正文。测试进程只得到产品工作目录，不得到凭据；root workflow 的读 token 仅在产品物化步骤使用。

已有研究 CI 可能按原有事件运行；不修改其 triggers，也不把它的结果替代产品 gate。产品运行时/包不得调用研究 runner。

## Physical migration procedure

有合法创建能力后先核验目标存在与否，避免重复；新建默认 private、不得把现有 private 资产改 public。导出产品目录到空产品根，排除运行缓存、数据、secrets 与全部研究 Git history；移植产品专用 CI，更新其目录入口。将新仓库 main 与完整 product-content digest 比较、跑 exact-SHA provider-free checks。当前目录保留一次只读迁移指针，不双 canonical、不双 writer。

迁移只改产品承载地址，不改 contracts、NEXT_READY 的行为义务或研究计划。未能创建时允许继续 synthetic L1/L2，禁止将未完成标 COMPLETE。
