# Product Work Contract

适用范围：仅 `products/hcl-assistant/**`；独立导出后适用于导出根。唯一目标：实现 adopted HCL Assistant 产品，不重开产品定位讨论，不接管研究 I02–I06。

## Start and writer ownership

读取本目录 README、STATUS、DEVELOPMENT_PLAN、Master Plan、contracts 和工作包。检查远端 main 与产品路径相关 PR（只读 metadata/本产品 patch）。同一产品边界一次仅一个主 writer；已有进行中认领不得平行实现。使用 `product/hcl-assistant/<package>` 分支和一条 PR 描述认领；一次会话结束写交接。研究 writer 可继续研究边界，产品 writer 不改其文件。

当前 setup 执行者：L0 合并/核验后停止。后续专门 Work：从 L1-01 连续推进已满足依赖的 L1/L2；普通 schema/UI/测试/CI/merge conflict 自行处理，不逐包问 Owner。

## Hard boundaries

- 允许写：本产品目录；必要的 `.github/workflows/hcl-assistant-planning.yml` 产品专用 CI。不得修改根研究 STATUS、DEVELOPMENT_PLAN、Master Plan、hcl/、eval/、reports/、scripts/、tests/ 或其他研究 workflow。
- 不读取 confirmation sources/gold、protected artifacts、研究 credentials、sealed LongMemEval。不要全仓 archive、遍历正文或运行研究脚本。
- CI/runtime 只使用产品导出树；无 `../../hcl`、symlink、submodule、动态读取研究目录或工作目录向上扫描。不能把目录隔离称为 repository ACL 隔离。
- L1/L2：synthetic/mock only、provider transport budget=0、no deployment credentials、no real user data。无真实语义接入、付费模型比较或外部 onboarding。
- 所有生产模拟路径也必经 Controller；Base-only 仅 Lab 实验模式，不写回生产 context。mock 永远明确标记，不改标签冒充 live。
- 失败测试不得删掉/降标为通过；保留 observed failed/refused/unresolved，修 bug 或记录真实阻塞。
- 禁止私有 chain-of-thought 收集/展示。记录显式结果与 provenance，不索取/持久化 provider hidden reasoning。

## Working without owner desktop

不要依赖 Owner Terminal、Desktop Commander、浏览器登录态或本地仓库。用云端 Work / GitHub 操作。支持只获取产品树；若工具只能提供包含受保护研究内容的全量材料，停止该读取并使用产品路径接口/允许清单导出，不绕开限制。

## Verification and merge

在产品根运行 `python3 scripts/check_planning.py` 与 `python3 -m unittest discover -s tests -v`；实现后增加对应 behavioral/browser tests，不以 planning tests 代替。每包需正向、负向、修订/持久化、历史回归证据与具体 DELTA。PR 写文件范围、actual tests、NOT_TESTED 和下一包；等待真实 exact-head 结果而非造 receipt。合并前复核 main 与冲突，合并后核验 exact-main/product-content。研究其他更新可以使全仓 SHA 前进；必须记录实际测试 SHA，不谎称后续 main 已认证。

禁止 force push、跳过失败 CI、重置并发研究提交。外部 runner 故障不能假装成功；如无法核验，保留分支/PR 和精确未验事实。

## Continuation and stopping

依赖安全的 NEXT_READY 存在即继续；外部权限/费用/许可阻塞记录 DEFERRED_EXTERNAL，推进无依赖包。不造 filler、不按 PR 数量衡量推进。L2 完成且 L3 gate 未满足时 STOP_WITH_HANDOFF。真实接入不得把 I06 的局部证据扩为所有语言/领域已验证。

## Migration

目标独立仓库 `haohongfei2001-png/hcl-assistant`。仅在有真实建仓能力时创建，默认 private；不得复制研究 Git 历史、数据、tokens 或 workflows。只导出产品允许树，重新核验 tests/digest，再建立唯一 canonical pointer，防双写。当前分仓未完成不阻塞 synthetic L1/L2，但阻塞 real-data/production/L3。
