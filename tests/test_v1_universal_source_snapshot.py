"""Shared source identity must stay coherent through ordinary HCL delivery.

All model phases use local stubs. These are boundary regressions, not efficacy.
"""
import json
import unittest
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.core import ClaimKind, Scope
from tests.test_v1_universal_question import Stub, operation, plan, run


SOURCE = 'Nia said, "I believe the gate is clear."'
REVISED = 'Nia said, "I believe the gate is blocked."'
QUESTION = 'What does the current source say Nia believes?'


def session():
    value = UniversalHCL()
    value.put_source('story', SOURCE)
    return value


def planned():
    return plan(operation('B01', 'What does Nia report believing?', ['story']))


class UniversalSourceSnapshotTests(unittest.TestCase):
    def assert_source_rejected(self, result, port, phases):
        self.assertEqual(result['status'], 'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(result['failure_type'], 'BOUNDARY_REJECTION')
        self.assertEqual(result['failure_reason'], 'SOURCE_CHANGED_DURING_ORCHESTRATION')
        self.assertNotIn('answer', result)
        self.assertNotEqual(result['final_delivery_code'], 'DELIVERED')
        self.assertEqual([phase for phase, _ in port.calls], phases)
        self.assertEqual(result['provider_calls'], 0)

    def test_workspace_revision_before_planning_stops_without_backend_call(self):
        active = session()
        active.workspace.put_source('story', REVISED)
        port = Stub(planned())
        result = run(active, QUESTION, port)
        self.assert_source_rejected(result, port, [])
        self.assertEqual(result['operations'], [])

    def test_workspace_revision_during_planning_stops_before_native_dispatch(self):
        active = session()
        port = Stub(planned(), callback=lambda phase:
                    active.workspace.put_source('story', REVISED) if phase == 'planning' else None)
        result = run(active, QUESTION, port)
        self.assert_source_rejected(result, port, ['planning'])
        self.assertEqual(result['operations'], [])
        self.assertEqual(active.sources['story']['version'], 1)
        self.assertEqual(active.workspace._versions['story'], 2)

    def test_workspace_revision_around_native_execution_never_reaches_answer(self):
        for when in ('before', 'after'):
            with self.subTest(when=when):
                active = session()
                original = active._execute
                def revise(*args):
                    if when == 'before':
                        active.workspace.put_source('story', REVISED)
                    result = original(*args)
                    if when == 'after':
                        active.workspace.put_source('story', REVISED)
                    return result
                port = Stub(planned())
                with patch.object(active, '_execute', side_effect=revise):
                    result = run(active, QUESTION, port)
                self.assert_source_rejected(result, port, ['planning'])
                self.assertEqual(result['hcl_execution']['native_results'], 1)
                self.assertNotIn('actual_final_messages', result)

    def test_revision_between_operations_preserves_completed_count_and_stops_dispatch(self):
        active = session()
        original = active._execute
        def revise(*args):
            result = original(*args)
            active.workspace.put_source('story', REVISED)
            return result
        port = Stub(plan(operation('B01', 'What does Nia report believing?', ['story']),
                         operation('B02', 'Who received this report?', ['story'])))
        with patch.object(active, '_execute', side_effect=revise) as native:
            result = run(active, QUESTION, port)
        self.assert_source_rejected(result, port, ['planning'])
        self.assertEqual(native.call_count, 1)
        self.assertEqual(result['hcl_execution']['status'], 'DISPATCH_ABORTED')
        self.assertEqual(result['hcl_execution']['native_results'], 1)

    def test_final_phase_workspace_revision_rejects_empty_support_native_result(self):
        active = UniversalHCL()
        active.put_source('story', 'Nia said, "The gate is clear."')
        port = Stub(plan(operation('C02', 'Why did Nia cross the gate?', ['story'])),
                    callback=lambda phase: active.workspace.put_source(
                        'story', 'Nia said, "I crossed the gate."') if phase == 'answer' else None)
        result = run(active, 'What does this source establish?', port)
        self.assert_source_rejected(result, port, ['planning', 'answer'])
        self.assertEqual(result['operations'][0]['result']['status'], 'SYSTEM_INSUFFICIENT')
        self.assertEqual(result['operations'][0]['support_claim_ids'], [])
        self.assertIn('answer_raw', result)
        self.assertEqual(result['final_delivery_code'], 'RETURNED_UNVALIDATED')

    def test_workspace_removal_at_either_model_phase_is_classified_and_rejected(self):
        for changed_phase in ('planning', 'answer'):
            with self.subTest(phase=changed_phase):
                active = session()
                port = Stub(planned(), callback=lambda phase:
                            active.workspace.remove_source('story') if phase == changed_phase else None)
                result = run(active, QUESTION, port)
                self.assert_source_rejected(result, port,
                    ['planning'] if changed_phase == 'planning' else ['planning', 'answer'])

    def test_equal_version_with_different_wrapper_text_is_not_identity(self):
        active = session()
        def change_text(phase):
            if phase == 'planning':
                active.sources['story']['text'] = REVISED
        port = Stub(planned(), callback=change_text)
        result = run(active, QUESTION, port)
        self.assertEqual(active.sources['story']['version'], active.workspace._versions['story'])
        self.assert_source_rejected(result, port, ['planning'])

    def test_normal_wrapper_revisions_are_still_rejected(self):
        for changed_phase in ('planning', 'answer'):
            with self.subTest(phase=changed_phase):
                active = session()
                port = Stub(planned(), callback=lambda phase:
                            active.put_source('story', REVISED) if phase == changed_phase else None)
                result = run(active, QUESTION, port)
                self.assert_source_rejected(result, port,
                    ['planning'] if changed_phase == 'planning' else ['planning', 'answer'])

    def test_same_version_reputs_unrelated_sources_and_derived_state_remain_valid(self):
        for update in ('same_text', 'unrelated_source', 'derived_state'):
            with self.subTest(update=update):
                active = session()
                def keep_source(phase):
                    if update == 'same_text':
                        active.workspace.put_source('story', SOURCE)
                    elif update == 'unrelated_source':
                        active.workspace.put_source('unselected', 'Zed reports an unrelated event.')
                    else:
                        claim = active.workspace.core.claim(Scope(source_ids=('story',)),
                            ClaimKind.SYSTEM_INTERPRETATION, {'phase': phase, 'test': 'source-unmodified'})
                        active.workspace.core.support(claim, active.workspace._spans['story'])
                port = Stub(planned(), callback=keep_source)
                result = run(active, QUESTION, port)
                self.assertEqual(result['final_delivery_code'], 'DELIVERED')
                self.assertEqual(result['hcl_execution']['native_results'], 1)
                self.assertTrue(result['operations'][0]['checked_treatment_present'])
                payload = json.loads(result['actual_final_messages'][-1]['content'])
                expected = [dict(source_id='story', text=SOURCE, version=1)]
                self.assertEqual(payload['sources'], expected)
                self.assertEqual(result['operations'][0]['result']['sources'], expected)
                self.assertEqual(result['provider_calls'], 0)
                self.assertEqual([phase for phase, _ in port.calls], ['planning', 'answer'])

    def test_source_root_withdrawal_remains_a_support_boundary(self):
        for changed_phase in ('planning', 'answer'):
            with self.subTest(phase=changed_phase):
                active = session()
                port = Stub(planned(), callback=lambda phase:
                            active.workspace.core.withdraw(active.workspace._spans['story'])
                            if phase == changed_phase else None)
                result = run(active, QUESTION, port)
                self.assertEqual(result['failure_reason'], 'SOURCE_SUPPORT_CHANGED')
                self.assertNotIn('answer', result)

    def test_explicit_wrapper_resynchronization_allows_fresh_version_execution(self):
        active = session()
        active.workspace.put_source('story', REVISED)
        active.put_source('story', REVISED)
        port = Stub(planned())
        result = run(active, QUESTION, port)
        self.assertEqual(result['final_delivery_code'], 'DELIVERED')
        expected = [dict(source_id='story', text=REVISED, version=2)]
        self.assertEqual(json.loads(result['actual_final_messages'][-1]['content'])['sources'], expected)
        self.assertEqual(result['operations'][0]['result']['sources'], expected)
        self.assertEqual(result['provider_calls'], 0)


if __name__ == '__main__':
    unittest.main()
