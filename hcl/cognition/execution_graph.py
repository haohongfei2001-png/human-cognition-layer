"""Source-bound belief, plan, expectation and relationship execution graph.

The links are conditional analysis dependencies, never evidence that a person
accepted a premise, knew a plan condition, or changed a relationship.
"""
from dataclasses import dataclass
import json
import re

from .core import ClaimKind
from .misunderstanding import prepare_misunderstanding
from .plan_feasibility import prepare_plan_feasibility
from .relationship_dynamics import RelationshipDynamicsWorkspace, prepare_relationship_dynamics

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUESTION = re.compile(
    rf"Explain how (?P<actor>{_NAME})'s reported belief and plan to (?P<action>[^.]+?) "
    rf"relate to (?P<recipient>{_NAME})'s expectation and view in (?P<context>{_TERM}) "
    rf"as (?P<role>{_TERM}), using (?P<term>{_TERM}) for (?P<item>{_TERM})\.")
_POLICY = ('The graph joins actual source-rooted cognition operations. Reported belief '
    'is conditional on an accurate, sincere self-report; a plan condition is not '
    'world feasibility. A mismatched expectation is not its proven cause. A reported '
    'relationship view is not rewritten by a plan check. No private intention, '
    'responsibility, blame or moral truth is inferred. A source correction revises '
    'the analyst graph, not the character at an earlier time.')


