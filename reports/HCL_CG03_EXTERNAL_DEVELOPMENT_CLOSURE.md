# HCL-CG-03 source-first Phase E closure

**Disposition: RETAIN — bounded development evidence only. One run consumed.**

Retain the explicit optional source/time/access factor and caller-premise checker.
Its useful delta here is preventing unsupported factor and premise promotions.
No default activation, broad responsibility competence, private intention truth,
independent/fresh external evidence or general efficacy claim follows. These are
four HCL-authored synthetic development cases, exposed with source/gold/prompts.

## Run identity and frozen authorization

- Authorized baseline: `main@1c784d87c104e5a0056eddfa92bd7862133c59bc`.
- Frozen package SHA-256: `e76c0fa13bc9c9f4f9c1de9f5986791621e3cd6e9bbdcf0f7d018463d00876e8`.
- Activation PR [#132](https://github.com/haohongfei2001-png/human-cognition-layer/pull/132): exact-head provider-free run 36427140836; exact-main run 36427243328 on `b375949c2d32403148c85cffe59bfe9da4ab4310`, 118 v1 + 176 historical PASS.
- Unique trigger PR [#133](https://github.com/haohongfei2001-png/human-cognition-layer/pull/133): exact-head run 36427513870; sole trigger addition merged as `4448b141c2a3ffcb7bb2ee3f359d320e72d2c5a1`; exact-main provider-free run 36427668767 PASS.
- [Paid run 36427668859](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36427668859), attempt 1, SUCCESS; artifact ID `10972111450`.
- Downloaded ZIP SHA-256 `cf7601f702564dca780e9ad4c679cb9b0b8cbdddd3174d5d4340ef6f3816faaf`, independently matched to GitHub's artifact digest and extracted result bytes.
- [Complete raw receipt](HCL_CG03_EXTERNAL_RUN_36427668859.json), byte-preserved `results.json`, SHA-256 `cc0c9a7187a3221853a163e0e62f8a7340b0d4c37048c7947c99d7f31aa661da`.

The raw receipt includes all 20 request payloads and full returned API objects,
actual answer text, usage, costs, per-arm scores and H/H-new final inputs and
treatment receipts. The journal and completed results were identical. Every
request and final input matched the frozen package exactly and the original
scorer recomputed identically. No case, gold, prompt, scorer, arm, treatment,
budget basis or sample was changed. All four preflights passed again in the
paid workflow before any provider call: anchored action/outcome, source validity,
five executed factor checks, executed premise checks, checked state in H,
removal in H-new, and input difference solely from that checked state.

## Provider, usage and cost

Exactly **20 calls, zero retries**, all `stop`, with the existing DeepSeek secret,
thinking disabled, JSON response mode, max output 512 and no service-tier
parameter. All returned model IDs were `deepseek-v4-pro`; the frozen/provider
published version is `DeepSeek-V4-Pro-0813`, while the returned alias alone does
not independently attest a backend revision.

Usage totals: **22,464 input and 1,857 output tokens**. Conservative frozen peak
all-cache-miss rating: **USD 0.03700620** under the **USD 0.30 hard cap**. The
cache-hit/miss and timestamp-based published-rate estimate is **USD 0.01768646**.
No billing invoice was returned or independently verified; do not label the
estimate a verified account charge. The hard-cap ledger used the conservative
rating and checked reservations before each call. No historical budget transfer,
new account/credential/paid plan or LongMemEval access occurred.

| Arm | Exact fields | Complete cases | Input / output tokens | Conservative rated USD |
|---|---:|---:|---:|---:|
| C | 19/28 | 1/4 | 1,390 / 390 | 0.00337920 |
| P | 21/28 | 2/4 | 1,546 / 375 | 0.00352572 |
| G | 20/28 | 1/4 | 1,789 / 376 | 0.00385044 |
| H | 28/28 | 4/4 | 10,562 / 347 | 0.01531596 |
| H-new | 23/28 | 2/4 | 7,177 / 369 | 0.01093488 |

## Source-first review

All arms received the same seven-field output contract and full label vocabulary,
the same focal question, normative rule and structured requirements. All 20
answers complied with that contract. P explicitly separates factor evidence;
G offers generic ordered source rows. Unlike CG-02, their errors below cannot
be explained by missing enum labels. They are the frozen competent simple and
generic comparison methods under the same provider configuration; qualification
here does not claim that every possible prompt/model configuration was tested.

1. **Explicit factors.** The narrator explicitly asserts cause and control;
   Alice reports action-time knowledge, expectation and intention. Every arm
   correctly labels all five as source-supported claims and the two-condition
   caller basis as conditionally supported. No increment on this easy case.
2. **Later learning.** The source says Alice learned about the weak latch
   afterward, without saying this was her first knowledge. It supplies no
   action-time control evidence. H preserves knowledge/control UNKNOWN and
   the knowledge-dependent premise UNRESOLVED. C turns later learning into
   contradicted knowledge; P invents control and rejects the premise despite
   unknown knowledge; G promotes later learning to action-time knowledge,
   invents control and supports the premise. H-new also invents control and
   changes unknown knowledge into contradiction. These are substantive time,
   evidence and premise-boundary errors.
3. **Third-party intention.** Bob reports what Alice supposedly said. The
   source supplies no explicit causal link or control evidence. H preserves
   ATTRIBUTED_ONLY intention, other factors UNKNOWN, and the rule UNRESOLVED.
   C promotes Bob's report to supported intention and a supported premise.
   P preserves attribution but invents cause/knowledge/foreseeability/control
   and treats unresolved intention as a failed condition. G invents cause/control,
   discards the available attribution and rejects the premise. H-new preserves
   intention attribution but labels cause ATTRIBUTED_ONLY without a causal
   claim and rejects the unresolved premise. H's advantage concerns distinct
   source factors and conditional evaluation, not a moral verdict.
4. **Explicit no control.** The narrator explicitly denies action-time control.
   H, P and H-new correctly leave unrelated factors UNKNOWN and mark the
   control-dependent rule conditionally unsupported. G adds an unsupported
   causal link; C additionally invents negative knowledge/foreseeability.
   No H increment over P/H-new on this case.

H exceeds both qualified P and G on meaningful boundary behavior, and the
H-new losses on the two difficult cases support attribution to the checked
CG-03 state. The final inputs differed only by that state. H had no observed
reverse error in this four-case review. This supports the predeclared **RETAIN**
rule for the bounded prototype. It neither estimates a population effect nor
establishes broad cognition, and the JSON-only task does not test natural-language
moral advice or all perspectives.

H costs **4.34x P** and **3.98x G**, exceeding the plan's eventual typical-cost
maturity target. On this package the added source/time/premise safeguards and
five-to-eight fewer semantic errors justify preserving an **explicit optional**
checker at about USD 0.00383 rated per case. They do not justify making it the
default path or claiming the maturity/cost gate has passed. Context cost and
independent transfer remain limitations for later stages. No budget or sample
expansion follows from RETAIN.

## Closed grant and next capability

The package and its synthetic source family are consumed for this comparison.
The USD 0.30 grant is closed at zero, unused money is not transferred, and the
unique trigger is removed with automatic triggering disabled. No rerun,
additional samples or new paid experiment is authorized. The frozen conclusion
is development-only RETAIN; independent external validation stays a later stage.

Proceed from `DEVELOPMENT_PLAN.md` section 8 to the next minimal capability:
**contextual value conflict and preference**. Represent explicit preferences
under a source-bound actor/role/context, preserve unresolved conflicts and local
changes, and avoid global fixed weights or inference from a choice to a lasting
value. This is implementation work, not a benchmark/source search.
