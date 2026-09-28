"""Copy hash-pinned freeze builders/transport into the certified CG05 checkout."""
import argparse
import hashlib
import json
from pathlib import Path
from scripts.verify_cg_frozen_execution import FREEZES, verify


def stage(root, adapter_hash, control=Path('.')):
    root, control = Path(root).resolve(), Path(control).resolve()
    package = json.loads((control / 'reports/HCL_CG05_EXTERNAL_PACKAGE.json').read_text())
    expected_package_hash = FREEZES['CG05'][1]
    if hashlib.sha256((control / 'reports/HCL_CG05_EXTERNAL_PACKAGE.json').read_bytes()).hexdigest() != expected_package_hash:
        raise ValueError('CG05 package drift')
    dependencies = json.loads((control / 'reports/HCL_CG04_EXTERNAL_PACKAGE.json').read_text())['frozen_engineering_sha256']
    for name in ('scripts/run_cg03_external_once.py', 'scripts/run_cg02_external_once.py'):
        if any(hashlib.sha256((p / name).read_bytes()).hexdigest() != dependencies[name] for p in (control, root)):
            raise ValueError('existing provider/ledger dependency drift')
    names = dict(package['frozen_engineering_sha256'])
    names['scripts/run_cg05_external_once.py'] = adapter_hash
    for name, expected in names.items():
        raw = (control / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('CG05 pinned builder/transport drift')
    # No hcl runtime file is copied. The new adapter only transports frozen messages.
    for name in [*names, 'reports/HCL_CG05_EXTERNAL_PACKAGE.json']:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((control / name).read_bytes())
    receipt = verify('CG05', root, control)
    receipt['execution_adapter_sha256'] = adapter_hash
    receipt['provider_ledger_sha256'] = {name: dependencies[name] for name in
        ('scripts/run_cg03_external_once.py', 'scripts/run_cg02_external_once.py')}
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--adapter-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    receipt = stage(args.runtime_root, args.adapter_sha256)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'cases'}))
