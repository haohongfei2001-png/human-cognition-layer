"""Self-authored public source text only; no candidate JSON, gold or provider call."""
BASE = (
    "Original finite thought experiment. A operates a valve; B has two goals, safety and completing a hazardous duty. "
    "At time 0 both A and B observe that the passage is open, A's valve setting is active, no external fault is present, "
    "and the causal theory is available to them. At time 1 the valve setting becomes inactive and an external fault occurs; only A sees these changes. "
    "At time 2 both observe the passage closing. At time 3 A offers a truthful report stating that the valve setting is inactive and an external fault is present. "
    "RECEPTION "
    "For the time-2 closing event only, the sole proposed structural theory, available to B throughout, is loss = action or external. This local event theory is not an equation for the earlier time-0 open state. "
    "Here action means A's active valve setting, external means an external fault, and loss means the closed passage. "
    "For the valve contribution question compare action=1 with action=0 while holding the other cause fixed, with loss=1 as the outcome. "
    "The actual time-2 structural observations are action=0, external=1 and loss=1; these observations are not automatically B's beliefs. "
    "Use a finite one-step plan with states open, closed, success, harm and waiting; the last three are terminal. "
    "The available, feasible actions are cross and wait, each with zero cost. Cross leads from open to success and from closed to harm; wait leads to waiting. "
    "Both actions leave terminal states unchanged and have the same observation. The graph's utility is success=1, harm=-1 and all other states=0. "
    "The safety goal's consequences are open=3, closed=-3, success=5, harm=-5, waiting=-1; the duty goal has the opposite value in each state. "
    "Compare B's initial appraisal at time 2 with reappraisal at time 3. Each episode uses the earlier open state with probability 1 and the current closed state with probability 1, "
    "and evaluates cross as the forecast action. Before any attention adjustment, safety has priority 1/4 and duty 3/4. "
    "A proposed problem-focused coping hypothesis multiplies safety priority by 9 only if safety desirability is negative and the valve contributes to loss; duty's multiplier remains 1. "
    "A proposed emotion mapping calls negative safety with valve contribution 'other-contribution distress'; negative safety when the valve cause is not actual is called 'situational-loss distress'. "
    "These are explicit experimental hypotheses, not psychological laws, moral blame, intentions or enacted actions."
)
QUESTION = "Compare B at times 2 and 3. Derive character-relative causal attribution, competing appraisal and the best one-step coping action using the stated hypotheses. Distinguish B's access from the analyst's observations and retain any uncertainty."
CASES = (
    dict(case_id="accepted-report", source=BASE.replace("RECEPTION", "B receives, understands and accepts the report at time 3."), question=QUESTION),
    dict(case_id="missed-report", source=BASE.replace("RECEPTION", "B misses the report at time 3 and receives no new information about the valve or fault."), question=QUESTION),
)
