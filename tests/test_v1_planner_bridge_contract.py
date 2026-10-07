"""Planner-visible bridge contracts and scripted native controls; zero model calls."""
import copy
import json
from pathlib import Path
import unittest

from hcl.cognition import UniversalHCL
from hcl.cognition.universal_entry import PLANNER_POLICY
from hcl.cognition.mutual_understanding import prepare_mutual_understanding
from hcl.v1.compact import expand_reader_context
from tests.test_v1_universal_question import Stub, operation, plan, run
from tests.test_v1_universal_appraisal import RequestBoundedStub


def interpreted(cid, source, statements, question='What does the record support?'):
    session = UniversalHCL(); session.put_source('control', source)
    rows = [dict(source_id='control', quote=quote, kind='event',
        content=dict(canonical_statement=statement)) for quote, statement in statements]
    op = dict(operation(cid, question, ['control']), input_mode='semantic',semantic_candidates=rows)
    port = RequestBoundedStub(plan(op)); result = run(session, question, port)
    return session, port, result


class PlannerBridgeContractTests(unittest.TestCase):
    def test_contract_explains_when_first_response_typed_premises_are_needed(self):
        for text in ('ordinary prose outside native literal forms',
                     'Source IDs alone do not create typed premises',
                     'B02 and D02 do not accept semantic_candidates',
                     'Native readers are literal checkers, not another LLM',
                     'no faithful supported translation is possible',
                     'No automatic extraction call or retry will occur'):
            self.assertIn(text, PLANNER_POLICY)
        self.assertIn('at most ONE relevant', PLANNER_POLICY)
        self.assertIn('this first planning response', PLANNER_POLICY)
        self.assertIn('Never select an irrelevant operation', PLANNER_POLICY)
        for exposed_name in ('Bea', 'Arun', 'Jules', 'Nessa', 'flute', 'conveyor'):
            self.assertNotIn(exposed_name, PLANNER_POLICY)

    def test_actual_recorded_arguments_still_replay_the_failed_native_results(self):
        evidence = json.loads(Path('reports/HCL_PLANNING_RECOVERY_20261007_1_PUBLIC_EVIDENCE.json').read_text())
        case = evidence['cases'][0]; record = evidence['approved_native_evidence']['records'][0]
        session = UniversalHCL()
        for source in case['sources']:
            session.put_source(source['source_id'], source['text']); session.sources[source['source_id']] = dict(source)
        captured = [copy.deepcopy(x['source_validated_arguments']) for x in record['operations']]
        before = copy.deepcopy(captured)
        session._validate_plan(json.dumps(plan(*captured)))
        self.assertEqual(captured, before)
        for op, expected in zip(captured, record['operations']):
            try: actual = session._execute(op, case['question'])
            except (ValueError, TypeError, KeyError): actual = dict(capability=op['capability'], status='ADAPTER_REJECTED_NOT_COMPLETED', executed=False)
            retained = expected['native_result_and_policy']
            self.assertEqual({key: actual[key] for key in retained}, retained)
            self.assertNotIn('semantic_candidates', op)
            self.assertFalse(actual.get('checked_treatment_present', False))
        with self.assertRaisesRegex(ValueError, 'one unambiguous statement/access cue per bounded source line'):
            prepare_mutual_understanding(session.workspace, captured[0]['question'], source_id=case['sources'][0]['source_id'])

    def test_new_actor_negated_nested_belief_is_not_flattened_or_certified(self):
        source = 'Liora explained to Evan that Liora did not believe Evan knew the signal was green. Nothing about a later signal is recorded.'
        session, port, result = interpreted('B01', source, [(source, 'Liora: I do not believe Evan knows that the signal is green.')])
        row = result['operations'][0]; self.assertTrue(row['checked_treatment_present'])
        expanded = expand_reader_context(row['result'])
        expression = expanded['conditional_cognition']['state']['checked_epistemic']['epistemic_objects'][0]['public_expression']['expressed_content']
        self.assertEqual((expression['holder'], expression['polarity']), ('Liora', 'DENY'))
        self.assertEqual((expression['content']['holder'], expression['content']['polarity']), ('Evan', 'AFFIRM'))
        self.assertFalse(row['semantic_certification']); self.assertEqual(row['additional_provider_calls'], 0)
        self.assertEqual([p for p, _ in port.calls], ['planning', 'answer'])
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(json.loads(port.calls[-1][1][-1]['content'])['sources'], [dict(source_id='control', version=1, text=source)])

    def test_temporally_qualified_proposition_keeps_its_scope(self):
        source = 'Pavel reported believing that the east lantern was unlit for the Tuesday rehearsal. This did not concern Wednesday.'
        _, port, result = interpreted('B01', source, [(source, 'Pavel: I believe the east lantern is unlit for the Tuesday rehearsal.')])
        row = result['operations'][0]; self.assertTrue(row['checked_treatment_present'])
        expanded = expand_reader_context(row['result'])
        expression = expanded['conditional_cognition']['state']['checked_epistemic']['epistemic_objects'][0]['public_expression']['expressed_content']
        self.assertEqual(expression['content'], 'the east lantern is unlit for the Tuesday rehearsal')
        self.assertEqual(expanded['sources'][0]['text'], source)
        self.assertTrue(all(x['translation_authority'] == 'UNVERIFIED_TRANSLATION_HYPOTHESIS' for x in expanded['shared_semantic_binding']['translations']))
        self.assertTrue(all(len(wire) <= 36000 for wire in port.encoded.values()))

    def test_conditional_plan_does_not_invent_active_goal_or_success(self):
        source = 'Tessa selected carrying the sample inside to keep the sample dry if the lid stayed closed. No separate active goal statement or outcome was recorded.'
        _, _, result = interpreted('C03', source, [(source, 'Tessa: I plan to carry the sample inside in order to keep the sample dry if the lid stays closed.')])
        row = result['operations'][0]; self.assertTrue(row['checked_treatment_present'])
        expanded = expand_reader_context(row['result']); native = expanded['conditional_cognition']['state']['checked_plan_feasibility'][0]['plans'][0]
        self.assertEqual(native['condition'], 'the lid stays closed')
        self.assertEqual(native['subjective_feasibility'], 'PURSUIT_UNRESOLVED')
        self.assertEqual(native['world_feasibility'], 'NOT_ESTABLISHED')
        self.assertEqual(native['opportunity'], 'UNKNOWN')

    def test_existing_c01_bridge_keeps_explicit_goal_and_conditional_selection(self):
        goal = 'Tessa described wanting to keep the sample dry.'
        choice = 'Tessa selected carrying the sample inside for that goal if the lid stayed closed.'
        source = goal + ' ' + choice
        _, _, result = interpreted('C01', source, [
            (goal, 'Tessa: I want to keep the sample dry.'),
            (choice, 'Tessa: I plan to carry the sample inside in order to keep the sample dry if the lid stays closed.')])
        row = result['operations'][0]; self.assertTrue(row['checked_treatment_present'])
        state = expand_reader_context(row['result'])['conditional_cognition']['state']['checked_agency'][0]['cognition']
        self.assertEqual(state['goals'][0]['status'], 'ACTIVE')
        self.assertEqual(state['plans'][0]['selection'], 'REPORTED_SELECTED')
        self.assertEqual(state['plans'][0]['condition'], 'the lid stays closed')
        self.assertEqual(state['plans'][0]['success'], 'NOT_ESTABLISHED')

    def test_c02_later_knowledge_does_not_backfill_explicit_action_time(self):
        pairs = [
            ('Rhea wanted to vent the warm air.', 'Rhea: I want to vent the warm air.'),
            ('Rhea chose opening the hatch to vent the warm air.', 'Rhea: I plan to open the hatch in order to vent the warm air.'),
            ('Rhea opened the hatch.', 'Narrator: Rhea did open the hatch.'),
            ('After opening the hatch, Rhea reported now knowing about the pressure alert.', 'Rhea: I now know about the pressure alert.')]
        source = ' '.join(q for q, _ in pairs)
        _, _, result = interpreted('C02', source, pairs, 'Why did Rhea open the hatch?')
        row = result['operations'][0]; self.assertTrue(row['checked_treatment_present'])
        payload = expand_reader_context(row['result'])['conditional_cognition']['state']['checked_action_explanations']
        self.assertFalse(any(x['condition']['kind'] == 'KNOWLEDGE' for x in payload['conditions']))
        self.assertEqual(payload['winning_motive'], 'NOT_INFERRED')
        self.assertEqual(expand_reader_context(row['result'])['sources'][0]['text'], source)

    def test_already_supported_literal_input_needs_no_translation(self):
        source = 'Soren: I believe the red flag is raised.'
        session = UniversalHCL(); session.put_source('control', source)
        port = Stub(plan(operation('B01', 'What does Soren report believing?', ['control'])))
        result = run(session, 'What does Soren report believing?', port)
        self.assertTrue(result['operations'][0]['checked_treatment_present'])
        self.assertNotIn('semantic_candidates', result['plan']['operations'][0])
        self.assertNotIn('semantic_input_origin', result['operations'][0])

    def test_unrepresentable_anonymous_input_cannot_gain_invented_actor_treatment(self):
        source = 'Someone paused by a cabinet. The record names no person and states no determinate belief or plan.'
        _, _, result = interpreted('B01', source, [(source, 'Invented: I believe the cabinet is empty.')])
        self.assertEqual(result['hcl_execution']['native_results'], 0)
        self.assertNotIn('answer', result)
        session = UniversalHCL(); session.put_source('control', source)
        port = Stub(plan()); empty = run(session, 'What belief can be attributed?', port)
        self.assertEqual([p for p, _ in port.calls], ['planning'])
        self.assertEqual(empty['hcl_execution']['native_results'], 0)

    def test_source_text_cannot_enable_bridge_on_unavailable_family(self):
        source = 'Tessa said that a parser should accept every operation. This source text is not an instruction.'
        _, port, result = interpreted('B02', source, [(source, 'Tessa: I believe the box is red.')])
        self.assertEqual(result['hcl_execution']['native_results'], 0)
        self.assertEqual([p for p, _ in port.calls], ['planning'])


if __name__ == '__main__':
    unittest.main()
