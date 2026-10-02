# HCL I02: one approved universal development comparison

The owner approved a new maximum USD 2.50, 18-call batch on 2026-10-02, after
executor verification. This is a new grant; no closed historical balance is reused.
No calls have occurred in preparation. Activation and execution require the frozen
package, exact grant, first main workflow invocation/attempt and all local/hosted
verification. The current capability integration remains partial.

## Fixed task mix and fairness

Six constructed human-domain tasks were authored and fixed before any model
outputs: no-source Chinese society analysis, public belief-report change,
communication receipt versus availability, competing action explanations,
conditional responsibility, and contextual values across two sources. They are
functional development checks, not independent external generalization or final
confirmation. Unsupported/gap cases stay in the batch; there is no capability-
trigger selection, replacement, post-output task edit, or automatic rerun.

Base and H receive the same complete original question/source content and common
JSON answer/source-inference contract, on the same model and answer token limit.
Base is a separately labelled comparator. Every H input enters UniversalHCL;
its internal model planner selects capabilities from the current A–H inventory.
No source metadata specifies a module route. Private states, values and moral
truth are never established by reported claims. Missing treatment remains an
observed outcome. The no-source answer is unsourced model analysis, not supplied
evidence. Planner/answer framing and added H costs are disclosed.

Five cases have frozen exact-option scoring, with explanation/citation support
reviewed separately. The open-ended Chinese case has a predeclared qualitative
rubric and no invented numeric accuracy/gold. Correct options do not certify an
explanation. Raw answers and failure states remain unchanged; source-first findings
cannot rewrite the frozen scores or become a causal efficacy certificate.

## Calls and conservative cost

DeepSeek V4 Pro, enabled/high thinking, existing provider/default tier. Six Base
answers, six H plans, six H answers: **18 calls maximum**, zero model graders,
zero extraction calls, zero retries. Planning output max4096; answering max8192;
32-token usage margin. Every full request is bounded at36,000 UTF-8 serialized
bytes, with input reserve2×bytes+2048. Peak rates USD1.32 input /3.96 output per
million tokens were verified from the official provider page on2026-10-02.

Maximum reserve per planning call USD0.11409024, per answer USD0.13031040;
all18 worst-case reservations **USD2.24826624**, below the approved USD2.50 cap.
Usage-rated peak amounts are conservative accounting, **not an invoice**; cached
or off-peak prices may differ. Physical model snapshot behind the returned alias
is not certified. Every actual serialized request and request hash is persisted
before transport. Dynamic H final inputs cannot be known before planning; the
builder/runtime, source, schema and hard byte/token/cost bounds are frozen first.

## Executor and failure gates

The caller-owned SDK client must target the existing official DeepSeek endpoint,
use max_retries=0 and finite inactivity timeouts. The port snapshots the exact
quoted message list before handing it to the SDK. Nonempty JSON requires positive,
consistent bounded token usage; impossible/missing usage preserves the full hold
as unknown. Only final content and numeric usage leave the port; protected
reasoning fields, debug bodies and raw exception text are excluded.

A daemon supervisor limits caller waiting to180 seconds. Timeout closes that
port, preserves a possibly in-flight call/reservation and **does not claim provider
cancellation or a refund**. The batch stops on any failed/unknown call. New call
admission stops after30 minutes; the job has a35-minute hard limit. The single-run
ledger uses atomic replacement and file/directory fsync before transport. Deadline,
19th-call and USD-cap refusals admit no new call. Existing output-directory refusal
and the workflow’s first-invocation/attempt gate prevent automated replay. Every
terminal result closes remaining authorization, including incomplete runs.

## Private result delivery

Raw source/planner/final response receipts stay in a mode0700 temporary job
directory. The workflow uploads **only** an authenticated encrypted envelope,
never that directory, a wildcard, raw response files, or raw log output. Public
logs contain fixed status messages only; provider debug logging is disabled.

The result uses RSA-OAEP-SHA256 to wrap a fresh AES-256-GCM key. The public recipient
is pinned in the package. Its private decryption key exists only outside the Git
repositories in the assistant’s current workspace; it is not sent to GitHub,
DeepSeek or logs. Package identity and recipient fingerprint are authenticated
associated data. Retrieval must also verify the GitHub run/head/artifact identity;
public-key encryption alone is not sender authentication. The local key must be
retained until private result review is complete; this is not a claim of permanent
cross-environment archival recovery.

Only sanitized result metrics and limitations may be committed/published. Exact
raw outputs are privately decrypted for source-first review. The original request
not to publicly upload raw experimental answers remains in force.

All constructed sources/queries are development-exposed and excluded from final
confirmation. LongMemEval remains sealed and untouched. No credentials are
created or moved; actual execution uses only the existing server-stored provider
key in the legitimate one-shot workflow after verification.
