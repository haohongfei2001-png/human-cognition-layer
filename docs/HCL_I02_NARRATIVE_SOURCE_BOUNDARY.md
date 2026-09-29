# I02 — exposed narrative source and editorial-oracle boundary

Status: **DEVELOPMENT-SCREENED / NO I01 CASE QUALIFIED / NO MODEL INPUT**.

This bounded screen tested whether readily available narrative material could
support I01's independent human-cognition tasks. It created no case or result.
The executable [lineage receipt](../reports/HCL_I02_EXPOSURE_LINEAGE.json)
records what the implementer saw, and the
[confirmation guard](../scripts/i02_source_lineage.py) rejects those declared
writing systems, question templates, related source authors and any exact
recorded source-text digest. Exact-content matching is only an additional
check; it cannot replace honest provenance or the repository-wide audit.

## NarrativeQA: source length is not task depth

The [publisher repository](https://github.com/google-deepmind/narrativeqa/tree/904246f6d1fe99a99a08a03501fe3e619af2cee5)
provides independently written question/answer pairs and links to external
stories. Its repository declares Apache 2.0 for its data; story rights remain
separate. The preselected train story was Joseph Conrad's *Amy Foster*, linked
to [Project Gutenberg #495](https://www.gutenberg.org/ebooks/495). At the
pinned publisher commit, the documents CSV has SHA256
`6dffa4cc0b5c9963fe3a097c87f04aa7767da36627500cc7a0d69e2405e1144a`
and the question CSV has SHA256
`990b02af0b5280de210f0e6b80f43b3fab80dc6de630c4d5059a1b7131c26e38`.

The implementer saw all 30 question texts for this source, two native reference
answers each for four selected questions, a Gutenberg catalog summary and
bounded story passages. Most question wording asked for short story facts;
four potentially social questions still required item-level source checks
and did not establish the I01 long character-development demand. The native
answers are development-exposed. This author/question system cannot be
relabelled unseen confirmation. No answer was scored and no model was called.

## Narrative Crossroads: teacher interpretation is not ordinary source

The independent teacher's [Narrative Crossroads](https://narrativecrossroads.org/)
site declares CC BY 4.0 for its materials. The two inspected
[modules](https://narrativecrossroads.org/practice/modules/) concern
*The Interlopers* and *The Most Dangerous Game*. They provide character
wants/fears, threshold interpretations and sample responses. Those are
editorial interpretations and answer aids; passing the whole module as
`source_text` would give every arm an oracle-like explanation that an ordinary
reader of the story does not receive. The modules offer a classroom lens and
threshold choices rather than a fixed, source-specific native I01 question
with a common answer contract. No HCL-authored combination of the lens and
threshold is promoted to an independent question.
The fetched Interlopers and Most Dangerous Game module PDFs have SHA256
`819773028b5ec6ccbf2056c69a2eb75fb6ecb88415f4c1a832052a87af8f462b`
and `aa77e46d0383fcc6f8006651301011482ea3676ac399a05836fbee361fb79b22`.

The underlying [Saki collection](https://www.gutenberg.org/ebooks/1477) and
[Gutenberg Canada Connell edition](https://www.gutenberg.ca/ebooks/connellr-mostdangerousgame/connellr-mostdangerousgame-00-h.html)
were also inspected. The Canadian edition itself warns that public-domain
status can differ elsewhere; this screen did not resolve model-input rights
for that edition. A normalized *Interlopers* story segment has SHA256
`2dad52d13d80532af5c5f345bece3dea9e8abe2abccf726f2d30c05bd8d86fbe`;
the guard recognizes only this exact normalized content. The teacher's two
modules and the two original story authors are conservatively treated as
development-exposed source systems. Their sample responses were seen, but
there are no native dataset labels to count.

The metadata-only [SQuALITY publisher](https://github.com/nyu-mll/SQuALITY)
was also inspected. No story, question or answer from it was displayed or
selected, so this screen makes no task-fit or exposure claim about an item.

## Boundary and next step

**EVALUATION_DELTA:** an exact previously screened source can no longer pass
the I02 confirmation guard merely under new declared lineage IDs, and known
original authors behind an exposed question system are excluded. The review
also records why teacher-provided mental-state tables and sample responses
cannot be smuggled into an ordinary-source comparison. This remains a bounded
known-exposure guard, not a semantic validator or independent source approval.

**HCL answer CAPABILITY_DELTA:** none. Provider calls/spend: **0 / USD 0**.
LongMemEval: **SEALED / NOT ACCESSED**. Continue I02 with genuinely unexposed
source and question systems, clear processing rights, source-first item task fit
and competent C/P/G qualification before I03. Do not recycle either consumed
calibration grant.
