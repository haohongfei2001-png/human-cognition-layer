"""Frozen input fairness, treatment coverage, scorer and dormant runner gates."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.cg04_external_package import build_package, PACKAGE, score_answer
from scripts.run_cg04_external_once import load_frozen_package as active_load, main, run_with_provider
from scripts.frozen_cg04_replay import replay_frozen_cg04 as load_frozen_package


class CG04PackageTests(unittest.TestCase):
    def test_exact_freeze_fair_labels_real_treatment_and_coverage(self):
        package = load_frozen_package()
        self.assertEqual(package, json.loads(PACKAGE.read_text()))
        self.assertFalse(package['execution_authorized'])
        certificate = json.loads(Path('reports/HCL_CG04_PROVIDER_FREE_CERTIFICATION.json').read_text())
        self.assertEqual(package['runtime_sha256'], certificate['exact_main']['runtime_sha256'])
        self.assertLessEqual(package['estimated_worst_case_usd_at_repository_frozen_rate'], .30)
        coverage = []
        for c in package['cases']:
            self.assertTrue(all(c['preflight'].values()))
            coverage.extend(s['state'] for s in c['checked_state']['statements'])
            h = json.loads(c['messages']['H'][1]['content'])
            hn = json.loads(c['messages']['H-new'][1]['content'])
            h['cognition_context']['preferences']['checked'] = {}
            self.assertEqual(h, hn)
            self.assertEqual(c['messages']['H'][0], c['messages']['H-new'][0])
            for arm in package['arms']:
                text = json.dumps(c['messages'][arm])
                for label in ('APPLICABLE_SOURCE_CLAIM', 'ATTRIBUTED_ONLY', 'OTHER_SCOPE',
                    'CONDITION_UNRESOLVED', 'SUPERSEDED_LOCAL', 'CONTESTED', 'NOT_INFERRED'):
                    self.assertIn(label, text)
                self.assertEqual(score_answer(c, json.dumps(c['gold']))['exact_fields'], 7)
        self.assertIn('SUPERSEDED_LOCAL', coverage)
        self.assertIn('ATTRIBUTED_ONLY', coverage)
        self.assertIn('CONDITION_UNRESOLVED', coverage)
        self.assertTrue(any(c['checked_state']['conflict_state'] == 'UNRESOLVED_CONFLICT' for c in package['cases']))

    def test_current_mechanism_preserves_every_frozen_input(self):
        current, frozen = build_package(), load_frozen_package()
        self.assertEqual(current['cases'], frozen['cases'])
        self.assertEqual(current['frozen_engineering_sha256'], frozen['frozen_engineering_sha256'])

    def test_frozen_scorer_nested_type_and_extra_claim(self):
        c = load_frozen_package()['cases'][0]
        bad = dict(c['gold'], choice_implies_enduring_value=0)
        self.assertFalse(score_answer(c, json.dumps(bad))['all_fields_correct'])
        bad = dict(c['gold'], moral_truth='safety wins')
        self.assertEqual(score_answer(c, json.dumps(bad))['exact_fields'], 0)
        bad = dict(c['gold'], preference_states={'pref-1': 'APPLICABLE_SOURCE_CLAIM'})
        self.assertEqual(score_answer(c, json.dumps(bad))['exact_fields'], 6)

    def test_package_drift_stops_before_provider_construction(self):
        with patch('scripts.run_cg04_external_once.build_package', return_value={}):
            with self.assertRaises(ValueError):
                active_load()

    def test_absent_new_grant_and_old_budget_cannot_construct_provider(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,
                {'HCL_CG03_AUTHORIZED_CAP_USD': '0.30'}, clear=True), \
                patch('scripts.run_cg04_external_once.build_package', return_value=load_frozen_package()), \
                patch('sys.argv', ['run', '--out', folder]), \
                patch('scripts.run_cg04_external_once.CG03Provider') as provider:
            with self.assertRaises(SystemExit):
                main()
            provider.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_twenty_frozen_calls_receipts_and_scores_with_fake_provider(self):
        package = load_frozen_package()
        answers = [json.dumps(c['gold']) for c in package['cases'] for _ in package['arms']]
        requests = []
        def fake(messages):
            raw = answers[len(requests)]
            requests.append(messages)
            return dict(model='deepseek-v4-pro', raw=raw, input_tokens=1,
                output_tokens=1, cost_usd=.00000528,
                provider_price_estimated_cost_usd=.00000264,
                usage_raw={'prompt_tokens': 1, 'completion_tokens': 1},
                response_raw={'fake_provider_only': raw}, finish_reason='stop')
        result = run_with_provider(fake, package)
        self.assertEqual(result['calls'], 20)
        self.assertEqual(len(requests), 20)
        self.assertTrue(all(r['score']['all_fields_correct'] for r in result['rows']))
        self.assertEqual(requests, [c['messages'][a] for c in package['cases'] for a in package['arms']])
        self.assertTrue(all(a['request_raw']['thinking'] == {'type': 'disabled'} for a in result['attempts']))

    def test_failure_keeps_completed_rows_raw_attempt_and_never_retries(self):
        package = load_frozen_package()
        calls, saved = [], {}
        def fake(messages):
            calls.append(messages)
            if len(calls) == 2:
                raise ValueError('fake provider failure')
            return dict(model='deepseek-v4-pro', raw=json.dumps(package['cases'][0]['gold']),
                input_tokens=1, output_tokens=1, cost_usd=.00000528,
                provider_price_estimated_cost_usd=None, usage_raw={}, response_raw={}, finish_reason='stop')
        def checkpoint(ledger, rows=None):
            saved['attempts'] = ledger.attempts
            if rows is not None:
                saved['rows'] = rows.copy()
        with self.assertRaises(ValueError):
            run_with_provider(fake, package, checkpoint)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(saved['rows']), 1)
        self.assertEqual(saved['attempts'][1]['failure_type'], 'ValueError')
        self.assertTrue(saved['attempts'][1]['request_raw'])


if __name__ == '__main__':
    unittest.main()
