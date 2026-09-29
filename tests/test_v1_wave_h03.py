"""H03 real cross-operation obligations from one ordinary source."""
import json
import unittest

from hcl.cognition.execution_graph import CognitiveExecutionGraph

SOURCE = '\n'.join((
    'Mira said, "I want to finish the project."',
    'Mira said, "I plan to deliver the ready report in order to finish the project if the permit arrives."',
    'Mira said, "I have an opportunity to deliver the ready report."',
    'Mira said, "I believe the permit arrives."',
    'Mira said, "In team, by ready I mean permit is true."',
    'Noor said, "In team, by ready I mean draft is true."',
    'Mira said, "I promise Noor to deliver the ready report if the permit arrives."',
    "Narrator: Noor did not hear Mira's last statement.",
    'Noor said, "I expect Mira to deliver the ready report."',
    'Mira said, "I failed to deliver the ready report in team."',
    'Mira said, "For the attempt to deliver the ready report in team, at the time I did not know the requirements."',
    "Noor said, \"In team, I distrust Mira's reliability because Mira failed to deliver the ready report.\"",
    'Narrator: In team, Mira serves as reviewer.',
    'Narrator: In team, a reviewer is required to deliver the ready report.',
    'Narrator: In team, Mira did not deliver the ready report.',
    "Narrator: In team, Mira's failure to deliver the ready report was the reviewer episode.",
))
QUERY = "Explain how Mira's reported belief and plan to deliver the ready report relate to Noor's expectation and view in team as reviewer, using ready for report."
CORRECTED = (SOURCE.replace('I believe the permit arrives.',
    'I believe it is false that the permit arrives.')
    .replace('at the time I did not know the requirements.',
        'at the time I knew the requirements.'))


