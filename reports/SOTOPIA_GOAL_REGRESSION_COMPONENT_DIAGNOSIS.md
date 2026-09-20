# SOTOPIA Goal Regression — Component-Level Diagnosis

## Evidence source

- repeat-stability run: `35482453412`
- diagnostic Hard ordinals 10-19
- independent goal-pursuit synthetic run: `35492464682`

## 1. Decision Policy v0.1 is not the only bottleneck

The independent goal-pursuit suite produced a raw **11/12**.

The sole raw failure was taxonomic, not behavioral:
- the fixture allowed INFORMATION_PROBE / DEFER / EXIT;
- the policy chose ALTERNATIVE_PATH;
- the actual intent was to decline a legally ambiguous irreversible purchase
  and seek another lawful second-hand item.

So the synthetic audit does **not** show a broad inability to reason about:
- option decay;
- refundable holds;
- reversible commitments;
- probe budgets;
- hard infeasibility;
- irreversible high-uncertainty actions.

## 2. Repeated SOTOPIA setting 19 exposes a checker/action mismatch

In seed 43, late in the episode, the Decision Policy eventually changed from
repeated verification to an option-preserving alternative:

> buy the item now as protective temporary custody, then privately resolve the
> ownership issue and return/compensate as appropriate.

The action generator followed that plan and drafted an immediate purchase.

The generic HCL answer checker then revised it away.

Its explicit reasons were:
- unresolved ownership uncertainty;
- a prior statement that the agent would not finalize before hearing back;
- "premature collapse" of uncertainty.

This is a category error.

The candidate action did **not** claim that ownership uncertainty had been
resolved. It chose an action *under* uncertainty because the opportunity was
decaying and the Decision Policy judged the action to preserve options.

The generic answer checker conflated:

```
taking a deliberate action under uncertainty
```

with:

```
asserting that the uncertain proposition is known to be true
```

As a result, it converted an option-preserving action back into another delay.

## 3. Previous self-statements are not always immutable facts

The checker also treated the agent's earlier provisional statement
("I cannot finalize until I hear back") as if it were a world fact.

In interactive decision making:
- earlier plans can be revised when time pressure changes;
- a provisional strategy is not automatically a hard constraint;
- changing strategy is not a factual contradiction if the agent does not
  misrepresent what happened.

The action checker must distinguish:
- world facts;
- explicit commitments / consent boundaries;
- provisional intentions;
- updated strategy.

## 4. Seed 44 shows Decision Policy variability still exists

In seed 44, the policy never made the same late option-preserving switch and
ultimately exited.

Therefore the Decision Policy is not declared solved.

However, because:
- the independent synthetic option-value suite is semantically strong; and
- seed 43 demonstrates a correct policy decision being actively blocked by the
  generic checker,

the **first engineering repair target is the checker interface**, not another
large Decision Policy rewrite.

## 5. Required architecture change

Replace the generic answer checker in SOTOPIA with an action-specific checker:

```
HCL cognition state
    ↓
Decision Policy
    ↓
candidate action
    ↓
HCL Action Checker
    ↓
final action
```

The Action Checker must ask:
1. is the action type allowed?
2. does the action violate a hard constraint or explicit consent boundary?
3. does its *language* assert uncertain information as fact?
4. does it invent material information?
5. does it materially diverge from the Decision Policy without justification?
6. if the plan intentionally acts under uncertainty, does the action preserve
   the stated contingency / reversibility?

It must **not** reject an action merely because uncertainty remains.

## 6. Next validation

Before SOTOPIA integration:
- test the new checker on independent synthetic action fixtures;
- include paired cases where the same unresolved uncertainty yields:
  - PASS for a reversible/conditional action;
  - REVISE for an irreversible or falsely certain action.

After the synthetic gate:
- integrate the checker;
- do not reuse Hard 10-19 as fresh evidence;
- validate on previously unused Hard settings.
