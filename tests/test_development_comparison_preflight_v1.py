"""Fair ordinary-arm orchestration, unrelated synthetic inputs, no provider."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import development_comparison_preflight_v1 as c


def case(identity='island', text='Iris: I believe the beacon is lit.'):
    return dict(case_id=identity, question='What does the complete record support and leave unresolved?',
        sources=[dict(source_id='record', version=1, text=text,
                      recorded_at='2026-10-08T00:00:00Z', record_time_basis='SYNTHETIC_FIXTURE')])


def operation(mode='literal', source_id='record'):
    return dict(capability='B01', question='What does Iris believe?', source_ids=[source_id], bindings=[], input_mode=mode)


def plan(operations=None):
    return json.dumps(dict(task='Interpret the supplied report.', operations=[operation()] if operations is None else operations,
                           limitations=['Statements do not certify private truth.']))


def final(value):
    return json.dumps(dict(answer='The report records an expressed position; independent verification is unavailable.',
        source_citations=[dict(source_id=s['source_id'], version=s['version'], quote=s['text'], start=0) for s in value['sources']],
        uncertainty='Private state and source sincerity are not established.', assumptions='No added evidence.'))


def responses(cases):
    return {f'{v["case_id"]}:{arm}:{phase}': plan() if phase == 'planning' else final(v)
            for v in cases for arm, phase in (('Base', 'answer'), ('HCL', 'planning'), ('HCL', 'answer'))}


def primed_final_port(value, result):
    original = result['arms'][1]['events'][0]
    port = c._SyntheticPort(value, 'HCL', {'planning': original['response_text'], 'answer': final(value)}, result['runtime_sha256'])
    messages = original['request']['messages']
    port.reservation_usd('planning', messages)
    port.complete('planning', messages)
    return port


class ComparisonPreflight(unittest.TestCase):
    def run_case(self, value=None, injected=None):
        values = [value or case()]
        return c.run_synthetic(values, injected or responses(values))

    def test_strong_base_is_one_high_call_without_any_hcl_native_gate(self):
        values = [case()]
        script = responses(values); script['island:HCL:planning'] = plan([])
        result = c.run_synthetic(values, script)
        base, hcl = result['arms']
        self.assertTrue(base['delivery_accepted'])
        self.assertEqual(base['native_integrity'], 'NOT_APPLICABLE')
        self.assertEqual(len(base['events']), 1)
        self.assertEqual(base['events'][0]['request']['reasoning_effort'], 'high')
        self.assertEqual(hcl['safe_failure']['code'], 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER')
        self.assertEqual(len(hcl['events']), 1)
        self.assertFalse(hcl['delivery_accepted'])
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(result['actual_spend_cny'], '0')

    def test_full_original_question_sources_and_explicit_phase_compute(self):
        value = case(text='Iris: I believe the beacon is lit.\r\nSecond observer: 未確認。')
        result = self.run_case(value)
        base, hcl = result['arms']
        self.assertTrue(base['delivery_accepted']); self.assertTrue(hcl['delivery_accepted'])
        self.assertEqual([e['request']['reasoning_effort'] for e in hcl['events']], ['high', 'low'])
        for row in result['arms']:
            for event in row['events']:
                request = event['request']; payload = json.loads(request['messages'][-1]['content'])
                self.assertEqual(payload['question'], value['question'])
                self.assertEqual(payload['sources'][0]['text'].encode(), value['sources'][0]['text'].encode())
                self.assertEqual(payload['sources'][0]['version'], 1)
                self.assertEqual(request['max_tokens'], 16384)
                self.assertEqual(request['thinking'], {'type': 'enabled'})
                self.assertEqual(event['request_sha256'], c.digest(request))
                self.assertEqual(event['request_bytes'], len(c.canonical(request)))
        contract = json.loads(hcl['events'][0]['request']['messages'][-1]['content'])['executable_entry_contract']
        self.assertEqual(contract['caller_requirement'], 'ORDINARY_EVIDENCE_LIMITS_ALLOWED')
        self.assertEqual(hcl['checked_results'], 1)
        self.assertFalse(result['efficacy_verified']); self.assertFalse(result['i02_certified'])

    def test_honest_unchecked_native_result_can_reach_ordinary_final(self):
        result = self.run_case(case(text='A visitor noted an unmarked crate beside the pier.'))
        hcl = result['arms'][1]
        self.assertTrue(hcl['delivery_accepted'])
        self.assertEqual(hcl['native_results'], 1)
        self.assertEqual(hcl['checked_results'], 0)
        self.assertEqual(len(hcl['events']), 2)
        self.assertEqual(hcl['semantic_review'], 'NOT_EVALUATED_SYNTHETIC_ONLY')

    def test_semantic_candidates_are_supplied_by_injected_planner_not_wrapper(self):
        value = case(text='During a briefing, Iris said, "I do not believe the beacon is lit."')
        script = responses([value]); op = operation('semantic')
        op['semantic_candidates'] = [dict(source_id='record', quote=value['sources'][0]['text'], kind='event',
             content={'canonical_statement': 'Iris: I do not believe the beacon is lit.'})]
        script['island:HCL:planning'] = plan([op])
        result = self.run_case(value, script)
        hcl = result['arms'][1]
        self.assertTrue(hcl['delivery_accepted']); self.assertEqual(hcl['checked_results'], 1)
        self.assertIn('DENY', json.dumps(hcl['native_capture']))
        self.assertEqual(hcl['events'][0]['response_text'], script['island:HCL:planning'])

    def test_insufficient_mode_no_native_never_falls_back_to_base(self):
        value = case(); script = responses([value]); script['island:HCL:planning'] = plan([operation('insufficient')])
        result = self.run_case(value, script)
        hcl = result['arms'][1]
        self.assertEqual(hcl['native_results'], 0)
        self.assertIsNone(hcl['final_text'])
        self.assertEqual(len(hcl['events']), 1)
        self.assertEqual(result['offline_transport_calls'], 2)

    def test_known_failure_retained_fixed_crossed_schedule_not_discarded(self):
        values = [case(), case('observatory')]
        script = responses(values); script['island:HCL:planning'] = '{'
        result = c.run_synthetic(values, script)
        self.assertEqual([(r['case_id'], r['arm']) for r in result['arms']],
                         [('island', 'Base'), ('island', 'HCL'), ('observatory', 'HCL'), ('observatory', 'Base')])
        self.assertEqual(result['arms'][1]['safe_failure'], {'code': 'INVALID_PLANNING_JSON', 'stage': 'PLANNING_RESPONSE_VALIDATION'})
        self.assertTrue(result['arms'][3]['delivery_accepted'])
        self.assertEqual(result['offline_transport_calls'], 5)
        self.assertEqual(result['maximum_potential_calls'], 6)
        self.assertEqual(result['illustrative_full_schedule_peak_cny'], '6.657984')

    def test_unknown_transport_stops_all_remaining_positions_without_retry(self):
        values = [case(), case('observatory')]; script = responses(values)
        script['island:HCL:planning'] = None
        result = c.run_synthetic(values, script)
        self.assertEqual(result['offline_transport_calls'], 2)
        self.assertEqual(result['arms'][1]['comparison_stop'], 'INTEGRITY_OR_UNKNOWN_STOP_NO_RETRY')
        self.assertEqual([r['status'] for r in result['arms'][2:]], ['NOT_ATTEMPTED', 'NOT_ATTEMPTED'])

    def test_bad_anchor_stops_before_hcl_final_even_with_another_valid_operation(self):
        value = case(); script = responses([value]); invalid = operation('semantic')
        invalid['semantic_candidates'] = [dict(source_id='record', quote='ABSENT ANCHOR', kind='event',
             content={'canonical_statement': 'Iris: I believe the beacon is lit.'})]
        script['island:HCL:planning'] = plan([operation(), invalid])
        hcl = self.run_case(value, script)['arms'][1]
        self.assertEqual(len(hcl['events']), 1)
        self.assertEqual(hcl['safe_failure'], {'code': 'invented or stale source anchor', 'stage': 'PLANNING_RESPONSE_VALIDATION'})
        self.assertEqual(hcl['native_results'], 0)
        self.assertIsNone(hcl['final_text'])

    def test_changed_native_result_rejected_before_answer_reservation(self):
        value = case(); result = self.run_case(value); hcl = result['arms'][1]
        messages = copy.deepcopy(hcl['runtime_receipt']['actual_final_messages'])
        payload = json.loads(messages[-1]['content'])
        payload['hcl_operations'][0]['result']['forged_fact'] = 'unsupported'
        messages[-1]['content'] = json.dumps(payload)
        port = primed_final_port(value, result)
        with self.assertRaisesRegex(ValueError, 'CAPTURED_NATIVE_RESULT'):
            port.reservation_usd('answer', messages)
        self.assertTrue(port.integrity_failure)
        self.assertEqual(len(port.events), 1)

    def test_prefinal_requires_complete_operations_and_exact_native_summary(self):
        value = case(); script = responses([value])
        script['island:HCL:planning'] = plan([operation(), operation()])
        result = self.run_case(value, script); hcl = result['arms'][1]
        self.assertTrue(hcl['delivery_accepted']); self.assertEqual(hcl['native_results'], 2)
        original = hcl['runtime_receipt']['actual_final_messages']
        mutations = [lambda p: p['hcl_operations'].pop(),
                     lambda p: p.update(hcl_operations=[]),
                     lambda p: p['hcl_execution'].update(native_results=999),
                     lambda p: p['hcl_execution'].update(dispatched_operations=999),
                     lambda p: p['hcl_execution'].update(selected_operations=1),
                     lambda p: p['hcl_execution'].update(status='FORGED'),
                     lambda p: p['hcl_execution'].update(execution_is_treatment_proof=0)]
        for mutate in mutations:
            messages = copy.deepcopy(original); payload = json.loads(messages[-1]['content']); mutate(payload)
            messages[-1]['content'] = json.dumps(payload)
            port = primed_final_port(value, result)
            with self.assertRaisesRegex(ValueError, 'PREFINAL_NATIVE'):
                port.reservation_usd('answer', messages)
            self.assertEqual(len(port.events), 1)

    def test_no_native_result_cannot_enter_final_through_direct_port(self):
        value = case(); op = operation('insufficient')
        session = c.UniversalHCL(); session.put_source('record', value['sources'][0]['text'])
        output = session._execute(op, value['question'])
        payload = dict(question=value['question'], sources=c._source_projection(value),
                       hcl_plan=json.loads(plan([op])), hcl_operations=[output],
                       hcl_execution=dict(status='NATIVE_RESULTS_RETURNED', selected_operations=1,
                            dispatched_operations=1, native_results=0,
                            selection_basis='LLM_BEST_EFFORT_NOT_SEMANTIC_CERTIFICATION', execution_is_treatment_proof=False))
        with self.assertRaisesRegex(ValueError, 'PREFINAL_NATIVE'):
            c._validate_payload(value, 'answer', [{'role': 'user', 'content': json.dumps(payload)}], '0' * 64)

    def test_alternate_valid_plan_and_native_cannot_replace_returned_planning(self):
        value = case(); result = self.run_case(value); hcl = result['arms'][1]
        prompt = copy.deepcopy(hcl['runtime_receipt']['actual_final_messages'])
        payload = json.loads(prompt[-1]['content']); alternate = operation()
        alternate['question'] = 'What does Iris believe about the beacon?'
        payload['hcl_plan']['operations'] = [alternate]
        payload['hcl_operations'] = [c.native._session(value)._execute(alternate, value['question'])]
        prompt[-1]['content'] = json.dumps(payload)
        # A separately valid replay is not the original returned plan.
        c._validate_payload(value, 'answer', prompt, result['runtime_sha256'])
        port = c._SyntheticPort(value, 'HCL', {'answer': final(value)}, result['runtime_sha256'])
        with self.assertRaisesRegex(ValueError, 'RETURNED_PLANNING_EVENT'):
            port.reservation_usd('answer', prompt)
        port = primed_final_port(value, result)
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_RETURNED_PLAN'):
            port.reservation_usd('answer', prompt)
        self.assertEqual(len(port.events), 1)

    def test_gold_extra_keys_versions_and_callback_objects_rejected_before_dispatch(self):
        values = [case()]
        for mutate in [lambda x: x[0].update(gold='secret'),
                       lambda x: x[0]['sources'][0].update(version=2),
                       lambda x: x[0]['sources'][0].update(version=True),
                       lambda x: x[0]['sources'][0].update(text=lambda: 'replacement')]:
            changed = copy.deepcopy(values); mutate(changed)
            with patch.object(c._SyntheticPort, 'complete') as complete, self.assertRaises(ValueError):
                c.run_synthetic(changed, responses(values))
            complete.assert_not_called()
        for mutation in [dict(responses(values), **{'extra:Base:answer': 'x'}),
                         {'island:Base:answer': lambda: None}]:
            with self.assertRaises(ValueError): c.run_synthetic(values, mutation)

    def test_invented_citation_rejected_equally_in_both_arms(self):
        values = [case()]; bad = json.loads(final(values[0])); bad['source_citations'][0]['version'] = 9
        script = responses(values)
        for arm in ('Base', 'HCL'): script[f'island:{arm}:answer'] = json.dumps(bad)
        result = c.run_synthetic(values, script)
        self.assertTrue(all(not r['delivery_accepted'] for r in result['arms']))

    def test_complete_request_boundary_and_no_truncation(self):
        for arm, phase in [('Base', 'answer'), ('HCL', 'planning'), ('HCL', 'answer')]:
            prompt = [{'role': 'user', 'content': ''}]
            initial = len(c.canonical(c.request(arm, phase, prompt)))
            prompt[0]['content'] = 'x' * (36000 - initial)
            self.assertEqual(len(c.canonical(c.request(arm, phase, prompt))), 36000)
            prompt[0]['content'] += 'x'
            with self.assertRaisesRegex((ValueError, c.meter.MeteredPortError), 'REQUEST_BOUND'):
                c.request(arm, phase, prompt)

    def test_full_source_capacity_failure_retains_arm_without_source_dropping(self):
        value = case(text='Iris: I believe the beacon is lit.\n' + 'x' * 12000)
        script = responses([value]); short = json.loads(final(value))
        short['source_citations'][0]['quote'] = 'Iris: I believe the beacon is lit.'
        script['island:Base:answer'] = json.dumps(short)
        result = self.run_case(value, script)
        self.assertTrue(result['arms'][0]['delivery_accepted'])
        self.assertEqual(result['arms'][1]['events'], [])
        self.assertEqual(result['arms'][1]['comparison_stop'], 'INTEGRITY_OR_UNKNOWN_STOP_NO_RETRY')
        self.assertEqual(result['original_cases'][0], value)

    def test_configuration_drift_refused_and_hcl_wire_matches_current_runtime(self):
        prompt = [{'role': 'user', 'content': '{}'}]
        for phase in ('planning', 'answer'):
            self.assertEqual(c.request('HCL', phase, prompt), c.meter.bounded_request(phase, prompt)[0])
        with patch.dict(c.meter.REASONING_EFFORT, answer='high'):
            with self.assertRaisesRegex(ValueError, 'CONFIGURATION_CHANGED'): c.request('Base', 'answer', prompt)

    def test_duplicate_phase_and_mismatched_reservation_are_rejected(self):
        value = case(); port = c._SyntheticPort(value, 'Base', {'answer': final(value)}, '0' * 64)
        prompt = c.ref.messages(value, 'Base'); port.reservation_usd('answer', prompt)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'): port.reservation_usd('answer', prompt)
        changed = copy.deepcopy(prompt); changed[0]['content'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'EXACT_RESERVED'): port.complete('answer', changed)
        self.assertEqual(port.events, [])

    def test_source_input_drift_rejected_before_fake_dispatch(self):
        value = case(); port = c._SyntheticPort(value, 'Base', {'answer': final(value)}, '0' * 64)
        prompt = c.ref.messages(value, 'Base'); data = json.loads(prompt[-1]['content'])
        data['sources'][0]['text'] += ' changed'; prompt[-1]['content'] = json.dumps(data)
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_INPUT'): port.reservation_usd('answer', prompt)
        self.assertEqual(port.events, [])

    def test_originals_persist_exact_responses_and_reject_file_replacement(self):
        result = self.run_case()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            sha = c.save_original(result, path)
            self.assertEqual(c.load_original(path, sha), result)
            with self.assertRaises(FileExistsError): c.save_original(result, path)
            changed = copy.deepcopy(result); changed['arms'][1]['native_capture']['native_outputs'] = []
            path.write_bytes(c.canonical(changed) + b'\n')
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_SYNTHETIC_BYTES_CHANGED'): c.load_original(path, sha)


if __name__ == '__main__':
    unittest.main()
