# I02 — bounded rights and privacy source screen v3

**Outcome: two systems rejected; zero independent items qualified.** This
screen was made before any provider input or answer inspection. It records
source-system exposure and introduces a fail-closed qualification wrapper
without changing the historical v2 lineage file, which is hashed into a
consumed EPC package.

The [OpenStax *Organizational Behavior* critical-thinking case](https://openstax.org/books/organizational-behavior/pages/13-critical-thinking-case/)
has a native case question and an apparent CC notice, but its publisher page
also says that the book may not be ingested into large language models or
generative AI offerings without OpenStax permission. No such permission is
present. This book's writing system is therefore **not approved for model
input**. The license line alone does not override the explicit publisher
restriction; this is a conservative source-selection decision, not a legal
interpretation of the license.

The [Open Oregon *Esther's Story* activity](https://openoregon.pressbooks.pub/contempfamilies2e/chapter/oo4-8/)
marks the adapted text and questions CC BY 4.0, but describes a potentially
identifiable refugee family and a missing child, citing an earlier account.
Its privacy/fictionalization status is not established by the license. The
story and questions were visible during this screen, so this writing system
is development-exposed and **not approved for model input or unseen
confirmation**. No additional private person material was collected.

The [versioned screen receipt](../reports/HCL_I02_SCREENED_SYSTEMS_V3.json)
contains URLs, writing-system IDs and rejection reasons, not case text,
questions or labels. The [v3 guard](../scripts/i02_source_qualification_v3.py)
composes the historical exposure check with a canonical HTTPS source URL and
source-first audit binding: exact source/question hashes, a license evidence
URL, explicit permission for this model use, privacy review, native-question
review, an outcome-independent reviewer assertion and zero viewed
confirmation outputs. It rejects either screened publisher URL prefix or
writing-system ID even if a row ID changes. A mirror or renamed source still
requires an independent historical exposure review; this short denylist is
not a repository-wide proof. The test's passing synthetic fixture is an
interface witness, **not** a real qualified external source. Audit fields are
reviewer assertions; code cannot itself prove that a rights or privacy review
was sound.

**EVALUATION_DELTA:** a positive CC license can no longer silently promote
these two exposed systems through the new I02 source gate when provider-use
terms or privacy remain unresolved. **HCL answer CAPABILITY_DELTA:** none.
**Provider calls/spend:** 0 / USD 0. **LongMemEval:** sealed. Continue with
genuinely unexposed, rights-clear source systems and native questions; do not
substitute these rejected rows under new names.
