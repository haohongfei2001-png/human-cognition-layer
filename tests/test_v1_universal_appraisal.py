"""C04 complete ordinary-entry wiring; scripted ports are not model evidence."""
import json
import unittest
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.appraisal import prepare_appraisal
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort, MAX_REQUEST_BYTES
from tests.test_v1_appraisal import G, H, P, N, E, Q
from tests.test_v1_universal_question import Stub, operation, plan, run

SOURCE = '\n'.join((G, H, P, N, E))
ORIGINAL = "How is the delay related to Mira's goals and reported feelings?"


class RequestBoundedStub(Stub):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = DeepSeekMeteredPort(SimpleNamespace(
            max_retries=0, base_url='https://api.deepseek.com', timeout=60))
        self.encoded = {}
        self.quoted_phases = []

    def reservation_usd(self, phase, messages):
        self.quoted_phases.append(phase)
        _, encoded = self.validator.request(phase, messages)
        self.encoded[phase] = encoded
        return '0'  # Pure local request validation, no SDK send or paid allowance.


def entry(source=SOURCE, query=Q, original=ORIGINAL, callback=None, bounded=False):
    session = UniversalHCL()
    session.put_source('scene', source)
    cls = RequestBoundedStub if bounded else Stub
    port = cls(plan(operation('C04', query, ['scene'])), callback=callback)
    return session, port, run(session, original, port)


def output(receipt):
    row = receipt['operations'][0]
    assert row['status'] == 'C04_EXECUTED', row
    return row, row['result']


