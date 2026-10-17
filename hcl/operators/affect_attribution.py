"""M03-bound finite M06 but-for attribution, never knowledge or responsibility.

The declared bridge names a candidate contrast and a character-accessible causal
hypothesis. Its desired cause/outcome values are tests, never added observations.
Every accepted trace shares its factual exogenous context with the intervention.
"""

from hcl.memory import codec
from hcl.operators.causal import evaluate_counterfactual
from hcl.semantics.model_compiler import structural_model

VERSION = "s3-finite-affect-2"
SCHEMA = "hcl-affect-candidates-2"
VALUES = frozenset(("CONTRIBUTES", "NO_BUT_FOR_DIFFERENCE", "CAUSE_NOT_ACTUAL", "OUTCOME_UNESTABLISHED"))


def trace_attribution(trace, bridge, target):
    factual, alternative = trace["factual"], trace["alternative"]
    if factual[target] != bridge["outcome_value"]:
        return "OUTCOME_UNESTABLISHED"
    if factual[bridge["cause_variable"]] != bridge["actual_value"]:
        return "CAUSE_NOT_ACTUAL"
    if alternative[target] != factual[target]:
        return "CONTRIBUTES"
    return "NO_BUT_FOR_DIFFERENCE"


def derive_attributions(episode, mental, current, *, allowance):
    """Use only actual current perspective worlds; charge all new M06 work.

    A per-bridge bound can preserve resources for coping. It never expands the
    caller's allowance. Unknown/inconsistent/unavailable cases stay in the union,
    so neither explored prefixes nor one favored structure manufacture certainty.
    """
    used = 0
    queries = {row["id"]: row for row in mental["causal"]}
    events = {event["id"]: event for event in mental["events"]}
    candidates = []
    for bridge in episode["attributions"]:
        rows, possibilities, frontier = [], set(), set()
        causal_work = 0
        atoms = set(bridge["observations"][v]["atom"] for v in bridge["observations"])
        atoms.update(a for s in bridge["structures"] for a in s["available_when"])
        # Projection preserves correlations. Repeated epistemic worlds never
        # become probability mass or consume duplicate causal evaluation work.
        projections = {codec.canonical({a: values[a] for a in sorted(atoms)}):
                       {a: values[a] for a in sorted(atoms)}
                       for values in current["view"]["values"]}
        if current["view"]["frontier"] or not projections:
            frontier.add("ATTRIBUTION_PERSPECTIVE_FRONTIER")
            possibilities.add("UNRESOLVED")
        for key in sorted(projections):
            values = projections[key]
            observations = {
                variable: int(values[binding["atom"]] == binding["positive"])
                for variable, binding in bridge["observations"].items()
            }
            row = dict(perspective_projection=values, observations=observations,
                       structures=[], possibilities=[])
            rows.append(row)
            available = [s for s in bridge["structures"]
                         if events[queries[s["causal_id"]]["model"]["source_event_id"]]["at"] <= episode["at"]
                         and all(values[a] == v for a, v in s["available_when"].items())]
            row["unavailable_structures"] = [dict(
                causal_id=s["causal_id"], source_event_id=queries[s["causal_id"]]["model"]["source_event_id"],
                source_at=events[queries[s["causal_id"]]["model"]["source_event_id"]]["at"],
                reason="SOURCE_EVENT_NOT_YET_AVAILABLE" if events[queries[s["causal_id"]]["model"]["source_event_id"]]["at"] > episode["at"]
                       else "CHARACTER_STRUCTURE_GATE_NOT_SATISFIED")
                for s in bridge["structures"] if s not in available]
            local = set()
            if not available:
                local.add("UNRESOLVED")
                frontier.add("ATTRIBUTION_STRUCTURE_UNAVAILABLE")
            for structure in available:
                causal = queries[structure["causal_id"]]
                budget = min(max(0, allowance - used),
                             max(0, bridge["max_world_evaluations"] - causal_work))
                result = evaluate_counterfactual(
                    structural_model(causal["model"]), causal["target"],
                    observations=observations,
                    interventions={bridge["cause_variable"]: bridge["contrast_value"]},
                    max_world_evaluations=min(4096, budget),
                )
                used += result["world_evaluations"]
                causal_work += result["world_evaluations"]
                computed = {trace_attribution(t, bridge, causal["target"])
                            for t in result["traces"]}
                if not result["traces"] or result["frontier"]:
                    computed.add("UNRESOLVED")
                    frontier.add("ATTRIBUTION_CAUSAL_FRONTIER" if result["frontier"]
                                 else "ATTRIBUTION_INCONSISTENT_CHARACTER_MODEL")
                local.update(computed)
                row["structures"].append(dict(
                    causal_id=causal["id"], structure=structure,
                    causal_model=causal["model"], target=causal["target"],
                    source_event_at=events[causal["model"]["source_event_id"]]["at"],
                    allowance=min(4096, budget), computation=result,
                    possibilities=sorted(computed),
                ))
            row["possibilities"] = sorted(local)
            possibilities.update(local)
        candidates.append(dict(
            attribution_id=bridge["id"], goal_id=bridge["goal_id"],
            actor=bridge["actor"], at=bridge["at"], event_id=bridge["event_id"],
            event_at=events[bridge["event_id"]]["at"], contributor=bridge["contributor"],
            cause_variable=bridge["cause_variable"],
            target_variable=queries[bridge["structures"][0]["causal_id"]]["target"],
            actual_value=bridge["actual_value"],
            contrast_value=bridge["contrast_value"], outcome_value=bridge["outcome_value"],
            status="UNRESOLVED" if "UNRESOLVED" in possibilities else
                   "DETERMINATE" if len(possibilities) == 1 else "COMPETING",
            possibilities=sorted(possibilities), cases=rows, frontier=sorted(frontier),
            world_evaluations=causal_work, source_variable_id=current["variable_id"],
            source_versions=current["source_versions"], segment_ids=bridge["segment_ids"],
            information="CHARACTER_BELIEF_POSSIBILITIES_NOT_KNOWLEDGE",
            causal_scope="FINITE_BUT_FOR_CONTRAST_NOT_GENERAL_ACTUAL_CAUSATION",
            structure_scope="SOURCE_PROPOSED_CHARACTER_MODEL_NOT_VALIDATED_BELIEF_EXTRACTION",
            intention="NOT_INFERRED", normative_responsibility="NOT_MODELED",
            cause_control="NOT_INFERRED_FROM_CAUSAL_CONTRIBUTION",
        ))
    return dict(candidates=candidates, world_evaluations=used,
                frontier=sorted({f for row in candidates for f in row["frontier"]}))


def profile_attribution(result, goal_id):
    return dict(status="CONDITIONAL_FINITE_ATTRIBUTION", candidates=[
        c for c in result["candidates"] if c["goal_id"] == goal_id])


def attribution_predicate(profile, condition):
    rows = [c for c in profile["attribution"].get("candidates", ())
            if c["attribution_id"] == condition["attribution_id"]]
    if len(rows) != 1:
        raise ValueError("attribution condition needs exactly its computed bridge")
    row = rows[0]
    possibilities = set(row["possibilities"])
    if not possibilities or "UNRESOLVED" in possibilities or row["frontier"]:
        return "UNKNOWN"
    expected = condition["value"]
    return "TRUE" if possibilities == {expected} else "UNKNOWN" if expected in possibilities else "FALSE"


def attribution_semantics(attribution):
    """Evidence/time/work changes alone are not character reappraisal."""
    fields = ("attribution_id", "goal_id", "event_id", "event_at", "contributor", "cause_variable",
              "target_variable", "actual_value", "contrast_value", "outcome_value", "status",
              "possibilities", "frontier")
    return dict(status=attribution["status"], candidates=[
        {key: c[key] for key in fields} for c in attribution["candidates"]])
