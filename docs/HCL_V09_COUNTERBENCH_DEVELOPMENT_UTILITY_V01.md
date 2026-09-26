# HCL v0.9 Supplemented CounterBench Development Utility v0.1

Status: **completed development-only; frozen generic-tool signal**. Historical
pre-execution protocol below remains intact; its unpaid/absent-trigger statements
are superseded by the final closure. Run 36265833551: C/P/D 2/8,2/8,7/8;
D/P 5/0; USD 0.00820461 under separate USD 0.10, variable zero.
See `reports/HCL_V09_CAUSAL_COUNTERFACTUAL_FINAL_DEVELOPMENT_CLOSURE.md`.

## Public source and qualification

Dataset: [CounterBench/CounterBench](https://huggingface.co/datasets/CounterBench/CounterBench),
MIT data card, public ungated revision `c6225dfa00b7a89ccfeae67797b9a6d80e48e44c`.
`data_balanced_alpha_V1.json`: 1,000 records; SHA-256
`39f935a48fb997869c1e4488c9a2b902dc08acd876da557c675722c269391a76`.
Metadata-source file was also inspected: `meta_model_alpha_V1.json` digest
`7db1b8b46c954b815ece85ec50e80fd43f638f5fe61cf5668f6821f4ec5d8ef7`.
It is not an input to the final runner.
[CounterBench's paper](https://arxiv.org/abs/2502.11008) describes deterministic
formal tasks, but ordinary causal sentences do not alone specify biconditional
Boolean equations. We must disclose this interpretation rather than import a
hidden generator as a world-truth oracle.

Every arm receives an explicit **supplemental contract**: positive causes are
complete child=parent equations, joint/alternative parents are AND/OR, negative
children invert the parent expression, and unassigned roots are unconstrained.
The same full source and exact query observations/interventions are supplied.
This defines an adapted formal task. It does not establish natural-language
causal sufficiency, an official CounterBench score, realistic story reasoning
or unknown private mental truth. The ordinary-wording assumption is never a
default policy in `hcl/v09`.

Native `answer` values are projected away without inspection. Generator mapping,
IDs, question types and graph labels do not enter state or answers. Only public
causal clauses build the model. A generic declared-grammar adapter validates
all clauses or refuses malformed ones; no case/ID/gold shortcut exists.
Source factual observations may enter the source view; the explanation query
and its factual baseline are released after source model registration. A
question phrased as “not X instead of X” is explicitly restated as factual X=1
and alternative do(X=0) to all arms, not silently supplied only to D.

## Exposure and deterministic selection

The dataset web viewer unavoidably displayed native labels for previews in
`graph5`; that entire family is excluded. An earlier metadata example from
model 0 is in the same excluded family. No native annotation values for the
selected cases were viewed. Source sufficiency review inspected provisional
sources including malformed question 468 and structural clone 671; those are
source-exposed and cannot later be represented as sealed sources.

Salt `HCL-V09-COUNTERBENCH-DEV-V01` sorts question IDs within basic/conditional
source categories. Select four each after complete supported-grammar validation,
exclude graph5 and deduplicate the complete renamed structural equation family
across nonsense names. Selection does not use published answers, provider
outcomes or answer balance. Manifest:
`eval/v09/counterbench_dev_selection_v01.json`, digest
`8efa7bc092c8eb9cf53c9cf797a9a00a7c7f02453475f3ac796b6fd20b4c75ee`.

| Case | Source question ID | Source audit under the disclosed contract |
|---|---|---|
| cf-dev-01 | 210 | Simple complete chain; forward intervention. |
| cf-dev-02 | 822 | Negative child and OR parents. |
| cf-dev-03 | 440 | Longer chain with a negative relation. |
| cf-dev-04 | 823 | Joint parent requirements. |
| cf-dev-05 | 71 | Source observation conflicts with factual X=1 and the declared equations; preserve inconsistency, expected UNKNOWN. |
| cf-dev-06 | 818 | Multiple exogenous contexts and observed roots; preserve their actual values. |
| cf-dev-07 | 279 | Factual observation contradicts a negative descendant; preserve inconsistency, expected UNKNOWN. |
| cf-dev-08 | 216 | Observed additional root and alternative parents. |

All selected sources are manually inspected development data, not sealed
fresh efficacy. Provider-free public-model reference consequences are already
known; native gold remains withheld. All first- and later selection source
exposures above must remain excluded from any sealed transfer pool, and
structural families must be separated across aliases, not only question IDs.

The source audit found **zero** supported non-graph5 conditional examples in
this file where a consistent observed endogenous consequence adds informative
abduction beyond the factual changed root. This slice consequently tests
bounded intervention/readout and consistency handling, **not the full latent
abduction claim** motivating the direction. It cannot qualify future complete
counterfactual efficacy. Executable Counterfactuals code/math and open-domain
sources are deferred because their arithmetic/continuous/program or open-world
semantics exceed this Boolean slice; no arbitrary source-code execution or
new benchmark ontology is introduced to force coverage.

## C/P/D and public-model diagnostic

C: strong direct evidence/model/uncertainty instruction. P: same plus thin
factual-context/intervention checklist. D: same source plus the v0.9 exact
conditional computation. No provider extraction is needed for this explicit
declared grammar; its source-only parsing is provider-free and identical for
all eight cases. D archives the exact model, source view, query and per-world
calculation actually supplied to its answer model, not only hashes/counts.

All answer calls use `deepseek-flash`, thinking disabled, temperature 0, seed
42 and 256-token maximum. A model alias is not an immutable checkpoint.
Output is YES/NO/UNKNOWN plus brief reason. The independent reference scorer
enumerates all complete Boolean assignments and checks equations directly,
without the runtime's AST evaluator or topological traversal. It is built
from the same disclosed public assumptions, not native labels. Scoring happens
after all three answers; no scorer output is supplied to any arm.

Report adapted declared-model agreement, invalid outputs, all paired
 discordances, exact source/state/response hashes and full operational metrics.
A separate arm-masked diagnostic before aggregate comparison checks whether
the reason follows the source/declared assumptions, preserves factual versus
alternative scope, and handles inconsistency. Save observations before
unmasking; disclose single-agent review, visible formal assumptions and known
provider-free reference outcomes. No p-value-driven expansion or fresh tuning.

Continue further validation only if at least two P-disagreements are corrected
by D, at most one reverse, and the archived calculation supports the gain
without an unsupported equation. Otherwise simplify to C/P. Even a positive
result supports only this adapted bounded computation. A generic exact
constraint solver has the same mathematical semantics as D; there is no
specialized architecture/novel algorithm claim. Prefer a simpler generic tool
where equivalent. A future fresh comparison would require a qualified source
with genuine abduction and a competent generic executable baseline; none is
selected or authorized here. Leave these development cases after a decision.

## Separate owner cost gate

The completed v0.8 approval covered its single development check, not this
new experiment. Keep v0.9 provider-unconsumed until the owner separately
authorizes **USD 0.10**. Use the existing credential only. LongMemEval remains
sealed; no paid account/plan change is requested.

Hard call ceiling 24 (8 C, 8 P, 8 D), no SDK retries; per-answer maximum 256
tokens. Input character ceilings C=20,000/P=22,000/D=70,000, aggregate 112,000;
output ceilings 10,000 each, aggregate 30,000. Input checks stop before a
request; output-character overflow stops after that response. The shared
pre-request reserved token-cost ledger is the actual paid control. Peak
character-as-token planning bound **USD 0.0696**, ledger cap **USD 0.10**.
Missing usage/uncertain transport consumes full reservation and stops.

`HCL_V09_COUNTERBENCH_DEV_COST_AUTHORIZED_USD` is unset and its exact-parent
one-shot trigger absent. First cloud attempt only, source/selection/runtime
checks before calls, artifact retained even on partial failure; never relaunch
a consumed development result as fresh. Authorization is closed after use.
