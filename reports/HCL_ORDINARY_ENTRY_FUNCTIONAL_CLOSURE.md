# Ordinary-entry functional confirmation — FAILED / CLOSED

One authored operational smoke, not efficacy or independent evidence.
Run [36527863771](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36527863771),
SHA `17d6ab1d9be93b51fee97383e25c68aed0c0703c` (E03 PR #184).
All six exact-head and exact-main correctness workflows passed (main v1 36527785182).
The separately dispatched functional job failed after one extraction call.

## Source-first finding

The response parses as JSON, but speech quotes contain literal extra backslashes
and supplied offsets do not match source spans. The strict anchor gate raised
`quote_offset_mismatch`. No source span was silently repaired, no candidate was
promoted, and no final model call occurred. The authored provider-free preflight
passed; it is not evidence that real extraction passed. No end-to-end functional
success or capability efficacy is established. G-ARCH live-entry remains unmet.

Raw request/response, package and provider-free preflight are under
`HCL_ORDINARY_ENTRY_FUNCTIONAL_36527863771/`; `source-first-audit.json` verifies
quotes and offsets without any provider call. Future entry work should use local
anchoring/explicit source identifiers rather than relying on model-computed byte
positions, while retaining ambiguous-anchor refusal. Do not reopen this run.

## Receipt and closure

- Actual model returned: `deepseek-flash`; one call, zero retries, no final call.
- Usage: 429 input, 532 output, 961 total; zero cache hits.
- Peak-rated USD **0.00076710**; cache/time estimated USD **0.00038355**.
- Conservative guard accounting USD **0.002673**; invoice cost unavailable.
- Fresh USD 0.30 allocation closed; remaining authorization **0**, no transfer.
- Workflow disabled after this first dispatch; no rerun or repeat dispatch.
- Package canonical hash `34c400d591239a1851580ef7d5f724ef010eeae157dc5fdd0e88236b5d53ffd4`.
- Runtime hash `20c2ea1c197b218d3aebd42f831d40d42dc0b8f34f949b6e719cc91c3df0b436`.
- GitHub artifact 11015477045 SHA256 `d1b97cd67835c191de8f02011f2ae3edfe35d7eb2c94198aec3ed10e77589b23`.
- Raw receipt file SHA256 `74a8312a260f345a7d072e1035289b9a7873168c5af6fad442bba522151ea200`.

Historical CG grants and dispositions unchanged. LongMemEval SEALED/NOT_ACCESSED.
Continue provider-free E04 and the dependency-safe construction queue.
