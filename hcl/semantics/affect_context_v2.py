"""Opt-in complete field contract for candidate production, preserving v1 bytes."""
from .affect_compiler import affect_context
from .affect_attribution import FIELDS
from .model_compiler import model_context


def affect_context_v2(snapshot, question):
    context = affect_context(snapshot, question)
    mental = model_context(snapshot, question)
    context.update(schema="hcl-affect-context-2", candidate_schema="hcl-affect-candidates-2",
                   return_envelope="hcl-affect-source-return-2",
                   episode_fields=[*context["episode_fields"], "attributions"],
                   attribution_fields=FIELDS.split(),
                   structure_fields="causal_id available_when segment_ids".split(),
                   observation_binding_fields="atom positive".split(),
                   attribution_condition_fields="goal_id dimension attribution_id value".split(),
                   mental_contract={k: v for k, v in mental.items() if k not in ("segments", "source_input_versions")})
    context["mental_contract"].update(
        agent_fields="id label source_id segment_ids".split(),
        variable_fields="id initial observed_by segment_ids".split(),
        plan_graph_fields="states terminal utilities actions horizon".split(),
        action_fields="id cost enabled feasible transitions observations".split(),
        state_binding_fields="state when".split(),
        policy_fields="beta rational_weight habit_weight error_weight habit".split(),
        causal_fields="id model target observations interventions segment_ids".split(),
        structural_model_fields="id source_event_id variables exogenous rules".split(),
        structural_rule_fields="target expression evidence_text".split(),
        formula_contract=dict(atom=dict(op="atom", name="declared_variable"),
                              negation=dict(op="not", arg="formula"),
                              conjunction=dict(op="and", args=["formula"]),
                              disjunction=dict(op="or", args=["formula"])),
    )
    context["attribution_instructions"] = (
        "Each episode has attributions (possibly empty). Each bridge binds an existing event, actor, goal, "
        "cause-variable and source-anchored causal structure. Observations map causal variables to mental "
        "atoms and polarity. available_when gates theory availability in the actor's perspective. "
        "Use integer Boolean actual/contrast/outcome values; actual and contrast differ. Never supply "
        "computed contribution, blame, emotion, or action verdicts. Include source excerpt evidence_text "
        "for every structural rule; unknown probabilities remain null. All source segments must be used "
        "or explicitly unmodeled; questions cannot ground source facts. Repairs only correct the indicated "
        "finite representation field under the same source versions and schema."
    )
    return context
