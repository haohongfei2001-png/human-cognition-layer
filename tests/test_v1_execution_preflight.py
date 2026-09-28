"""Financial gate rejects live runtime and frozen content substitution."""
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

from scripts.verify_cg_frozen_execution import FREEZES, verify


class FrozenExecutionTests(unittest.TestCase):
    def stage(self, capability, root):
        baseline = FREEZES[capability][0]
        raw = subprocess.check_output(['git', 'archive', baseline, 'hcl'])
        with tarfile.open(fileobj=io.BytesIO(raw)) as bundle:
            bundle.extractall(root, filter='data')
        package_path = f'reports/HCL_{capability}_EXTERNAL_PACKAGE.json'
        package = json.loads(Path(package_path).read_text())
        for name in [package_path, *package['frozen_engineering_sha256']]:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(Path(name).read_bytes())
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        objects = Path(subprocess.check_output(['git', 'rev-parse', '--git-path', 'objects'], text=True).strip()).resolve()
        (root / '.git/objects/info/alternates').write_text(str(objects) + '\n')
        subprocess.run(['git', '-C', str(root), 'update-ref', 'refs/heads/frozen', baseline], check=True)
        subprocess.run(['git', '-C', str(root), 'symbolic-ref', 'HEAD', 'refs/heads/frozen'], check=True)

    def test_both_certified_runtimes_rebuild_full_fair_treatments(self):
        for cap in FREEZES:
            with self.subTest(cap=cap), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.stage(cap, root)
                receipt = verify(cap, root)
                self.assertEqual(receipt['gates'], 'PASS')
                self.assertEqual(receipt['provider_calls'], 0)

    def test_latest_runtime_or_package_or_helper_drift_rejected(self):
        for mutation in ('runtime', 'package', 'helper', 'head'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                self.stage('CG04', root)
                paths = {'runtime': 'hcl/v1/cg04.py',
                         'package': 'reports/HCL_CG04_EXTERNAL_PACKAGE.json',
                         'helper': 'scripts/cg04_external_package.py'}
                if mutation == 'head':
                    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
                    subprocess.run(['git', '-C', str(root), 'update-ref', 'refs/heads/frozen', head], check=True)
                else:
                    with (root / paths[mutation]).open('a') as file:
                        file.write('\n# simulated substitution\n')
                with self.assertRaises(ValueError):
                    verify('CG04', root)
