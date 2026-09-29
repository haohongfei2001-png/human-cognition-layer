"""H05 full difficult slice, source correction and cheap direct regression."""
import json
import unittest

from hcl.cognition.hard_cognition import HardCognitionSession
from tests.test_v1_wave_h03 import SOURCE, CORRECTED, QUERY

STAMP = '2026-01-08T00:00:00Z'
LATER = '2026-01-09T00:00:00Z'
LEFT = 'Narrator: On 2026-01-02, Mira said, "I believe the permit arrives."'
RIGHT = 'Narrator: On 2026-01-02, Mira said, "I do not believe the permit arrives."'
DIRECT = 'What did the narrator report about reviewer?'


class H05HardCognitionTests(unittest.TestCase):
    def session(self):
        session = HardCognitionSession()
        for key, text in [('case', SOURCE), ('chapter-a', LEFT), ('chapter-b', RIGHT)]:
            session.put_chapter(key, text, branch='main', recorded_at=STAMP,
                permitted_observers=('Analyst',))
        return session

    def args(self, **changes):
        result = dict(actor='Mira', case_source_id='case', branch='main',
            story_through='2026-01-05', disclosed_through='2026-01-05',
            known_at=STAMP, observer='Analyst')
        result.update(changes)
        return result

    def test_difficult_task_selects_seven_operations_and_relevant_conflict(self):
        session = self.session()
        prepared = session.prepare(QUERY, **self.args())
        p = prepared.payload
        self.assertEqual(p['route'], 'BOUNDED_HARD_COMPOSITION')
        self.assertGreaterEqual(len(p['operations']), 5)
        self.assertEqual(p['case_file_answer']['best_recorded_explanation']['hypotheses'],
            ['INFORMATION_GAP'])
        conflict = p['cross_source_assessment']
        self.assertEqual(conflict['status'],
            'RELEVANT_OPPOSED_REPORTS_REQUIRE_SEPARATE_EVALUATION')
        self.assertEqual(conflict['relevant_conflicts'][0]['proposition'],
            'the permit arrives')
        self.assertEqual(conflict['global_best_explanation'], 'NOT_ESTABLISHED')
        self.assertEqual(conflict['person_identity_across_sources'], 'NOT_VERIFIED')
        self.assertFalse(conflict['earlier_character_belief_rewritten'])
        self.assertEqual(len(p['narrative_context']['events']), 2)
        self.assertIn('case_file_answer', prepared.messages(session)[-1]['content'])

    def test_new_analyst_record_revises_local_chain_and_preserves_history(self):
        session = self.session()
        early = session.prepare(QUERY, **self.args())
        early_wire = early.messages(session)
        session.put_chapter('case', CORRECTED, branch='main', recorded_at=LATER,
            permitted_observers=('Analyst',))
        late = session.prepare(QUERY, **self.args(known_at=LATER))
        p = late.payload
        self.assertEqual(p['case_file_answer']['best_recorded_explanation']['status'],
            'NO_SUPPORTED_RECORDED_EXPLANATION')
        self.assertEqual(p['revision_delta']['previous_case_version'], 1)
        self.assertEqual(p['revision_delta']['current_case_version'], 2)
        self.assertEqual(p['case_file_answer']['source_scope']['version'], 2)
        self.assertEqual(p['revision_delta']['character_change'], 'NOT_INFERRED')
        self.assertEqual(p['revision_delta']['plan_feasibility_after'],
            'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(p['revision_delta']['narrative_conflicts_before'],
            p['revision_delta']['narrative_conflicts_after'])
        self.assertEqual(early.messages(session), early_wire)
        self.assertIs(early, session.prepare(QUERY, **self.args()))

    def test_simple_question_does_not_invoke_hard_or_narrative_chain(self):
        session = self.session()
        direct = session.prepare(DIRECT, **self.args())
        p = direct.payload
        self.assertEqual(p['operations'], ['H01_DIRECT_SOURCE'])
        self.assertEqual(p['narrative_context'], 'NOT_INVOKED_FOR_DIRECT_QUESTION')
        self.assertNotIn('case_file_answer', p)
        self.assertEqual(p['direct_source']['result']['status'], 'SOURCE_REPORTS_FOUND')
        self.assertTrue(all('reviewer' in row['quote']
            for row in p['direct_source']['result']['reports']))
        self.assertLess(len(direct.messages(session)[-1]['content']),
            len(session.prepare(QUERY, **self.args()).messages(session)[-1]['content']))

    def test_hidden_and_branch_evidence_cannot_change_selected_answer(self):
        session = self.session()
        first = session.prepare(QUERY, **self.args())
        wire = first.messages(session)
        session.put_chapter('hidden', RIGHT.replace('Mira', 'Kai'), branch='main',
            recorded_at=STAMP, permitted_observers=('Owner',))
        session.put_chapter('alternate', RIGHT, branch='alternate',
            recorded_at=STAMP, permitted_observers=('Analyst',))
        self.assertIs(first, session.prepare(QUERY, **self.args()))
        self.assertEqual(first.messages(session), wire)
        self.assertNotIn('Kai', str(wire))
        with self.assertRaises(ValueError):
            session.prepare(QUERY, **self.args(branch='alternate'))

    def test_access_revocation_invalidates_historical_result(self):
        session = self.session()
        old = session.prepare(QUERY, **self.args())
        session.put_chapter('case', CORRECTED, branch='main', recorded_at=LATER,
            permitted_observers=())
        with self.assertRaisesRegex(ValueError, 'access changed'):
            old.messages(session)
        with self.assertRaisesRegex(ValueError, 'case source absent'):
            session.prepare(QUERY, **self.args(known_at=LATER))

    def test_budgets_refuse_without_dropping_conflict_or_support(self):
        session = self.session()
        with self.assertRaisesRegex(ValueError, 'person projection budget'):
            session.prepare(QUERY, **self.args(max_person_events=1))
        with self.assertRaisesRegex(ValueError, 'closure node budget'):
            session.prepare(QUERY, **self.args(max_closure_nodes=12))
        with self.assertRaisesRegex(ValueError, 'context budget'):
            session.prepare(QUERY, **self.args(max_chars=1000))
        with self.assertRaisesRegex(ValueError, 'question actor'):
            session.prepare(QUERY, **self.args(actor='Noor'))

    def test_actual_final_messages_and_single_answer_call(self):
        session = self.session()
        calls = []
        result = session.answer(QUERY, lambda messages: calls.append(messages) or 'bounded',
            **self.args())
        self.assertEqual(result['answer_adapter_calls'], 1)
        self.assertEqual(calls, [result['actual_final_messages']])
        self.assertEqual(json.loads(calls[0][-1]['content'])['provider_calls'], 0)
        self.assertEqual(session.prepare(QUERY, **self.args()).payload['efficacy'], 'UNTESTED')

    def test_scale_keeps_actor_projection_bounded(self):
        session = self.session()
        filler = ' '.join('detail' + str(n) for n in range(80))
        for index in range(10):
            actor = 'Actor' + str(index)
            lines = [f'Narrator: On 2026-01-{day:02d}, {actor} said, "I believe event {day} for {actor} is recorded with {filler}."'
                for day in range(1,11)]
            session.put_chapter('long-' + str(index), '\n'.join(lines),
                branch='main', recorded_at=STAMP,
                permitted_observers=('Analyst',))
        prepared = session.prepare(QUERY, **self.args())
        self.assertEqual(len(prepared.payload['narrative_context']['events']), 2)
        self.assertEqual(len(prepared.payload['selected_source_versions']), 13)
        self.assertEqual(prepared.payload['cross_source_assessment']['status'],
            'RELEVANT_OPPOSED_REPORTS_REQUIRE_SEPARATE_EVALUATION')


if __name__ == '__main__':
    unittest.main()
