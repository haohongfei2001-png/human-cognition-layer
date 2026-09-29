# I02 — one-use C/P/G functional calibration

Status: **FROZEN / NOT EXECUTED**. This is a calibration of baseline interfaces,
not an H comparison or independent efficacy experiment. The single input is
the first already exposed question from the first narrative group of the
[author-team TAUR-Lab/MuSR Hugging Face CC BY 4.0 distribution](https://huggingface.co/datasets/TAUR-Lab/MuSR).
The exact CSV SHA256, source-group SHA256, case ID, model, execution hashes,
prompts, phases, output contract and budget are in the
[frozen package](../reports/HCL_I02_COMPARATOR_CALIBRATION_PACKAGE.json). The
[provider-free preflight](../reports/HCL_I02_COMPARATOR_CALIBRATION_PREFLIGHT.json)
checks those bytes, equal ordinary question and complete source, no native
answer fields, current runtime amendment and the all-phase cost reservation.
The source's reported glimpse at a desk makes a desk-based answer plausible;
actual future search and private belief are not source facts. The second
question in this group has unresolved perceptual support and is excluded.

- C: one direct `deepseek-v4-pro` call with complete source.
- P: one independently written process prompt and complete source.
- G: one generic source-map call and one final call receiving both the complete
  source and exact-quote-validated map. All four calls use the same output
  fields: `answer`, `source_citations`, `uncertainty`, `assumptions`.
- Thinking disabled, provider default tier, temperature zero, no retries;
  output limits 768/768/1024/768 tokens. At most four calls in order.
- USD 0.12 hard cap using published peak Pro rates of USD 1.32/M input miss and
  USD 3.96/M output. The provider-free all-phase reservation is below the cap.
  The runner reserves before each call and closes unused authorization after
  success or failure. Usage-based rated and estimated actual cost, raw request,
  response and actual model ID are saved; invoice cost is unavailable.

The repository's existing `DEEPSEEK_API_KEY` is used only in the one-shot
[workflow](../.github/workflows/hcl-i02-comparator-calibration-once.yml) after
the frozen package and workflow merge. The trigger is separate and unique;
the workflow rejects reruns and uploads raw artifacts even on failure. No new
credential, account or billing plan is required. The calibration gives C/P/G
functional feedback only; it cannot qualify all four task families, all source
systems, a second model family, or H treatment. The post-repair native H
preflight still fails with zero checked observations, so **H and H-new receive
zero calls here**. Native answer/gold, confirmation items and LongMemEval stay
outside all requests.

After the single run, inspect original source first, then every raw response,
exact quote, access/time claim, necessary inference, JSON field and cost. Mark
which baseline parts work and which require generic repair. Do not use native
gold as a private-belief oracle, and do not choose a case based on H performance.
The exposed HF dataset viewer also showed unrelated murder-mystery examples;
that split must not enter a future unseen confirmation set in this agent's
evaluation sequence.

**EVALUATION_DELTA:** the strong-base, process and generic-scaffold candidates
can receive bounded real-provider functional calibration with complete source
and cost accounting. **CAPABILITY_DELTA:** none; the separately merged I02
information-state repair is the latest cognition gain. This run does not modify
HCL runtime or historical evidence dispositions.
