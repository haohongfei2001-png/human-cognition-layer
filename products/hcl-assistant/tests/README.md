# Evidence boundary

`test_planning.py`只测L0控制面完整性、状态声明、契约区分、路径与adoption gate。它不测试真实cognition、自动语义分类、persistent store或完整browser体验。当前仅28项planning测试；L1/L2必须增加对应实际behavioral tests，不能以这些静态检查代替。

发布的capability JSON Schema可供标准Draft2020-12工具验证；当前stdlib checker是针对产品契约的定向验证，不冒充通用JSON Schema引擎。运行记录必须注明检查范围。