class H03ExecutionTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None, acl=()):
        graph = CognitiveExecutionGraph()
        graph.put_source('scene', source, permitted_observers=acl)
        return graph, graph.prepare_graph(QUERY, source_id='scene', observer=observer)

    def test_positive_correction_propagates_through_actual_graph(self):
        graph, old = self.prepare()
        self.assertEqual(old.payload['nodes']['plan']['subjective_feasibility'],
            'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(old.payload['nodes']['relationship']['source_view']['conditional_alternatives'],
            ['INFORMATION_GAP'])
        before = old.payload['nodes']
        invalidated = graph.revise_source('scene', CORRECTED,
            kind='ANALYST_SOURCE_CORRECTION')
        self.assertTrue(set(old.claim_ids) & invalidated)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            old.messages(graph)
        new = graph.prepare_graph(QUERY, source_id='scene')
        after = new.payload['nodes']
        self.assertEqual(after['plan']['subjective_feasibility'],
            'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(after['interaction']['status'], before['interaction']['status'])
        self.assertNotEqual(after['interaction']['plan_dependency_claim_id'],
            before['interaction']['plan_dependency_claim_id'])
        self.assertEqual(after['relationship']['source_view']['conditional_alternatives'], [])
        self.assertEqual(after['relationship']['source_view']['reported_regard'],
            before['relationship']['source_view']['reported_regard'])
        self.assertEqual(new.payload['provider_calls'], 0)
        self.assertEqual(len(new.payload['edges']), 2)
        self.assertTrue(all(c in graph.core.grounded() for c in new.claim_ids))

    def test_real_belief_plan_interaction_relationship_support_edges(self):
        graph, result = self.prepare()
        plan, interaction, relationship = result.claim_ids
        self.assertIn(tuple(sorted((plan, *result.payload['source_support_receipt']['interaction']))),
            graph.core.dependencies[interaction])
        self.assertIn(tuple(sorted((interaction, *result.payload['source_support_receipt']['relationship']))),
            graph.core.dependencies[relationship])
        self.assertTrue(any(plan in group for group in graph.core.dependencies[interaction]))
        self.assertTrue(any(interaction in group for group in graph.core.dependencies[relationship]))
        # A challenge disputes the parent and propagates without making a fact false.
        belief = result.payload['source_support_receipt']['plan'][-1]
        target = next(iter(next(iter(graph.core.dependencies[belief]))))
        report = next(k for k, c in graph.core.claims.items()
            if c.kind.value == 'SOURCE_REPORT' and c.scope == graph.core.claims[target].scope)
        graph.core.challenge(target, report)
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(graph)
        self.assertEqual(graph.core.support_statuses()[relationship], 'DEPENDENCY_CONTESTED')

    def test_one_factor_correction_preserves_unrelated_relationship_report(self):
        graph, old = self.prepare()
        graph.revise_source('scene', SOURCE.replace('I believe the permit arrives.',
            'I believe it is false that the permit arrives.'), kind='ANALYST_SOURCE_CORRECTION')
        new = graph.prepare_graph(QUERY, source_id='scene')
        self.assertEqual(new.payload['nodes']['relationship']['source_view']['conditional_alternatives'],
            old.payload['nodes']['relationship']['source_view']['conditional_alternatives'])
        self.assertNotEqual(new.payload['nodes']['plan']['subjective_feasibility'],
            old.payload['nodes']['plan']['subjective_feasibility'])

    def test_unrelated_source_cached_without_reexecution(self):
        graph, old = self.prepare()
        graph.put_source('club', SOURCE.replace('team', 'club'))
        other_question = QUERY.replace('team', 'club')
        other = graph.prepare_graph(other_question, source_id='club')
        graph.revise_source('scene', CORRECTED, kind='ANALYST_SOURCE_CORRECTION')
        graph.prepare_graph(QUERY, source_id='scene')
        self.assertIs(other, graph.prepare_graph(other_question, source_id='club'))
        self.assertEqual(graph.graph_executions[(other_question, 'club', None)], 1)
        self.assertEqual(old.payload['nodes']['relationship']['source_view']['reported_regard'],
            other.payload['nodes']['relationship']['source_view']['reported_regard'])

    def test_condition_and_actor_mismatch_refuse_bridge(self):
        for changed in (SOURCE.replace('if the permit arrives."\nNarrator:',
                        'if the draft arrives."\nNarrator:'),
                SOURCE.replace('Mira said, "I believe', 'Kai said, "I believe')):
            if 'Kai said' in changed:
                _, result = self.prepare(changed)
                self.assertEqual(result.payload['nodes']['plan']['subjective_feasibility'],
                    'BELIEF_CONDITION_UNRESOLVED')
            else:
                with self.assertRaisesRegex(ValueError, 'conditions differ'):
                    self.prepare(changed)

    def test_missing_failure_or_promise_refuses(self):
        with self.assertRaises(ValueError):
            self.prepare(SOURCE.replace('Mira said, "I promise', 'Kai said, "I promise'))
        with self.assertRaises(ValueError):
            self.prepare(SOURCE.replace('Mira said, "I failed', 'Kai said, "I failed'))

    def test_access_scope_and_source_correction_do_not_reveal_hidden_text(self):
        graph = CognitiveExecutionGraph()
        graph.put_source('scene', SOURCE, permitted_observers=('Noor',))
        with self.assertRaises(ValueError):
            graph.prepare_graph(QUERY, source_id='scene', observer='Kai')
        result = graph.prepare_graph(QUERY, source_id='scene', observer='Noor')
        self.assertIn('Mira said', result.messages(graph)[1]['content'])
        graph.revise_source('scene', CORRECTED, kind='ANALYST_SOURCE_CORRECTION',
            permitted_observers=('Noor',))
        with self.assertRaisesRegex(ValueError, 'source changed'):
            result.messages(graph)

    def test_exact_final_input_and_budget(self):
        graph, result = self.prepare()
        calls = []
        answer = graph.answer_graph(QUERY, lambda messages: calls.append(messages) or 'conditional',
            source_id='scene')
        self.assertEqual(answer['answer_adapter_calls'], 1)
        self.assertEqual(answer['provider_calls_created_by_graph'], 0)
        self.assertEqual(calls, [answer['actual_final_messages']])
        state = json.loads(calls[0][-1]['content'])
        self.assertEqual(state['nodes']['relationship']['changed'], 'NOT_INFERRED')
        self.assertEqual(state['nodes']['interaction']['causal_misunderstanding'], 'NOT_ESTABLISHED')
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(graph, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