class UniversalAppraisalTests(unittest.TestCase):
    def test_real_mixed_appraisal_reaches_complete_final_request(self):
        session, port, receipt = entry(bounded=True)
        row, native = output(receipt)
        self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(native['appraisal']['goal_congruence'], 'MIXED_GOAL_CONGRUENCE')
        self.assertEqual(native['appraisal']['reported_emotions'], ['relieved', 'worried'])
        self.assertEqual(native['appraisal']['inferred_actual_emotion'], 'NOT_ESTABLISHED')
        self.assertIn('observed expressions', native['policy'])
        final = json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'], ORIGINAL)
        self.assertEqual(final['hcl_plan']['operations'][0]['question'], Q)
        self.assertEqual(final['sources'], [dict(source_id='scene', version=1, text=SOURCE)])
        self.assertEqual(final['hcl_operations'][0]['result'], native)
        self.assertTrue(row['support_claim_ids'])
        self.assertTrue(all(session.workspace.core.support_statuses()[key] == 'SUPPORT_AVAILABLE'
                            for key in row['support_claim_ids']))
        self.assertEqual(set(port.encoded), {'planning', 'answer'})
        self.assertTrue(all(len(raw) <= MAX_REQUEST_BYTES for raw in port.encoded.values()))
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertEqual(receipt['reserved_usd'], '0')

    def test_catalog_contract_reaches_planner_without_forcing_selection(self):
        contract = CATALOG['C04'].entry_contract
        self.assertEqual(contract.question_origin, 'OPERATION_QUESTION')
        self.assertEqual((contract.minimum_sources, contract.maximum_sources), (1, 1))
        self.assertEqual(contract.question_forms, ('How does <Actor> appraise <episode>?',))
        session, port, _ = entry()
        inventory = json.loads(port.calls[0][1][-1]['content'])['capability_inventory']
        self.assertEqual(next(x for x in inventory if x['capability_id'] == 'C04'),
                         json.loads(json.dumps(asdict(CATALOG['C04']))))
        no_plan = Stub(plan())
        result = run(session, ORIGINAL, no_plan)
        self.assertEqual(result['operations'], [])
        self.assertFalse(result['answer_gain_established'])

    def test_missing_and_multiple_sources_remain_explicit(self):
        for source_ids in ([], ['a', 'b']):
            session = UniversalHCL()
            session.put_source('a', SOURCE)
            session.put_source('b', SOURCE)
            port = Stub(plan(operation('C04', Q, source_ids)))
            receipt = run(session, ORIGINAL, port)
            self.assertEqual(receipt['operations'][0]['status'],
                             'C04_REQUIRES_ONE_SOURCE' if source_ids else 'SOURCE_PREREQUISITE_UNAVAILABLE')
            self.assertFalse(receipt['operations'][0]['executed'])
            self.assertEqual(len(json.loads(port.calls[-1][1][-1]['content'])['sources']), 2)

    def test_unsupported_question_and_existing_statement_budgets_refuse(self):
        for query in ('How does Mira feel about the delay?', 'How does Mira appraise ' + 'x' * 161 + '?'):
            _, _, receipt = entry(query=query)
            self.assertEqual(receipt['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')
            self.assertFalse(receipt['operations'][0]['executed'])
        _, port, receipt = entry(source='\n'.join([E] * 21))
        self.assertEqual(receipt['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')
        self.assertEqual(json.loads(port.calls[-1][1][-1]['content'])['sources'][0]['text'], '\n'.join([E] * 21))

    def test_goal_only_empty_and_missing_episode_are_not_c04_treatment(self):
        unanchored = G + '\nMira said, "I now see the delay as harmful for my goal to rest."'
        for source, query in ((G, Q), ('Nothing was reported.', Q),
                              (SOURCE, 'How does Mira appraise the arrival?'),
                              (E.replace('Mira', 'Noor'), Q), (unanchored, Q)):
            _, _, receipt = entry(source=source, query=query)
            row, native = output(receipt)
            self.assertTrue(row['executed'])
            self.assertFalse(row['checked_treatment_present'])
            self.assertEqual(native['retained_v08']['current_evidence'], [])
            self.assertEqual(native['appraisal']['reported_emotions'], [])

    def test_agency_and_appraisal_row_caps_are_separate_native_limits(self):
        sources = (('\n'.join([E] * 17), 'agency statement budget'),
                   (E + '\n' + '\n'.join(f'Actor{i}: I wait.' for i in range(20)),
                    'appraisal source statement budget'))
        for source, error in sources:
            session = UniversalHCL()
            session.put_source('scene', source)
            with self.assertRaisesRegex(ValueError, error):
                prepare_appraisal(session.workspace, Q, source_id='scene')
            result = run(session, ORIGINAL, Stub(plan(operation('C04', Q, ['scene']))))
            self.assertEqual(result['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')
            self.assertFalse(result['operations'][0]['executed'])

    def test_selecting_one_source_preserves_other_outer_sources(self):
        session = UniversalHCL()
        session.put_source('scene', SOURCE)
        session.put_source('other', 'A separate supplied account.')
        port = Stub(plan(operation('C04', Q, ['scene'])))
        result = run(session, ORIGINAL, port)
        _, native = output(result)
        self.assertEqual([x['source_id'] for x in native['original_sources']], ['scene'])
        final = json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual([x['source_id'] for x in final['sources']], ['scene', 'other'])
        self.assertEqual(final['sources'][1]['text'], 'A separate supplied account.')

    def test_missing_or_future_goal_is_not_backfilled(self):
        for source in (P, P + '\n' + G):
            _, _, receipt = entry(source=source)
            row, native = output(receipt)
            self.assertFalse(row['checked_treatment_present'])
            self.assertEqual(native['appraisal']['goal_congruence'], 'NO_CURRENT_GOAL_LINKED_APPRAISAL')
            self.assertIn('APPRAISAL_LACKS_PRIOR_SOURCE_GOAL', str(native['diagnostics']))

    def test_expression_and_attribution_are_not_direct_feelings(self):
        source = 'Narrator: Mira smiled during the delay.\nNoor said, "Mira seems worried about the delay."'
        _, _, receipt = entry(source=source)
        row, native = output(receipt)
        self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(native['appraisal']['reported_emotions'], [])
        self.assertEqual({e['strength'] for e in native['retained_v08']['current_evidence']}, {'INFERRED', 'ATTRIBUTED'})
        self.assertEqual(native['appraisal']['inferred_actual_emotion'], 'NOT_ESTABLISHED')

    def test_character_uncertainty_control_and_certainty_keep_report_channels(self):
        source = '\n'.join(('Mira said, "I am unsure how I feel about the delay."',
            'Mira said, "About the delay, I feel in control."',
            'Mira said, "About the delay, I am certain about the outcome."'))
        _, _, receipt = entry(source=source)
        row, native = output(receipt)
        self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(native['retained_v08']['emotion_status'], 'CHARACTER_UNCERTAIN')
        self.assertEqual(native['appraisal']['actual_control'], 'NOT_ESTABLISHED')
        self.assertEqual(native['appraisal']['actual_knowledge'], 'NOT_ESTABLISHED')

    def test_embedded_ambiguous_and_hypothetical_sources_cannot_create_feelings(self):
        for source in ('```example\n' + E + '\n```', '[Direction.\n' + E + '\n]',
                       'Narrator: In a hypothetical scene:\n' + E,
                       '“Quoted example.\n' + E + '\n”', E.replace('Mira', 'She')):
            _, _, receipt = entry(source=source)
            row, native = output(receipt)
            self.assertFalse(row['checked_treatment_present'])
            self.assertEqual(native['appraisal']['reported_emotions'], [])
        _, _, receipt = entry(source='Noor said, "This scene is hypothetical."\n' + E)
        self.assertEqual(output(receipt)[1]['appraisal']['reported_emotions'], ['relieved', 'worried'])

    def test_reappraisal_and_goal_revision_recompute_on_shared_source_version(self):
        session, _, before = entry()
        old = prepare_appraisal(session.workspace, Q, source_id='scene')
        revision = 'Mira said, "I now see the delay as harmful for my goal to rest."'
        session.put_source('scene', SOURCE + '\n' + revision)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            old.messages(session.workspace)
        result = run(session, ORIGINAL, Stub(plan(operation('C04', Q, ['scene']))))
        _, native = output(result)
        self.assertEqual(native['appraisal']['goal_congruence'], 'HINDERS_EVIDENCED_GOALS')
        self.assertEqual(len(native['retained_v08']['historical_evidence']), 1)
        self.assertEqual(native['original_sources'][0]['version'], 2)
        self.assertEqual(output(before)[1]['appraisal']['goal_congruence'], 'MIXED_GOAL_CONGRUENCE')
        session.put_source('scene', SOURCE + '\nMira said, "I abandoned my goal to finish the report."')
        result = run(session, ORIGINAL, Stub(plan(operation('C04', Q, ['scene']))))
        _, native = output(result)
        self.assertEqual(native['appraisal']['goal_congruence'], 'SUPPORTS_EVIDENCED_GOALS')
        self.assertEqual(len(native['appraisal']['suspended_goal_links']), 1)
        self.assertEqual(native['appraisal']['reported_emotions'], ['relieved', 'worried'])
        self.assertEqual(native['original_sources'][0]['version'], 3)

    def test_revision_during_planning_or_answer_prevents_delivery(self):
        for changed_phase in ('planning', 'answer'):
            session = UniversalHCL()
            session.put_source('scene', SOURCE)
            port = Stub(plan(operation('C04', Q, ['scene'])),
                        callback=lambda phase: session.put_source('scene', G) if phase == changed_phase else None)
            result = run(session, ORIGINAL, port)
            self.assertEqual(result['status'], 'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
            self.assertNotIn('answer', result)
            self.assertIn('SOURCE_CHANGED', result['failure_reason'])

    def test_withdrawal_of_appraisal_support_during_answer_prevents_delivery(self):
        session = UniversalHCL()
        session.put_source('scene', SOURCE)
        def withdraw(phase):
            if phase == 'answer':
                final = next(key for key, claim in session.workspace.core.claims.items()
                             if claim.content.get('operation') == 'GOAL_APPRAISAL_AFFECT_CHANNEL_JOIN')
                session.workspace.core.withdraw(final)
        result = run(session, ORIGINAL, Stub(plan(operation('C04', Q, ['scene'])), callback=withdraw))
        self.assertEqual(result['status'], 'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(result['failure_reason'], 'SOURCE_SUPPORT_CHANGED')
        self.assertNotIn('answer', result)

    def test_withdrawal_after_preparation_stops_before_answer_admission(self):
        session = UniversalHCL()
        session.put_source('scene', SOURCE)
        execute = session._execute
        def changed(*args):
            result = execute(*args)
            final = next(key for key, claim in session.workspace.core.claims.items()
                         if claim.content.get('operation') == 'GOAL_APPRAISAL_AFFECT_CHANNEL_JOIN')
            session.workspace.core.withdraw(final)
            return result
        port = Stub(plan(operation('C04', Q, ['scene'])))
        with patch.object(session, '_execute', side_effect=changed):
            result = run(session, ORIGINAL, port)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])
        self.assertEqual(result['failure_reason'], 'SOURCE_SUPPORT_CHANGED')
        self.assertNotIn('answer', result)

    def test_complete_request_overflow_stops_before_answer_without_dropping_operations(self):
        session = UniversalHCL()
        source = '\n'.join(SOURCE.replace('Mira', actor) for actor in ('Mira', 'Noor', 'Sana'))
        session.put_source('scene', source)
        port = RequestBoundedStub(plan(*(operation('C04', f'How does {actor} appraise the delay?', ['scene'])
                                         for actor in ('Mira', 'Noor', 'Sana'))))
        receipt = run(session, 'Compare their reported appraisals without guessing private feelings.', port)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])
        self.assertEqual(port.quoted_phases, ['planning', 'answer'])
        self.assertEqual(len(receipt['operations']), 3)
        self.assertTrue(all(row['executed'] for row in receipt['operations']))
        final = json.loads(receipt['actual_final_messages'][-1]['content'])
        self.assertEqual(final['sources'][0]['text'], source)
        self.assertTrue(all(row['result']['original_sources'][0]['text'] == source for row in final['hcl_operations']))
        self.assertEqual(receipt['status'], 'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertNotIn('answer', receipt)

    def test_oversized_complete_source_stops_before_planner_call(self):
        session = UniversalHCL()
        source = 'Complete supplied source. ' * 2000
        session.put_source('scene', source)
        port = RequestBoundedStub(plan(operation('C04', Q, ['scene'])))
        result = run(session, ORIGINAL, port)
        self.assertEqual(port.calls, [])
        self.assertEqual(port.quoted_phases, ['planning'])
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(session.sources['scene']['text'], source)


if __name__ == '__main__':
    unittest.main()
