"""H04: bounded source-first answer synthesis over an H03 execution graph."""
from dataclasses import dataclass
import json

from .evidence_closure import EvidenceClosureIndex
from .execution_graph import CognitiveExecutionGraph
from .relationship_dynamics import prepare_relationship_dynamics

_POLICY = ('The answer sections are an audit of recorded, source-visible evidence, '
    'not an automatic semantic correctness verdict. Preserve exact quotations, '
    'speaker/source, condition, access scope, decisive counterevidence, live '
    'dependency status and reasonable unresolved alternatives. A reported fact '
    'is not world truth. A single most-supported recorded explanation is not a '
    'unique actual cause; an unsupported alternative is not disproved. Do not '
    'infer private belief, intention, blame, value weights or moral truth.')


@dataclass(frozen=True)
class AuditedAnswer:
    graph: object
    closure: object
    closure_index: object
    payload_json: str

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded answer context required')
        self.graph.messages(workspace)
        self.closure.current_messages(self.closure_index)
        messages = [dict(role='system', content=_POLICY),
            dict(role='user', content=self.payload_json)]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('audited answer exceeds context budget; narrow source/question')
        return messages

    def draft(self, workspace):
        """A readable conditional draft with no model or provider invocation."""
        self.messages(workspace)
        p = self.payload
        best = p['best_recorded_explanation']
        best_text = ', '.join(best['hypotheses']) if best['hypotheses'] else 'none established'
        others = ', '.join(x['hypothesis'] + ' (' + x['status'] + ')'
            for x in p['other_recorded_explanations']) or 'none recorded'
        return ('Source reports: ' + ' '.join(row['quote'] for row in p['source_reports']) +
            '\nBest recorded conditional explanation: ' + best_text + ' (' + best['status'] + ').' +
            '\nOther recorded explanations: ' + others + '.' +
            '\nConditional conclusion: ' + p['conditional_conclusion']['text'] +
            '\nLimits: reported statements and declared conditions do not establish '
            'private belief, actual cause, changed regard or blame.')


