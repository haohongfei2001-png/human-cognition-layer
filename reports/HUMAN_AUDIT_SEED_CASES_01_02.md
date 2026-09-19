# Human Audit Seed — Cases 01–02

This file records the research owner's direct judgments. These are not model-generated labels.

## Case 01 — b2_059_4

### Owner judgment

> 小华似乎不知道冰箱里有苹果，所以小华会选择桌子上的苹果篮。但小丽可能知道也可能不知道：如果知道小华不知道，那么会选 A；如果不知道小华不知道，则可能会认为小华知道在冰箱里。

### Structured interpretation

- **Gold status**: questionable / underdetermined
- **Model status**: not safely classifiable as a genuine cognitive error
- **Key issue**: the story does not establish what Xiaoli believes about Xiaohua's access to the refrigerator information.
- **Reusable mechanism**: separate world truth, agent knowledge, and one agent's belief about another agent's knowledge.
- **General correction principle**: do not collapse missing second-order epistemic evidence into a single certain belief.

## Case 02 — b3_027_3

### Owner judgment

> 我更倾向 D。妈妈没拿衣架回来有很多可能：可能没找到、可能看到了小雪的行动，也可能发生了其他事情。仅凭“空手回来”不足以让小雪确定妈妈看到了她的动作。

### Structured interpretation

- **Gold status**: questionable / underdetermined
- **Model status**: model answer A is also overcommitted; the safest answer is uncertainty.
- **Key issue**: observing an outcome (mother returns without hangers) is not equivalent to knowing its hidden cause (mother saw the action).
- **Reusable mechanism**: hidden-cause ambiguity in second-order belief inference.
- **General correction principle**: maintain multiple causal hypotheses when several latent explanations are consistent with the same observation.

## Provisional reusable principles

These principles come directly from the owner's first two audits and may be reused to screen the remaining cases:

1. **Epistemic access must be explicit.**
   Narrator knowledge is not automatically character knowledge.
2. **Second-order belief requires an evidence bridge.**
   A character cannot be assumed to know what another character knows unless the story provides a credible observation/inference path.
3. **Do not infer hidden causes from ambiguous outcomes.**
   If multiple latent causes fit the same observed behavior, preserve uncertainty.
4. **Benchmark gold is not privileged when the story is underdetermined.**
   Such cases should be excluded from future HCL training targets rather than forcing the model toward the benchmark answer.
