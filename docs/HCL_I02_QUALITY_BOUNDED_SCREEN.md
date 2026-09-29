# I02 — bounded QuALITY source and task-fit screen

Status: **SCREENED / NOT I01 FAMILY-QUALIFIED / NOT MODEL-INPUT-QUALIFIED**.

The independent [QuALITY publisher repository](https://github.com/nyu-mll/quality/tree/f84977c40dbfef70c9cab48037b7becfc8e45f73)
and [project license notice](https://nyu-mll.github.io/quality/) state that
its human-written question dataset is CC BY 4.0. The selected original
article's [publisher](https://thelongandshort.org/society/can-women-do-politics-differently)
links to a [CC BY 4.0 text policy](https://thelongandshort.org/using-our-content),
with image rights excluded. The dataset's article-level license field likewise
points to that policy. These are direct provenance and text-license findings,
not a blanket permission for embedded third-party quotations or an item-level
provider-input decision.

The preselected development article is QuALITY `article_id=99919`, first
writer `1020`, in the pinned v1.0.1 `dev` file. The
[executable metadata screen](../scripts/i02_quality_bounded_screen.py) pins
publisher commit, Git blob and file SHA256 and saves only digests/counts in
the [receipt](../reports/HCL_I02_QUALITY_BOUNDED_SCREEN.json). It finds two
writer sets for the same article. All nine selected writer questions pass the
dataset's human-majority answerability metadata, but **zero of nine** have a
human majority saying that at least a third of the article is needed. The
questions were read source-first without options or gold: they ask mainly for
the author's stated position on politics and emotion. They do not provide a
persuasive I01 abstract concept/philosophy witness with competing premises,
counterarguments and uncertainty. Human context ratings are annotations, not
proof of semantic validity; the narrow manual read supports the same negative
task-fit decision.

The original article body and the nine question texts were visible to the
implementer during this screen. The script itself prints neither text nor
answer material. The source group and the shared QuALITY question template
are recorded in the [exposure firewall](HCL_I02_SOURCE_LINEAGE.md) as
development-screened, never unseen confirmation. A separate public
[Project Gutenberg #62314 catalog](https://www.gutenberg.org/ebooks/62314)
displayed an automatically generated plot summary during metadata research;
that exact Hannes Bok source is also recorded as exposed, even though no
QuALITY question, option or gold for it was opened. No other QuALITY article
or test split was opened for this package.

No case is qualified, no model input is allowed, no HCL arm was run, and no
native options or gold were inspected. Provider calls/spend: zero.
LongMemEval remains sealed. The next task is a genuinely different, unexposed
source with a source-first item audit; do not switch to a second question or
writer on this exposed article to seek a favorable H result.

**EVALUATION_DELTA:** direct text rights, task demand and exposure are now
separate gates: apparent CC BY 4.0 provenance does not promote an easy
author-position item to a deep cognition witness. **HCL answer
CAPABILITY_DELTA:** none.
