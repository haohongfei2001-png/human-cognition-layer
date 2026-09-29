# I02 — one-use EPC C/P/G v5 development calibration

**Status: frozen / provider-free preflight passed / trigger absent.** This is a
new, independent low-cost development calibration of the generic comparator,
not a rerun of either consumed MuSR or Moral Stories grant and not an H efficacy
comparison. The [package](../reports/HCL_I02_EPC_CPG_V5_PACKAGE.json),
[runner](../scripts/run_i02_epc_cpg_v5_once.py) and
[one-shot workflow](../.github/workflows/hcl-i02-epc-cpg-v5-once.yml) pin the
source selection, question, scorer obligations, prompts, model, cost and
execution hashes before any output. No trigger exists in this package commit.

## Source and rights boundary

The independent [EPC glass safety case](https://epc.ac.uk/toolkit/case-study-glass-safety-in-a-heritage-building-conversion/)
names six original authors and marks the case page
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The license
allows copying and adaptation, including commercial uses, subject to
attribution and share-alike terms. The selected model input is only the
publisher's scenario summary and dilemma part one, joined as four original
paragraphs. It excludes teaching notes, external codes/links, part-two
outcome, and facilitator aids. The package stores SHA256 and five source-first
span anchors rather than third-party case prose. The runner fetches the page
and refuses changed authorship, license, selected text or native question
before any provider call. Its raw receipt includes attribution and the license
link. This is **calibration-only approval for that exact source hash**; the
exposure firewall still prohibits confirmation use of this case, authors or
writing system.

The native open question asks what ethical issues arise. Before model output,
five weighted, source-anchored review obligations distinguish changed standards from a proved
violation, cost pressure from malicious intent, a contractor's risk claim from
measured probability, a request to conceal from actual concealment, and vague
records from certainty. Two further weighted global obligations require moral
or professional duty to remain conditional on a stated premise and forbid
silently importing an outside professional code. There is
no binary gold or HCL-authored answer target. The source and question were
selected before observing any H/provider outcome; the earlier provider-free H
entry was direct with no cognition treatment, so this run calls only C/P/G.

## Frozen call and cost boundary

- Existing `DEEPSEEK_API_KEY`; `deepseek-v4-pro` / DeepSeek-V4-Pro-0813;
  thinking disabled, default service tier, JSON output, temperature 0.
- C, P, G-map, G-final in that order; at most **4 calls**, **0 retries**;
  output limits 768/768/1024/768 tokens and 4,000 bytes for G-map.
- **USD 0.15 hard cap**, separate from all historical grants. The complete
  four-phase provider-free peak reservation is USD 0.08573136; the remaining
  guard provides room for the checked graph's added metadata in G-final.
  Actual calls reserve again before transport and may stop before G-final if
  that expanded input would exceed the cap.
  [Current provider prices](https://api-docs.deepseek.com/quick_start/pricing/)
  are pinned at USD 1.32/M peak cache-miss input and USD 3.96/M peak output;
  actual usage, rated peak cost, estimated billed cost and unavailable invoice
  cost are kept distinct.
- C/P receive byte-identical v3 ordinary user input. G-map receives the same
  complete source/question and its own generic workspace instructions;
  G-final gets the complete source plus source-checked provisional graph. All
  final outputs use `answer`, `source_citations`, `uncertainty`, `assumptions`.
  No native label, gold, H context or answer enters an arm.

The workflow requires a unique main-branch trigger, first run attempt, exact
SHA checkout and a one-run history check. It saves raw requests/responses,
model IDs, usage, costs and parsed results, including partial failure receipts.
No rerun, case substitution or old-budget transfer is permitted. After the
single run, inspect the original source first, then C/P/G outputs against the
frozen obligations. A valid G shape alone does not make G semantically
competent. Record omissions, fabricated citations, unsupported intention,
conditional norms, uncertainty and cost. Close the budget and remove the
trigger before claiming any comparator qualification. If G-map fails, G-final
is not called and this package closes as an interface failure.

**EVALUATION_DELTA:** a rights-bounded independent development source and v5
generic comparator now have a fixed one-use semantic calibration procedure.
**HCL answer CAPABILITY_DELTA:** none. **Provider calls so far:** 0.
**LongMemEval:** sealed, untouched.
