"""Run consumed CNY gates at their unchanged, network-disabled historical tree."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.development_final_context_amendment import BASELINE, validate_preserved_history

CHILD = r'''
import json, socket, unittest
def deny_network(*args, **kwargs):
    raise RuntimeError('HISTORICAL_REPLAY_NETWORK_FORBIDDEN')
socket.create_connection = socket.getaddrinfo = deny_network
socket.socket.connect = socket.socket.connect_ex = deny_network
from scripts.development_explicit_citation_amendment import validate_current
validate_current()
suite = unittest.defaultTestLoader.loadTestsFromNames((
    'tests.test_two_stage', 'tests.test_two_stage_review', 'tests.test_two_stage_account'))
result = unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
from scripts import run_two_stage_once as runner
for stage in (1, 2):
    runner.configure(stage)
    if json.loads(runner.PACKAGE.read_text()) != runner.build_package():
        raise SystemExit('FROZEN_PACKAGE_DRIFT')
    grant = json.loads(runner.GRANT.read_text())
    if (grant['status'] != 'CLOSED_NO_TRANSFER_NO_RETRY'
            or grant['remaining_authorized_calls'] != 0
            or grant['remaining_authorized_cny'] != '0'):
        raise SystemExit('FROZEN_GRANT_NOT_CLOSED_ZERO')
print(json.dumps(dict(status='PASS_EXACT_CNY_HISTORY_PROVIDER_FREE',
    baseline_commit=BASELINE_COMMIT, tests_run=result.testsRun,
    provider_calls=0, provider_spend_cny=0, historical_outputs_rescored=False)))
'''


def replay():
    validate_preserved_history()
    root = Path(__file__).resolve().parents[1]
    env = dict(PATH=os.environ.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    with tempfile.TemporaryDirectory(prefix='hcl-final-context-history-') as directory:
        snapshot = Path(directory) / 'baseline'
        subprocess.run(['git', 'worktree', 'add', '--detach', '--quiet', str(snapshot), BASELINE],
                       cwd=root, check=True)
        try:
            actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=snapshot, text=True).strip()
            if actual != BASELINE:
                raise ValueError('exact historical baseline required')
            subprocess.run([sys.executable, '-c', 'BASELINE_COMMIT = ' + repr(BASELINE) + '\n' + CHILD],
                           cwd=snapshot, env=env, check=True)
        finally:
            subprocess.run(['git', 'worktree', 'remove', '--force', str(snapshot)], cwd=root, check=True)
    validate_preserved_history()


if __name__ == '__main__':
    replay()
