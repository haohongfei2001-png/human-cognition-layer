# HCL I02: proposed one-call planning diagnostic

Status: COMPLETED DIAGNOSTIC / GRANT CLOSED. The newly approved one-call grant
(owner response Sentinel_f17fe125465081918e221f0c9c2a6020) was used exactly once.
The active workflow is removed; frozen executor/package remain historical evidence.
The prior18-call grant also remains closed.

## Observed diagnostic result

[Run37027133992](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37027133992)
completed its executor/encryption workflow. The private verified receipt records
one failed planning invocation: `INCOMPLETE_ANSWER_NO_RETRY`. Workflow success
means the diagnostic and private delivery completed, not that planning succeeded.

The adapter accepted the model identity and positive bounded usage, then rejected
the single-choice/finish-reason completeness check. The exact finish reason and
choice count were not retained. Token exhaustion is a possibility, not an observed
fact. No valid plan was obtained; no Base, answer or retry call was made. This
result cannot retroactively identify the earlier run's cause.

The full USD0.04293432 reservation remains held because actual usage-rated cost
was not retained. No invoice cost is asserted. Both package and recipient were
verified during local decryption of the encrypted artifact; no raw output is
published. [Sanitized receipt](../reports/HCL_PLANNING_DIAGNOSTIC_RESULT_20261002.json).
The grant is CLOSED_NO_TRANSFER_NO_RETRY with zero remaining authority. Any further
paid diagnosis needs a new approval; the subsequent offline repair now
preserves bounded finish-status and numeric usage metadata without raw responses.
It retains known usage-rated cost on rejected completions only when positive bounded
counts pass validation; malformed/unknown usage still retains the full hold.
Unknown finish strings map to OTHER_OR_MISSING. Incomplete plans remain rejected.
No historical receipt is changed or retroactively upgraded.

## Historical frozen proposal

The previous comparison stopped after its first H planning invocation, with an
unresolved generic backend/journal failure. This bounded proposal repeats only
the exact failed request, not Base or the H final answer. It is an operational
diagnostic and cannot establish efficacy, six-case completion, or the original
failure's precise cause.

The frozen request SHA256 is
`ac155023d233e7806ba3ab4e015cd3a5d16fe1d5a27ed999903a635c095ef5b8`:
9,047 UTF-8 serialized bytes, the same source-free Chinese question, current
capability inventory and original planning contract. No expected answers or
private data are added. DeepSeek V4 Pro, enabled/high thinking, planning output
4,096 tokens, 32-token accounting margin; input bound is twice request bytes plus
2,048. The frozen peak reservation is USD0.04293432. Proposed NEW authorization:
maximum one call and USD0.05, no transfer from a prior grant.

Both SDK and caller wait are bounded at180 seconds; SDK retries are zero.
The exact request and reservation are durably journalled before invocation.
Only one planning allowance exists. Every terminal result closes all remaining
permission. A timeout retains possible in-flight cost and does not promise
provider cancellation. Repeated output directories and later workflow invocations
are rejected. Manual and exact-marker routes share a paginated earliest-run gate.
The marker binds the reviewed parent commit, package and new grant and must be the
sole changed file. Any future activation requires independent review, exact-head
provider-free CI and the separately approved READY grant.

A successful content response is privately retained and checked against the
existing plan schema without executing selected capabilities or calling an answer
model. A schema rejection is distinct from a fixed allowlisted adapter failure.
Only validated numeric usage can produce a usage-rated cost; unknown usage retains
the full hold. Raw provider exceptions and protected reasoning are never saved.
The workflow uploads only the same reviewed RSA-OAEP/AES-GCM encrypted envelope to
the pinned public recipient; private decryption material remains outside GitHub.
Public summaries may contain safe codes, hashes and accounting, never raw outputs.

Any fresh result describes this new call only. It cannot retroactively identify
the previous failed call's cause, establish planner quality across domains, or
finish I02's original development comparison goal.
