"""L0 setup tests only. No runtime cognition, research data or provider access."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('product_planning', ROOT / 'scripts/check_planning.py')
planning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(planning)


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.plan = read('control/plan.json')
        self.catalog = read('contracts/catalog.json')
        self.capabilities = read('contracts/capabilities.json')
        self.schema = read('contracts/capability-manifest.schema.json')

    def assert_plan_rejected(self):
        with self.assertRaises(planning.PlanningError):
            planning.validate_plan(self.plan)

    def assert_manifest_rejected(self):
        with self.assertRaises(planning.PlanningError):
            planning.validate_capabilities(self.capabilities, self.schema, self.catalog)

    def test_complete_product_tree(self):
        result = planning.validate_tree(ROOT)
        self.assertEqual(result['package_count'], 9)
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(result['capability_candidates'], 10)

    def test_research_sequence_is_unchanged(self):
        self.plan['research_sequence'].remove('I04')
        self.assert_plan_rejected()

    def test_production_base_bypass_is_rejected(self):
        self.plan['invariants']['production_base_bypass'] = True
        self.assert_plan_rejected()

    def test_controller_cannot_be_optional(self):
        self.plan['invariants']['controller_required_for_production_answer'] = False
        self.assert_plan_rejected()

    def test_no_hidden_reasoning_storage(self):
        self.plan['invariants']['hidden_chain_of_thought_storage'] = True
        self.assert_plan_rejected()

    def test_mock_cannot_be_relabelled(self):
        self.plan['invariants']['mock_may_be_relabelled_real'] = True
        self.assert_plan_rejected()

    def test_confirmation_data_is_forbidden(self):
        self.plan['invariants']['confirmation_material_allowed'] = True
        self.assert_plan_rejected()

    def test_no_provider_budget_in_l0_l2(self):
        self.plan['invariants']['max_provider_calls_l0_l2'] = 1
        self.assert_plan_rejected()

    def test_unsplit_repository_blocks_real_data(self):
        self.plan['boundary']['real_data_allowed'] = True
        self.assert_plan_rejected()

    def test_unsplit_repository_blocks_deployment(self):
        self.plan['boundary']['public_deployment_allowed'] = True
        self.assert_plan_rejected()

    def test_unknown_next_rejected(self):
        self.plan['next_package_id'] = 'L1-99'
        self.assert_plan_rejected()

    def test_duplicate_package_rejected(self):
        self.plan['packages'][2]['id'] = 'L1-01'
        self.assert_plan_rejected()

    def test_cyclic_dependency_rejected(self):
        self.plan['packages'][1]['depends_on'] = ['L2-04']
        self.assert_plan_rejected()

    def test_contract_missing_rejected(self):
        self.catalog['contracts'].pop()
        with self.assertRaises(planning.PlanningError):
            planning.validate_catalog(self.catalog)

    def test_guess_and_report_cannot_collapse(self):
        self.catalog['enums']['context_kinds'].remove('USER_GUESS')
        with self.assertRaises(planning.PlanningError):
            planning.validate_catalog(self.catalog)

    def test_stop_using_and_delete_cannot_collapse(self):
        self.catalog['enums']['revision_actions'].remove('STOP_USING')
        with self.assertRaises(planning.PlanningError):
            planning.validate_catalog(self.catalog)

    def test_three_permission_dimensions_required(self):
        self.catalog['permission_dimensions'].pop()
        with self.assertRaises(planning.PlanningError):
            planning.validate_catalog(self.catalog)

    def test_pending_capability_cannot_be_production(self):
        self.capabilities['capabilities'][0]['product_activation_policy']['production_enabled'] = True
        self.assert_manifest_rejected()

    def test_disabled_capability_cannot_be_active(self):
        row = self.capabilities['capabilities'][0]
        row['i06_disposition'] = 'DISABLE'
        row['product_activation_policy']['mode'] = 'SCOPE_DEFAULT'
        self.assert_manifest_rejected()

    def test_design_only_cannot_claim_language_qualification(self):
        self.capabilities['capabilities'][0]['language'] = ['zh-CN']
        self.assert_manifest_rejected()

    def test_duplicate_capability_rejected(self):
        self.capabilities['capabilities'].append(copy.deepcopy(self.capabilities['capabilities'][0]))
        self.assert_manifest_rejected()

    def test_research_package_key_rejected(self):
        self.capabilities['capabilities'][0]['capability_id'] = 'B03'
        self.assert_manifest_rejected()

    def test_missing_runtime_field_rejected(self):
        del self.capabilities['capabilities'][0]['runtime_implementation']
        self.assert_manifest_rejected()

    def test_path_traversal_and_absolute_path_rejected(self):
        for relative in ('../../hcl', '/tmp/not-product'):
            with self.subTest(relative=relative), self.assertRaises(planning.PlanningError):
                planning.safe_path(ROOT, relative)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outside').symlink_to(ROOT.parent, target_is_directory=True)
            with self.assertRaises(planning.PlanningError):
                planning.safe_path(root, 'outside/README.md')

    def test_missing_doc_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'product'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.venv', '__pycache__', 'node_modules'))
            (root / 'contracts/PRODUCT_CONTRACTS_V1.md').unlink()
            with self.assertRaises(planning.PlanningError):
                planning.validate_tree(root)

    def test_status_queue_disagreement_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'product'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.venv', '__pycache__', 'node_modules'))
            (root / 'STATUS.md').write_text('NEXT_READY: wrong', encoding='utf-8')
            with self.assertRaises(planning.PlanningError):
                planning.validate_tree(root)

    def test_outside_doc_link_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'product'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.venv', '__pycache__', 'node_modules'))
            with (root / 'README.md').open('a', encoding='utf-8') as stream:
                stream.write('\n[invalid](../../hcl)\n')
            with self.assertRaises(planning.PlanningError):
                planning.validate_tree(root)


if __name__ == '__main__':
    unittest.main()
