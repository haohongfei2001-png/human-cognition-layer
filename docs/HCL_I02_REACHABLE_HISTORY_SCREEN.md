# I02 reachable Git history exposure gate

The v5 source screen checked one current checkout snapshot. A source copied
into the repository and later deleted could pass that snapshot screen. The
[v6 gate](../scripts/i02_source_qualification_v6.py) now runs the
[reachable-history screen](../scripts/i02_exposure_history.py) before the v5
snapshot and older rights, lineage and source-first assertions. An overlap
requires independent review; absence of overlap grants no qualification.

The screen inventories unique objects reachable from current local Git refs.
It derives old and new blob IDs of every LongMemEval-named historical path from
Git metadata **before reading any blob**, then skips those IDs even if Git
reports another path for the same object. It checks exact bytes and 12-word
windows for other UTF-8 blobs, records only hashes, paths and counts, and
fails closed on a large text blob it cannot inspect. The audit says nothing
about deleted refs no longer reachable, other repositories, provider training,
paraphrase leakage, rights, privacy or item semantics. A current remote-main
SHA must still be checked before qualification. LongMemEval content was not
opened.

The [actual main-history receipt](../reports/HCL_I02_REACHABLE_HISTORY_KPU_SCREEN.json)
uses the already development-exposed KPU source as a negative witness at
`main@08900c6331a9f15b40302200a7fac2edaaef62d1`: three historical blobs
overlap, 2,701 non-sealed UTF-8 blobs were scanned, and 54 sealed blob IDs
were skipped. No source prose was copied into the receipt. Synthetic unit
checks prove a deleted source still blocks qualification, current-HEAD
binding, a clean non-sealed candidate can advance to older gates, short-source
rejection, local revision, and the sealed-object skip. This is an **evaluation
correctness delta**, not an HCL answer gain or independent source qualification.

One separately screened teaching page aggregated third-party cases under a
non-commercial book notice. Its page-wide license could not authorize all
embedded sources; it was not used as a case or model input. This was a bounded
negative screen, not a new sample selection.

**Provider calls/spend:** 0 / USD 0. **LongMemEval:** SEALED_NOT_ACCESSED.
**NEXT_READY:** `I02_UNEXPOSED_SOURCE_QUALIFICATION`; genuine independent
rights, privacy, native-task fit and C/P/G semantic qualification remain open.
