# Final-context structural whitespace and size diagnostics

This development change is limited to `UniversalHCL.answer`. Its final user
payload uses compact JSON separators. Parsing that JSON produces the same
fields and values, including every string, complete source, source ID/version,
plan, native result, support ID, uncertainty and assumption. It does not dedupe,
summarize, truncate or replace any content. Planning and all native dispatch,
source-support, final-answer and original-citation checks remain unchanged.

The final-context character ceiling and complete provider request's 36,000
UTF-8-byte ceiling are unchanged. An oversized request still fails without
truncation, retry or an answer call. Removing structural spaces can make a
previously oversized synthetic request fit; this is a transport-capacity change,
not a claim that model behavior or answer quality is unchanged or improved.

## Local size-only receipt

Before the final context or provider gates, `final_context_metrics` records:

- `payload_utf8_bytes`: exact final user-content bytes.
- `serialized_messages_utf8_bytes`: complete messages serialized as compact
  JSON, including string escaping, but excluding the provider envelope.
- `payload_value_utf8_bytes`: standalone compact JSON sizes of the six fixed
  top-level values. These exclude the top-level keys and punctuation, so their
  sum is not the complete payload or provider request size.

The new field contains fixed names and numeric sizes, with no copied source,
plan, model response or hidden reasoning. It is local receipt metadata and is
not sent to the model. If UTF-8 encoding is unavailable, a fixed false flag is
recorded without adding a new offline-stub admission rule; the unchanged
provider serializer still governs its own admission.

Historical executors are not changed to persist this new field. Therefore this
does not recover the missing PAIR1 failed wire or establish its exact field-level
cause. A future authorized caller would have to retain the returned local receipt.

## Offline evidence and limits

Existing scripted fixtures exercise real native HCL operations with local model
stand-ins. Paired old/new runs preserve parsed final payloads, system policies
and the other receipt values. Three existing payloads shrink from 29,934 to
28,720, 6,682 to 6,380, and 6,869 to 6,571 UTF-8 bytes. A separate existing C02
combination's complete serialized request shrinks from 36,775 to 35,749 bytes
while preserving all three actual native results. These are synthetic transport
measurements, not outputs from a new model evaluation.

Tests retain a truly oversized three-native-result combination, exact 36,000 and
36,001 byte bounds with Chinese/emoji, unchanged source/citations, source revision
and withdrawal refusal, and refusal when no actual native result exists.

## Development identity does not reopen paid authority

`development_final_context_amendment` accepts one exact reviewed runtime file
hash and the exact resulting runtime digest. Replacing that one file's hash
with its prior value must reproduce the complete prior runtime digest; other
file drift, additions or omissions fail closed. Caller-supplied digest text
cannot replace verification of the actual files.

The previous amendment and 45 consumed two-stage files are separately pinned.
Paid executors, fixed runtime constants, packages, grants, launch markers,
reports and scores remain byte-identical. Both CNY grants remain closed with
zero remaining calls and money. New negative tests verify that the historical
packages reject the new runtime before a client or output directory is created.

Current development tests and witnesses use the new development identity.
Unchanged consumed two-stage tests run only in an isolated checkout of
`dbd7ba9fe9b8a2d4aa165f4e39a949b510cd1ee5`, with socket networking disabled and no
provider credentials forwarded. Previous historical replay gates are retained.

No model calls, paid tests, fact-coverage model, reference codec, new spending
authority, historical rescore or efficacy claim is part of this change.