class AnswerAuditWorkspace(CognitiveExecutionGraph):
    """A selected graph, not a general model judge or exhaustive world search."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.answer_cache = {}
        self.answer_executions = {}

    def prepare_audited_answer(self, question, *, source_id, observer=None,
                               max_nodes=128, max_chars=64000):
        if type(max_nodes) is not int or not 1 <= max_nodes <= 1024:
            raise ValueError('bounded closure node budget required')
        key = (question, source_id, observer, max_nodes, max_chars)
        previous = self.answer_cache.get(key)
        if previous:
            try:
                previous.messages(self, max_chars=max_chars)
            except ValueError:
                pass
            else:
                return previous
        graph = self.prepare_graph(question, source_id=source_id, observer=observer)
        selected = graph.payload
        closure_index = EvidenceClosureIndex(self, max_nodes=max_nodes)
        closure = closure_index.select(graph.claim_ids[-1], observer=observer,
            query=question, max_chars=128000)
        recorded = json.loads(closure.messages[-1]['content'])['cognition']
        if recorded['target_status'] != 'SUPPORT_AVAILABLE':
            raise ValueError('selected graph conclusion is not supported')
        if not recorded['source_spans']:
            raise ValueError('recorded graph lacks source quotation')
        source_reports = []
        for row in recorded['source_spans']:
            # The full-document root is an authorization container. Exact
            # statement spans provide the quotable, bounded answer anchors.
            if '\n' in row['quote'] or not row['active']:
                continue
            source_reports.append({k: row[k] for k in
                ('id', 'source_id', 'version', 'start', 'end', 'quote')})
        source_reports.sort(key=lambda row: (row['source_id'], row['version'], row['start']))
        if not source_reports or len(source_reports) > 32:
            raise ValueError('quotable source anchor budget exceeded or unavailable')
        # Reuse E05's actual factor comparisons. The answer layer neither
        # reinterprets a source sentence as knowledge nor invents a ranking.
        actor, recipient, action = (selected[k] for k in ('actor', 'recipient', 'action'))
        relation = prepare_relationship_dynamics(self, selected['relationship_query'],
            source_id=source_id, observer=observer).payload
        alternatives = relation['failure']['explanations']
        supported = [a['hypothesis'] for a in alternatives if a['status'] == 'CONDITIONALLY_SUPPORTED']
        best_status = ('SINGLE_MOST_SUPPORTED_RECORDED_CONDITIONAL' if len(supported) == 1 else
            'MULTIPLE_CONDITIONALLY_SUPPORTED' if supported else 'NO_SUPPORTED_RECORDED_EXPLANATION')
        other = [dict(hypothesis=a['hypothesis'], status=a['status'],
            conditions=a['conditions'], actual_cause='NOT_ESTABLISHED')
            for a in alternatives if a['hypothesis'] not in supported]
        factors = relation['failure']['factor_checks']
        bindings = {r['claim_id']: r for r in relation['failure']['factor_source_bindings']}
        counterevidence = []
        for alt in other:
            if alt['status'] not in ('WEAKENED_BY_COUNTEREVIDENCE', 'CONFLICTING_PREMISES'):
                continue
            for factor, state in alt['conditions'].items():
                if state not in ('CONTRADICTED', 'CONFLICT'):
                    continue
                for row in factors[factor]['support'] + factors[factor]['contradiction']:
                    binding = bindings.get(row['claim_id'])
                    if binding:
                        counterevidence.append(dict(hypothesis=alt['hypothesis'],
                            factor=factor, condition_state=state,
                            original_quote=binding['original_quote'],
                            source_claim_id=binding['source_claim_id'],
                            authority=row['authority'], time=binding['time']))
        unique = {(r['hypothesis'], r['source_claim_id']): r for r in counterevidence}
        counterevidence = list(unique.values())
        graph_nodes = selected['nodes']
        conditional = dict(plan_feasibility=graph_nodes['plan']['subjective_feasibility'],
            expectation=graph_nodes['interaction']['status'],
            relationship_alternatives=graph_nodes['relationship']['source_view']['conditional_alternatives'],
            reported_regard=graph_nodes['relationship']['source_view']['reported_regard'],
            actual_cause='NOT_ESTABLISHED', moral_blame='NOT_INFERRED',
            text=(f"Under the recorded self-report, {actor}'s plan to {action} is "
                f"{graph_nodes['plan']['subjective_feasibility']}; {recipient}'s reported "
                f"expectation is {graph_nodes['interaction']['status']}. "
                f"The source-linked relationship explanation is conditional, and "
                f"{recipient}'s reported regard is not rewritten."))
        payload = dict(schema='hcl-h04-audited-answer-v1', question=question,
            source_scope=dict(source_id=source_id, version=self._versions[source_id],
                observer=observer, source_authority='AUTHORIZED_REPORTED_TEXT_NOT_WORLD_TRUTH'),
            source_reports=source_reports,
            best_recorded_explanation=dict(status=best_status, hypotheses=supported,
                authority='COMPARISON_OF_RECORDED_CONDITIONAL_CHECKS_NOT_ACTUAL_CAUSE'),
            other_recorded_explanations=other,
            decisive_counterevidence=counterevidence,
            conditional_conclusion=conditional,
            assumptions=['ACCURATE_SINCERE_SELF_REPORT_NOT_VERIFIED',
                'SOURCE_ORDER_NOT_VERIFIED_EVENT_CHRONOLOGY',
                'MATCHING_PLAN_AND_PROMISE_CONDITION',
                'NO_CAUSAL_MISUNDERSTANDING_OR_BLAME_INFERENCE'],
            support_audit=dict(status='BOUNDED_RECORDED_CLOSURE_NOT_SEMANTIC_PASS',
                target_claim_id=recorded['target_claim_id'],
                selected_node_count=recorded['selected_node_count'],
                challenge_count=sum(len(c['challenges']) for c in recorded['claim_nodes']),
                source_anchor_count=len(source_reports),
                closure_completeness=recorded['external_evidence_completeness'],
                graph_edges=selected['edges']),
            provider_calls=0, policy=_POLICY)
        answer = AuditedAnswer(graph, closure, closure_index,
            json.dumps(payload, ensure_ascii=False, sort_keys=True))
        answer.messages(self, max_chars=max_chars)
        self.answer_cache[key] = answer
        self.answer_executions[key] = self.answer_executions.get(key, 0) + 1
        return answer

    def answer_audited(self, question, answer_backend=None, *, source_id,
                       observer=None, max_nodes=128, max_chars=64000):
        prepared = self.prepare_audited_answer(question, source_id=source_id,
            observer=observer, max_nodes=max_nodes, max_chars=max_chars)
        messages = prepared.messages(self, max_chars=max_chars)
        if answer_backend is None:
            return dict(answer=prepared.draft(self), actual_final_messages=messages,
                answer_adapter_calls=0)
        return dict(answer=answer_backend(messages), actual_final_messages=messages,
            answer_adapter_calls=1)
