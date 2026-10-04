# Exact encrypted-result readback

This is an offline operator path for existing result artifacts. It closes the gap
between the low-level decrypt helper and safely checking a downloaded GitHub ZIP.
It does **not** establish current private-key custody, authorize a provider call,
repair a historical result, or finish I02. No runtime, parser, model default,
historical receipt, encryption format, grant, or live workflow changes.

## Existing target and verified public check

`reports/HCL_ENCRYPTED_READBACK_TARGET.json` records the existing failed G05
planner-contract smoke artifact, not a new diagnostic package:

- Repository: `haohongfei2001-png/human-cognition-layer`
- Run: `37084124429`; head: `79aced8962a63aa53d9eeb442fdd4b273fd9267f`
- Artifact: `11259761707`, `hcl-planner-contract-smoke-encrypted-37084124429`
- ZIP member: `planner-contract-smoke.enc.json`
- Package, archive and receipt hashes come from the unchanged historical closure.
- Recipient comes from the unchanged existing public-recipient PEM.

On 2026-10-04, the authenticated GitHub connector returned the exact artifact,
run/head and archive digest. Its downloaded 55,813-byte ZIP matched the published
SHA256, contained one 73,812-byte envelope, and passed the new `inspect` command.
The matching private key was **not** available in the previously authorized scoped
HCL workspace/shared/tmp metadata search. Global loss is not established. No
private key was read and no historical private decryption was performed here.

## Use

Fetch one artifact metadata object from the authenticated GitHub API, separately
from the ZIP. Check the expected repository/artifact/run/head and immutable
closure hashes through an independent trusted source. The script has no network
access and cannot authenticate the origin of a caller-supplied metadata file.
Do not take expectations or metadata from an untrusted archive or compute the
expected receipt hash from newly decrypted content.

```sh
python -m scripts.verify_encrypted_readback inspect \
  --archive /authorized/path/artifact.zip \
  --metadata /authorized/path/artifact-metadata.json \
  --expected reports/HCL_ENCRYPTED_READBACK_TARGET.json
```

After the owner-authorized existing key is available locally, on its custody
machine, use the same exact files plus the owner-only PEM path:

```sh
python -m scripts.verify_encrypted_readback verify \
  --archive /authorized/path/artifact.zip \
  --metadata /authorized/path/artifact-metadata.json \
  --expected reports/HCL_ENCRYPTED_READBACK_TARGET.json \
  --private-key /authorized/private/location/existing-recipient.pem
```

The key must already exist as a regular POSIX file owned by the current effective
user, with one hard link and no group/other access.
The tool does not create keys, change permissions, install credentials, search
for secrets, upload files, or contact a provider. Do not paste a private key into
chat, an argument, or the repository. Encrypted/password-protected PEM keys are
not supported by the unchanged underlying helper; arrange any required secure
handling separately, rather than weakening key protections to fit this command.

## Checked boundaries and output

Both commands require the exact expectation schema and validate repository,
artifact ID/name, workflow run/head, GitHub-reported archive digest, downloaded
ZIP digest, exact flat member name, package and recipient. ZIP contents stay in
memory: no extraction, traversal, symlink, extra/duplicate member, encrypted ZIP,
or unbounded decompression. Inputs must be regular bounded files; final-component
symlinks and FIFOs are rejected on supported POSIX systems. JSON duplicate keys,
nonfinite values, unexpected envelope fields and invalid ciphertext bounds fail.

`inspect` reports `CIPHERTEXT_IDENTITY_VERIFIED_PRIVATE_READBACK_NOT_RUN`.
`verify` additionally authenticates/decrypts via the unchanged existing helper,
requires the exact frozen plaintext receipt SHA256 and inner package, and reports
`EXACT_PRIVATE_RECEIPT_READBACK_VERIFIED`. Neither command emits plaintext, private
key bytes, raw parser/crypto exceptions or input paths. There is no plaintext
output option or default plaintext file. Only sanitized identity/digest evidence
is printed. This verifier does not perform semantic answer review or cost review.

The legacy AEAD header authenticates package and recipient, **not run/head**.
Run/head are matched through the separately obtained GitHub metadata and its
archive digest. Output deliberately marks this external provenance boundary and
never claims it independently authenticated the metadata origin. Public-key
encryption also does not by itself authenticate the sender; the independently
frozen receipt/archive hashes remain necessary.

A successful local decrypt proves possession for that one read. It does not prove
a durable key backup, continued access, secure long-term custody or live provider
readiness. `durable_key_custody_verified` remains false and `authorized_calls`
remains zero. Do not turn a scripted success into a live-readiness flag.

## Next actual diagnostic

The existing dormant G05 package uses an older runtime and is not adopted or
launchable on current main. Complete actual secure readback/custody first, then
refreeze and independently review one original failed G05 input on current HCL:
one planning call and at most one answer, relevant nonempty native preparation,
valid original-source citations, encrypted result readback and complete cost
accounting. No Base, retry, repair call, item substitution, old budget reuse or
capability expansion. The ordinary planner default remains 4,096 tokens; the
historical 16,384 diagnostic choice is a separately explicit configuration, not
a new production default or a claim that every future task requires it.

Offline tests use disposable RSA keys only in memory. Those tests and the real
ciphertext inspection are preparation evidence, not actual historical decryption,
model compliance, efficacy, fresh evaluation or I02 completion.
