import unittest
from hcl.v1.capabilities import CAPABILITIES, CapabilityType, resolve_dependencies

class RegistryTests(unittest.TestCase):
    def test_unique_ids_locations_and_evidence(self):
        self.assertEqual(len(CAPABILITIES), 26)
        for cid, cap in CAPABILITIES.items():
            self.assertEqual(cid, cap.capability_id)
            self.assertTrue(cap.implementation and cap.evidence_level and cap.failure_behavior)
            for dep in cap.dependencies:
                self.assertIn(dep, CAPABILITIES)
    def test_minimal_closure(self):
        self.assertEqual(resolve_dependencies(()), ())
        selected = resolve_dependencies(('belief',))
        self.assertIn('perspective', selected)
        self.assertNotIn('affect', selected)
        self.assertNotIn('intention', selected)
    def test_inactive_denied_and_immutable(self):
        for cid, cap in CAPABILITIES.items():
            if cap.kind == CapabilityType.INACTIVE:
                with self.assertRaises(ValueError): resolve_dependencies((cid,))
        with self.assertRaises(TypeError): CAPABILITIES['new'] = None
