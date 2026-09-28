"""B05 ordinary multi-person updates drive actual retained checks locally."""
import json
import unittest
from hcl.cognition.integrated_scene import IntegratedScene
from hcl.cognition import CommunicationScene
from hcl.v1 import NarrativePremise, FactorRequirement, ResponsibilityFactor

RULE = NarrativePremise('control-rule', 'For this analysis control is required.',
    (FactorRequirement(ResponsibilityFactor.CONTROL, True),))
QUERIES = ('What does Noor think Mira believes?',
    "Interpret Mira's meaning of fair for proposal in team.", "Explain Mira's conditional responsibility.")
SCENE = '\n'.join(('Mira said, "In team, by fair I mean consent is true."',
    "Narrator: Noor missed Mira's last statement.", 'Narrator: In team, proposal has consent false.',
    'Narrator: Mira and Noor read the previous statement.',
    'Noor said, "I believe Mira believes the gate is open."',
    'Mira said, "I do not believe the gate is open."', "Narrator: Noor missed Mira's last statement.",
    'Mira said, "At the time I could not control the opening."', "Narrator: Noor missed Mira's last statement.",
    'Mira said, "I opened the gate."', "Narrator: Noor heard Mira's last statement.",
    'Narrator: The animals escaped.', 'Narrator: Mira and Noor read the previous statement.',
    'Narrator: Mira opening the gate caused the animals to escape.', 'Narrator: Mira and Noor read the previous statement.',
    'Kai said, "I believe the road is safe."'))


def payload(scene, result):
    return json.loads(result.current_messages(scene)[-1]['content'])


def checked(operation, key):
    state = operation['cognitive_state']
    return state['cognition_context'][key]['checked']


