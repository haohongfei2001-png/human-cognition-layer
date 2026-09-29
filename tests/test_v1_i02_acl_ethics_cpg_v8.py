"""One-use strong C/P/G calibration: budget, raw receipts and no H leakage."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_i02_acl_ethics_cpg_v8_once import (
    build_package, execute, load_package, preflight)


SOURCE = json.loads(Path(
    'reports/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.json').read_text())
QUOTE = 'publicly-accessible EPub versions of all the books of the commercial Amazonia bookshop web storefront'
ANSWER = dict(answer='The abstract reports book use but gives no permission evidence.',
    source_citations=[dict(source_id=SOURCE['source_id'], quote=QUOTE)],
    uncertainty='Worker conditions and rights are unstated.', assumptions='')
MAP = dict(source_index=[dict(id='e1', source_id=SOURCE['source_id'],
                              quote=QUOTE)],
           relations=[], answer_plan=[], open_questions=[])


def provider_responses(g_map=MAP, p_answer=ANSWER):
    contents = [ANSWER, p_answer, g_map, ANSWER]
    for value in contents:
        yield dict(model='deepseek-v4-pro', created=1790000000,
            choices=[dict(finish_reason='stop',
                message=dict(role='assistant', content=json.dumps(value),
                             reasoning_content='bounded reasoning receipt'))],
            usage=dict(prompt_tokens=800, completion_tokens=500,
                prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=800,
                completion_tokens_details=dict(reasoning_tokens=200)))


class AclEthicsCpgV8Tests(unittest.TestCase):
    def setUp(self):
        # Rehearse the consumed package at its recorded v2 runtime identity.
        # Current-runtime execution remains refused by the unmodified runner.
        old = json.loads(Path('reports/HCL_I02_ACL_ETHICS_CPG_V8_PACKAGE.json').read_text())[
            'hcl_runtime_sha256']
        for target in ('scripts.run_i02_acl_ethics_cpg_v8_once.runtime_digest',
                       'scripts.i02_acl_ethics_development_preflight.runtime_digest'):
            active = patch(target, return_value=old)
            active.start()
            self.addCleanup(active.stop)

    def test_frozen_package_and_all_phase_provider_free_preflight(self):
        package = load_package()
        self.assertEqual(package, build_package())
        gate, arms = preflight(package)
        self.assertLess(gate['all_phase_peak_reservation_usd'],
                        package['budget_cap_usd'])
        self.assertLessEqual(package['maximum_provider_calls'], 4)
        self.assertEqual(package['h_arm_calls'], 0)
        self.assertEqual(package['hnew_arm_calls'], 0)
        self.assertEqual(arms['qualification'],
            'C_P_G_V8_PROVIDER_FREE_CANDIDATE_UNQUALIFIED')
        self.assertTrue(all(spec['thinking']['type'] == 'enabled'
            for spec in package['call_specs'].values()))

    def test_one_use_raw_requests_responses_and_shape_record(self):
        package = load_package()
        responses = iter(provider_responses())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            receipt = execute(package, lambda _: next(responses), path)
            self.assertEqual(receipt['provider_calls'], 4)
            self.assertEqual(receipt['retries'], 0)
            self.assertEqual(receipt['status'],
                'COMPLETED_REQUIRES_SOURCE_FIRST_SEMANTIC_AUDIT')
            self.assertEqual(set(receipt['shape_results'].values()),
                             {'SHAPE_AND_SOURCE_CITATIONS_VALID'})
            self.assertLess(receipt['conservative_reserved_usd'],
                            package['budget_cap_usd'])
            self.assertEqual(receipt['authorization_remaining_usd'], 0)
            self.assertEqual([a['phase'] for a in receipt['attempts']],
                             ['C', 'P', 'G_map', 'G_final'])
            for attempt in receipt['attempts']:
                self.assertEqual(attempt['request_raw']['thinking']['type'],
                                 'enabled')
                self.assertNotIn('provider', attempt['request_raw'])
                self.assertEqual(attempt['response_raw']['model'],
                                 'deepseek-v4-pro')
                self.assertIn('usage', attempt)
            with self.assertRaisesRegex(ValueError, 'existing receipt'):
                execute(package, lambda _: None, path)

    def test_invalid_p_citation_does_not_hide_g_and_invalid_map_stops_g_final(self):
        bad_p = dict(ANSWER, source_citations=[dict(source_id=SOURCE['source_id'],
            quotes=[QUOTE])])
        with tempfile.TemporaryDirectory() as directory:
            responses = iter(provider_responses(p_answer=bad_p))
            receipt = execute(load_package(), lambda _: next(responses),
                              Path(directory) / 'p-invalid.json')
            self.assertEqual(receipt['provider_calls'], 4)
            self.assertEqual(receipt['shape_results']['P'], 'INVALID_VALUEERROR')
            bad_map = dict(MAP, source_index=[dict(id='e1',
                source_id=SOURCE['source_id'], quote='invented private motive')])
            responses = iter(provider_responses(g_map=bad_map))
            receipt = execute(load_package(), lambda _: next(responses),
                              Path(directory) / 'map-invalid.json')
            self.assertEqual(receipt['provider_calls'], 3)
            self.assertEqual(receipt['status'], 'G_MAP_INVALID_G_FINAL_NOT_CALLED')
            self.assertEqual(receipt['authorization_remaining_usd'], 0)


if __name__ == '__main__':
    unittest.main()
