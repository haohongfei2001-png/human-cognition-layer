"""Execute dormant workflow guards: no default grant or silent runtime migration."""
import os
from pathlib import Path
import re
import subprocess
import unittest
from scripts.frozen_cg04_replay import BASE_SHA, replay_frozen_cg04


class FrozenExecutionTests(unittest.TestCase):
    def guard(self, cap='0', baseline='UNAUTHORIZED', attempt='1'):
        workflow = Path('.github/workflows/hcl-cg04-external-dev-once.yml').read_text()
        block = workflow.split('      - name: Verify unique trigger and owner grant\n', 1)[1].split('\n      - name:', 1)[0]
        script = '\n'.join(line[10:] for line in block.split('        run: |\n', 1)[1].splitlines())
        parent = subprocess.check_output(['git', 'rev-parse', 'HEAD^'], text=True).strip()
        script = script.replace('${{ github.event.before }}', parent)
        env = dict(PATH=os.environ['PATH'], GITHUB_RUN_ATTEMPT=attempt,
            GITHUB_SHA=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            HCL_CG04_AUTHORIZED_CAP_USD=cap, HCL_CG04_AUTHORIZED_BASE_SHA=baseline,
            HCL_CG04_FROZEN_RUNTIME_SHA=BASE_SHA, HCL_CG04_RUN_ONCE_TOKEN='HCL_CG04_EXTERNAL_DEV_OWNER_ONCE',
            HCL_CG04_FROZEN_PACKAGE_SHA256='0ffcfdfae3d9d5130c96205f2247991d1d88a872edbb144b701ad01da3202ce9',
            DEEPSEEK_API_KEY='fake-placeholder-never-used-by-a-provider')
        return subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], env=env, capture_output=True)

    def test_default_zero_grant_cannot_reach_execution(self):
        self.assertNotEqual(self.guard().returncode, 0)
        self.assertFalse(Path('.github/HCL_CG04_EXTERNAL_DEV_TRIGGER').exists())
        self.assertTrue(all(all(c['preflight'].values()) for c in replay_frozen_cg04()['cases']))

    def test_latest_runtime_or_retry_cannot_replace_the_explicit_frozen_grant(self):
        latest = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        self.assertNotEqual(latest, BASE_SHA)
        self.assertNotEqual(self.guard('0.30', latest).returncode, 0)
        self.assertNotEqual(self.guard('0.30', BASE_SHA, '2').returncode, 0)
        # Even a hypothetical exact grant has no unique trigger in this night.
        self.assertNotEqual(self.guard('0.30', BASE_SHA).returncode, 0)


if __name__ == '__main__':
    unittest.main()
