"""Source/protocol preparation checks; no real or stub model execution runner."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import source_inference_synthetic_diagnostic as m
from scripts.development_confirmation_firewall import require_final_development_disjoint


def keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from keys(child)


class SyntheticSourceFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = m.load_cases()
        cls.rubric = m.load_rubric(cls.corpus)
        cls.package = m.build_package()

    def test_twelve_original_complete_sources_not_selected_by_treatment(self):
        self.assertEqual(len(self.corpus['cases']), 12)
        self.assertEqual(len(self.package['inputs']), 12)
        self.assertEqual([r['case_id'] for r in self.corpus['cases']],
                         [r['case_id'] for r in self.package['inputs']])
        self.assertIn('NO_OUTPUT_OR_TREATMENT_FILTER', self.package['source_selection'])
        self.assertEqual(len({r['source_sha256'] for r in self.corpus['cases']}), 12)
        self.assertEqual(self.corpus['classification'], 'AGENT_AUTHORED_SYNTHETIC_DEVELOPMENT_DIAGNOSTIC')

    def test_case_hashes_original_questions_and_authorship_limits(self):
        for row in self.corpus['cases']:
            self.assertEqual(row['source_sha256'], hashlib.sha256(row['source'].encode()).hexdigest())
            self.assertEqual(row['question_sha256'], hashlib.sha256(row['question'].encode()).hexdigest())
            self.assertIn('fictional adults', row['original_author_provenance']['character_status'])
        self.assertIn('NOT_NATIVE_DRC_OR_GENERAL_UTILITY_OR_FINAL_EVIDENCE', self.package['evidence'])

    def test_complete_identical_source_and_question_reach_all_three_arms(self):
        for row, prepared in zip(self.corpus['cases'], self.package['inputs']):
            expected = dict(query=row['question'], sources=[dict(source_id='synthetic-source', version=1, text=row['source'])])
            for arm in m.ARMS:
                frames = [json.loads(msg['content']) for msg in prepared['arms'][arm]['request']['messages'] if msg['role'] == 'user']
                self.assertTrue(any(f.get('query') == expected['query'] and f.get('sources') == expected['sources'] for f in frames))

    def test_rubric_ids_and_expected_criteria_never_enter_answer_requests(self):
        forbidden = {'case_id', 'rubric', 'gold', 'required_propositions', 'forbidden_promotions',
                     'acceptable_hypotheses', 'anchor_quotes', 'original_author_provenance'}
        for row in self.package['inputs']:
            for arm in m.ARMS:
                for message in row['arms'][arm]['request']['messages']:
                    if message['role'] == 'user':
                        self.assertFalse(forbidden & set(keys(json.loads(message['content']))))
                    self.assertNotIn(row['case_id'], message['content'])

    def test_same_model_thinking_output_and_common_contract(self):
        for row in self.package['inputs']:
            for arm in m.ARMS:
                req = row['arms'][arm]['request']
                self.assertEqual({k: v for k, v in req.items() if k != 'messages'},
                    dict(model='deepseek-v4-pro', thinking={'type': 'enabled'}, reasoning_effort='high',
                         max_tokens=8192, response_format={'type': 'json_object'}))
                self.assertEqual(sum(x['content'] == m.RESPONSE_POLICY for x in req['messages']), 1)

    def test_v24_v25_checked_state_and_actual_treatment_preserved(self):
        for row in self.package['inputs']:
            old = row['arms']['H_v24']['request']['messages']
            new = row['arms']['H_v25']['request']['messages']
            self.assertEqual(old[1:], new[1:])
            self.assertTrue(new[0]['content'].startswith(old[0]['content'] + ' '))
            self.assertEqual(row['actual_H_v24_checked_treatment'], row['actual_H_v25_checked_treatment'])

    def test_fixed_balanced_call_order_and_zero_extra_calls(self):
        positions = {a: [0, 0, 0] for a in m.ARMS}
        for row in self.package['inputs']:
            self.assertEqual(set(row['execution_order']), set(m.ARMS))
            for index, arm in enumerate(row['execution_order']):
                positions[arm][index] += 1
        self.assertEqual(positions, {a: [4, 4, 4] for a in m.ARMS})
        self.assertEqual(self.package['proposed_maximum_answer_calls'], 36)
        for field in ('proposed_extraction_calls', 'proposed_paid_judge_calls', 'proposed_retries'):
            self.assertEqual(self.package[field], 0)

    def test_proposed_cap_covers_all_answers_at_peak_with_margin(self):
        estimates = [a['estimate'] for r in self.package['inputs'] for a in r['arms'].values()]
        self.assertEqual(len(estimates), 36)
        self.assertTrue(all(x['serialized_request_bytes'] <= 12000 for x in estimates))
        self.assertTrue(all(x['output_tokens_with_margin'] == 8224 for x in estimates))
        self.assertAlmostEqual(sum(x['proposed_peak_reservation_usd'] for x in estimates),
                               self.package['frozen_request_peak_reservation_usd'])
        self.assertAlmostEqual(self.package['maximum_request_envelope_peak_usd'], 2.4102144)
        self.assertLessEqual(self.package['frozen_request_peak_reservation_usd'], 2.4102144)
        self.assertEqual(self.package['proposed_hard_cap_usd'], 2.50)
        self.assertIsNone(self.package['charged_actual_usd'])

    def test_oversized_whole_request_refuses_instead_of_truncation(self):
        req = m.request([dict(role='user', content='文' * 12000)])
        with self.assertRaisesRegex(ValueError, 'no truncation or case substitution'):
            m.estimate(req, self.package['prices'])
        self.assertEqual(req['messages'][0]['content'], '文' * 12000)

    def test_official_price_receipt_and_snapshot_uncertainty(self):
        price = self.package['prices']
        self.assertEqual(price['http_status'], 200)
        self.assertEqual(price['url'], 'https://api-docs.deepseek.com/quick_start/pricing/')
        self.assertEqual(len(price['html_sha256']), 64)
        self.assertIn('physical snapshot not verified', price['model_snapshot'])
        self.assertEqual(price['peak_rates_usd_per_million'], dict(input_cache_miss=1.32, output=3.96))

    def test_rubric_anchors_are_original_not_generated_answer_keys(self):
        for row in self.corpus['cases']:
            rubric = self.rubric['cases'][row['case_id']]
            self.assertTrue(rubric['required_propositions'])
            self.assertTrue(rubric['forbidden_promotions'])
            for requirement in rubric['required_propositions']:
                self.assertTrue(all(quote in row['source'] for quote in requirement['anchor_quotes']))
        self.assertEqual(self.rubric['model_answer_outputs_seen'], 0)
        self.assertEqual(self.rubric['semantic_verdict'], 'REQUIRES_BLINDED_SOURCE_FIRST_REVIEW')

    def test_no_execution_authority_or_transport_exists(self):
        self.assertEqual(self.package['authorization'], dict(status='NOT_GRANTED', maximum_calls=0,
            remaining_usd=0, inherited_grants_usable=False, transport_implemented=False))
        self.assertEqual(self.package['provider_calls'], 0)
        self.assertEqual(self.package['provider_spend_usd'], 0)
        for name in ('execute', 'provider', 'require_grant', 'OpenAI'):
            self.assertFalse(hasattr(m, name))
        self.assertFalse(Path('.github/HCL_SID001_GRANT.json').exists())

    def test_execute_cli_is_rejected_and_old_grants_do_not_enable_it(self):
        env = dict(os.environ, DEEPSEEK_API_KEY='fake-nonsecret-test', HCL_DRC008_AUTHORIZED='ONE_DEVELOPMENT_REALITY_CHECK_ONLY')
        result = subprocess.run([sys.executable, '-m', 'scripts.source_inference_synthetic_diagnostic', '--execute'],
            capture_output=True, text=True, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unrecognized arguments: --execute', result.stderr)

    def test_author_system_and_renamed_fixture_are_ineligible_for_final(self):
        for candidate in (dict(dataset_id=m.DATASET), dict(writing_system_id=m.WRITING_SYSTEM),
                          dict(dataset_id='renamed', source_text=self.corpus['cases'][0]['source'])):
            with self.assertRaises(ValueError):
                require_final_development_disjoint(candidate)

    def test_prior_history_receipt_is_exact_baseline_not_final_novelty(self):
        history = json.loads(m.HISTORY.read_text())
        self.assertEqual(history['checkout_head'], m.BASELINE)
        self.assertEqual(history['corpus_sha256'], m.digest(self.corpus))
        self.assertFalse(history['matches'])
        self.assertFalse(history['skipped_large_paths'])
        self.assertIn('no deleted-ref', history['limits'])
        self.assertGreater(history['sealed_blob_ids_not_opened'], 0)

    def test_frozen_artifact_matches_actual_inputs_runtime_and_all_files(self):
        self.assertEqual(m.verify_package(), self.package)
        for row in self.package['inputs']:
            for arm in m.ARMS:
                a = row['arms'][arm]
                self.assertEqual(a['request_sha256'], m.digest(a['request']))

    def test_mutated_frozen_request_is_not_silently_rebuilt_as_approved(self):
        value = copy.deepcopy(self.package)
        value['inputs'][0]['arms']['Base']['request']['messages'][0]['content'] += ' changed'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'package.json'
            path.write_text(json.dumps(value))
            with patch.object(m, 'PACKAGE', path):
                with self.assertRaisesRegex(ValueError, 'freeze drift'):
                    m.verify_package()

    def test_bad_source_hash_and_bad_rubric_anchor_fail_closed(self):
        corpus = copy.deepcopy(self.corpus)
        corpus['cases'][0]['source'] += ' changed'
        rubric = copy.deepcopy(self.rubric)
        first = self.corpus['cases'][0]['case_id']
        rubric['cases'][first]['required_propositions'][0]['anchor_quotes'] = ['not an original quote']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'modified.json'
            path.write_text(json.dumps(corpus))
            with patch.object(m, 'CASES', path):
                with self.assertRaises(ValueError):
                    m.load_cases()
            path.write_text(json.dumps(rubric))
            with patch.object(m, 'RUBRIC', path):
                with self.assertRaises(ValueError):
                    m.load_rubric(self.corpus)


if __name__ == '__main__':
    unittest.main()
