"""Complete D01 lifecycle wiring through scripted ordinary HCL entry."""
import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from hcl.cognition import CognitionWorkspace, UniversalHCL
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.commitments import prepare_commitment
from tests.test_v1_commitments import SOURCE, QUERY
from tests.test_v1_universal_appraisal import RequestBoundedStub
from tests.test_v1_universal_question import Stub, operation, plan, run

ORIGINAL = 'What was promised, what was received, and what remains unresolved?'
OP = lambda query=QUERY, ids=('scene',): operation('D01', query, list(ids))
NEGATIVE = SOURCE.replace('Noor heard', 'Noor did not hear')
LATER = "Narrator: Noor later heard Mira's last statement."
WITHDRAWAL = 'Mira said, "I withdraw my promise to Noor to deliver the report."'


def entry(source=SOURCE, query=QUERY, bounded=False):
    session = UniversalHCL(); session.put_source('scene', source)
    port = (RequestBoundedStub if bounded else Stub)(plan(OP(query)))
    return session, port, run(session, ORIGINAL, port)


def output(result):
    row = result['operations'][0]
    assert row['status'] == 'D01_EXECUTED', row
    return row, row['result']


class UniversalCommitmentTests(unittest.TestCase):
    def test_complete_native_payload_policy_claims_and_original_source_reach_answer(self):
        session, port, result = entry(bounded=True)
        row, payload = output(result)
        self.assertTrue(row['checked_treatment_present'])
        native = prepare_commitment(session.workspace, QUERY, source_id='scene')
        self.assertEqual(payload, native.payload)
        self.assertEqual(row['support_claim_ids'], list(native.claim_ids))
        self.assertIn('No moral obligation', payload['policy'])
        final = json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'], ORIGINAL)
        self.assertEqual(final['sources'], [dict(source_id='scene', version=1, text=SOURCE)])
        self.assertEqual(final['hcl_operations'][0]['result'], payload)
        self.assertTrue(all(len(raw) <= 36000 for raw in port.encoded.values()))
        self.assertEqual(result['provider_calls'], 0)

    def test_catalog_describes_native_contract_without_forcing_selection(self):
        contract = CATALOG['D01'].entry_contract
        self.assertEqual(contract.question_origin, 'OPERATION_QUESTION')
        self.assertEqual((contract.minimum_sources, contract.maximum_sources), (1, 1))
        self.assertEqual(contract.question_forms, ("What is the status of <Speaker>'s promise to <Recipient> to <action>?",))
        session, port, _ = entry()
        inventory = json.loads(port.calls[0][1][-1]['content'])['capability_inventory']
        self.assertEqual(next(x for x in inventory if x['capability_id'] == 'D01'), json.loads(json.dumps(asdict(CATALOG['D01']))))
        self.assertEqual(run(session, ORIGINAL, Stub(plan()))['operations'], [])

    def test_condition_reports_keep_unknown_false_true_and_conflict_distinct(self):
        for suffix, expected in (('', 'UNKNOWN'),
            ('\nNarrator: It is false that the permit arrives.', 'SOURCE_REPORTED_FALSE'),
            ('\nNarrator: It is true that the permit arrives.', 'SOURCE_REPORTED_TRUE'),
            ('\nNarrator: It is true that the permit arrives.\nNarrator: It is false that the permit arrives.', 'CONFLICTING_SOURCE_CLAIMS')):
            with self.subTest(expected=expected):
                _, _, result = entry(SOURCE + suffix)
                value = output(result)[1]['commitment']
                self.assertEqual(value['condition_status'], expected)
                self.assertEqual(value['obligation'], 'NOT_ESTABLISHED')
                self.assertEqual(value['blame'], 'NOT_INFERRED')

    def test_receipt_addressing_acceptance_and_private_understanding_are_separate(self):
        for source, receipt in ((NEGATIVE, 'REPORTED_NON_EXPOSURE'),
            (SOURCE.replace("Narrator: Noor heard Mira's last statement.", 'Narrator: Mira sent their last statement privately to Noor.'), 'ADDRESSED_RECEIPT_UNKNOWN'),
            (SOURCE.replace("Narrator: Noor heard Mira's last statement.", "Narrator: Mira's last statement was publicly available."), 'PUBLIC_AVAILABILITY_EXPOSURE_UNKNOWN')):
            _, _, result = entry(source); value = output(result)[1]['commitment']
            self.assertEqual(value['receipt'], receipt)
            self.assertFalse(value['conditions_received'])
            self.assertEqual(value['acceptance'], 'REPORTED_ACCEPTANCE')
            self.assertEqual(value['private_understanding'], 'NOT_ESTABLISHED')

    def test_later_receipt_never_backfills_earlier_expectation(self):
        session, _, before = entry(NEGATIVE)
        old = prepare_commitment(session.workspace, QUERY, source_id='scene')
        session.put_source('scene', NEGATIVE + '\n' + LATER)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            old.messages(session.workspace)
        after = run(session, ORIGINAL, Stub(plan(OP())))
        value = output(after)[1]
        self.assertEqual(value['commitment']['receipt'], 'REPORTED_LATER_EXPOSURE')
        self.assertEqual(value['cg02_source_check']['expectation_comparisons'][0]['condition_receipt_at_expectation'], 'REPORTED_NON_EXPOSURE')
        self.assertEqual(output(before)[1]['commitment']['receipt'], 'REPORTED_NON_EXPOSURE')
        self.assertEqual(json.loads(after['actual_final_messages'][-1]['content'])['sources'][0]['version'], 2)

    def test_withdrawal_and_fulfillment_keep_original_promise_and_history(self):
        source = SOURCE + '\n' + WITHDRAWAL + '\nMira said, "I fulfilled my promise to Noor to deliver the report."'
        _, _, result = entry(source); value = output(result)[1]
        self.assertEqual(value['commitment']['lifecycle'], 'REPORTED_WITHDRAWAL_AND_FULFILLMENT')
        self.assertEqual(len(value['commitment']['original_promise']['conditions']), 1)
        self.assertEqual(value['commitment']['fulfillment'], 'SOURCE_REPORT_NOT_VERIFIED_OUTCOME')
        self.assertEqual(value['cg02_source_check']['expectation_comparisons'][0]['withdrawal_order'], 'AFTER_REPORTED_EXPECTATION')

    def test_missing_negative_and_hypothetical_promises_are_not_treatment(self):
        for source in ('Mira said, "Ordinary words."', SOURCE.replace('I promise', 'I do not promise'),
                       'Narrator: In a hypothetical scene:\n' + SOURCE):
            _, _, result = entry(source); row, payload = output(result)
            self.assertFalse(row['checked_treatment_present'])
            self.assertEqual(payload['status'], 'SYSTEM_INSUFFICIENT')
            self.assertEqual(row['support_claim_ids'], [])

    def test_missing_multiple_sources_and_unsupported_questions_stay_explicit(self):
        for ids in ([], ['scene', 'other']):
            session = UniversalHCL(); session.put_source('scene', SOURCE); session.put_source('other', SOURCE)
            result = run(session, ORIGINAL, Stub(plan(OP(ids=ids))))
            self.assertEqual(result['operations'][0]['status'], 'D01_REQUIRES_ONE_SOURCE' if ids else 'SOURCE_PREREQUISITE_UNAVAILABLE')
        for query in ('What should Mira do?', QUERY.replace('Noor', 'Mira'),
                      QUERY.replace('deliver the report', 'x' * 201)):
            _, _, result = entry(query=query)
            self.assertEqual(result['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_multiple_promises_bounds_and_nonactual_receipt_refuse_without_repair(self):
        for source in (SOURCE + '\n' + SOURCE.splitlines()[0],
                       SOURCE + '\n' + '\n'.join('Noor said, "Ordinary words."' for _ in range(25)),
                       SOURCE.replace("Narrator: Noor heard Mira's last statement.", "Narrator: In a hypothetical scene:\nNarrator: Noor heard Mira's last statement.")):
            _, port, result = entry(source)
            self.assertEqual(result['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')
            self.assertEqual(json.loads(port.calls[-1][1][-1]['content'])['sources'][0]['text'], source)

    def test_withdrawal_of_source_or_read_dependency_stops_before_answer(self):
        for mode in ('source', 'candidate', 'result'):
            session = UniversalHCL(); session.put_source('scene', SOURCE); execute = session._execute
            def changed(*args):
                row = execute(*args)
                if mode == 'source':key = session.workspace._spans['scene']
                elif mode == 'result':key = row['support_claim_ids'][0]
                else:key = next(k for k, c in session.workspace.core.claims.items() if c.content.get('kind') == 'event')
                session.workspace.core.withdraw(key); return row
            port = Stub(plan(OP()))
            with patch.object(session, '_execute', side_effect=changed):result = run(session, ORIGINAL, port)
            self.assertEqual([p for p, _ in port.calls], ['planning'])
            self.assertEqual(result['failure_reason'], 'SOURCE_SUPPORT_CHANGED')
            self.assertNotIn('answer', result)

    def test_revision_or_support_change_during_answer_discards_delivery(self):
        for mode in ('revision', 'support'):
            session = UniversalHCL(); session.put_source('scene', SOURCE)
            def change(phase):
                if phase != 'answer':return
                if mode == 'revision':session.put_source('scene', SOURCE + '\n' + WITHDRAWAL)
                else:
                    key = next(k for k, c in session.workspace.core.claims.items() if c.content.get('operation') == 'SOCIAL_COMMITMENT_LIFECYCLE')
                    session.workspace.core.withdraw(key)
            result = run(session, ORIGINAL, Stub(plan(OP()), callback=change))
            self.assertIn('SOURCE_', result['failure_reason'])
            self.assertNotIn('answer', result)

    def test_selected_source_does_not_merge_other_outer_sources(self):
        session = UniversalHCL(); session.put_source('scene', SOURCE); session.put_source('other', 'Narrator: It is true that the permit arrives.')
        result = run(session, ORIGINAL, Stub(plan(OP())))
        self.assertEqual(output(result)[1]['commitment']['condition_status'], 'UNKNOWN')
        self.assertEqual(len(json.loads(result['actual_final_messages'][-1]['content'])['sources']), 2)

    def test_complete_planning_request_overflow_makes_no_backend_call(self):
        source = SOURCE + '\n' + 'x' * 16000
        _, port, result = entry(source, bounded=True)
        self.assertEqual(port.calls, [])
        self.assertEqual(result['status'], 'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertNotIn('answer', result)

    def test_native_expectation_withdrawal_and_social_act_limits_stay_explicit(self):
        expectation = 'Noor said, "I expect Mira to deliver the report."'
        accept = 'Noor said, "I accept Mira\'s promise to deliver the report."'
        for extra in ('\n' + expectation + '\n' + expectation,
                      '\n' + '\n'.join([WITHDRAWAL] * 3),
                      '\n' + '\n'.join([accept] * 5)):
            _, _, result = entry(SOURCE + extra)
            self.assertEqual(result['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_shared_candidate_limit_and_complete_line_contract_remain_visible(self):
        source = SOURCE + '\n' + '\n'.join('Noor said, "Ordinary words."' for _ in range(17))
        self.assertTrue(output(entry(source)[2])[0]['checked_treatment_present'])
        for rejected in (source + '\nNoor said, "Ordinary words."',
                         SOURCE.replace('\n', '\n\n', 1),
                         SOURCE.replace('\n', ' ', 1)):
            _, _, result = entry(rejected)
            self.assertEqual(result['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_complete_answer_overflow_keeps_all_three_native_results_and_source(self):
        source = SOURCE.replace('the permit arrives', 'the permit arrives ' + 'before the deadline ' * 40)
        session = UniversalHCL(); session.put_source('scene', source)
        port = RequestBoundedStub(plan(OP(), OP(), OP()))
        result = run(session, ORIGINAL, port)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])
        self.assertEqual(result['status'], 'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(len(result['operations']), 3)
        self.assertTrue(all(row['executed'] for row in result['operations']))
        self.assertTrue(all(row['result']['original_source'] == source for row in result['operations']))
        self.assertNotIn('answer', result)


if __name__ == '__main__':
    unittest.main()
