"""Control-side gate: rebuild only with the certified, isolated runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FREEZES = {
    'CG04': ('018afbc93c645975d7f6f1077c8c8380635d9f2f',
             '0ffcfdfae3d9d5130c96205f2247991d1d88a872edbb144b701ad01da3202ce9'),
    'CG05': ('c7593bcf5ef8199eb8f1adb3b6f96fb2a0367b94',
             '9ade82883d7dd954b3b092af7b4501b679ca950bf0ca432f108bd35a29400dc7'),
}
LABELS = {
    'CG04': ('APPLICABLE_SOURCE_CLAIM', 'OTHER_SCOPE', 'ATTRIBUTED_ONLY',
             'CONDITION_NOT_MET', 'CONDITION_UNRESOLVED', 'SUPERSEDED_LOCAL',
             'MET_BY_SOURCE_CLAIM', 'NOT_MET_BY_SOURCE_CLAIM', 'UNKNOWN', 'CONTESTED',
             'UNRESOLVED_CONFLICT', 'NO_OBSERVED_CONFLICT', 'NOT_INFERRED'),
    'CG05': ('SUPERSEDED_LOCAL', 'OTHER_SCOPE', 'ATTRIBUTED_ONLY', 'CONTESTED_APPLICATION',
             'DECLARED_COUNTEREXAMPLE', 'CRITERIA_NOT_MET', 'CRITERIA_UNRESOLVED', 'CRITERIA_MET',
             'MET_BY_SOURCE_CLAIM', 'NOT_MET_BY_SOURCE_CLAIM', 'UNKNOWN', 'CONTESTED',
             'MULTIPLE_LOCAL_READINGS', 'ONE_OBSERVED_READING', 'NO_SOURCE_READING',
             'NOT_ESTABLISHED', 'NOT_INFERRED'),
}


def verify(capability, runtime_root, control_root=Path('.')):
    root, control = Path(runtime_root).resolve(), Path(control_root).resolve()
    baseline, package_hash = FREEZES[capability]
    relative = f'reports/HCL_{capability}_EXTERNAL_PACKAGE.json'
    raw = (control / relative).read_bytes()
    if hashlib.sha256(raw).hexdigest() != package_hash or (root / relative).read_bytes() != raw:
        raise ValueError('frozen package hash/bytes mismatch')
    package = json.loads(raw)
    sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if sha != baseline:
        raise ValueError('certified runtime checkout mismatch')
    digest = hashlib.sha256()
    for path in sorted(root.glob('hcl/**/*.py')):
        digest.update(path.relative_to(root).as_posix().encode() + b'\0' + path.read_bytes())
    certificate = json.loads((control / f'reports/HCL_{capability}_PROVIDER_FREE_CERTIFICATION.json').read_text())
    if (digest.hexdigest() != package['runtime_sha256'] or
            certificate['exact_main']['runtime_sha256'] != digest.hexdigest()):
        raise ValueError('certified runtime content mismatch')
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor',
                    certificate['exact_main']['sha'], sha], check=True, capture_output=True)
    for name, expected in package['frozen_engineering_sha256'].items():
        if any(hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected
               for folder in (control, root)):
            raise ValueError('frozen engineering dependency mismatch')
    code = ('import sys; sys.path.insert(0, "."); import json; '
            f'from scripts.{capability.lower()}_external_package import build_package; '
            'print(json.dumps(build_package()))')
    rebuilt = json.loads(subprocess.check_output([sys.executable, '-I', '-c', code], cwd=root, timeout=60))
    if rebuilt != package:
        raise ValueError('frozen input/source/gold/treatment/scorer drift')
    if (package['arms'] != ['C', 'P', 'G', 'H', 'H-new'] or len(package['cases']) != 4 or
            package['model'] != 'deepseek-v4-pro' or package['model_version'] != 'DeepSeek-V4-Pro-0813' or
            package['provider_request'] != dict(thinking={'type': 'disabled'},
                response_format={'type': 'json_object'}, max_retries=0) or
            package['maximum_provider_calls_if_separately_authorized'] != 20 or
            package['maximum_output_tokens_per_call_if_authorized'] != 512 or
            package['proposed_new_hard_cap_usd'] != .30 or
            package['estimated_worst_case_usd_at_repository_frozen_rate'] > .30):
        raise ValueError('authorization contract drift')
    for case in package['cases']:
        if not all(case['preflight'].values()):
            raise ValueError('treatment-presence failure')
        query = json.loads(case['messages']['H'][1]['content'])['query']
        for arm in package['arms']:
            messages = case['messages'][arm]
            text = '\n'.join(m['content'] for m in messages)
            if any(label not in text for label in LABELS[capability]):
                raise ValueError('incomplete shared label vocabulary')
            task = json.loads(messages[1]['content'])['query'] if arm in ('H', 'H-new') else messages[1]['content'].split('\n', 1)[0]
            if task != query or any(field not in text for field in case['gold']):
                raise ValueError('unequal task/output contract')
    return dict(capability=capability, frozen_runtime_sha=sha,
        certified_implementation_sha=certificate['exact_main']['sha'],
        runtime_sha256=digest.hexdigest(), package_sha256=package_hash,
        engineering_sha256=package['frozen_engineering_sha256'],
        gates='PASS', provider_calls=0, shared_full_vocabulary=True,
        cases=[dict(case_id=c['case_id'], preflight=c['preflight'],
                    h_messages=c['messages']['H'], h_new_messages=c['messages']['H-new'])
               for c in package['cases']])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--capability', choices=FREEZES, required=True)
    parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.capability, args.runtime_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'cases'}))
