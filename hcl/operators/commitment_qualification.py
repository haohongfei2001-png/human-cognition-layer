"""Conservative state qualifications over one actually computed M07/M03 history.

A bookkeeping status is not proof that unproved fulfillment or activation is false. No second mental state is constructed and no later event is backfilled.
"""

from itertools import product

from hcl.operators.interaction_model import receipts, qualified_commitment_history


def commitment_condition(reference, interaction, result_id, remaining):
    output = dict(
        reference=reference,
        status="UNCOMPUTED",
        possible_values=(False, True),
        result_id=result_id,
        history=None,
        original_terms=None,
        assumption_environments=(),
        evidence_events=(),
        possible_statuses=(),
        state_completion_complete=False,
        explored_completions=0,
        completion_scope="CONSERVATIVE_CARTESIAN_QUERY_MARGINALS_NOT_JOINT_TRAJECTORIES",
        frontier=[],
        work=0,
        scope="DECLARED_M07_STATE_QUALIFICATION_NOT_PRIVATE_INTENTION_OR_MORAL_VERDICT",
    )
    if remaining < 1:
        output["frontier"].append("COMMITMENT_BUDGET_FRONTIER")
        return output
    output["work"] = 1
    if interaction is None:
        output["frontier"].append("COMMITMENT_UNCOMPUTED")
        return output
    actual = next(
        (
            c
            for c in interaction["commitments"]
            if c["commitment_id"] == reference["commitment_id"]
        ),
        None,
    )
    if actual is None:
        output["frontier"].append("COMMITMENT_UNCOMPUTED")
        return output
    source = interaction["inputs"]
    at = reference["at"]
    terms = actual["terms"]
    output["original_terms"] = terms
    # Reuse the *actual* existing M03 events and M07 fact queries. Re-evaluate
    # only the bounded lifecycle prefix, never the cognition or causal model.
    deliveries, interpretations = receipts(source, interaction["actual_mental"])
    acts = [a for a in source["acts"] if a["at"] <= at]
    message_ids = {terms["offer_id"]} | {
        a["id"] for a in acts if a["refers_to"] == terms["offer_id"]
    }
    source_events = {e["id"]: e for e in source["mental"]["events"]}
    event_ids = {
        d["event_id"]
        for u in source["utterances"]
        if u["id"] in message_ids
        for d in u["deliveries"]
        if source_events[d["event_id"]]["at"] <= at
    }
    computed = {
        e["event_id"]: e
        for e in interaction["actual_mental"]["values"]["models"][0]["events"]
    }
    evidence = [computed[e] for e in sorted(event_ids) if e in computed]
    output["evidence_events"] = evidence
    # A withdrawn or unexplored receipt cannot establish that acceptance never
    # occurred. Fully specified *unreceived* deliveries remain distinct.
    if any(
        e not in computed or computed[e]["computation"]["status"] != "APPLIED"
        for e in event_ids
    ):
        output["frontier"].append("COMMITMENT_RECEIPT_UNRESOLVED")
        return output
    facts = [f for f in actual["facts"] if f["at"] <= at]
    # relevant_times includes every event, act, offer, deadline and model end.
    # Between those instants this finite model has no additional transition.
    # Passing an arbitrary consumer time to the lifecycle would fabricate a
    # query-less row whose default unknown marginals can change CURRENT state.
    # Replay only the last actually queried prefix; never invent a new fact.
    prefix_at = max(
        (fact["at"] for fact in facts), default=min(at, terms["offered_at"] - 1)
    )
    prefix = qualified_commitment_history(
        terms,
        facts,
        acts,
        [d for d in deliveries if d["at"] <= at],
        [i for i in interpretations if i["at"] <= at],
        through=prefix_at,
    )
    output["history"] = prefix
    conditions = {a for f in facts for a in f["assumption_environments"]}
    conditions.update(
        a
        for d in (*deliveries, *interpretations)
        if d["at"] <= at and d["message_id"] in message_ids
        for a in d["assumption_environments"]
    )
    output["assumption_environments"] = tuple(sorted(conditions))
    # The lifecycle's invalid-act record is not proof that one of several
    # retained readings never accepted the original terms. Keep that disjunction.
    for act in acts:
        if act["refers_to"] != terms["offer_id"] or act["kind"] not in (
            "ACCEPT",
            "REFUSE",
        ):
            continue
        if act["kind"] == "ACCEPT" and (
            not terms["requires_acceptance"]
            or any(
                row["at"] < act["at"] and row["accepted"] for row in prefix["history"]
            )
        ):
            # A later redundant acceptance cannot undo an already established
            # acceptance, including the explicit no-acceptance-needed rule.
            continue
        readings = [
            i
            for i in interpretations
            if i["message_id"] == terms["offer_id"]
            and i["actor"] == terms["recipient"]
            and i["at"] <= act["at"]
        ]
        latest = max((i["at"] for i in readings), default=-1)
        if any(
            len(i["versions"]) > 1 or len(i["contents"]) > 1
            for i in readings
            if i["at"] == latest
        ):
            output["frontier"].append("COMMITMENT_INTERPRETATION_UNRESOLVED")
            return output
    if prefix["frontier"] or prefix["status"] == "FRONTIER_UNEXPLORED":
        output["frontier"] = [
            "COMMITMENT_CONDITION_UNRESOLVED",
            *prefix["frontier"],
        ]
        return output

    # The original status is a bookkeeping prefix: absence of proved activation
    # or fulfillment is not proof of its negation. Complete every computed
    # Boolean marginal throughout the prefix and reuse the original lifecycle.
    # Cross-time/query correlation is unavailable, so this is a conservative
    # overapproximation. Never claim its combinations are genuine trajectories.
    uncertain = [
        (index, field, tuple(fact[field]))
        for index, fact in enumerate(facts)
        for field in ("condition", "outcome")
        if len(fact[field]) != 1
    ]
    if not uncertain:
        statuses = {prefix["status"]}
        output["state_completion_complete"] = True
        output["explored_completions"] = 1
    else:
        statuses = set()
        for choices in product(*(values for _, _, values in uncertain)):
            if output["work"] >= remaining:
                output["frontier"].append("COMMITMENT_BUDGET_FRONTIER")
                break
            output["work"] += 1
            completed = [dict(fact) for fact in facts]
            for (index, field, _), value in zip(uncertain, choices):
                completed[index][field] = (value,)
            result = qualified_commitment_history(
                terms,
                completed,
                acts,
                [d for d in deliveries if d["at"] <= at],
                [i for i in interpretations if i["at"] <= at],
                through=prefix_at,
            )
            output["explored_completions"] += 1
            statuses.add(result["status"])
            output["frontier"].extend(result["frontier"])
        else:
            output["state_completion_complete"] = True
    output["possible_statuses"] = tuple(sorted(statuses))
    if not output["state_completion_complete"] or output["frontier"]:
        output["frontier"] = sorted(set(output["frontier"]))
        return output
    possibilities = tuple(
        sorted({status == reference["status"] for status in statuses})
    )
    output.update(status="COMPUTED", possible_values=possibilities)
    if len(possibilities) != 1:
        output["frontier"].append("COMMITMENT_CONDITION_UNRESOLVED")
    return output
