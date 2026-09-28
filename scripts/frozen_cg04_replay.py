"""Replay the immutable CG04 freeze at its certified checkout, without network."""
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

BASE_SHA = '018afbc93c645975d7f6f1077c8c8380635d9f2f'
PACKAGE_SHA = '0ffcfdfae3d9d5130c96205f2247991d1d88a872edbb144b701ad01da3202ce9'
PACKAGE_PATH = 'reports/HCL_CG04_EXTERNAL_PACKAGE.json'

@lru_cache(maxsize=1)
def replay_frozen_cg04():
    # Archive only the runtime and builder: never inspect sealed eval material.
    paths = ['hcl', 'scripts/cg04_external_package.py', 'scripts/run_cg04_external_once.py',
             'scripts/run_cg03_external_once.py', 'scripts/run_cg02_external_once.py', PACKAGE_PATH]
    archive = subprocess.check_output(['git', 'archive', BASE_SHA, *paths], timeout=30)
    with tempfile.TemporaryDirectory() as folder:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            for member in bundle.getmembers():
                if member.issym() or member.islnk() or '..' in Path(member.name).parts:
                    raise ValueError('unsafe frozen archive')
            bundle.extractall(folder, filter='data')
        raw = Path(folder, PACKAGE_PATH).read_bytes()
        if hashlib.sha256(raw).hexdigest() != PACKAGE_SHA:
            raise ValueError('immutable CG04 package hash mismatch')
        code = 'from scripts.cg04_external_package import build_package; import json; print(json.dumps(build_package()))'
        rebuilt = json.loads(subprocess.check_output([sys.executable, '-I', '-c',
            'import sys; sys.path.insert(0, "."); ' + code], cwd=folder, timeout=30))
        frozen = json.loads(raw)
        if rebuilt != frozen or Path(PACKAGE_PATH).read_bytes() != raw:
            raise ValueError('CG04 certified replay or current frozen file drift')
        return frozen

if __name__ == '__main__':
    package = replay_frozen_cg04()
    print(json.dumps(dict(baseline_sha=BASE_SHA, package_sha256=PACKAGE_SHA,
                         cases=len(package['cases']), provider_calls=0, replay='PASS')))
