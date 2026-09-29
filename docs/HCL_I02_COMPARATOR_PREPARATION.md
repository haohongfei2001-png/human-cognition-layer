# I02 — fair comparator preparation (partial)

Status: **C/P/G CANDIDATES IMPLEMENTED / NOT QUALIFIED**. I01's frozen
architecture and evaluation question remain unchanged. This packet prepares
three provider-free message paths from **one identical ordinary question and
complete authorized source**. The common answer contract is `answer`,
`source_citations`, `uncertainty`, `assumptions`; none is HCL-specific.

- **C:** direct strong-base answer with the full source and evidence citation
  contract. No native model reasoning capability is disabled here; model choice
  and reasoning configuration still require I02 qualification.
- **P:** a strong process prompt asks for source, actor, access, time,
  alternatives, counterevidence and normative-premise discipline, while still
  answering necessary supported inferences.
- **G:** a separately charged generic evidence-map call indexes original
  quotations, reports, contrary claims and unknowns. A final call receives
  both the *complete original source* and the map. Source ID and exact quote
  presence are checked; invalid mappings fail rather than silently disappear.
  The map is model-produced working material, not independent source evidence.

The [preparation code](../scripts/serious_eval_arms.py) makes zero provider
calls. Five tests cover identical input and answer fields, two opposed source
reports reaching G final, unauthorized/unsupported quote refusal, invalid map
refusal, and bounded ordinary input. The authored test witness is engineering
evidence only. It does not show C/P/G competence, source independence, model
parity, treatment presence in H, output quality, or H gain.

**EVALUATION_DELTA:** a generic comparator can now do real two-step source
indexing while retaining the complete original source; G's extra call is
explicitly charged. C and P have equally complete input and output contracts.
**CAPABILITY_DELTA:** none claimed; the post-G-ARCH main line is external
evaluation, not architecture expansion.

Next within I02: source provenance/license/access and task-fit screening; then
calibrate current strong C, P and G on a separate development/calibration
split without viewing H's confirmation results. Freeze model IDs, service
settings, prompt versions, generic map contract, output scorer, sample size,
cost/latency bands and confirmation selection before I03. A shallow or broken G
must be repaired before comparison, not scored as a valid baseline. No paid
call, credential setup, LongMemEval access or leaderboard selection occurred.