@dataclass(frozen=True)
class CognitiveExecution:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=120000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 160000:
            raise ValueError('bounded graph context required')
        if any(workspace._versions.get(s) != v for s, v in self.source_versions):
            raise ValueError('graph source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('graph support changed; recompute')
        messages = [dict(role='system', content=_POLICY),
            dict(role='user', content=self.payload_json)]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('graph context budget exceeded')
        return messages


class CognitiveExecutionGraph(RelationshipDynamicsWorkspace):
    """One active writer/session; source-version cache protects local recomputation."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graph_cache = {}
        self.graph_executions = {}

    def prepare_graph(self, question, *, source_id, observer=None):
        match = _QUESTION.fullmatch(question) if isinstance(question, str) and len(question) <= 8000 else None
        if not match or match['actor'] == match['recipient'] or match['term'] not in match['action'].split():
            raise ValueError('bounded actor, recipient, action and relevant concept required')
        if source_id not in self._documents:
            raise ValueError('registered source required')
        key = (question, source_id, observer)
        cached = self.graph_cache.get(key)
        if cached:
            try:
                cached.messages(self)
            except ValueError:
                pass
            else:
                return cached
        actor, recipient, action, context, role, term, item = (match[k] for k in
            ('actor', 'recipient', 'action', 'context', 'role', 'term', 'item'))
        plan = prepare_plan_feasibility(self,
            f"Could {actor}'s plans work under their beliefs and the declared model?",
            source_id=source_id, observer=observer)
        interaction = prepare_misunderstanding(self,
            f"Explain {recipient}'s expectation of {actor}'s promise to {action} "
            f"in {context}, using {term} for {item}.", source_id=source_id, observer=observer)
        relation_query = (f"Explain how {recipient}'s view of {actor} relates to the {role} role "
            f"and preferences in {context} after the failure to {action}.")
        relation = prepare_relationship_dynamics(self, relation_query,
            source_id=source_id, observer=observer)
        matching = [p for p in plan.payload['plans'] if p['action'] == action]
        if len(matching) != 1 or interaction.payload.get('status') == 'SYSTEM_INSUFFICIENT' or not relation.claim_ids:
            raise ValueError('unambiguous source-grounded plan, promise and relationship required')
        selected = matching[0]
        original = interaction.payload['original_promise']
        conditions = original['conditions']
        if len(conditions) != 1 or conditions[0]['key'] != selected['condition']:
            raise ValueError('plan and promise conditions differ; no silent cross-operation bridge')
        if not relation.payload['failure'].get('explanations'):
            raise ValueError('anchored failure factors required')
        core, scope = self.core, plan.scope
        if any(core.claims[c].scope != scope for c in (*interaction.claim_ids, *relation.claim_ids)):
            raise ValueError('cross-scope graph requires explicit projection')
        # The plan's own claim already depends on its reported-belief transition.
        # Each further edge records an operation obligation, not merely a shared
        # JSON container. Removing source or challenging a dependency invalidates
        # the downstream chain through EvidenceCore.support_statuses().
        plan_id = selected['claim_id']
        interaction_id = core.claim(scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='PLAN_EXPECTATION_DEPENDENCY', action=action,
                plan_condition=selected['condition'],
                plan_feasibility=selected['subjective_feasibility'],
                expectation_status=interaction.payload['status'],
                cause='NOT_ESTABLISHED', actual_understanding='NOT_ESTABLISHED'))
        core.support(interaction_id, plan_id, *interaction.claim_ids)
        # The graph reads the failure and role path, not E05's separate value
        # interpretation. Keep that independent branch out of this obligation.
        relation_support = tuple(dict.fromkeys((
            *relation.payload['support_claim_ids']['failure'],
            *relation.payload['support_claim_ids']['identity'])))
        relation_id = core.claim(scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='EXPECTATION_RELATIONSHIP_DEPENDENCY', action=action,
                plan_feasibility=selected['subjective_feasibility'],
                expectation_status=interaction.payload['status'],
                relationship_explanations=relation.payload['relationship_interpretation']['conditional_alternatives'],
                relationship_changed='NOT_INFERRED', moral_blame='NOT_INFERRED'))
        core.support(relation_id, interaction_id, *relation_support)
        nodes = dict(reported_belief=[b for b in plan.payload['reported_belief_states']
            if b['proposition_key'] == selected['condition']],
            plan={k: v for k, v in selected.items() if k != 'support_claim_ids'},
            interaction=dict(status=interaction.payload['status'],
                initial_factors=interaction.payload.get('initial_factors'),
                explanation_revision=interaction.payload.get('explanation_revision'),
                plan_dependency_claim_id=interaction_id,
                causal_misunderstanding='NOT_ESTABLISHED'),
            relationship=dict(source_view=relation.payload['relationship_interpretation'],
                role_evaluation=relation.payload['role_evaluation'],
                dependency_claim_id=relation_id, changed='NOT_INFERRED'))
        payload = dict(question=question, actor=actor, recipient=recipient, action=action,
            context=context, role=role, relationship_query=relation_query,
            source_id=source_id, source_version=self._versions[source_id], nodes=nodes,
            edges=[dict(from_claim=plan_id, to_claim=interaction_id, kind='CONDITIONAL_PLAN_EXPECTATION'),
                dict(from_claim=interaction_id, to_claim=relation_id, kind='CONDITIONAL_EXPECTATION_RELATIONSHIP')],
            source_support_receipt=dict(plan=selected['support_claim_ids'],
                interaction=list(interaction.claim_ids), relationship=list(relation_support)),
            provider_calls=0, policy=_POLICY)
        result = CognitiveExecution(((source_id, self._versions[source_id]),),
            json.dumps(payload, ensure_ascii=False, sort_keys=True), (plan_id, interaction_id, relation_id))
        # Final input must be available before caching or claiming execution.
        result.messages(self)
        self.graph_cache[key] = result
        self.graph_executions[key] = self.graph_executions.get(key, 0) + 1
        return result

    def answer_graph(self, question, answer_backend, *, source_id, observer=None, max_chars=120000):
        prepared = self.prepare_graph(question, source_id=source_id, observer=observer)
        messages = prepared.messages(self, max_chars=max_chars)
        answer = answer_backend(messages)
        return dict(answer=answer, actual_final_messages=messages,
            answer_adapter_calls=1, provider_calls_created_by_graph=0)
