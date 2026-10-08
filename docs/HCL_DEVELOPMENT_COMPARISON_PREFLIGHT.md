# Ordinary development comparison preflight

`scripts/development_comparison_preflight_v1.py` proves a small comparison's
control flow with injected synthetic responses. It uses the current ordinary HCL
entry and the existing citation/native replay helpers. It does not invoke a model
or introduce a live executor, authorization, launch marker or semantic pass gate.
Current development priority remains the Development Reality Check in `STATUS.md`.

## Fairness contract

- Base receives the complete question and sources in one 16,384-token, **high**
  reasoning request. It has no HCL planning/native-treatment requirement.
- HCL receives the same complete question/source text, IDs and versions, with
  its current 16,384/high planning and 16,384/low final configuration. Full wire
  requests remain limited to 36,000 UTF-8 bytes, with no truncation.
- HCL uses ordinary `required_checked_capabilities=()`. Actual native execution
  is still necessary before its final. A real insufficient-evidence result can
  support an honestly limited answer. Empty/explicitly insufficient plans do not
  get a Base fallback. Checked treatment and relevance are distinct from delivery.
- Native source/argument/result integrity is replayed before HCL final admission;
  that replay does not certify relevance. Both arms use the same explicit-source
  citation acceptance rule. All returned final bytes, including rejected answers,
  stay in the synthetic original.
- One or two input cases are supported. The fixed order is Base/HCL for the first
  case and HCL/Base for the second. Known bounded output/native failures remain in
  the denominator; unknown synthetic transport or integrity failures stop later
  arms, which remain `NOT_ATTEMPTED`. There are no retries or replacement cases.
  This free design control does not authorize continuation in a future paid run.
- All HCL calls and synthetic wall time are retained. This compares a strong Base
  with ordinary HCL, **not matched compute**. Fake timings are not model latency.

Only explicit model-input fields enter the wrapper. Gold answers, evaluator
rubrics, callbacks and transport objects are rejected. Input snapshots start at
version 1; the wrapper does not normalize a supplied different version. It uses
no source-specific route, required capability family or expected-answer lookup.

## Evidence and limits

`run_synthetic` returns complete synthetic request/response events, the runtime
receipt and original native capture. `save_original` creates one local file
exclusively and returns its byte hash. `load_original` requires that independently
retained hash; a changed file with a newly computed hash is not the original.
This is local synthetic evidence, **not a private storage route for a live run**
and not a public exporter. It never emits a semantic-success approval.

At the historical peak-rate arithmetic of CNY 9/27 per million input/output tokens,
each maximum wire request plus the 32-token output margin has a 1.109664 CNY bound.
Two complete comparison cases would require at most six calls and 6.657984 CNY
under those assumptions. This is not a current price check, invoice, requested
budget or authority. Any live study still needs a suitable frozen task set,
independent source/executor reviews, current price admission, explicit failure
policy and a new bounded authorization. All previous grants remain closed.

## October 8 bounded source screen

The original seed selected at most three candidates in each of ConditionalQA and
FairytaleQA. Before viewing the final three native questions, a task-fit amendment
required nonadjacent source synthesis plus multi-agent information/goals, nested
perspective or conflicting evidence. It did not select by gold answers, native
checked results, model performance or rewritten questions.

The original six-candidate limit produced **no eligible pair**:

- ConditionalQA `dev-43`: complete HCL planning request 37,401 bytes; rejected.
- ConditionalQA `dev-232`: explicitly listed account categories; task fit weak.
- ConditionalQA `dev-203`: the source's last paragraph directly answers the native
  question; task fit weak.
- FairytaleQA `why-dog-and-cat-are-enemies#4`: explicit first-paragraph cause;
  task fit weak.
- FairytaleQA `the-page-boy-and-the-silver-goblet#41`: its native question is
  answered in one section despite the richer surrounding story; task fit weak.
- FairytaleQA `peerifool#54`: complete HCL planning request 47,666 bytes; rejected.

All candidates and rejection reasons remain recorded. No replacement source,
new seed, shortened source or paid proposal was created. This shortfall is a
source-set/task-fit result, not a new runtime execution failure.

The attempted historical overlap scan was invalidated after programmatically
reading 44 protected-associated blobs due to an incorrect exclusion. Their bodies
were not output to the model, uploaded or sent to a provider, but the reads count
as exposure. The invalid scan's zero matches cannot establish novelty. Later
synthetic metadata-guard repairs do not undo this incident; real history scanning
remains stopped. Current-register absence also does not establish novelty.
Candidate status stays `DEVELOPMENT_EXPOSED_PRIOR_HISTORY_UNKNOWN`; no I02 or
sealed qualification is claimed. The successful PR420 exposed-case result is
unchanged and is not evidence of Base improvement.

Two possible later designs, neither started here, are clearly labeled original
synthetic contrasts for mechanism diagnosis, or a separately bounded public-source
screen with the task-fit rule fixed before reading. Synthetic contrasts offer
controlled differences but cannot establish external generalization. Public tasks
offer external validity but add rights, exposure and capacity uncertainty.

Run the dependency-free synthetic checks with:
`python -m unittest tests.test_development_comparison_preflight_v1`.
