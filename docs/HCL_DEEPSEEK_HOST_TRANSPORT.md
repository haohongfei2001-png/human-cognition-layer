# DeepSeek host transport and native-CNY batch accounting

Status: **INTEGRATED_OFFLINE**. A real HTTP sender is implemented and exercised
against an isolated loopback server. Its candidates and usage are synthetic.
This is not evidence of external model extraction, real spend, LIVE_FUNCTIONAL,
full M01/M08, or completion of S2/S3/S4. The PR453 disconnected protocol remains
unchanged and cannot be promoted to live by changing a flag.

## Provider-specific wire

Official documentation checked on 2026-10-17:

- [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [Chinese model and CNY pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)

The only destination is `https://api.deepseek.com/chat/completions`. Requests use
`deepseek-v4-pro`; the exact accepted returned identities are this request alias
and the documented `DeepSeek-V4-Pro-0813`. No prefix match, fallback model, SDK,
proxy environment, redirect, tool execution, Search/Fetch, automatic retry, or
TLS verification bypass is installed. The sender supplies verified-default TLS
with the fixed hostname. Host credentials are borrowed only for that endpoint
through `HostCredentialProvider`; the transport itself has no environment/file/
keychain loader or key constructor argument. A separate default-closed host
runner, described below, can borrow only the existing core Actions secret after
its one-use admission checks. No READY grant or trigger marker is shipped.

The request uses `max_tokens=16384`, `thinking={type: disabled}`,
`reasoning_effort=none`, `temperature=0`, `stream=false`,
`response_format={type: json_object}`, and `tool_choice=none`. Its two messages
are the fixed extraction instruction and the existing source/version-bound
context. OpenAI-only `max_completion_tokens`, `n`, and `store` are not sent.
Only one returned choice is accepted. Candidate JSON follows the existing
source envelope and compiler, not a parallel model-generated answer path.

The complete body is capped at 1 MiB, headers at 16 KiB, raw response at 1 MiB,
and visible candidate at 256 KiB, also respecting smaller task byte budgets.
The host must provide at least the fixed 16,384-token task output allowance.
A separate connect timeout covers DNS/connect/TLS; the absolute monotonic
deadline covers connect, headers and body, including slow drip responses.
Synchronous credential/gate work is checked against the deadline immediately
before the first write. These byte caps are not claims of exact online token
counts. Monetary reservation uses the full documented 1,048,576-token context,
including all system, schema and framing contributions.

### Narrow HTTP response-header compatibility

The sender accepts repeated `Set-Cookie`, `Vary`, and `Cache-Control` fields,
discarding every occurrence. It has no cookie jar or HTTP response cache and
never combines, persists, or forwards these values. All lines are first checked
for token field names and invalid control characters; whitespace before the
colon, obsolete folding, and bare CR/LF remain rejected. Header/body limits and
deadlines still apply. Every other duplicate name, including unknown extension
fields and `Content-Length`, `Transfer-Encoding`, `Content-Type`, and
`Content-Encoding`, remains rejected even when the values are identical.
Duplicate fields are never combined or normalized into an accepted response.
`Content-Length` together with `Transfer-Encoding` and unsupported encodings
remain rejected. This patch does not broaden media-type parameter parsing.
The no-redirect/no-retry policy is unchanged.

Primary standards checked on 2026-10-17:

- [RFC 9110 §5.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.3)
  describes repeated list fields and the separate `Set-Cookie` case;
  [§12.5.5](https://www.rfc-editor.org/rfc/rfc9110.html#section-12.5.5)
  defines `Vary` as a list.
- [RFC 9111 §5.2](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2)
  defines `Cache-Control` as a directive list.
- [RFC 6265 §5.2](https://www.rfc-editor.org/rfc/rfc6265.html#section-5.2)
  permits ignoring `Set-Cookie` entirely.
- [RFC 9112 §5](https://www.rfc-editor.org/rfc/rfc9112.html#section-5)
  and [§6.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3)
  cover field syntax and framing ambiguity. This bounded client deliberately
  keeps stricter duplicate framing rejection rather than recovering it.

Isolated loopback tests reproduce the former blanket-duplicate rejection,
then exercise all three accepted fields with fixed-length, chunked, and
close-delimited bodies, the existing candidate-to-cognition path, no cookie
retention/replay, and malformed/ambiguous-header full-hold failures. These are
synthetic compatibility tests. The earlier one-use external run stopped with
`DEEPSEEK_HEADERS_INVALID`; its original headers were not retained, so the
specific provider header and underlying cause remain unknown. This patch
does not establish that it fixes that run, settle its unknown usage, authorize
another call, reopen its closed grant, or change its immutable marker.

## Native CNY, shared across the batch

No simulated USD nanodollar value is converted into CNY. The unit is integer
nanoyuan: 1 CNY = 1,000,000,000 nanoyuan. The reviewed conservative peak rates
are 9 CNY/million uncached input, 0.30 cached input, and 27 output. The full
per-call reservation is:

`1,048,576 * 9/1,000,000 + (16,384 + 32) * 27/1,000,000 = 9.880416 CNY`.

The 32-token output reserve margin is not requested generation. Two complete
reservations total 19.760832 CNY, below the hard 20 CNY batch cap. One or two
explicit request fingerprints may share the batch, but its total is at most
two sends including semantic repair. There is at most one repair, only after
valid mechanical usage and a compiler/source-envelope rejection. It goes back
through the same compiler, runner, actual M03/M06/M08/M05, and answer assembler.
No human candidate is inserted to label failed extraction successful.

The host must freshly verify the exact tariff, expected model version, and the
existing direct HCL core account's CNY denomination. An immutable explicit
attestation expires after at most 15 minutes and is rechecked at reserve and
send. Unknown/expired price, USD denomination, another provider, or another
account scope fails closed. Historical grants are not imported or reactivated.
The general transport never invents this attestation. The separate one-use host
fetches fresh official price and existing-account denomination before issuing it.

`prompt_cache_hit_tokens + prompt_cache_miss_tokens = prompt_tokens` is
required. If present, `prompt_tokens_details.cached_tokens` must match the hit
count; reasoning tokens must be bounded by completion tokens and are not billed
twice. Total tokens, exact model/id, choice/index, finish reason, integer types,
nonnegative counts, and the context/output limits are validated. Missing or
contradictory billing never means zero. Overspend is recorded without clamping
and blocks the batch. A non-stop response cannot trigger a transport retry.
Reasoning text is neither retained in objects, the sidecar, nor receipts/logs.

Settlement is explicitly a **usage-derived CNY peak upper bound**, not an
invoice or exact debited balance. `actual_billed_cny` remains unknown. Off-peak
pricing or account credits may make the actual debit lower. There is no USD
conversion. The task usage and batch usage expose separate observed upper
bounds, reservations, unknowns, and call counts.

## Durable claim and recovery boundary

`CNYBatchLedger.create` is a trusted host issuance operation and exclusively
creates a new file. `CNYBatchLedger(...)` only opens an existing canonical file.
Missing, relocated/replaced, empty, wrong-schema, inconsistent-usage, or
mismatched-authority databases fail closed. The immutable grant binds both
ledger and state-store paths and exact task fingerprints. Schema, row state,
receipt identity and cost arithmetic are validated on every transaction.

`BEGIN IMMEDIATE` atomically claims the shared budget across connections and
processes. Any existing unresolved claim blocks another claim. A serialized
send gate rechecks durable revocation and fresh HCL access before the first
HTTP write. Reopening or registering the same grant cannot reset CLOSED,
REVOKED, BLOCKED or UNKNOWN. A privileged host/database administrator remains
outside this application-level trust boundary.

The sidecar claim is persisted before the task-call record. A crash anywhere
between the two databases conservatively retains the full claim and stops the
batch. Even a pre-send RESERVED claim is not released or reused. Once
SEND_STARTED exists, interruption/cancellation/disconnect/timeout is unknown.
There is no unlock/release/reset API. Returned usage is durably recorded before
semantic or late-ACL validation. A known returned candidate/computed result may
be recovered through the existing authenticated engine without any resend;
an unknown send cannot be resumed. Settled receipts in the sidecar contain only
mechanical metadata, never source, visible response, or credential contents.

A newly recreated ephemeral CI runner ledger is **not** cross-run protection.
The one-use host below first enforces exact published ancestry and complete
workflow-run history. A concurrency group, `run_attempt==1`, or a promise not
to rerun is insufficient. Privileged repository/history administrators remain
outside this application-level trust boundary, as in the existing once-host.

## Default-closed one-use host

`scripts/deepseek_core_smoke_once.py` and
`.github/workflows/hcl-deepseek-core-smoke-once.yml` are executable preparation,
not authorization or evidence of a real call. The repository ships only
`CLOSED_UNISSUED`; the new trigger marker is absent. The workflow has no manual
or pull-request dispatch and only read-only `contents`/`actions` permissions.
There is no credential creation, replacement, persistence or setup operation.

After independent acceptance, an authorized host must create exactly this new
three-commit chain on main: reviewed executor E, direct grant-only child G,
then direct marker-only child M. The new READY grant binds E, exact runtime and
read-only-reader hashes, the public synthetic case hash, fixed model/version,
CNY, two total calls including repair, and 20 CNY. The marker binds G and the
exact grant hash; its path must be absent at both E and G. Neither legacy grants
nor legacy markers are accepted. No caller-selected grant, marker, source,
ledger path, provider or model argument is supported.

The host requires a clean checkout at M, the exact repository/main/push/
workflow/first-attempt identity, and complete paginated workflow-run history
containing exactly one row matching that same run and head. A second dispatch,
a rerun, a later marker edit, a different branch/event or incomplete history
fails closed before credential borrowing or a model request. After admission,
an exclusive fsynced consumption record blocks repeated execution in the same
runner. Together with the immutable chain and first-run history, this prevents
fresh ephemeral SQLite files from supplying another budget across runs. The
concurrency group is only coordination, never the authorization boundary.

The host then reads the fixed official price page with verified TLS, no proxy
or redirect and a 512 KB cap, and the fixed existing `/user/balance` metadata
with the same protections and a 64 KB cap. Strict JSON rejects duplicate keys
and nonfinite numbers; USD, multiple/unknown currencies and unavailable account
metadata block all model calls. Only denomination and availability are retained,
not balances. The exact legacy parsers are content-pinned without changing their
historical files. Both checks bind the same run/head and remain fresh for at most
ten minutes; the native authorization starts at the earlier check time. The
existing `secrets.DEEPSEEK_API_KEY` is borrowed only after permanent admission,
never copied into a grant or artifact. Its presence, validity and CNY account
have not been checked by this offline preparation.

The two source/question cases are self-authored public text. They contain finite
explicit hypotheses but no hand-supplied candidate answer; production execution
must receive its candidate from the real sender and use the same compiler,
cognition, and formal answer assembly. One first-case repair consumes the final
call and skips the second case. The public artifact contains only synthetic
results and mechanical usage, with no private DB, raw HTTP/error body, headers,
key, balance or reasoning. A terminal always-step closes retained holds without
sending. Early failures expose only allowlisted codes/stages. Missing/corrupt
post-admission accounting is unknown, never invented zero spend. The artifact
never automatically claims semantic fidelity, an effect gain or stage completion.

This change does not issue the later grant/marker, trigger the workflow, read a
real credential or perform an external model request.

### Read-only repository lifecycle audit

Provider-free CI uses `scripts/deepseek_core_smoke_lifecycle.py` to validate the
versioned preparation, exact grant-only G, exact marker-only M, and terminal
closure states. It is not imported by the live host and cannot authorize a send.
The live preflight still accepts only READY with its exact E/G/M/run gates.
The CLOSED/no-marker rejection test uses an explicit fixture, rather than
incorrectly requiring the repository to remain unissued after an authorized run.

After the one run terminates, a single-parent grant-only child C of M may change
the original grant's status to `CLOSED_CONSUMED` or `CLOSED_BLOCKED` and add exactly
`closure={schema: hcl-deepseek-core-smoke-closure-1, marker_commit: M,
run_id: <positive decimal string>, receipt_sha256: <64 lowercase hex>}`. All
other grant fields stay equal to G. The receipt hash identifies the sanitized
public artifact; the audit does not claim to verify the external run or invoice.
The marker remains untouched. No terminal state can be reset to UNISSUED/READY.
If cancelled before M exists, a grant-only child C of G may instead set
`CLOSED_CANCELLED`, with exactly
`closure={schema: hcl-deepseek-core-smoke-closure-1, grant_commit: G,
reason: CANCELLED_BEFORE_TRIGGER}`. No marker may exist anywhere in that
history; this terminal branch cannot later acquire one or authorize execution.

Normal development after C is allowed, while any later grant/marker edit,
including an edit then revert, is rejected. The audit validates G against the
historical E runtime blobs and frozen v1 source/reader identities, never against
an unrelated future runtime and never by executing historical Python. This
keeps a legitimate closed experiment from permanently breaking subsequent CI.
G and C match the existing Unified provider-free path filter; M matches only
the new one-use workflow. Real secret/account/model checks are not part of this
read-only audit, and repository closure is not a refund or a reset of usage.

## Evidence and compatibility

- `tests/test_unified_deepseek_transport.py`: real sender over loopback, exact
  TLS parameters, wire framing, successful cognition/answer, one repair/shared
  batch, 401/402/429/5xx/redirect, disconnect, slow headers/body, synchronous
  deadline, cancellation, corrupt usage/cache/model, duplicate JSON keys,
  overspend, revocation, crash seams, no-resend recovery and concurrent claims.
- `tests/test_unified_deepseek_once.py`: exact local three-commit chain, first-run
  history/replay rejection, exclusive consumption, strict account/freshness,
  unknown terminal accounting and real loopback two-case/repair execution.
- `tests/test_unified_deepseek_upgrade.py`: execute actual PR453 main
  `660c43593b7642f39ede95e5ae9c2f4855966ae5`, tree
  `b94a906f06e6a738fdd96062bdc9d51a3dc575e8`, then explicit side-copy migration.
  Preserve old offline and simulated context/request/response/proof/claim/
  answer/usage bytes, old-writer fencing, ACL and zero-resend recovery.
- `scripts/witness_unified_deepseek_transport.py`: loopback-only sender into
  actual cognition and formal answer; exact HEAD/runtime hashes. It clearly
  separates synthetic usage from external calls and real spend, both zero.

All existing caps, old protocol bytes, predecessor pins and acceptance gates
remain. No automatic extraction success, scientific gain or stage completion
is claimed by this transport preparation.
