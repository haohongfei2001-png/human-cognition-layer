"""Replay consumed gates only in their exact, isolated, provider-free baseline."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.development_final_delivery_amendment import BASELINE, validate_preserved_history

TESTS = ('tests.test_current_flow_diagnostic', 'tests.test_current_flow_public_evidence',
         'tests.test_four_comparison', 'tests.test_v1_deepseek_metered')

# Only fixed offline test modules and package reconstruction are invoked. Neither
# historical executor CLI is launched. No provider credential is passed through.
CHILD = r'''
import json, socket, unittest
def deny_network(*args, **kwargs):
    raise RuntimeError('HISTORICAL_REPLAY_NETWORK_FORBIDDEN')
socket.create_connection = socket.getaddrinfo = deny_network
socket.socket.connect = socket.socket.connect_ex = deny_network
suite = unittest.defaultTestLoader.loadTestsFromNames(TEST_MODULES)
result = unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
from scripts import run_current_flow_diagnostic as current, run_four_comparison as four
for runner in (current, four):
    if json.loads(runner.PACKAGE.read_text()) != runner.build_package():
        raise SystemExit('FROZEN_PACKAGE_DRIFT')
    grant = json.loads(runner.GRANT.read_text())
    if (grant['status'] != 'CLOSED_NO_TRANSFER_NO_RETRY' or
            grant['remaining_authorized_calls'] != 0 or grant['remaining_authorized_usd'] != '0'):
        raise SystemExit('FROZEN_GRANT_NOT_CLOSED_ZERO')
print(json.dumps(dict(status='PASS_EXACT_BASELINE_PROVIDER_FREE',
    baseline_commit=BASELINE_COMMIT, tests_run=result.testsRun,
    provider_calls=0, provider_spend_usd=0, historical_outputs_rescored=False)))
'''


def replay():
    validate_preserved_history()
    root = Path(__file__).resolve().parents[1]
    env = dict(PATH=os.environ.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    with tempfile.TemporaryDirectory(prefix='hcl-final-delivery-history-') as directory:
        snapshot = Path(directory) / 'baseline'
        subprocess.run(['git', 'worktree', 'add', '--detach', '--quiet', str(snapshot), BASELINE],
                       cwd=root, check=True)
        try:
            actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=snapshot, text=True).strip()
            if actual != BASELINE:
                raise ValueError('exact historical baseline required')
            program = 'TEST_MODULES = ' + repr(TESTS) + '\nBASELINE_COMMIT = ' + repr(BASELINE) + '\n' + CHILD
            subprocess.run([sys.executable, '-c', program], cwd=snapshot, env=env, check=True)
        finally:
            # This fresh temporary worktree belongs solely to this replay.
            subprocess.run(['git', 'worktree', 'remove', '--force', str(snapshot)], cwd=root, check=True)
    validate_preserved_history()


if __name__ == '__main__':
    replay()
