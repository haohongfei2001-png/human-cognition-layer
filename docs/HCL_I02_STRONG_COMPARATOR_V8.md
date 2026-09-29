# I02 strong comparator candidate v8

**Status:** provider-free candidate; C/P/G model semantics and independent
sources remain unqualified. No provider calls, no new budget, no H efficacy
claim. Historical v1–v7 prompts, executions and closures are unchanged.

The KPU development closure found a P `source_citations` entry with a `quotes`
array, while the frozen semantic scorer accepts one exact `quote` (or
`quotation`) per citation. `scripts/serious_eval_arms_v8.py` now gives C, P,
and G-final the same explicit final citation shape: each citation has exactly
`source_id` and one exact `quote`. This is a prompt contract repair, not proof
that a model will obey it. The same complete ordinary question and source,
answer fields, and v7 G map policy remain available. Invalid G source quotes
still fail closed.

I01 also requires a **strong native C** with a reasonable reasoning budget.
Earlier development calibrations intentionally disabled thinking and cannot
qualify that comparator. The new `call_spec_v8` returns an explicit candidate
DeepSeek V4 Pro configuration with thinking enabled, high reasoning effort,
JSON output and an 8,192 generated-token ceiling. C, P, G-map and G-final use
the same native setting; G retains its separately charged map call. The
provider's [Thinking Mode guide](https://api-docs.deepseek.com/guides/thinking_mode/)
documents the toggle and effort field, and its
[Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
documents JSON output and token limits. The candidate omits temperature
because the provider says it has no effect in thinking mode.

**EVALUATION_DELTA:** the comparator builder now produces a concrete strong
native call candidate and scorer-compatible final citation instructions for
all answer arms. The ordinary-input positive witness, unsupported-motive
rejection, exact-source citation check, G workspace composition and v7
historical boundary run provider-free in `tests/test_v1_i02_comparator_v8.py`.
**HCL answer CAPABILITY_DELTA:** none. I02 must still qualify unexposed,
rights-clear independent source systems, confirm native question validity,
establish C/P/G model semantics and freeze costs/latency before I03. An 8,192
token ceiling is a candidate safety bound, not a sample-size or cost freeze;
no one-use trigger or provider grant was created.

**NEXT_READY:** `I02_UNEXPOSED_SOURCE_QUALIFICATION`.
