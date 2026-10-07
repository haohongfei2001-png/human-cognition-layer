# Expose existing goal and plan lifecycle forms

The ordinary planner policy described goals and selected plans but omitted six
existing forms for considered plans, abandoned/completed plans, abandoned/completed
goals and uncertain goals. The parser already supported these distinctions. A
model constructing native arguments should receive their actual bounded contract
instead of having to guess it or silently lose the distinction.

The contract change adds those six forms and three general qualifications to the
code-owned `PLANNER_POLICY`: consideration is not selection, goal and plan changes
are separate, and an outcome does not establish completion. The policy adds 406 UTF-8 bytes. A pre-existing long-question fixture then exceeded
the planning limit (36,297 bytes), before any call. The same planning payload is
now serialized with only structural JSON spaces removed: its parsed fields and
embedded string bytes are identical, saving 626 bytes and producing a complete
35,671-byte request for that unchanged fixture. No content is trimmed, escaped
differently, filtered or dropped; truly oversized requests still refuse.

This changes no parser, source text, routing decision,
native result, final policy, provider phase, token allowance or transport ceiling.
There is no case-specific module selection or source-format requirement.

Six provider-free tests check the actual first planning policy and exercise the
existing conditional C01 bridge with separate authored workshop examples. They
cover all six existing forms, active-goal versus plan closure, selected-plan versus
goal closure/uncertainty, complete original source delivery, unverified translation
bindings and a real native result before final delivery. Unicode, punctuation and
embedded whitespace remain byte-identical; canonical request bytes/hashes agree
and oversized planning still stops before a call. At the predecessor,
the policy exposure test fails seven assertions; the three existing-native behavior
controls already pass. The repair makes the contract discoverable, not newly
implemented. Scripted backend output is not evidence of model planning competence.

The exact runtime amendment changes only `hcl/cognition/universal_entry.py`,
preserving all 54 prior history pins and three pursuit-amendment artifacts.
Current validator references and provider-free workflow filters are retargeted.
Historical paired delivery tests verify the exact fixed policy insertion, normalize
only structural planning JSON spaces and compare every remaining value exactly.
Historical grants, paid executors, reports, scores and HCLA remain unchanged.
Source snapshots, trusted native policy/shared contexts, unresolved pursuit and
original-only citation checks retain their existing behavior.

Final case/package qualification and independent review must use this runtime,
including the added planning bytes. Exact-head/main CI records adoption. There
are zero provider calls in this repair, no demonstrated answer improvement and
no advancement of final I02-I06 evaluation.
