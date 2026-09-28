"""No provider access: exact frozen transport and failure/no-grant gates."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.frozen_cg05_replay import replay_frozen_cg05
from scripts.run_cg05_external_once import main, run_with_provider


class CG05RunnerTests(unittest.TestCase):
    def test_exact_twenty_requests_results_treatment_and_usage(self):
        package = replay_frozen_cg05()
        calls = []
        expected = [(c, a) for c in package['cases'] for a in package['arms']]
        def fake(messages):
            case, arm = expected[len(calls)]
            self.assertEqual(messages, case['messages'][arm])
            calls.append(messages)
            raw = json.dumps(case['gold'])
            return dict(model='deepseek-v4-pro', raw=raw, input_tokens=1, output_tokens=1,
                cost_usd=.00000528, provider_price_estimated_cost_usd=None,
                usage_raw={}, response_raw={'fake': True}, finish_reason='stop')
        receipt = run_with_provider(fake, package)
        self.assertEqual(receipt['calls'], 20)
        self.assertEqual(len(receipt['attempts']), 20)
        self.assertTrue(all(r['score']['all_fields_correct'] for r in receipt['rows']))
        self.assertEqual(receipt['rows'][3]['preflight'], package['cases'][0]['preflight'])

    def test_failure_keeps_raw_attempt_and_never_retries(self):
        calls, snapshots = [], []
        def failed(messages):
            calls.append(messages)
            raise ValueError('fake transport failure')
        def checkpoint(ledger, rows=None):
            snapshots.append(json.loads(json.dumps(ledger.attempts)))
        with self.assertRaises(ValueError):
            run_with_provider(failed, replay_frozen_cg05(), checkpoint)
        self.assertEqual(len(calls), 1)
        self.assertEqual(snapshots[-1][0]['failure_type'], 'ValueError')
        self.assertTrue(snapshots[-1][0]['request_raw'])

    def test_other_grant_or_live_runtime_never_constructs_provider(self):
        for env, sha in (({'HCL_CG04_AUTHORIZED_CAP_USD': '0.30'}, 'unused'),
                ({'HCL_CG05_AUTHORIZED_CAP_USD': '0.30',
                  'HCL_CG05_AUTHORIZED_BASE_SHA': 'c7593bcf5ef8199eb8f1adb3b6f96fb2a0367b94',
                  'GITHUB_RUN_ATTEMPT': '1', 'DEEPSEEK_API_KEY': 'fake'}, 'latest-runtime')):
            with self.subTest(env=env), tempfile.TemporaryDirectory() as folder, \
                    patch.dict(os.environ, env, clear=True), \
                    patch('scripts.run_cg05_external_once.load_frozen_package', return_value=replay_frozen_cg05()), \
                    patch('scripts.run_cg05_external_once.subprocess.check_output', return_value=sha), \
                    patch('scripts.run_cg05_external_once.CG03Provider') as provider, \
                    patch('sys.argv', ['run', '--out', folder]):
                with self.assertRaises(SystemExit):
                    main()
                provider.assert_not_called()
                self.assertFalse(list(Path(folder).iterdir()))
