# I02 — second-source one-use C/P/G functional calibration

Status: **FROZEN / NOT EXECUTED**. This package tests whether the repaired
generic source-map interface can actually operate beside C and P on a
different independently authored source system. It is not an H comparison or
independent HCL efficacy evidence. The only exposed record is the **first**
record of the author-team [Moral Stories Hugging Face distribution](https://huggingface.co/datasets/demelin/moral_stories),
fixed before reading it. Its official card identifies MIT licensing, original
crowdsourced seven-sentence stories and two alternative action/consequence
paths; the [author repository license](https://github.com/demelin/moral_stories/blob/master/LICENSE)
is MIT. No test/confirmation record or label is used. The dataset-card examples
and this first record are exposed development material and must be excluded
from future unseen confirmation.

The pinned full file SHA256 is
`98a62d4a083e02ba234ca3d4f2312df6c337ef10cd3f12dcf917a2957ba59c10`
at author-team distribution commit `b830cf56eb00bc4edd1860dd544a192216eb3587`;
the first line SHA256 is
`47412695b214e8ba181d8cc8376001d84e3077436e181834b1b9c5d99b456cb9`.
The [source adapter](../scripts/i02_moral_calibration.py) checks the full-file
hash and parses only that first line. It replaces the dataset's `moral` and
`immoral` field names with neutral **Alternative A/B** names in every model
input; the source-reported norm is a premise, not universal moral truth. The
source's goal to add security does not establish an intention to harm from a
reported injury in one alternative. The two consequences belong to separate
reported paths, not one actual timeline.

The [frozen package](../reports/HCL_I02_MORAL_CPG_CALIBRATION_PACKAGE.json)
pins the source, source adapter, question, model, prompts, runtime digest,
workflow, four phases and budget. The [provider-free preflight](../reports/HCL_I02_MORAL_CPG_CALIBRATION_PREFLIGHT.json)
checks complete common source/question, final answer vocabulary, distinct
intermediate G-map contract, source/license metadata, source hash and all-phase
peak reservation.

- C: one direct `deepseek-v4-pro` call with the complete source.
- P: one process prompt with the same complete source and final answer fields.
- G: one intermediate exact-quote map call with `source_index` and
  `open_questions`, followed by one final call that retains the complete
  source/question and the same final answer fields as C/P. The map is checked
  against the original source before G-final.
- Thinking disabled, temperature zero, provider default tier, zero retries;
  maximum output tokens 768/768/1024/768. At most four calls in that order.
- **USD 0.06 hard cap**. The published peak-rate all-phase reservation is
  USD 0.05820672. The runner reserves before every call, stores every raw
  request/response and usage, and closes unused authorization after success
  or failure. Rated/usage-estimated cost is reported; invoice cost may be
  unavailable.

The existing `DEEPSEEK_API_KEY` is used only by the unique one-shot
[workflow](../.github/workflows/hcl-i02-moral-cpg-calibration-once.yml), after
this freeze merges and a separate trigger passes exact-head CI. The workflow
rejects repeated runs and uploads partial raw artifacts on failure. There is
no new account, credential, billing plan or historical budget transfer. The
MuSR C/P/G calibration has already closed and is never rerun. H/H-new and
LongMemEval receive zero calls. The first row here is a **different source
family**; any C/P/G functionality result remains calibration-only and cannot
qualify all four task families, three writing systems or two model families.

After one run, inspect original source first, then exact citations, alternative
path separation, actor intention/knowledge claims, G-map shape, G-final source
use, model IDs, usage and cost. Mark the comparator interface qualified only
to the extent actually demonstrated. Do not turn a source norm or generated
path label into moral truth, and do not tune a later confirmation selection to
an H result. No frozen question, source, prompt, arm, output contract or budget
may change after the trigger.

**EVALUATION_DELTA:** C/P/G v2 can be functionally tested on an independent
writing system under a source- and budget-locked protocol. **HCL cognition
CAPABILITY_DELTA:** none in this freeze; the preceding I02 v2 repair is the
current provider-free cognition gain.
