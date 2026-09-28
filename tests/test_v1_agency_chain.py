import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace, prepare_agency_chain

SOURCE = '\n'.join(('Mira said, "I want to attend the concert."',
    'Mira said, "I plan to leave the meeting in order to attend the concert if the train is running."',
    'Mira said, "I have an opportunity to leave the meeting."',
    'Mira said, "I believe the train is running."',
    'Narrator: In the declared model, it is false that the train is running.',
    'Mira said, "At the time, I knew about the meeting."',
    'Mira said, "At the time, I could leave the meeting."',
    'Mira said, "I left the meeting."',
    'Mira said, "The delay hinders my goal to attend the concert."'))
QUERY = 'Why did Mira leave the meeting, considering their plans and appraisal of the delay?'


class AgencyChainTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None, acl=()):
        w = SemanticWorkspace()
        w.put_source('scene', source, permitted_observers=acl)
        return w, prepare_agency_chain(w, QUERY, source_id='scene', observer=observer)

    def test_positive_dependency_changes_and_emotion_does_not(self):
        w, before = self.prepare()
        self.assertEqual(before.payload['explanations'][0]['disposition'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(before.payload['current_plans'][0]['model_condition_check'], 'MODEL_CONDITION_CONTRADICTED')
        w.put_source('scene', SOURCE.replace('I believe the train is running.', 'I believe it is false that the train is running.'))
        after = prepare_agency_chain(w, QUERY, source_id='scene')
        self.assertEqual(after.payload['explanations'][0]['disposition'], 'WEAKENED_BY_PLAN_COUNTEREVIDENCE')
        self.assertEqual(after.payload['appraisal']['reported_emotions'], [])
        self.assertEqual(after.payload['appraisal']['inferred_actual_emotion'], 'NOT_ESTABLISHED')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            before.messages(w)
        self.assertIn('WEAKENED_BY_PLAN_COUNTEREVIDENCE', after.messages(w)[1]['content'])

    def test_later_belief_does_not_backfill_action(self):
        _, result = self.prepare(SOURCE + '\nMira said, "I now believe it is false that the train is running instead of the train is running."')
        self.assertEqual(result.payload['current_plans'][0]['subjective_feasibility'], 'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(result.payload['explanations'][0]['disposition'], 'CONDITIONALLY_SUPPORTED')

    def test_absent_belief_unknown_not_opposite(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "I believe the train is running."\n', ''))
        self.assertEqual(result.payload['explanations'][0]['disposition'], 'PLAN_DEPENDENCY_UNRESOLVED')

    def test_other_actor_belief_cannot_fill(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "I believe', 'Noor said, "I believe'))
        self.assertEqual(result.payload['explanations'][0]['disposition'], 'PLAN_DEPENDENCY_UNRESOLVED')

    def test_missing_action_stays_insufficient(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "I left the meeting."\n', ''))
        self.assertEqual(result.payload['status'], 'SYSTEM_INSUFFICIENT_ACTION')
        self.assertIsNone(result.payload['action_time'])

    def test_hidden_source_not_in_final_input(self):
        w, result = self.prepare(observer='Noor')
        self.assertNotIn('train', json.dumps(result.messages(w)))
        self.assertEqual(result.payload['status'], 'SYSTEM_INSUFFICIENT_ACTION')

    def test_authorized_observer_and_shared_source_root(self):
        w, result = self.prepare(observer='Noor', acl=('Noor',))
        span_id = result.payload['action_time']['source_span_id']
        self.assertEqual(w.core.spans[span_id].quote, SOURCE[:result.payload['action_time']['end']])
        self.assertTrue(all(c in w.core.grounded() for c in result.claim_ids))
        w.core.withdraw(span_id)
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(w)

    def test_final_input_and_budget(self):
        w, result = self.prepare()
        state = json.loads(result.messages(w)[1]['content'])
        self.assertTrue(state['action_time']['plans'])
        self.assertTrue(state['explanations'][0]['condition_claim_id'])
        self.assertEqual(state['appraisal']['goal_congruence'], 'HINDERS_EVIDENCED_GOALS')
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)

    def test_semantic_reuse_invalidation_and_unrelated_source(self):
        w, _ = self.prepare()
        self.assertEqual(len(w.semantic_cache), 1)
        first = w.prepare_semantic('one', source_ids=('scene',))
        w.put_source('other', 'Noor said, "I want to rest."')
        self.assertIs(first, w.prepare_semantic('two', source_ids=('scene',)))
        w.put_source('scene', SOURCE + '\nMira said, "I feel worried about the delay."')
        second = w.prepare_semantic('three', source_ids=('scene',))
        self.assertIsNot(first, second)

    def test_no_backend_retry_and_acl_precedes_call(self):
        class Backend:
            calls = 0
            def complete_json(self, *args, **kwargs):
                self.calls += 1
                raise RuntimeError('offline')
        backend = Backend()
        w = SemanticWorkspace(semantic_backend=backend)
        w.put_source('scene', SOURCE)
        w.prepare_semantic('hidden', source_ids=('scene',), observer='Noor')
        self.assertEqual(backend.calls, 0)
        # Failures propagate and consume the attempt; no retry.
        with self.assertRaisesRegex(RuntimeError, 'offline'):
            w.prepare_semantic('visible', source_ids=('scene',))
        self.assertEqual(backend.calls, 1)
        w.put_source('scene', SOURCE + '\nMira said, "I want to rest."')
        with self.assertRaisesRegex(ValueError, 'attempt budget'):
            w.prepare_semantic('changed', source_ids=('scene',))
        self.assertEqual(backend.calls, 1)

    def test_one_extraction_replay_feeds_all_operations(self):
        from hcl.cognition.semantic import AuthorizedText, _local_candidates
        class Replay:
            calls = 0
            def complete_json(self, messages, **kwargs):
                self.calls += 1
                data = json.loads(messages[1]['content'])
                return json.dumps(dict(candidates=[r for item in data['sources']
                    for r in _local_candidates(AuthorizedText(**item))]))
        backend = Replay()
        w = SemanticWorkspace(semantic_backend=backend)
        w.put_source('scene', SOURCE)
        result = prepare_agency_chain(w, QUERY, source_id='scene')
        self.assertEqual(backend.calls, 1)
        self.assertEqual(result.payload['explanations'][0]['disposition'], 'CONDITIONALLY_SUPPORTED')
        self.assertTrue(next(iter(w.semantic_cache.values())).backend_calls)

    def test_unique_motive_and_expression_not_emotion(self):
        _, result = self.prepare(SOURCE + '\nNarrator: Mira cried during the delay.')
        self.assertEqual(result.payload['appraisal']['reported_emotions'], [])
        self.assertTrue(all(e['unique_motive'] == 'NOT_INFERRED' for e in result.payload['explanations']))

    def test_multiple_action_episodes_refused(self):
        with self.assertRaisesRegex(ValueError, 'multiple matching'):
            self.prepare(SOURCE + '\nMira said, "I left the meeting."')


if __name__ == '__main__':
    unittest.main()
