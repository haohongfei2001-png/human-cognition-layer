"""Offline contract/diagnostic regressions; no claim about a particular model response."""
import copy
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch

from hcl.cognition.universal_entry import (
    CallAllowance, HCLBoundaryError, UniversalHCL, safe_orchestration_failure_details,
)
from test_v1_universal_question import Stub, operation, plan, run


def actor(source='episode', quote='Mira', **extra):
    value = dict(role='actor', source_id=source, quote=quote)
    value.update(extra)
    return value


def session(text='Mira: I opened the gate.\nNarrator: The animals escaped.'):
    value = UniversalHCL()
    with patch('hcl.cognition.universal_entry.datetime') as clock:
        clock.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)
        value.put_source('episode', text)
    return value


def proposed(*bindings):
    return plan(operation('G02', 'Assess the original caller rule.', ['episode'], bindings))


class QuoteBindingTests(unittest.TestCase):
    def test_unique_missing_offset_matches_explicit_plan_without_mutating_input(self):
        original = proposed(actor()); before = copy.deepcopy(original)
        implicit = session()._validate_plan(json.dumps(original), require_input_modes=True)
        explicit = session()._validate_plan(json.dumps(proposed(actor(start=0))), require_input_modes=True)
        self.assertEqual(implicit, explicit)
        self.assertEqual(original, before)

    def test_missing_and_explicit_paths_execute_same_real_g02_conditions(self):
        results = []
        for b in (actor(), actor(start=0)):
            s = session(); port = Stub(proposed(b))
            result = run(s, 'For this analysis, responsibility requires causal contribution. Was Mira responsible?', port)
            self.assertEqual(result['status'], 'ANSWERED_WITH_EXPLICIT_LIMITS')
            self.assertTrue(result['operations'][0]['executed'])
            self.assertEqual(result['operations'][0]['result']['individuals'][0]['status'], 'SOURCE_FACTORS_CHECKED')
            final = json.loads(port.calls[-1][1][-1]['content'])
            self.assertEqual(final['sources'][0]['text'], s.sources['episode']['text'])
            self.assertEqual(final['hcl_plan']['operations'][0]['bindings'], [actor(start=0)])
            results.append((result['plan'], result['operations'][0]['result']))
        self.assertEqual(*results)

    def test_unicode_offsets_count_exact_codepoints_without_normalization(self):
        text = '\U0001f33fe\u0301\r\nMira left.'
        s = session(text)
        value = s._validate_plan(json.dumps(proposed(actor())))
        self.assertEqual(value['operations'][0]['bindings'][0]['start'], 5)
        for quote in ('é', ' Mira', 'mira'):
            with self.subTest(quote=quote), self.assertRaises(HCLBoundaryError):
                s._validate_plan(json.dumps(proposed(actor(quote=quote))))
        self.assertEqual(s.sources['episode']['text'], text)

    def test_repeated_quotes_need_explicit_offset_and_overlaps_count(self):
        s = session('Mira met Mira.')
        with self.assertRaises(HCLBoundaryError): s._validate_plan(json.dumps(proposed(actor())))
        for offset in (0, 9):
            value = s._validate_plan(json.dumps(proposed(actor(start=offset))))
            self.assertEqual(value['operations'][0]['bindings'][0]['start'], offset)
        with self.assertRaises(HCLBoundaryError):
            session('aaaa')._validate_plan(json.dumps(proposed(actor(quote='aaa'))))

    def test_explicit_invalid_offsets_never_get_repaired_even_for_unique_quote(self):
        for offset in (None, False, True, 0.0, '0', -1, 1, 999999):
            with self.subTest(offset=offset), self.assertRaises(HCLBoundaryError):
                session()._validate_plan(json.dumps(proposed(actor(start=offset))))

    def test_absent_empty_oversized_and_nonstring_quotes_refuse(self):
        for quote in ('', 'Absent', 'x' * 129, None, [], 7):
            with self.subTest(quote=quote), self.assertRaises(HCLBoundaryError):
                session()._validate_plan(json.dumps(proposed(actor(quote=quote))))

    def test_binding_schema_role_and_source_selection_remain_strict(self):
        bad = [actor(source='unknown'), actor(role='authority'), actor(untrusted=True)]
        for key in ('role', 'source_id', 'quote'):
            value = actor(); del value[key]; bad.append(value)
        for value in bad:
            with self.subTest(value=value), self.assertRaises(HCLBoundaryError):
                session()._validate_plan(json.dumps(proposed(value)))

    def test_uniqueness_is_within_named_source_and_never_borrows_another_source(self):
        s = session(); s.put_source('other', 'Mira arrived.')
        value = proposed(actor(), actor(source='other'))
        value['operations'][0]['source_ids'].append('other')
        parsed = s._validate_plan(json.dumps(value))
        self.assertEqual([b['start'] for b in parsed['operations'][0]['bindings']], [0, 0])
        s.put_source('episode', 'Someone left.')
        with self.assertRaises(HCLBoundaryError): s._validate_plan(json.dumps(proposed(actor())))
        with self.assertRaises(HCLBoundaryError): s._validate_plan(json.dumps(proposed(actor(source='other'))))

    def test_invalid_later_binding_prevents_every_native_dispatch_and_final(self):
        value = plan(operation('B01', 'What does Mira believe?', ['episode']),
                     operation('G02', 'Assess responsibility.', ['episode'], [actor(start=1)]))
        s = session('Mira: I believe the gate is open.'); port = Stub(value)
        with patch.object(s, '_execute', side_effect=AssertionError('NO_DISPATCH')):
            result = run(s, 'What is supported?', port)
        self.assertEqual(result['operations'], [])
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])

    def test_unique_quote_does_not_adopt_rule_or_bypass_duplicate_actor_rejection(self):
        s = session(); port = Stub(proposed(actor()))
        result = run(s, 'Was Mira responsible?', port)
        self.assertEqual(result['operations'][0]['result']['individuals'][0]['status'], 'NO_ADOPTED_INDIVIDUAL_RULE')
        s = session(); port = Stub(proposed(actor(), actor()))
        result = run(s, 'For this analysis, responsibility requires control.', port)
        self.assertEqual(result['hcl_execution']['native_results'], 0)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])

    def test_binding_bound_and_distinct_episode_requirements_stay_native_constraints(self):
        value = session('x' * 128)._validate_plan(json.dumps(proposed(actor(quote='x' * 128))))
        self.assertEqual(value['operations'][0]['bindings'][0]['start'], 0)
        # Admission's retained 128-character limit does not enlarge G02's actor bound.
        result = run(session('x' * 128), 'Was the actor responsible?', Stub(value))
        self.assertEqual(result['hcl_execution']['native_results'], 0)
        s = session('Mira opened the gate and Kai watched.')
        result = run(s, 'Assess responsibility.', Stub(proposed(actor(), actor(quote='Kai'))))
        self.assertEqual(result['hcl_execution']['native_results'], 0)
        self.assertEqual(result['operations'][0]['status'], 'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_independent_names_and_positions_resolve_without_interpreting_events(self):
        for text, name in [('At dawn, Lena arrived.', 'Lena'),
                           ('The visitor was Sol', 'Sol'),
                           ('\u6d77\u8fb9\uff1aYuki waited.', 'Yuki')]:
            with self.subTest(text=text):
                result = session(text)._validate_plan(json.dumps(proposed(actor(quote=name))))
                binding = result['operations'][0]['bindings'][0]
                self.assertEqual(text[binding['start']:binding['start'] + len(name)], name)
                self.assertEqual(binding['quote'], name)

    def test_complete_planning_capacity_remains_at_least_the_exact_prior_boundary(self):
        from hcl.cognition.deepseek_metered import bounded_request, MeteredPortError
        from scripts.development_plan_diagnostics_amendment import (
            BINDING_POLICY_BEFORE, BINDING_POLICY_AFTER, G02_INPUT_LIMITS_BEFORE,
        )
        for prefix in ('s', '\u6f22' * 127):
            def messages(size):
                s = UniversalHCL()
                for index in range(8):
                    s.put_source(prefix + str(index), 'An observer wrote a plain report.' + ('x' * size if index == 0 else ''))
                port = Stub(plan()); run(s, 'What is supported?', port)
                after = port.calls[0][1]; before = copy.deepcopy(after)
                before[0]['content'] = before[0]['content'].replace(BINDING_POLICY_AFTER, BINDING_POLICY_BEFORE)
                payload = json.loads(before[-1]['content'])
                next(row for row in payload['capability_inventory'] if row['capability_id'] == 'G02')['entry_contract']['input_limits'] = G02_INPUT_LIMITS_BEFORE
                before[-1]['content'] = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                return before, after
            low, high = 0, 36001
            while low + 1 < high:
                mid = (low + high) // 2
                try: bounded_request('planning', messages(mid)[0])
                except MeteredPortError as error:
                    self.assertEqual(str(error), 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'); high = mid
                else: low = mid
            before, after = messages(low)
            self.assertEqual(len(bounded_request('planning', before)[1]), 36000)
            self.assertEqual(len(bounded_request('planning', after)[1]), 35995)
            self.assertEqual(json.loads(before[-1]['content'])['sources'], json.loads(after[-1]['content'])['sources'])
            with self.assertRaisesRegex(MeteredPortError, 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'):
                bounded_request('planning', messages(low + 6)[1])

    def test_source_revision_or_withdrawal_still_prevents_delivery(self):
        for phase in ('planning', 'answer'):
            for withdraw in (False, True):
                with self.subTest(phase=phase, withdraw=withdraw):
                    s = session()
                    def change(current):
                        if current == phase:
                            if withdraw: s.workspace.core.withdraw(s.workspace._spans['episode'])
                            else: s.put_source('episode', 'Mira stayed outside.')
                    result = run(s, 'Was Mira responsible?', Stub(proposed(actor()), callback=change))
                    self.assertNotIn('answer', result)
                    self.assertEqual(result['failure_reason'], 'SOURCE_SUPPORT_CHANGED' if withdraw else 'SOURCE_CHANGED_DURING_ORCHESTRATION')


class FailureDiagnosticTests(unittest.TestCase):
    def assert_diagnostic(self, result, code, stage):
        self.assertEqual(safe_orchestration_failure_details(result), dict(code=code, stage=stage))

    def test_invalid_json_is_distinct_from_valid_empty_plan(self):
        class BadJSON(Stub):
            def complete(self, phase, messages):
                self.calls.append((phase, messages))
                return dict(text='not JSON PRIVATE_CANARY', actual_usd='0', usage={'offline_stub': True})
        port = BadJSON(); result = run(session(), 'What is supported?', port)
        self.assert_diagnostic(result, 'INVALID_PLANNING_JSON', 'PLANNING_RESPONSE_VALIDATION')
        self.assertNotIn('PRIVATE_CANARY', json.dumps(safe_orchestration_failure_details(result)))
        result = run(session(), 'What is supported?', Stub(plan()))
        self.assert_diagnostic(result, 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')

    def test_plan_shape_mode_and_anchor_rejections_keep_exact_safe_codes(self):
        values = [(dict(task='x', operations=[], limitations=[], extra=True), 'invalid bounded task plan'),
                  (plan(dict(capability='B01', question='What does Mira believe?', source_ids=['episode'], bindings=[])), 'EXPLICIT_READER_INPUT_MODE_REQUIRED'),
                  (proposed(actor(start=1)), 'invented or stale source anchor')]
        for value, code in values:
            with self.subTest(code=code):
                port = Stub(value); result = run(session(), 'What is supported?', port)
                self.assert_diagnostic(result, code, 'PLANNING_RESPONSE_VALIDATION')
                self.assertEqual([phase for phase, _ in port.calls], ['planning'])

    def test_entry_refusal_is_distinct_from_actual_insufficient_native_result(self):
        s = session('The observer left a plain note.'); port = Stub(plan(operation('B01', 'What does Mira believe?', ['episode'])))
        result = s.answer('What is supported?', planner_backend=port, answer_backend=port,
                          allowance=CallAllowance(2, 0, 'OFFLINE_DIAGNOSTICS'), required_checked_capabilities=('B01',))
        self.assert_diagnostic(result, 'LITERAL_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE', 'ENTRY_ADMISSION')
        self.assertEqual(result['operations'], [])
        s = session('Mira: I believe the gate is open.'); port = Stub(plan(operation('B01', 'What does Other believe?', ['episode'])))
        result = s.answer('What is supported?', planner_backend=port, answer_backend=port,
                          allowance=CallAllowance(2, 0, 'OFFLINE_DIAGNOSTICS'), required_checked_capabilities=('B01',))
        self.assert_diagnostic(result, 'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')
        self.assertEqual(len(result['operations']), 1)

    def test_final_schema_failure_has_its_own_stage_and_success_has_no_failure(self):
        class BlankFinal(Stub):
            def complete(self, phase, messages):
                value = super().complete(phase, messages)
                if phase == 'answer': value['text'] = json.dumps(dict(answer='', source_citations=[], uncertainty='', assumptions=''))
                return value
        result = run(session(), 'Was Mira responsible?', BlankFinal(proposed(actor())))
        self.assert_diagnostic(result, 'NONBLANK_FINAL_ANSWER_REQUIRED', 'FINAL_RESPONSE_VALIDATION')
        result = run(session(), 'Was Mira responsible?', Stub(proposed(actor())))
        self.assertIsNone(safe_orchestration_failure_details(result))
        self.assertNotIn('failure_stage', result)

    def test_arbitrary_exception_and_diagnostic_values_cannot_leak_content(self):
        class Broken(Stub):
            def complete(self, *args): raise RuntimeError('PRIVATE_EXCEPTION_CANARY')
        result = run(session(), 'What is supported?', Broken())
        safe = safe_orchestration_failure_details(result)
        self.assertNotIn('PRIVATE_EXCEPTION_CANARY', json.dumps(safe))
        self.assertEqual(safe['stage'], 'PLANNING_ADMISSION')
        for field in ('failure_reason', 'failure_stage'):
            for value in ('PRIVATE_SOURCE_CANARY', {}, [], None):
                forged = dict(status='ORCHESTRATION_UNAVAILABLE_OR_FAILED', failure_reason='ORCHESTRATION_FAILURE', failure_stage='ENTRY_ADMISSION')
                forged[field] = value
                self.assertNotIn('PRIVATE_', json.dumps(safe_orchestration_failure_details(forged)))
        self.assertIsNone(safe_orchestration_failure_details({'failure_reason': 'PRIVATE_CANARY'}))

    def test_string_subclasses_cannot_spoof_enum_membership_or_trigger_hash_errors(self):
        def spoof(target):
            class ForgedString(str):
                def __hash__(self): return hash(target)
                def __eq__(self, other): return True
            return ForgedString('PRIVATE_SUBCLASS_CANARY')
        class UnhashableString(str):
            __hash__ = None
        for code in (spoof('ORCHESTRATION_FAILURE'), UnhashableString('PRIVATE_SUBCLASS_CANARY')):
            for stage in (spoof('ENTRY_ADMISSION'), UnhashableString('PRIVATE_SUBCLASS_CANARY')):
                safe = safe_orchestration_failure_details(dict(status='ORCHESTRATION_UNAVAILABLE_OR_FAILED',
                                                               failure_reason=code, failure_stage=stage))
                self.assertEqual(safe, dict(code='ORCHESTRATION_FAILURE', stage='UNKNOWN'))
                self.assertEqual(HCLBoundaryError(code).code, 'ORCHESTRATION_FAILURE')
                self.assertNotIn('PRIVATE_', json.dumps(safe))
        self.assertEqual(HCLBoundaryError('INVALID_PLANNING_JSON').code, 'INVALID_PLANNING_JSON')


if __name__ == '__main__':
    unittest.main()
