# HCL v0.7 External Benchmark Audit v0.1

Status: **SOURCE AUDIT / NO PROVIDER CALLS / NO v0.7 OUTCOME CONSUMED**

The v0.7 capability is intention, goal and action reasoning under an evidence
constraint. A label inferred from a hidden character plan is not automatically
truth about the public narrative. Candidate labels need public support or must
be treated as human judgments with uncertainty.

## Candidate sources

| Source | Public evidence and labels | Decision |
|---|---|---|
| [SAGA](https://github.com/saiumbc/SAGA) | Crowdsourced goals, action explanations and goal-change judgments over short narratives and alternatives; human ratings include goal coherence, faithfulness and truthfulness. | **Primary development candidate**, conditional on per-case evidence audit. Treat inferred goals as plausible human judgments, not unique private truth. |
| [Moral Stories](https://github.com/demelin/moral_stories) | Human-written situations, explicit intentions, actions and consequences. | **Secondary explicit-goal/action check**. Useful for grounding; weak as a test of inferring a hidden motive because intention is supplied. |
| [OpenToM](https://github.com/seacowx/OpenToM) | Narrative and psychological-state questions, with actions designed from character intentions. | **Defer** until question/gold construction is audited for public-narrative sufficiency; generated intent can be hidden-state truth. |
| [MulTivationBench](https://github.com/HKUST-KnowComp/MultivationBench) | Visual sequential motivation questions with human review. | **Defer** for the text-first minimal runtime; requires image evidence and a separate multimodal adapter. |
| DynToM | Earlier CQ-00 audit found three of four sampled belief labels stronger than public narrative evidence. | **Reject as primary v0.7 evidence** under the current strict boundary. |

SAGA repository main at this audit:
`9c66afefb06b8bad77fc7f5913ddc8264a57c69b`. The public
`data/actual_test.jsonl` blob is `a4dee51652b35f1b04ec80e08ae6174b3d1eb0d9`
and SHA-256 is
`a00ed709011dfdcb2016b0bb25753eaca4445afdbf8ae87bf4b33c213e415764`
(219 records). Only 67 of those records expose a `goal_revision` field, so a
goal-change utility slice needs a specific inventory instead of assuming every
record supplies that label. No model outcome was observed during this audit.

SAGA's goal labels are crowdsourced interpretations of narratives; the sample
inspected includes uncertainty and alternative goals. A small V07-C utility
check should therefore score evidence-grounded goal recognition or calibrated
agreement with human judgments, preserve disagreements, and not call a
plausible alternate motive wrong by fiat. Before any provider run:

1. Pin a disjoint development slice and manually audit public evidence versus
   labels without using the selected cases to tune runtime rules.
2. Keep narrative construction separate from released task/answer; preserve
   source, question and gold hashes.
3. Use one model and equal answer budgets for C/P/D; freeze a competent generic
   G before a later fresh pilot.
4. Record calls, characters, wall time, repairs and paired outcomes. A fresh
   set remains sealed until mechanism and protocol are frozen.

SAGA's repository has no declared license metadata in its GitHub repository
record at this audit. Public availability supports source inspection; any
redistribution of its raw narratives requires a separate rights check. The HCL
repository should store hashes and IDs, not raw stories.
