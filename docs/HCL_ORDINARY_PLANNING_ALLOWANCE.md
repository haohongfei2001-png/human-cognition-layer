# Fixed ordinary planning completion allowance

The ordinary DeepSeek port now reserves and requests 16,384 completion tokens for
planning, with enabled/high thinking. Final answers remain at 8,192, complete
requests at 36,000 UTF-8 bytes, and visible planning JSON at 32,000 characters.
There is no retry, automatic escalation, source truncation or bypass of mandatory
native HCL execution. The complete-source prompt and all native/citation rules
are unchanged. An allowance sized for the former request cannot silently fund the
larger one: exact-request admission occurs before the SDK sends anything.

The former 4,096 value originated in the initial bounded metered port, commit
`fb54b186634a3c22c1938c227f1aa4dd4ec41682`; it was a local chosen allowance, not
a provider maximum. The [October 7 failure](HCL_RELIABILITY_20261007_RESULTS.md)
used all 4,096 completion tokens and never reached native execution or a final
answer. It does not reveal private reasoning allocation or prove every 4K input
must fail. Older diagnostics completed one source-planning request at 16,384
with 5,667 completion tokens, but on a different runtime and without proving
current native treatment or response quality.

Official documentation checked on October 7 states a thinking-mode default of
64K (128K at max effort), accepted max_tokens up to 393,216, and enabled/high as
the ordinary thinking default. The selected 16K remains an explicit bounded local
configuration rather than adopting a potentially much larger provider default.
It keeps reasoning effort stable; disabling thinking or changing to low would
introduce a different unverified quality tradeoff.

- [Official Chat Completions parameters](https://api-docs.deepseek.com/api/create-chat-completion/)
- [Official thinking-mode controls](https://api-docs.deepseek.com/guides/thinking_mode/)
- [Official CNY prices](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)

At the existing conservative input bound of `2 * request_bytes + 2048`, maximum
36KB requests and CNY 9/27 per million input/output tokens, full phase holds are
CNY 1.109664 for planning and 0.888480 for a final answer. These are authorization
bounds, not invoices. The ordinary USD reservation uses its unchanged published
reference rates and now includes all 16,384 output tokens plus the existing
32-token margin. Usage beyond the phase's bound remains rejected. Known rejected
responses preserve safe enum/count/validated-cost facts, never private content.

Offline tests establish the fixed request, exact reservation, sufficient valid
completion handling, old-budget refusal, unchanged final limit and stop-without-
retry behavior. They do not show that a real model will finish planning, execute
useful HCL operations or preserve all answer facts. The failed 4K package, executor,
case/rules, results, review and closed grant are immutable. Its 98 historical executor tests plus 15 legacy metered-port tests
run at the exact closed baseline using the existing isolated, network-disabled
history-replay pattern; current runtime tests validate this new allowance.

Any real repair-validation run needs a new bounded authorization and a separately
frozen package. The old CNY 12 experiment is closed and cannot fund another try.
