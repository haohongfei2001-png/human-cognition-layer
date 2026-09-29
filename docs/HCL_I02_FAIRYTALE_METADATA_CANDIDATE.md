# I02 — bounded FairytaleQA metadata preselection

Status: **ONE LONG-NARRATIVE CANDIDATE PRESELECTED / CONTENT SEALED / NOT QUALIFIED**.
The [UCI author-team repository](https://github.com/uci-soe/FairytaleQAData)
describes 278 storybooks and education-expert questions, with a repository
[Apache 2.0 license](https://github.com/uci-soe/FairytaleQAData/blob/a24ddc17364666b7c13a425b9970c87368b03417/LICENSE).
Its metadata-only inventory is pinned at commit
`a24ddc17364666b7c13a425b9970c87368b03417` and SHA256
`bd45290eb48a908829d50792fa465592f26bbe898ca16778e8576fbe2f1fdf76`.
The repository's [license text](../reports/HCL_I02_FAIRYTALE_APACHE_LICENSE.txt)
is retained with the copied metadata; this does not assert that the
underlying Gutenberg-derived story has the same license.
The [metadata file](../reports/HCL_I02_FAIRYTALE_METADATA.csv),
[candidate receipt](../reports/HCL_I02_FAIRYTALE_METADATA_CANDIDATE.json)
and [selection guard](../scripts/i02_fairytale_metadata.py) preserve the
selection without opening any story, question or native answer.

The prespecified rule chooses the longest `japanese-fairybook` metadata row
after excluding `happy-hunter-skillful-fisher`, whose story content appeared
in a public search snippet during rights screening. It selects
`bamboo-cutter-moon-child` (native validation split): 43 sections, 5,731
reported words, 61 questions. The publisher's Git tree pins the story and
question file blob IDs in the receipt. These counts suggest potential
long-character task fit, but neither question type nor answer validity has
been checked; no source content, question, answer or provider request was
opened. No sample was selected based on an H result.

The repository says its stories derive from Project Gutenberg. The likely
underlying edition is [Yei Theodora Ozaki's *Japanese Fairy Tales*](https://www.gutenberg.org/ebooks/4018),
which Gutenberg marks public domain **in the USA**. The Japanese National
Diet Library's [author record](https://id.ndl.go.jp/auth/ndlna/01162614)
gives Ozaki's death year as 1932. The [2020 Chinese copyright law listed by
WIPO](https://www.wipo.int/wipolex/en/legislation/details/21065) states a
natural person's economic rights generally last through the fiftieth year
after death; on those facts that term ended in 1982. This is a scoped rights
inference, **not** a global permission conclusion. The exact dataset story
has not yet been matched to Ozaki's edition, and the author-team adaptation
and question rights still need item-level confirmation. These gaps keep
`model_input_allowed` and `confirmation_qualified` false.

The next source gate may compare exact files to the proposed public-domain
edition *without displaying the held-out story, questions or answers to the
implementer*. Item semantic audit and final case selection must wait for
the model/scorer/sample/cost freeze required by I01. If edition, rights or
task fit fails, exclude this candidate without looking for a favorable H
outcome. This metadata-only package makes zero provider calls, uses zero
historical grant and leaves LongMemEval sealed.

**EVALUATION_DELTA:** an independently authored, long-narrative candidate is
selected by a reproducible metadata rule and pinned to exact publisher blobs
without exposing case material. **HCL answer CAPABILITY_DELTA:** none.
