# HCL v0.5 LongMemEval C/D/G provider-free execution package

Status: **PROVIDER-FREE PREFLIGHT PASS / PAID EXECUTION NOT STARTED / SEALED 32 UNCONSUMED**

## Candidate and checks

- Candidate code head: `8a0ee63e4d6a3a3fe89033e979df68ce3858933f`
- C/D/G provider-free preflight run `36101999945`: SUCCESS
- Preflight artifact `10848579774`, ZIP SHA-256 `044bd96ab776b77bfe87b3e157b127fc3e4be681c7892deea30b56f3e299fd1e`
- v0.5 Current Stance Core run `36101999992`: SUCCESS
- v0.4 Minimal Slice run `36101999856`: SUCCESS
- Local provider-free unit checks: 9/9 passed; the same suite ran in cloud preflight.
- Pinned cleaned-S verified again: 32 selected histories / 15,601 events / 2 abstention IDs / zero provider calls.
- Pinned official `evaluate_qa.py` Git blob `4732f3772b04a2b9069121ade304e6320494abc2` verified in cloud; judge model ID frozen as `gpt-4o-2024-08-06`.

## What is implemented

- A full-history D/G ingestion barrier before question or oracle evidence release.
- Equal answer-time oracle session packet and identical common C/D/G answer messages.
- Canonical v0.5 D; generic entity/attribute/value G with deterministic 16,000-character budget, deterministic compaction, one bounded schema repair, and terminal failure instead of silent event loss.
- Frozen 30,000-character common answer packet and 256-token answer limit.
- First-attempt GitHub Actions guard plus a one-shot nonce for paid answer execution. No workflow currently supplies the nonce.
- Raw C/D/G answers checkpointed per arm; attempted IDs remain marked consumed if execution fails.
- Separate official-judge stage that checks complete frozen raw answers and official source blob before scoring; partial judge output is checkpointed.
- Provider-free paired summary with exact two-sided McNemar, fixed-seed paired bootstrap, abstention flags, costs, and claim-gate checks.

The code has not been exercised against a paid DeepSeek, OpenAI judge, or second-family endpoint in this milestone. The provider-free suite verifies structure and deterministic boundaries, not provider response quality or external efficacy. The old internal G failure is addressed at the mechanism level by deterministic compaction and terminal failure, but its real provider failure rate is unknown until a frozen run.

## Outstanding prerequisites

The sealed run remains gated by the frozen contract:
1. exact-head one-shot workflow and immutable artifact handling for the raw answers and judge outputs;
2. verified access to the official judge model and a second independent base-model family (Qwen remains a candidate);
3. a bounded paid cost commitment for at least 15,601 D and 15,601 G event updates plus answer/judge calls;
4. provider-free request-shape validation of the selected second-family endpoint and exact-main certification.

The 971-event diagnostic extrapolates to roughly 58.34 million D input characters and 3.45 D provider wall hours, excluding G and all answer/judge work. Characters are not billable tokens; actual prices and caching can differ. No new account, credential, billing change, or selected provider run was initiated here.

**Gate: HCL_V05_LONGMEMEVAL_CDG_V01_PROVIDER_FREE_PACKAGE_PASS_PAID_PREREQUISITES_OPEN**
