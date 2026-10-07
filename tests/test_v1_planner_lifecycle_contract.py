"""Planner-visible existing lifecycle grammar, not model efficacy evidence."""
from dataclasses import asdict
import hashlib
import json
import unittest

from hcl.cognition import UniversalHCL
from hcl.cognition.universal_entry import PLANNER_POLICY, CATALOG
from hcl.v1.compact import expand_reader_context
from tests.test_v1_universal_question import operation, plan, run
from tests.test_v1_universal_appraisal import RequestBoundedStub

FORMS = (
    'NAME: I am considering a plan to ACTION in order to GOAL if CONDITION.',
    'NAME: I abandoned the plan to ACTION.',
    'NAME: I completed the plan to ACTION.',
    'NAME: I abandoned my goal to GOAL.',
    'NAME: I completed my goal to GOAL.',
    'NAME: I am unsure whether to GOAL.',
)
LIFECYCLE_CONTRACT_ADDITION = (
    'Goal/plan lifecycle forms also include NAME: I am considering a plan to ACTION in order to GOAL if CONDITION.; '
    'NAME: I abandoned the plan to ACTION.; NAME: I completed the plan to ACTION.; '
    'NAME: I abandoned my goal to GOAL.; NAME: I completed my goal to GOAL.; NAME: I am unsure whether to GOAL. '
    'Keep goal and plan changes distinct. Consideration is not selection. Do not infer completion from an outcome. ')
GOAL = ('Pelo expressed a desire to illuminate the workshop.',
        'Pelo: I want to illuminate the workshop.')
PLAN = ('Pelo chose to use a lantern to illuminate the workshop.',
        'Pelo: I plan to use a lantern in order to illuminate the workshop.')
QUESTION = "What are Pelo's goals and plans, and what remains unestablished?"


def perform(pairs):
    source = '\n'.join(quote for quote, _ in pairs)
    session = UniversalHCL()
    session.put_source('workshop', source)
    rows = [dict(source_id='workshop', quote=quote, kind='event',
                 content=dict(canonical_statement=statement)) for quote, statement in pairs]
    op = dict(operation('C01', "What are Pelo's goals and plans?", ['workshop']),
              semantic_candidates=rows)
    port = RequestBoundedStub(plan(op))
    result = run(session, QUESTION, port)
    expanded = expand_reader_context(result['operations'][0]['result'])
    return source, rows, port, result, expanded['conditional_cognition']['state']['checked_agency'][0]['cognition']


