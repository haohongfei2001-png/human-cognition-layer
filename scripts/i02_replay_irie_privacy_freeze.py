"""Provider-free replay of the consumed v5 run, never current-runtime substitution."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

BASE='844a79535dafb7947016142e045f9a61df8d761f'
PACKAGE='reports/HCL_I02_IRIE_PRIVACY_CPG_PACKAGE.json'

def replay(repository='.'):
    def git(*args):
        return subprocess.check_output(['git','-C',str(repository),*args],timeout=30)
    raw=git('show',BASE+':'+PACKAGE)
    if Path(PACKAGE).read_bytes()!=raw:
        raise ValueError('consumed package changed')
    package=json.loads(raw)
    files=set(package['execution_files'])|{PACKAGE,
        'tests/test_i02_exposure_history.py','tests/test_v1_reader_argument_question.py',
        'tests/test_i02_shea_development_case.py',
        'reports/HCL_I02_SHEA_CONCEPT_DEVELOPMENT_ENTRY.json',
        'reports/HCL_I02_ACL_ETHICS_CPG_V8_PACKAGE.json'}
    # Code imports are replayed at the same commit. Never archive sealed paths.
    code=git('ls-tree','-r','--name-only',BASE,'scripts').decode().splitlines()
    files.update(p for p in code if p.endswith('.py') and 'longmemeval' not in p.lower())
    if any('longmemeval' in p.lower() for p in files):
        raise ValueError('sealed paths forbidden in replay')
    archive=git('archive',BASE,'hcl',*sorted(files))
    with tempfile.TemporaryDirectory() as folder:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            for m in bundle.getmembers():
                if m.issym() or m.islnk() or m.name.startswith('/') or '..' in Path(m.name).parts:
                    raise ValueError('unsafe replay archive')
            bundle.extractall(folder,filter='data')
        for name,expected in package['execution_files'].items():
            if hashlib.sha256(Path(folder,name).read_bytes()).hexdigest()!=expected:
                raise ValueError('certified execution hash mismatch')
        subprocess.run([sys.executable,'-m','unittest','tests.test_i02_irie_privacy',
            'tests.test_i02_exposure_history','tests.test_v1_reader_argument_question',
            'tests.test_i02_shea_development_case'],cwd=folder,check=True,timeout=60)
        output=Path(folder,'preflight.json')
        subprocess.run([sys.executable,'scripts/run_i02_irie_privacy_cpg_once.py',
            '--preflight','--output',str(output)],cwd=folder,check=True,timeout=30)
        gate=json.loads(output.read_text())
        if gate['source_gate']['h_runtime_sha256']!=package['hcl_runtime_sha256']:
            raise ValueError('historical runtime replaced')
    return dict(schema='hcl-i02-irie-privacy-certified-replay-v1',baseline_sha=BASE,
        package_file_sha256=hashlib.sha256(raw).hexdigest(),
        historical_runtime_sha256=package['hcl_runtime_sha256'],
        status='PASS_CERTIFIED_V5_PROVIDER_FREE_NOT_CURRENT_RUNTIME',
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repository',default='.')
    args=parser.parse_args();print(json.dumps(replay(args.repository),indent=2))
