"""Exact read-only imports of reviewed bounded helpers; no live entry is invoked."""
import importlib.util
from pathlib import Path
import hashlib
import sys

DIRECTORY = Path(__file__).resolve().parents[1] / '.github/frozen/hcl-entry-contract-smoke-20261008/executor'
PINS = {'hcl_entry_contract_smoke_candidate.py': 'a609a39d44653fe2db9cbd4fa034f5fff1238b5d6d199a77dde01d13cafaae36', 'hcl_entry_contract_smoke_public.py': '7eef8df9cd472394ecb51ba2963b5ed8893e5929c263108233c19398ace77425', 'hcl_entry_contract_smoke_native_public.py': '9f3b1e17afbffeb4f1f834da22ad97e2eb30f93d7442b005f0c6821a62099a28'}


def _load(name):
    if type(name) is not str or name + '.py' not in PINS:
        raise ValueError('EXACT_ARCHIVED_HELPER_NAME_REQUIRED')
    path = DIRECTORY / (name + '.py')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PINS[path.name]:
        raise ValueError('ARCHIVED_HELPER_HASH_CHANGED')
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(existing.__file__).resolve() != path:
            raise ValueError('ARCHIVED_HELPER_IMPORT_IDENTITY_CHANGED')
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


_reference = _load('hcl_entry_contract_smoke_candidate')
_native = _load('hcl_entry_contract_smoke_native_public')
_public = _load('hcl_entry_contract_smoke_public')