class PlannerLifecycleContractTests(unittest.TestCase):
    def test_compact_planning_preserves_every_value_and_embedded_whitespace(self):
        for text in ('Line one.\n\n Two spaces:  : ,  \t🙂 中文', 'Mara reported "quoted" text and \\slashes.'):
            with self.subTest(text=text):
                session = UniversalHCL()
                session.put_source('unicode-source', text)
                port = RequestBoundedStub(plan())
                question = 'Keep  exact spacing:  : , and 🙂?'
                result = run(session, question, port)
                self.assertEqual(len(port.calls), 1)
                self.assertEqual(result['failure_reason'], 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER')
                content = port.calls[0][1][-1]['content']
                expected = dict(question=question, sources=list(session.sources.values()),
                                capability_inventory=[asdict(c) for c in CATALOG.values()])
                self.assertEqual(json.loads(content), json.loads(json.dumps(expected)))
                self.assertEqual(json.loads(content)['sources'][0]['text'].encode(), text.encode())
                request = json.loads(port.encoded['planning'])
                self.assertEqual(request['messages'][-1]['content'], content)
                canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
                self.assertEqual(hashlib.sha256(port.encoded['planning']).hexdigest(), hashlib.sha256(canonical).hexdigest())
                self.assertEqual(port.encoded['planning'], canonical)
                self.assertEqual(content, json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
                self.assertLess(len(content), len(json.dumps(expected, ensure_ascii=False, sort_keys=True)))

    def test_truly_oversized_complete_planning_is_still_refused(self):
        session = UniversalHCL()
        session.put_source('large', 'Source content. ' * 1000)
        port = RequestBoundedStub(plan())
        result = run(session, 'Question ' * 800, port)
        self.assertEqual(port.calls, [])
        self.assertEqual(result['final_delivery_code'], 'NOT_REACHED')
        self.assertEqual(result['hcl_execution']['native_results'], 0)

    def test_existing_lifecycle_forms_are_available_in_actual_planning_policy(self):
        _, _, port, _, _ = perform((GOAL, PLAN))
        self.assertEqual(port.calls[0][0], 'planning')
        self.assertEqual(port.calls[0][1][0]['content'], PLANNER_POLICY)
        for form in FORMS:
            with self.subTest(form=form):
                self.assertIn(form, PLANNER_POLICY)
        self.assertIn('Consideration is not selection', PLANNER_POLICY)
        self.assertIn('Do not infer completion from an outcome', PLANNER_POLICY)

    def test_plan_consideration_and_closure_keep_goal_separate(self):
        cases = (
            ((GOAL, ('Pelo considered using a lantern to illuminate the workshop without selecting it.',
                     'Pelo: I am considering a plan to use a lantern in order to illuminate the workshop.')),
             'CONSIDERED_NOT_SELECTED'),
            ((GOAL, PLAN, ('Pelo reported canceling the lantern plan.',
                          'Pelo: I abandoned the plan to use a lantern.')), 'REPORTED_ABANDONED'),
            ((GOAL, PLAN, ('Pelo reported finishing the lantern plan.',
                          'Pelo: I completed the plan to use a lantern.')), 'REPORTED_COMPLETED'),
        )
        for pairs, expected in cases:
            with self.subTest(selection=expected):
                _, _, _, _, agency = perform(pairs)
                self.assertEqual(agency['plans'][0]['selection'], expected)
                self.assertEqual(agency['goals'][0]['status'], 'ACTIVE')
                self.assertEqual(agency['plans'][0]['success'], 'NOT_ESTABLISHED')

    def test_goal_uncertainty_and_closure_do_not_rewrite_selected_plan(self):
        cases = (
            ('Pelo expressed uncertainty about pursuing workshop illumination.',
             'Pelo: I am unsure whether to illuminate the workshop.', 'CHARACTER_UNCERTAIN'),
            ('Pelo reported giving up the workshop illumination goal.',
             'Pelo: I abandoned my goal to illuminate the workshop.', 'ABANDONED'),
            ('Pelo reported completing the workshop illumination goal.',
             'Pelo: I completed my goal to illuminate the workshop.', 'COMPLETED'),
        )
        for quote, statement, expected in cases:
            with self.subTest(goal_status=expected):
                _, _, _, _, agency = perform((GOAL, PLAN, (quote, statement)))
                self.assertEqual(agency['goals'][0]['status'], expected)
                self.assertEqual(agency['plans'][0]['selection'], 'REPORTED_SELECTED')
                self.assertEqual(agency['plans'][0]['success'], 'NOT_ESTABLISHED')

    def test_full_source_unverified_bindings_and_real_native_delivery_remain(self):
        source, rows, port, result, _ = perform((GOAL, PLAN,
            ('Pelo reported canceling the lantern plan.', 'Pelo: I abandoned the plan to use a lantern.')))
        self.assertEqual([phase for phase, _ in port.calls], ['planning', 'answer'])
        self.assertEqual(result['final_delivery_code'], 'DELIVERED')
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(result['hcl_execution']['native_results'], 1)
        native = result['operations'][0]
        self.assertEqual(native['status'], 'EXISTING_CONDITIONAL_READER_EXECUTED')
        self.assertTrue(native['checked_treatment_present'])
        self.assertFalse(native['semantic_certification'])
        expanded = expand_reader_context(native['result'])
        bindings = expanded['shared_semantic_binding']['translations']
        self.assertEqual(len(bindings), len(rows))
        self.assertTrue(all(x['translation_authority']=='UNVERIFIED_TRANSLATION_HYPOTHESIS' for x in bindings))
        final = json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'], QUESTION)
        self.assertEqual(final['sources'], [dict(source_id='workshop', version=1, text=source)])
        self.assertTrue(all(len(raw) <= 36000 for raw in port.encoded.values()))


if __name__ == '__main__':
    unittest.main()
