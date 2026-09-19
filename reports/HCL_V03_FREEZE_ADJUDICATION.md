# HCL v0.3 Freeze Holdout Adjudication

Run: `35415237645`

Raw independent result:
- **17 / 18**
- mode accuracy: **94.4%**
- uncertainty accuracy: **94.4%**
- schema validity: **100%**

## Sole failed case: h16_strong_prior_but_not_unique

Scene:
> 外面刚下过大雨。小齐从室外进来，裤脚全湿，手里拿着一把正在滴水的伞。没有说明他刚才具体去了哪里。

Question:
> 为什么小齐的裤脚和伞是湿的？

Fixture expectation:
- CAUSAL_AMBIGUITY
- medium/high uncertainty

HCL output:
- SIMPLE
- low uncertainty
- one dominant hypothesis: recent rain / outdoor rain exposure
- explicitly notes that exact location/activity is unknown but irrelevant to the coarse question.

## Adjudication

The HCL output is consistent with principles fixed **before this holdout**:

1. minimal sufficient model;
2. ordinary contextual assumptions are allowed when strongly supported;
3. merely logical alternatives should not be manufactured into decision-relevant uncertainty;
4. uncertainty is evaluated at the granularity of the question.

The question is not “exactly where was Xiaoqi and precisely how did each drop get there?” It asks for the coarse cause of wet trousers and a dripping umbrella immediately after heavy rain.

Therefore the fixture expectation overstates ambiguity.

This does **not** convert the historical raw result into 18/18. The raw fresh score remains 17/18. The case is recorded as a fixture-design error discovered by the frozen principles.

## Freeze decision

No new systematic representation failure was found in the final holdout.

HCL v0.3 **state semantics are frozen**.

The next work moves to answer-loop integration and then multi-turn social evaluation.
