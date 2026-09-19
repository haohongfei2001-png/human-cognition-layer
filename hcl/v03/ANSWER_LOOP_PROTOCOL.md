# HCL v0.3 Always-On Answer Loop

## Canonical pipeline

User input → Frozen HCL cognition state → Base-model draft → HCL consistency/calibration checker → Optional bounded revision → HCL final verification → Final answer

The HCL is present at every stage. A correct draft may pass unchanged, but only after the HCL checker explicitly verifies it.

## Checker violation families

- FACT_CONTRADICTION
- INFORMATION_ACCESS
- BELIEF_LEVEL
- PREMATURE_COLLAPSE
- OVER_UNCERTAINTY
- GRANULARITY
- UNSUPPORTED_INVENTION

## Bounded revision

The loop allows at most two revision opportunities: after the first checker verdict and after final verification. This prevents an unbounded self-critique loop while keeping HCL always-on.

## Portability

The semantic protocol does not depend on DeepSeek. Current transport is OpenAI-compatible Chat Completions. The same answer-loop contract can later be backed by GPT, Claude-compatible adapters, Qwen, or local models without changing frozen HCL state semantics.
