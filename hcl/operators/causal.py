"""Pure declared-SCM adapter. Never creates the legacy v0.9 state store."""

from hcl.v09.runtime import CausalModel


def evaluate_counterfactual(
    model, target, *, observations=None, interventions=None, max_world_evaluations=4096
):
    if type(model) is not CausalModel:
        raise ValueError("typed finite structural model required")
    if type(max_world_evaluations) is not int or not 0 <= max_world_evaluations <= 65536:
        raise ValueError("bounded world evaluation allowance required")
    # Every exogenous assignment is tested in the factual model; each retained
    # assignment can require one intervened evaluation. Reserve before solving.
    hold = 2 * (2 ** len(model.exogenous))
    if hold > max_world_evaluations:
        return dict(
            status="FRONTIER_UNEXPLORED",
            traces=[],
            possible_values=[],
            value=None,
            frontier=["CAUSAL_WORLD_BOUND"],
            world_evaluations=0,
            reserved_world_evaluations=0,
        )
    result = model.counterfactual(target, observations=observations, interventions=interventions)
    result["world_evaluations"] = 2 ** len(model.exogenous) + result["world_count"]
    result["reserved_world_evaluations"] = hold
    result["frontier"] = []
    result["identification"] = "CONDITIONAL_ON_DECLARED_STRUCTURE_NOT_CAUSAL_DISCOVERY"
    return result
