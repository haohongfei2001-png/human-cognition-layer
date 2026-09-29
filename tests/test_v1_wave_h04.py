"""H04 source-first, bounded final answer support audit."""
import json
import unittest

from hcl.cognition.answer_audit import AnswerAuditWorkspace
from tests.test_v1_wave_h03 import SOURCE, CORRECTED, QUERY


class H04AnswerAuditTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None, acl=()):
        workspace = AnswerAuditWorkspace()
        workspace.put_source('scene', source, permitted_observers=acl)
        return workspace, workspace.prepare_audited_answer(QUERY,
            source_id='scene', observer=observer)

    def test_positive_source_first_answer_and_counterevidence(self):
        workspace, result = self.prepare()
        p = result.payload
        self.assertEqual(p['best_recorded_explanation']['hypotheses'], ['INFORMATION_GAP'])
        self.assertEqual(p['best_recorded_explanation']['status'],
            'SINGLE_MOST_SUPPORTED_RECORDED_CONDITIONAL')
        self.assertIn('CONTROL_CONSTRAINT', [x['hypothesis'] for x in p['other_recorded_explanations']])
        self.assertIn('UNRESOLVED', [x['status'] for x in p['other_recorded_explanations']])
        self.assertEqual(p['decisive_counterevidence'][0]['hypothesis'],
            'INFORMED_CONTROLLABLE_STATED_CHOICE')
        self.assertIn('did not know the requirements',
            p['decisive_counterevidence'][0]['original_quote'])
        self.assertEqual(p['support_audit']['status'],
            'BOUNDED_RECORDED_CLOSURE_NOT_SEMANTIC_PASS')
        self.assertEqual(p['support_audit']['closure_completeness'], 'NOT_ESTABLISHED')
        self.assertIn('Other recorded explanations:', result.draft(workspace))
        self.assertIn('not establish', result.draft(workspace))

    def test_source_offsets_are_exact_and_scope_is_preserved(self):
        workspace, result = self.prepare()
        for row in result.payload['source_reports']:
            self.assertEqual(SOURCE[row['start']:row['end']], row['quote'])
            self.assertEqual(row['source_id'], 'scene')
            self.assertEqual(row['version'], 1)
        self.assertEqual(result.payload['source_scope']['observer'], None)
        self.assertEqual(result.payload['source_scope']['source_authority'],
            'AUTHORIZED_REPORTED_TEXT_NOT_WORLD_TRUTH')
        self.assertEqual(result.payload['conditional_conclusion']['actual_cause'],
            'NOT_ESTABLISHED')
        self.assertEqual(result.payload['conditional_conclusion']['moral_blame'],
            'NOT_INFERRED')

    def test_source_correction_changes_best_and_decisive_counterevidence(self):
        workspace, before = self.prepare()
        workspace.revise_source('scene', CORRECTED, kind='ANALYST_SOURCE_CORRECTION')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            before.messages(workspace)
        after = workspace.prepare_audited_answer(QUERY, source_id='scene')
        self.assertEqual(after.payload['best_recorded_explanation']['status'],
            'NO_SUPPORTED_RECORDED_EXPLANATION')
        self.assertEqual(after.payload['decisive_counterevidence'][0]['hypothesis'],
            'INFORMATION_GAP')
        self.assertIn('knew the requirements',
            after.payload['decisive_counterevidence'][0]['original_quote'])
        self.assertEqual(after.payload['conditional_conclusion']['reported_regard'],
            before.payload['conditional_conclusion']['reported_regard'])

    def test_unknown_factor_does_not_become_best_or_refutation(self):
        source = SOURCE.replace('Mira said, "For the attempt to deliver the ready report in team, at the time I did not know the requirements."\n', '')
        _, result = self.prepare(source)
        self.assertEqual(result.payload['best_recorded_explanation']['status'],
            'NO_SUPPORTED_RECORDED_EXPLANATION')
        self.assertFalse(result.payload['decisive_counterevidence'])
        self.assertTrue(any(row['status'] == 'UNRESOLVED'
            for row in result.payload['other_recorded_explanations']))

    def test_actor_and_condition_boundaries_are_inherited(self):
        with self.assertRaises(ValueError):
            self.prepare(SOURCE.replace('Mira said, "I believe', 'Kai said, "I believe')
                .replace('Mira said, "I promise', 'Kai said, "I promise'))
        with self.assertRaisesRegex(ValueError, 'conditions differ'):
            self.prepare(SOURCE.replace('if the permit arrives."\nNarrator:',
                'if the draft arrives."\nNarrator:'))

    def test_unrelated_source_and_hidden_access(self):
        workspace, first = self.prepare()
        workspace.put_source('club', SOURCE.replace('team', 'club'))
        other_query = QUERY.replace('team', 'club')
        other = workspace.prepare_audited_answer(other_query, source_id='club')
        original_input = other.messages(workspace)
        workspace.revise_source('scene', CORRECTED, kind='ANALYST_SOURCE_CORRECTION')
        workspace.prepare_audited_answer(QUERY, source_id='scene')
        self.assertIs(other, workspace.prepare_audited_answer(other_query, source_id='club'))
        self.assertEqual(other.messages(workspace), original_input)
        self.assertEqual(workspace.answer_executions[(other_query, 'club', None, 128, 64000)], 1)
        self.assertEqual(first.payload['source_scope']['source_id'], 'scene')
        workspace = AnswerAuditWorkspace()
        workspace.put_source('scene', SOURCE, permitted_observers=('Noor',))
        with self.assertRaises(ValueError):
            workspace.prepare_audited_answer(QUERY, source_id='scene', observer='Kai')
        self.assertIn('Mira said', workspace.prepare_audited_answer(QUERY,
            source_id='scene', observer='Noor').messages(workspace)[-1]['content'])

    def test_full_closure_or_context_budget_refuses_instead_of_truncating(self):
        workspace, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            workspace.prepare_audited_answer(QUERY, source_id='scene', max_nodes=12)
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(workspace, max_chars=1000)

    def test_exact_final_input_optional_backend_and_historical_boundary(self):
        workspace, prepared = self.prepare()
        calls = []
        answer = workspace.answer_audited(QUERY, lambda messages:
            calls.append(messages) or 'conditional answer', source_id='scene')
        self.assertEqual(calls, [answer['actual_final_messages']])
        self.assertEqual(answer['answer_adapter_calls'], 1)
        self.assertEqual(json.loads(calls[0][-1]['content']), prepared.payload)
        direct = workspace.answer_audited(QUERY, source_id='scene')
        self.assertEqual(direct['answer_adapter_calls'], 0)
        self.assertIn('not establish', direct['answer'])
        self.assertEqual(prepared.payload['provider_calls'], 0)


if __name__ == '__main__':
    unittest.main()
