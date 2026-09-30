import copy,json,os,unittest
from unittest.mock import patch
from scripts.i02_clifford_closure_audit import audit
from scripts.i02_clifford_certified_replay import load_certified_package
from scripts.run_i02_clifford_cpg_once import require_execution_grant
class CliffordClosureTests(unittest.TestCase):
    def test_exact_raw_archive_and_frozen_ineligible_outputs(self):
        g=audit();self.assertEqual(g['strict_invalid_quotation_counts'],{'C':2,'P':2,'G_map':31});self.assertIsNone(g['formal_semantic_scores']);self.assertEqual(g['new_audit_provider_calls'],0)
    def test_consumed_authorization_refuses_even_first_run_env(self):
        with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'1','HCL_I02_CLIFFORD_AUTHORIZED':'ONE_DEVELOPMENT_CALIBRATION_ONLY'}):
            with self.assertRaises(ValueError):require_execution_grant(load_certified_package())
if __name__=='__main__':unittest.main()
