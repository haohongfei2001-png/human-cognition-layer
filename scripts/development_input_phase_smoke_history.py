"""Replay the closed input-phase failure without migrating its runtime or evidence."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from scripts.development_executable_entry_amendment import BASELINE, validate_preserved_history

CHILD = r'''
import json, socket, unittest, sys
from pathlib import Path
def deny_network(*args, **kwargs):
    raise RuntimeError('HISTORICAL_REPLAY_NETWORK_FORBIDDEN')
socket.create_connection = socket.getaddrinfo = deny_network
socket.socket.connect = socket.socket.connect_ex = socket.socket.sendto = deny_network
from scripts.development_input_phase_contract_amendment import validate_current
validate_current()
folder=Path('.github/frozen/hcl-input-phase-smoke-20261007')
sys.path.insert(0,str(folder/'executor'))
import hcl_input_phase_smoke_candidate as r
import hcl_input_phase_smoke_public as public
import hcl_input_phase_smoke_native_public as native
package=r.FrozenPackage(json.loads((folder/'package.json').read_text()),
    json.loads((folder/'cases.json').read_text()),Path('.').resolve())
package.verify()
suite=unittest.defaultTestLoader.discover(str(folder/'executor/tests'))
if suite.countTestCases()!=123:raise SystemExit('EXACT_HISTORICAL_EXECUTOR_TEST_COUNT_REQUIRED')
result=unittest.TextTestRunner(verbosity=1).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
source_suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_v1_explicit_input_phase')
if source_suite.countTestCases()!=18:raise SystemExit('EXACT_HISTORICAL_INPUT_PHASE_TEST_COUNT_REQUIRED')
source_result=unittest.TextTestRunner(verbosity=1).run(source_suite)
if not source_result.wasSuccessful():raise SystemExit(1)
grant=json.loads(Path('.github/HCL_INPUT_PHASE_SMOKE_20261007_1_GRANT.json').read_text())
if grant['status']!='CLOSED_NO_TRANSFER_NO_RETRY' or grant['remaining_authorized_calls']!=0 or grant['remaining_authorized_cny']!='0':
    raise SystemExit('HISTORICAL_GRANT_MUST_REMAIN_CLOSED_ZERO')
evidence=json.loads(Path('reports/HCL_INPUT_PHASE_SMOKE_20261007_1_PUBLIC_EVIDENCE.json').read_text())
review=json.loads(Path('reports/HCL_INPUT_PHASE_SMOKE_20261007_1_SOURCE_REVIEW.json').read_text())
native.validate_published_native_evidence(evidence['approved_native_evidence'],package,
    grant['public_native_evidence_permission'],public_capture=evidence)
public.validate_actual_entry_requirements(evidence,package)
try:public.validate_phase1_gate(package,evidence,review,native_permission=grant['public_native_evidence_permission'])
except ValueError as error:
    if str(error)!='PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED':raise
else:raise SystemExit('RECORDED_FAILURE_MUST_REMAIN_FAILURE')
if evidence['provider_calls']!=1 or evidence['arms'][0]['final_delivery_code']!='NOT_REACHED':
    raise SystemExit('ONE_HISTORICAL_PLANNING_CALL_NO_FINAL_REQUIRED')
if any(Path(f'.github/HCL_INPUT_PHASE_SMOKE_20261007_2_{suffix}.json').exists() for suffix in ('GRANT','TRIGGER')):
    raise SystemExit('SINGLE_SMOKE_MUST_HAVE_NO_STAGE_TWO')
print(json.dumps(dict(status='PASS_EXACT_CLOSED_INPUT_PHASE_SMOKE_HISTORY_PROVIDER_FREE',
    baseline_commit=BASELINE_COMMIT,executor_tests_run=result.testsRun,
    input_phase_tests_run=source_result.testsRun,provider_calls=0,provider_spend_cny=0,
    historical_outputs_rescored=False)))
'''


def replay():
    validate_preserved_history()
    root=Path(__file__).resolve().parents[1]
    env=dict(PATH=os.environ.get('PATH',''),PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',
        GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='gc.auto',GIT_CONFIG_VALUE_0='0',
        GIT_CONFIG_KEY_1='maintenance.auto',GIT_CONFIG_VALUE_1='false')
    with tempfile.TemporaryDirectory(prefix='hcl-input-phase-history-') as directory:
        snapshot=Path(directory)/'baseline'
        subprocess.run(['git','worktree','add','--detach','--quiet',str(snapshot),BASELINE],cwd=root,check=True)
        try:
            actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=snapshot,text=True).strip()
            if actual!=BASELINE:raise ValueError('exact historical baseline required')
            subprocess.run([sys.executable,'-c','BASELINE_COMMIT = '+repr(BASELINE)+'\n'+CHILD],cwd=snapshot,env=env,check=True)
        finally:
            subprocess.run(['git','worktree','remove','--force',str(snapshot)],cwd=root,check=True)
    validate_preserved_history()


if __name__=='__main__':replay()
