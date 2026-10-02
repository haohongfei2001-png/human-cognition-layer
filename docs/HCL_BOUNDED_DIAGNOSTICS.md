# New bounded synthetic I02 diagnostics

## Prepared for review; not launched

The owner confirmed a new, separate ceiling of **US$1 and 12 provider calls**,
ending **2026-10-03 08:00 UTC**. The first bound reached stops admission. This is
separate from HCLA's budget. Both older HCL grants remain byte-for-byte closed.
The new grant is `PREPARED_REVIEW_REQUIRED`; no active paid workflow or trigger
is installed by this preparation. Initial package review and exact executor CI
must precede activation. This document reports no new live result.

The runtime is pinned to certified main
`df0c5d3cdf60219ad0ceab8b25a7bf82ac8087be` (PR344), runtime digest
`ad67e85c9bd00cb23dd61825bf7c35790f72282754574da19612435e96839cfe`.
The production HCL runtime does not change. A separate diagnostic port varies
only the bounded planning output limit; it does not silently change product
configuration, provider or model.

## Fixed diagnostic sequence

1. One fresh authored no-source planning probe using existing `deepseek-v4-pro`,
   thinking enabled, high effort and a 4,096-token output limit.
2. Only a returned exact-model, one-choice `length` response with valid bounded
   usage permits one predeclared differential at 8,192 tokens. Its source,
   question, messages, provider, model, thinking and effort are identical. This
   is a separately reserved intervention, not an unbounded retry.
3. A schema-valid plan selects that planning limit for three fixed synthetic HCL
   flows: general volunteer coordination, competing publicly reported action
   goals, and a source-local single-premise counterfactual. Each flow performs
   actual universal planning and, when admitted, answer delivery. HCL selects
   its own capabilities; no adapter or successful treatment is forced.

Any other probe failure stops before full flows. A second length response stops;
there is no further output increase, prompt repair, fallback model, replacement
case or retry. Full-flow orchestration or source-review failure stops the batch.
Unknown transport outcomes retain the entire reservation. Missing treatment and
unsupported operations remain observations, not concealed successes. There is
no Base arm, paid judge, numeric efficacy score, private user data or external
lookup. These authored cases are development-exposed and cannot qualify as final
confirmation. Historical failure causes remain unresolved unless the original
receipt actually established them; new behavior does not relabel past runs.

## Cost, time and single-run boundaries

The fixed schedule uses seven calls after baseline success, or eight after the
one conditional differential. Twelve is the owner's hard ceiling, not a target.
Unused capacity is not filled with extra experiments and is closed without
transfer at termination.

Every complete serialized UTF-8 request is limited to 18,000 bytes. The input
reserve is twice that byte count plus 2,048 tokens. Output reserve includes a
32-token margin; all subsequent planning/answer outputs are at most 8,192 tokens.
There is no source, plan, catalog or answer-input truncation to fit the limit.
Dynamic answer expansion can therefore stop a flow before transport.

The [official DeepSeek price page](https://api-docs.deepseek.com/quick_start/pricing/)
was checked on 2026-10-02: the conservative V4 Pro cache-miss peak rates used here
are US$1.32 per million input and US$3.96 per million output tokens. Full schedule
worst-case reservation is **US$0.64610304**. Even a hypothetical twelve-call
sequence with the frozen first probe would reserve at most **US$0.97726464**.
Usage-rated amounts are not invoice costs, and returned usage never replenishes
the budget. Prices must remain conservative before activation.

The ledger checks the US$1 cap, 12-call cap, absolute expiry and a 30-minute run
window separately. Each 180-second SDK/wall wait must fit before the expiry;
there is a second time check immediately before transport. An SDK timeout cannot
prove an already-sent request was cancelled, so its cost remains fully held and
no later call follows.

Before transport, the request digest, unique stage/phase identity, call ordinal,
reservation and invocation state are durably saved. Disk failure closes admission.
A new output directory cannot reuse an old run, and the template accepts only the
first exact marker-only push after the reviewed executor, on main, attempt one.
There is no manual dispatch route. Complete workflow history and package/grant
hashes are checked before exposing the existing server-side DeepSeek secret.
No key is created, read into chat, rotated or transferred.

## Diagnostics and results

Request/answer content stays in the existing encrypted-result path. Rejected
responses retain only allowlisted scalar observations: returned-response flag,
validated-usage flag/counts, choice count, finish-reason enum, content presence/
length, and optional bounded reasoning-token count. Reasoning text, SDK dumps,
raw exceptions, headers, refusals and arbitrary metadata are not retained.
Reasoning tokens are not charged twice or deducted from completion usage. Missing
or invalid optional counts remain unknown rather than zero.

Offline tests cover success and controlled differential, real retained G05 output,
source completeness, invalid metadata, privacy canaries, output/request mismatch,
expiry at launch and send, call/dollar caps, journal failures, duplicate identity,
old/prepared/enlarged grants, directory reuse and one-shot marker admission.
After termination, review the encrypted receipt, preserve failures and unknown
holds, close the new grant, and remove any active paid workflow/trigger before
resuming changes to the tested runtime. A successful synthetic flow is functional
interface evidence, not model efficacy or independent generalization.
