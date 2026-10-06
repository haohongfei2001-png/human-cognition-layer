"""Run unchanged predecessor contract tests at their exact provider-free commit."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.development_explicit_citation_amendment import BASELINE, validate_preserved_history

CHILD = r'''
import json, socket, unittest
def deny_network(*args, **kwargs):
    raise RuntimeError('HISTORICAL_REPLAY_NETWORK_FORBIDDEN')
socket.create_connection = socket.getaddrinfo = deny_network
socket.socket.connect = socket.socket.connect_ex = deny_network
from scripts.development_final_delivery_amendment import validate_current
validate_current()
suite = unittest.defaultTestLoader.loadTestsFromNames((
    'tests.test_v1_final_delivery_diagnostics', 'tests.test_v1_answer_citation_contract'))
result = unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print(json.dumps(dict(status='PASS_EXACT_PREDECESSOR_PROVIDER_FREE',
    baseline_commit=BASELINE_COMMIT, tests_run=result.testsRun,
    provider_calls=0, provider_spend_usd=0, historical_outputs_rescored=False)))
'''


def replay():
    validate_preserved_history()
    root = Path(__file__).resolve().parents[1]
    env = dict(PATH=os.environ.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    with tempfile.TemporaryDirectory(prefix='hcl-explicit-citation-history-') as directory:
        snapshot = Path(directory) / 'baseline'
        subprocess.run(['git', 'worktree', 'add', '--detach', '--quiet', str(snapshot), BASELINE],
                       cwd=root, check=True)
        try:
            actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=snapshot, text=True).strip()
            if actual != BASELINE:
                raise ValueError('exact historical baseline required')
            program = 'BASELINE_COMMIT = ' + repr(BASELINE) + '\n' + CHILD
            subprocess.run([sys.executable, '-c', program], cwd=snapshot, env=env, check=True)
        finally:
            # This fresh temporary worktree belongs solely to this replay.
            subprocess.run(['git', 'worktree', 'remove', '--force', str(snapshot)], cwd=root, check=True)
    validate_preserved_history()


if __name__ == '__main__':
    replay()
