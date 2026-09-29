# I02 — blind upstream edition match for selected long narrative

Status: **EXACT NORMALIZED EDITION MATCH / CONTENT NOT DISPLAYED / ITEM NOT QUALIFIED**.
The prior [metadata preselection](HCL_I02_FAIRYTALE_METADATA_CANDIDATE.md)
fixed `bamboo-cutter-moon-child` from the UCI FairytaleQA distribution
before opening a story, question or answer. The
[blind matcher](../scripts/i02_fairytale_blind_match.py) fetched the pinned
publisher story and [Project Gutenberg #4018](https://www.gutenberg.org/ebooks/4018)
into process memory, checked source SHA256 and Git blob identity, parsed only
section structure internally and compared normalized words. It emitted
[this receipt](../reports/HCL_I02_FAIRYTALE_BLIND_EDITION_MATCH.json), **not
the story text**. No question or native answer file was read.

The publisher story bytes have SHA256
`d4c92d2c038bae6ff535e051cad53d9ee4092bb49e3ecdd2a13ef6c5bb961891`
and pinned Git blob `ad5754d177a8e85ff9800896d8c7f592d32fe883`.
The Gutenberg text bytes have SHA256
`a17eec00fcaaba3d8e3496945486a3be8a984cbb694d4f6db0f4616e782af115`.
All 5,800 normalized words across 43 publisher sections form one exact,
contiguous sequence in that 74,685-word Gutenberg edition. This strongly
establishes the dataset story's upstream text provenance without presenting
held-out narrative content to the implementer. It does not validate any
question, answer, character inference or model performance.

For scoped rights, Gutenberg marks the edition public domain in the USA;
Japan's [National Diet Library authority](https://id.ndl.go.jp/auth/ndlna/01162614)
records Ozaki's death in 1932, and [WIPO's current China law entry](https://www.wipo.int/wipolex/en/legislation/details/21065)
sets the general natural-author economic term at life plus fifty years. From
those primary facts, the selected text appears out of term for intended
US/China handling. The UCI repository is Apache 2.0 marked and its license
copy accompanies the metadata. This is a **scoped inference**, not a global
legal clearance or a claim about every story in the dataset. The question
file's exact authorship/license scope and semantic validity still need an
affirmative receipt before provider input.

The selected question and native answer remain sealed; the original dataset
validation split is public, so novelty to model pretraining cannot be
assumed. I01 still requires an independent source-first item audit,
prespecified sample and scoring freeze, disjoint calibration/confirmation
systems, strong C/P/G and fair arm access. The receipt keeps
`confirmation_qualified=false`; there were zero provider calls and zero
historical-budget transfer. LongMemEval remains sealed.

**EVALUATION_DELTA:** the preselected long-narrative source is now tied to
one exact public-domain edition by an executable, content-blind provenance
check. **HCL answer CAPABILITY_DELTA:** none.
