# Current provider-free source-history gate

The next canonical development reality check needs a concrete source-history
screen before source admission. The old scanner asks Git for raw history without
forcing full object IDs. Git may return abbreviated IDs there while the later
object inventory uses full IDs. A protected blob renamed or copied to an ordinary
path can then evade the ID comparison before a content read.

This integration takes only the full-ID guard and its three synthetic tests from
PR324 at `a73f65b2f280da337a6cb9c2a507020832453453`. Their Git blob IDs are
`7e1612109984e7aba1b7f7594fdab5941593e17a` (scanner) and
`1e2dda8b3f0d466191f29442d3d03388ca1af0bd` (tests). Neither PR323's delivery policy,
PR324's experimental source/protocol package nor PR325's runner is adopted.

Independent review then reproduced a second gap using only invented data: a blob
first introduced on a protected path by a merge resolution can be absent from
ordinary raw history output. The v3 successor includes per-parent merge diffs and
full reachable history. A guarded two-parent-merge regression proves the protected
blob is identified and skipped even after an ordinary-path copy. The imported v2
scanner and tests remain exact for historical isolation.

## Fresh work

Use `scripts.development_source_history.screen_development_source(repository,
source)` for new development-source history preparation. It first rejects shallow
or indeterminate repository history, and rejects partial/promisor configuration,
before any blob inventory or body scan. This prevents a metadata query from
lazy-fetching missing protected bodies in a partial clone. These preconditions
belong to the current entrypoint; callers must not bypass it for new source work. The
current v3 scanner then discovers protected object IDs from merge-aware raw path
metadata using `git log --full-history -m --no-abbrev` and excludes those IDs before content reads, including
under renamed/copied ordinary paths. Ordinary removed sources still count as
prior exposure. Synthetic-only tests trap attempted protected-content reads and
include an actual shallow clone containing a renamed invented fixture.

The result contains hashes, match metadata and bounded coverage, not candidate or
repository text. A clear result is only a history negative: rights verification,
native-task/source review, subset/model/scorer/input freeze and a new bounded
budget remain separate. The entry has no model client, execution trigger, live
workflow, grant or provider call; it explicitly reports zero authorized calls and
spending. Do not mistake it for a complete source qualification.

## Historical isolation

`scripts/i02_exposure_history.py` and the consumed packages importing it stay
byte-for-byte unchanged. They exist for exact historical reconstruction, not as
the fresh-source entrypoint. Current-source callers must not copy those imports. The v2 helper is also
historical; new work uses the merge-aware v3 current entry.
All frozen receipts, source hashes and earlier qualification claims retain their
original limits. This patch does not retroactively certify every old caller or
assert that every historical scan was affected: some pinned packages explicitly
set full abbreviation length or were also protected by their path.

Fourteen provider-free guard/regression tests and all 36 consumed-archive tests
pass locally. Exact-head CI and independent review are recorded in the PR.

Only invented temporary repositories are used for this repair. No protected
source/gold, private raw experiment output or LongMemEval content is read or
published. Currently reachable history is the scope; deleted refs, model training
and semantic independence are not proved. Canonical capability and evaluation
priorities remain unchanged.
