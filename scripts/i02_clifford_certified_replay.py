"""Provider-free historical replay using exact files verified at the paid run SHA.

No latest-runtime substitution, transport, environment credential or old rescoring.
The current closed grant is required before any frozen preflight code is invoked.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

CERTIFICATE = Path('reports/HCL_I02_CLIFFORD_CERTIFIED_REPLAY.json')
ARCHIVE = Path('reports/HCL_I02_CLIFFORD_CERTIFIED_REPLAY.zip')
PACKAGE = Path('reports/HCL_I02_CLIFFORD_CPG_PACKAGE.json')
GRANT = Path('.github/HCL_I02_CLIFFORD_CPG_GRANT.json')
CERTIFICATE_SHA256 = 'aba5a23face2af42a07b154e6a0a18d3e41a2148ef0dd0f318e1fc9127b85b5e'
RUN_SHA = 'a8c2c3d08e0addbcf24dcfd247805c025c8cacab'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_archive():
    cert_raw = CERTIFICATE.read_bytes()
    if _sha(cert_raw) != CERTIFICATE_SHA256:
        raise ValueError('certified replay certificate drift')
    cert = json.loads(cert_raw)
    raw = ARCHIVE.read_bytes()
    if (_sha(raw) != cert['archive_sha256'] or len(raw) != cert['archive_size_bytes']
            or cert['run_sha'] != RUN_SHA or cert['replay_allowed'] != 'PROVIDER_FREE_PREFLIGHT_ONLY_NEVER_EXECUTE'):
        raise ValueError('certified replay archive or execution boundary drift')
    runtime = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(cert['files']):
            raise ValueError('archive membership drift')
        for name, row in cert['files'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts or not name.startswith(('hcl/', 'scripts/', 'reports/', 'tests/', '.github/')):
                raise ValueError('unsafe certified path')
            data = archive.read(name)
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if (_sha(data) != row['sha256'] or len(data) != row['size_bytes']
                    or blob != row['git_blob_sha1']):
                raise ValueError('certified Git blob drift')
            if name.startswith('hcl/') and name.endswith('.py'):
                runtime[name] = _sha(data)
        p_raw = archive.read(str(PACKAGE))
        p = json.loads(p_raw)
        digest = _sha(json.dumps(p, sort_keys=True, separators=(',', ':')).encode())
        code_digest = _sha(json.dumps(runtime, sort_keys=True, separators=(',', ':')).encode())
        if (PACKAGE.read_bytes() != p_raw or digest != cert['package_sha256']
                or code_digest != cert['hcl_runtime_sha256'] or code_digest != p['hcl_runtime_sha256']
                or any(cert['files'][name]['sha256'] != sha for name, sha in p['execution_files'].items())):
            raise ValueError('certified package/runtime/execution mismatch')
    return cert, p


def load_certified_package():
    return validate_archive()[1]


def replay_provider_free(*, tests=False):
    cert, _ = validate_archive()
    grant = json.loads(GRANT.read_text())
    if (grant.get('status') != 'CLOSED' or grant.get('remaining_usd') != 0
            or grant.get('maximum_calls') != 0
            or Path('.github/workflows/hcl-i02-clifford-cpg-once.yml').exists()):
        raise ValueError('historical replay requires closed grant and removed live trigger')
    env = dict(os.environ)
    for key in list(env):
        if key.endswith(('_API_KEY', '_AUTHORIZED')) or key in ('PYTHONPATH', 'GITHUB_RUN_ATTEMPT'):
            env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix='hcl-clifford-certified-') as temp:
        root = Path(temp)
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in cert['files']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
        # The frozen package did not include an execution grant. Supply only the
        # present CLOSED grant: even a first-attempt environment cannot run it.
        (root / GRANT).write_bytes(GRANT.read_bytes())
        if tests:
            subprocess.run([sys.executable, '-m', 'unittest', 'tests.test_i02_clifford_cpg',
                'tests.test_i02_full_source_arms_v9', 'tests.test_v1_i02_semantic_score'],
                cwd=root, env=env, check=True)
        output = root / 'historical-preflight.json'
        subprocess.run([sys.executable, '-m', 'scripts.run_i02_clifford_cpg_once',
            '--preflight', '--output', str(output)], cwd=root, env=env, check=True)
        receipt = json.loads(output.read_text())
        if receipt['package_sha256'] != cert['package_sha256'] or receipt['provider_calls'] != 0:
            raise ValueError('historical preflight mismatch')
    return dict(status='PASS_EXACT_CERTIFIED_RUNTIME_PREFLIGHT_ONLY', run_sha=RUN_SHA,
        archive_sha256=cert['archive_sha256'], hcl_runtime_sha256=cert['hcl_runtime_sha256'],
        package_sha256=cert['package_sha256'], latest_runtime_substituted=False,
        provider_calls=0, closed_grant_required=True, outputs_rescored=False,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    print(json.dumps(replay_provider_free(tests='--tests' in sys.argv), indent=2))
