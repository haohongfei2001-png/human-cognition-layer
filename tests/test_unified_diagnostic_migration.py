"""Current-head equivalents plus explicit rejection of historical authority."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_unified_diagnostic_regressions import (
    ROOT, CURRENT_CONTROL_METHODS, current_offline_control_fixture,
)


class CurrentDiagnosticMigration(unittest.TestCase):
    def test_original_signed_preflight_rejects_current_before_fake_client_or_output(self):
        from scripts import hcl_offline_diagnostic_preflight_v1 as f
        from scripts import hcl_offline_diagnostic_export_v1 as r
        with self.assertRaisesRegex(ValueError, '^CURRENT_RUNTIME_DRIFT$'):
            f.preflight()
        with tempfile.TemporaryDirectory() as directory, patch.object(r, 'FakeClient') as factory:
            target = Path(directory)/'never'
            with self.assertRaisesRegex(ValueError, '^CURRENT_RUNTIME_DRIFT$'):
                f.run_control('malformed_json', target)
            factory.assert_not_called()
            self.assertFalse(target.exists())

    def test_original_live_package_rejects_current_without_factory(self):
        from scripts import hcl_diagnostic_smoke_live_v1 as live
        package = live.LivePackage(live.load_json(ROOT/live.PACKAGE_PATH), live.load_json(ROOT/live.CASE_PATH), ROOT)
        with patch.object(live, '_make_existing_client') as factory:
            with self.assertRaisesRegex(ValueError, '^FINAL_DIAGNOSTIC_CONFIGURATION_OR_RUNTIME_DRIFT$'):
                package.verify()
            factory.assert_not_called()

    def test_current_fixture_is_bound_and_restores_original_gate_on_error(self):
        from scripts import hcl_offline_diagnostic_preflight_v1 as f
        from scripts import hcl_offline_diagnostic_export_v1 as r
        original = f.preflight
        with self.assertRaisesRegex(RuntimeError, 'test cleanup'):
            with current_offline_control_fixture() as package:
                self.assertEqual(package.value['runtime_sha256'], r.runtime_digest(ROOT))
                self.assertNotEqual(package.value['runtime_sha256'], f._read_json(f.MANIFEST)['expected_package']['runtime_sha256'])
                package.verify()
                raise RuntimeError('test cleanup')
        self.assertIs(f.preflight, original)

    def test_current_fresh_process_forbids_sdk_network_credentials_and_live_cli(self):
        code = """
import os, socket, sys
from pathlib import Path
class DenyLiveImports:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('openai', 'requests', 'httpx') or fullname in ('scripts.two_stage_account', 'scripts.two_stage_price', 'hcl_entry_contract_smoke_cli'):
            raise AssertionError('NO_LIVE_IMPORT')
def deny(*args, **kwargs):
    raise AssertionError('NO_NETWORK_OR_CREDENTIAL_LOOKUP')
sys.meta_path.insert(0, DenyLiveImports())
socket.socket.connect = socket.create_connection = deny
from scripts.run_unified_diagnostic_regressions import current_offline_control_fixture
from scripts import hcl_offline_diagnostic_preflight_v1 as f
with current_offline_control_fixture():
    os.getenv = deny
    result = f.run_control('malformed_json', Path(sys.argv[1]))
    assert result['provider_calls'] == 0 and result['actual_spend_cny'] == '0'
"""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-c', code, str(Path(directory)/'run')],
                                    cwd=ROOT, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())


def _current_control(method):
    def test(self):
        from tests.test_hcl_offline_diagnostic_preflight_v1 import CurrentSmokePreflight
        original = CurrentSmokePreflight(method)
        with current_offline_control_fixture():
            # Execute the original assertion body unchanged, on current code.
            getattr(original, method)()
    return test


for _method in CURRENT_CONTROL_METHODS:
    setattr(CurrentDiagnosticMigration, _method, _current_control(_method))
