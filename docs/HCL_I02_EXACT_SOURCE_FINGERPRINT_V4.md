# I02 exact-content exposure overlay v4

**Status:** provider-free gate improvement; zero confirmation items qualified.
The existing v3 source qualification guard rejects known publisher URLs and
writing-system IDs, but the consumed KPU case could otherwise be copied to
a new URL and assigned new lineage IDs. The [v4 guard](../scripts/i02_source_qualification_v4.py)
adds a SHA256 exact-source check before invoking the unchanged v3 rights,
privacy, historical-lineage and ordinary-input checks. The
[fingerprint receipt](../reports/HCL_I02_SOURCE_FINGERPRINTS_V4.json)
pins the historical KPU source file, its text digest, run ID and closure.
The public v4 qualification call always loads that pinned receipt; callers
cannot supply an empty replacement fingerprint table. Changing the receipt
or underlying file fails closed. The KPU source
is CC BY 4.0, but its eligibility for **development calibration only** does
not become confirmation eligibility under a mirror.

The test uses a synthetic confirmation case and a copied KPU source with
invented publisher URL, author, template, writing-system and group IDs. V3
accepts the artificial metadata assertion; v4 rejects the exact exposed
source content. Additional tests preserve a passing synthetic v3 composition,
its normal URL denial, and fingerprint tamper rejection. No model call or
confirmation output is viewed. This exact-byte guard does not detect a
paraphrase, partial excerpt or an unrecorded repository exposure. A separate
repository-wide audit and independently verified rights and item semantics
remain required by I01/I02 before any I03 confirmation claim.

**EVALUATION_DELTA:** a previously demonstrated mirror-and-renaming path can
no longer promote the consumed KPU source into a protected confirmation item.
**HCL answer CAPABILITY_DELTA:** none. **Provider calls/spend:** 0 / USD 0.
**LongMemEval:** sealed and not accessed. **NEXT_READY:** I02 unexposed
source qualification.
