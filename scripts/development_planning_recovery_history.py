"""Replay the consumed 16K recovery gate at its exact closed historical tree."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.development_semantic_bridge_contract_amendment import BASELINE, validate_preserved_history

CHILD = r'''
import json, socket, unittest, sys
from pathlib import Path
def deny_network(*args, **kwargs):
    raise RuntimeError('HISTORICAL_REPLAY_NETWORK_FORBIDDEN')
socket.create_connection = socket.getaddrinfo = deny_network
socket.socket.connect = socket.socket.connect_ex = socket.socket.sendto = deny_network
from scripts.development_planning_allowance_amendment import validate_current
validate_current()
folder = Path('.github/frozen/hcl-planning-recovery-20261007')
sys.path.insert(0, str(folder / 'executor'))
import hcl_recovery_candidate as r
import hcl_recovery_public as public
package = r.FrozenPackage(json.loads((folder / 'package.json').read_text()),
    json.loads((folder / 'cases.json').read_text()), Path('.').resolve())
package.verify()
suite = unittest.defaultTestLoader.discover(str(folder / 'executor/tests'))
if suite.countTestCases() != 106:
    raise SystemExit('EXACT_HISTORICAL_TEST_COUNT_REQUIRED')
result = unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
grant = json.loads(Path('.github/HCL_PLANNING_RECOVERY_20261007_1_GRANT.json').read_text())
if grant['status'] != 'CLOSED_NO_TRANSFER_NO_RETRY' or grant['remaining_authorized_calls'] != 0 or grant['remaining_authorized_cny'] != '0':
    raise SystemExit('HISTORICAL_GRANT_MUST_REMAIN_CLOSED_ZERO')
evidence = json.loads(Path('reports/HCL_PLANNING_RECOVERY_20261007_1_PUBLIC_EVIDENCE.json').read_text())
review = json.loads(Path('reports/HCL_PLANNING_RECOVERY_20261007_1_SOURCE_REVIEW.json').read_text())
try:
    public.validate_phase1_gate(package, evidence, review,
        native_permission=grant['public_native_evidence_permission'])
except ValueError as error:
    if str(error) != 'EXACT_INDEPENDENT_SOURCE_REVIEW_REQUIRED':
        raise
else:
    raise SystemExit('FAILED_HISTORICAL_SMOKE_MUST_REJECT_STAGE2')
print(json.dumps(dict(status='PASS_EXACT_CLOSED_PLANNING_RECOVERY_HISTORY_PROVIDER_FREE',
    baseline_commit=BASELINE_COMMIT, tests_run=result.testsRun,
    provider_calls=0, provider_spend_cny=0, historical_outputs_rescored=False)))
'''


def replay():
    validate_preserved_history()
    root = Path(__file__).resolve().parents[1]
    env = dict(PATH=os.environ.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1')
    with tempfile.TemporaryDirectory(prefix='hcl-planning-recovery-history-') as directory:
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
