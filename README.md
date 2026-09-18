# Human Cognition Layer

通过**可迁移、可拔插的认知层**，提高模型对人的信念、意图、知识状态、情绪与隐含心理状态的理解。

## Research thesis

The base model is replaceable. The cognition layer is the asset.

本项目不把第一阶段目标设为微调某个模型，而是先回答一个更基础的问题：

> 在不修改底座权重的情况下，能否通过明确、可复现的认知结构，提高模型在人类心智推理任务上的表现？

## Current phase: Phase 0 — CogToM baseline

当前阶段**禁止实现 Human Cognition Layer、禁止训练模型**。先建立干净基线并人工审计错误。

1. 使用官方 [Beijing-AISI/CogToM](https://github.com/Beijing-AISI/CogToM) 评测代码。
2. 用 DeepSeek OpenAI-compatible API 跑 smoke test。
3. 再跑正式 baseline。
4. 导出逐题错误，人工分析真实 failure modes。
5. 只有在错误审计后，才设计 HCL v0.1。

上游 CogToM 固定到 commit:

`28c6781b6ea7d7ef7d491f61adc18f076f8b993c`

这样不同实验之间不会因为 benchmark 代码变化而失去可比性。

## Quick start

### Local

```bash
export DEEPSEEK_API_KEY="..."
python scripts/run_cogtom_baseline.py --model deepseek-flash --limit 20 --language zh
```

正式 baseline：

```bash
python scripts/run_cogtom_baseline.py --model deepseek-v4-pro --limit 200 --language zh
```

> DeepSeek 当前 API 与 OpenAI Chat Completions 兼容；本项目只从环境变量读取密钥，任何密钥都不得提交到仓库。

### GitHub Actions

仓库包含手动 workflow：`CogToM Baseline`。

运行前需要在 repository secret 中添加：

`DEEPSEEK_API_KEY`

之后可以直接从 Actions 手动选择模型、语言和样本数运行。结果不会 commit 回仓库，而是作为 workflow artifact 保存。

## Outputs

每次运行生成：

```text
artifacts/<run-name>/
├── raw.jsonl
├── summary.json
├── errors.jsonl
└── AUDIT.md
```

`AUDIT.md` 是人工错题审计工作表，不由 AI 自动替代人的第一轮判断。

## Research discipline

- Benchmark 原题/标准答案不进入训练数据。
- 可以根据 benchmark 暴露的**抽象失败模式**自行生成新的训练材料。
- Phase 0 只建立 baseline，不为了提高分数修改 prompt。
- 所有实验必须记录模型、prompt、上游 benchmark commit、seed、limit 和运行时间。
- API key、原始私密数据和本地 `.env` 永不提交。

Canonical state: [STATUS.md](STATUS.md)
