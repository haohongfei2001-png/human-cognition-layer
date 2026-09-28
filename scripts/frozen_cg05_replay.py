"""Rebuild CG05 inputs using its certified runtime and frozen builder hashes."""
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

BASE_SHA = 'c7593bcf5ef8199eb8f1adb3b6f96fb2a0367b94'
PACKAGE = Path('reports/HCL_CG05_EXTERNAL_PACKAGE.json')
PACKAGE_SHA = '9ade82883d7dd954b3b092af7b4501b679ca950bf0ca432f108bd35a29400dc7'

@lru_cache(maxsize=1)
def replay_frozen_cg05():
    raw = PACKAGE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PACKAGE_SHA:
        raise ValueError('immutable CG05 package hash mismatch')
    frozen = json.loads(raw)
    certificate = json.loads(Path('reports/HCL_CG05_PROVIDER_FREE_CERTIFICATION.json').read_text())
    if (certificate['exact_main']['sha'] != BASE_SHA or
        certificate['exact_main']['runtime_sha256'] != frozen['runtime_sha256']):
        raise ValueError('CG05 frozen runtime/certification mismatch')
    archive = subprocess.check_output(['git', 'archive', BASE_SHA, 'hcl'], timeout=30)
    with tempfile.TemporaryDirectory() as folder:
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            if any(m.issym() or m.islnk() or '..' in Path(m.name).parts for m in bundle.getmembers()):
                raise ValueError('unsafe frozen runtime archive')
            bundle.extractall(folder, filter='data')
        for name, expected in frozen['frozen_engineering_sha256'].items():
            if name not in ('scripts/cg05_external_package.py', 'scripts/cg04_external_package.py'):
                raise ValueError('unexpected frozen builder dependency')
            raw = Path(name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError('frozen CG05 builder drift')
            path = Path(folder, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        code = ('import sys; sys.path.insert(0, "."); from scripts.cg05_external_package import build_package; '
                'import json; print(json.dumps(build_package()))')
        rebuilt = json.loads(subprocess.check_output([sys.executable, '-I', '-c', code], cwd=folder, timeout=30))
        if rebuilt != frozen:
            raise ValueError('CG05 frozen input/gold/treatment/scorer drift')
        return frozen

if __name__ == '__main__':
    p = replay_frozen_cg05()
    print(json.dumps(dict(baseline_sha=BASE_SHA, package_sha256=hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),
                         replay='PASS', provider_calls=0)))