class IntegratedSceneTests(unittest.TestCase):
    def test_positive_access_revision_changes_nested_concept_and_responsibility_checks(self):
        scene = IntegratedScene(SCENE)
        before = scene.prepare('Noor', QUERIES, responsibility_premises=(RULE,))
        old = payload(scene, before)
        self.assertFalse(old['operations'][0]['cognitive_state']['comparisons'])
        self.assertEqual(old['operations'][1]['operation'], 'RETAINED_TASK_NOT_GROUNDED')
        factors = {r['factor']: r['state'] for r in checked(old['operations'][2], 'responsibility')['factors']}
        self.assertEqual(factors['CONTROL'], 'UNKNOWN')
        self.assertEqual(scene.update(SCENE.replace('Noor missed', 'Noor heard')), ('Noor',))
        after = scene.prepare('Noor', QUERIES, responsibility_premises=(RULE,))
        new = payload(scene, after)
        self.assertEqual(new['operations'][0]['cognitive_state']['comparisons'][0]['relation'], 'DIFFERS_FROM_SUBJECT_REPORT')
        self.assertEqual(checked(new['operations'][1], 'concepts')['readings'][0]['state'], 'CRITERIA_NOT_MET')
        resp = checked(new['operations'][2], 'responsibility')
        factors = {r['factor']: r['state'] for r in resp['factors']}
        self.assertEqual(factors['CONTROL'], 'CONTRADICTED_CLAIM')
        self.assertEqual(factors['STATED_INTENTION'], 'UNKNOWN')
        self.assertEqual(factors['KNOWLEDGE'], 'UNKNOWN')
        self.assertEqual(resp['premise_assessments'][0]['result'], 'CONDITIONALLY_NOT_SUPPORTED')
        with self.assertRaises(ValueError):
            before.current_messages(scene)

    def test_unrelated_and_direct_views_reuse_results_without_reexecution(self):
        scene = IntegratedScene(SCENE)
        mira_queries = QUERIES[1:]
        mira = scene.prepare('Mira', mira_queries, responsibility_premises=(RULE,))
        kai = scene.prepare('Kai', ('What does Kai believe?',))
        mira_wire, kai_wire = mira.current_messages(scene), kai.current_messages(scene)
        scene.prepare('Noor', QUERIES, responsibility_premises=(RULE,))
        self.assertEqual(scene.update(SCENE.replace('Noor missed', 'Noor heard')), ('Noor',))
        self.assertIs(scene.prepare('Mira', mira_queries, responsibility_premises=(RULE,)), mira)
        self.assertIs(scene.prepare('Kai', ('What does Kai believe?',)), kai)
        self.assertEqual(mira.current_messages(scene), mira_wire)
        self.assertEqual(kai.current_messages(scene), kai_wire)
        self.assertEqual(scene.executions['Mira'], 1)
        self.assertEqual(scene.executions['Kai'], 1)

    def test_existing_real_belief_concept_join_gains_missing_definition(self):
        text = '\n'.join(('Mira said, "In team, by fair I mean consent is true."',
            "Narrator: Noor missed Mira's last statement.", 'Narrator: In team, proposal has consent false.',
            'Narrator: Mira and Noor read the previous statement.', 'Mira said, "In team, I believe proposal is fair."',
            "Narrator: Noor heard Mira's last statement."))
        query = ("Compare Mira's belief and meaning of fair for proposal in team.",)
        scene = IntegratedScene(text)
        before = payload(scene, scene.prepare('Noor', query))
        self.assertEqual(before['operations'][0]['cognitive_state']['composed_cognition']['belief_concept_comparison']['rows'], [])
        scene.update(text.replace('Noor missed', 'Noor heard'))
        after = payload(scene, scene.prepare('Noor', query))
        row = after['operations'][0]['cognitive_state']['composed_cognition']['belief_concept_comparison']['rows'][0]
        self.assertEqual(row['relation'], 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA')
        self.assertEqual(row['belief_status'], 'AFFIRMED')

    def test_narrator_fact_needs_explicit_receipt_and_is_not_a_person(self):
        fact = 'Narrator: In team, proposal has consent false.'
        self.assertFalse(CommunicationScene(fact).view('Noor').events)
        view = CommunicationScene(fact + '\nNarrator: Noor read the previous statement.').view('Noor')
        self.assertEqual(view.visible_text, fact)
        self.assertIsNone(view.events[0].actor_id)
        self.assertTrue(view.events[0].metadata['narrator'])
        with self.assertRaises(ValueError):
            CommunicationScene(fact).view('Narrator')

    def test_ambiguous_access_cannot_become_generic_narrator_fact(self):
        for cue in ("Narrator: Noor probably heard Mira's last statement.",
                "Narrator: Noor later missed Mira's last statement."):
            with self.assertRaises(ValueError):
                CommunicationScene('Mira said, "I believe the gate is open."\n' + cue).view('Noor')

    def test_hidden_text_changes_neither_visible_input_nor_execution(self):
        scene = IntegratedScene(SCENE)
        result = scene.prepare('Kai', ('What does Kai believe?',))
        original = result.current_messages(scene)
        changed = SCENE.replace('consent is true', 'consent is false')
        self.assertEqual(scene.update(changed), ())
        self.assertIs(scene.prepare('Kai', ('What does Kai believe?',)), result)
        self.assertEqual(result.current_messages(scene), original)
        self.assertNotIn('consent', str(original))

    def test_empty_view_is_missing_evidence_not_a_fabricated_source(self):
        scene = IntegratedScene('Mira said, "I believe the gate is open."')
        result = scene.prepare('Noor', ('What does Noor believe?', "Explain Mira's conditional responsibility."))
        wire = payload(scene, result)
        self.assertEqual(wire['visible_source'], '')
        self.assertEqual(wire['receipt'], [])
        self.assertEqual(wire['operations'][1]['operation'], 'MISSING_OBSERVER_EVIDENCE')
        self.assertNotIn('the gate is open', str(wire))

    def test_invalid_update_is_transactional(self):
        scene = IntegratedScene(SCENE)
        result = scene.prepare('Kai', ('What does Kai believe?',))
        original = result.current_messages(scene)
        with self.assertRaises(ValueError):
            scene.update(SCENE + '\nUnparseable future material.')
        self.assertEqual(result.current_messages(scene), original)

    def test_final_adapter_receives_exact_combined_state_once(self):
        scene = IntegratedScene(SCENE.replace('Noor missed', 'Noor heard'))
        calls = []
        answer = scene.answer('Noor', QUERIES, lambda messages: calls.append(messages) or 'bounded answer',
            responsibility_premises=(RULE,))
        self.assertEqual(answer['answer_adapter_calls'], 1)
        self.assertEqual(calls, [answer['actual_final_messages']])
        self.assertEqual(len(json.loads(calls[0][-1]['content'])['operations']), 3)

    def test_budget_unsupported_queries_and_premise_routing_fail_before_answer(self):
        scene = IntegratedScene(SCENE)
        calls = []
        for queries, kwargs in [(('Infer secret motives.',), {}),
                (('What does Kai believe?',), {'responsibility_premises': (RULE,)}),
                (QUERIES, {'max_chars': 2000, 'responsibility_premises': (RULE,)})]:
            with self.assertRaises(ValueError):
                scene.answer('Noor', queries, lambda m: calls.append(m), **kwargs)
        self.assertFalse(calls)

    def test_historical_input_snapshot_stays_distinct_after_explicit_later_receipt(self):
        old_text = 'Mira said, "I believe the gate is open."\nNarrator: Noor missed Mira\'s last statement.'
        earlier = IntegratedScene(old_text)
        result = earlier.prepare('Noor', ('What does Mira believe?',))
        later = IntegratedScene(old_text + "\nNarrator: Noor later heard Mira's last statement.")
        new = later.prepare('Noor', ('What does Mira believe?',))
        self.assertNotIn('the gate is open', str(result.current_messages(earlier)))
        self.assertIn('the gate is open', str(new.current_messages(later)))


if __name__ == '__main__':
    unittest.main()
