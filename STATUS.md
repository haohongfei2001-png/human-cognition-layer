# Canonical Status

## Project
Human Cognition Layer

## Current phase
**PHASE-00 — CogToM baseline + manual error audit**

## Research question
Can a portable cognition layer improve a strong language model's reasoning about human beliefs, intentions, knowledge states, emotions, and implicit mental states without modifying the base model?

## Current rules
- No model training in PHASE-00.
- No HCL implementation in PHASE-00.
- Use the official CogToM evaluator unchanged.
- Keep the upstream CogToM revision pinned.
- Benchmark items and gold answers must not become training examples.
- First intervention may only be designed after inspecting real model errors.

## Upstream benchmark
- Repository: Beijing-AISI/CogToM
- Pinned commit: `28c6781b6ea7d7ef7d491f61adc18f076f8b993c`
- License: MIT

## Baseline provider
DeepSeek OpenAI-compatible API

Initial model:
- `deepseek-flash`

## Next gate
1. Add repository secret `DEEPSEEK_API_KEY`.
2. Run 20-group Chinese smoke test.
3. Confirm pipeline and scoring are healthy.
4. Run 200-group baseline.
5. Manually audit at least 100 failed or partially failed groups.
6. Only then decide whether PHASE-01 (HCL v0.1) is justified.

## Status
**BLOCKED_ON_SECRET**

No API key is stored in this repository.
