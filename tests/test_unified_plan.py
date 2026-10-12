"""Scope and status consistency, not cognitive-function acceptance."""
import json
from pathlib import Path
import unittest

from scripts.render_hcl_status import render

ROOT = Path(__file__).resolve().parents[1]


class UnifiedPlanTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT/'docs/hcl_design_manifest.json').read_text())

    def test_full_approved_scope_and_dependency_graph_are_present(self):
        m = self.manifest
        for key, prefix, count in [('issues', 'P', 38), ('mechanisms', 'M', 16), ('acceptance', 'T', 32)]:
            self.assertEqual([row['id'] for row in m[key]], [f'{prefix}{i:02}' for i in range(1, count+1)])
        self.assertEqual({row['id']: row['depends_on'] for row in m['stages']}, {
            'S1': [], 'S2': ['S1'], 'S3': ['S2'], 'S4': ['S2'], 'S5': ['S3', 'S4'], 'S6': ['S5'], 'S7': ['S6']})
        self.assertEqual(len(m['migration']), 61)
        self.assertEqual([row['id'] for row in m['decisions']], [f'D{i}' for i in range(1, 7)])
        self.assertEqual([row['id'] for row in m['execution_slices']], ['S1.1', 'S1.2', 'S1.3', 'S2.1', 'S2.2', 'S2.3'])

    def test_current_indexes_are_derived_from_manifest(self):
        for name, expected in render(self.manifest).items():
            self.assertEqual((ROOT/name).read_text(), expected, name)

    def test_first_slice_does_not_close_stage_or_acceptance_families(self):
        current = self.manifest['current_execution']
        self.assertEqual(current['readiness'], 'INTEGRATED_OFFLINE')
        self.assertFalse(current['stage_complete'])
        self.assertEqual(current['next_slice'], 'S3 ∥ S4')
        self.assertEqual(current['delivered_slice'], 'S2.3')
        self.assertEqual(current['provider_calls'], 0)
        self.assertEqual(current['provider_spend_usd'], '0')
        self.assertEqual(current['sealed_content_reads'], 0)
        self.assertTrue(all(row['status'] == 'PLANNED_NOT_EXECUTED' for row in self.manifest['acceptance']))
        self.assertFalse(self.manifest['execution_slices'][0]['evidence']['stage_complete'])

    def test_design_adoption_authority_stays_historical(self):
        # Runtime implementation authorization is a separate current record;
        # never rewrite what the earlier documentation-only grant authorized.
        self.assertFalse(self.manifest['adoption']['runtime_code_change_authorized_this_run'])
        self.assertFalse(self.manifest['adoption']['paid_calls_authorized_this_run'])
        self.assertEqual(self.manifest['baseline'], '58bfa17aed8da5773714309173438796b33491ec')

    def test_partial_domain_evidence_cannot_close_the_approved_stages(self):
        current = self.manifest['current_execution']
        self.assertEqual(current['current_stage'], 'S3 ∥ S4')
        self.assertEqual(current['domain_evidence'][0]['mechanisms'], ['M03','M05','M06'])
        self.assertFalse(current['domain_evidence'][0]['stage_complete'])
        for row in self.manifest['mechanisms']:
            if row['id'] in ('M03','M05','M06'):
                self.assertFalse(row['partial_implementation_evidence']['complete'])
                self.assertEqual(row['evidence_status'],'DESIGNED_NOT_HCL_VALIDATED')

    def test_argument_increment_preserves_full_concept_and_reflection_obligations(self):
        row=next(row for row in self.manifest['mechanisms'] if row['id']=='M13')
        self.assertFalse(row['partial_implementation_evidence']['complete'])
        self.assertEqual(row['evidence_status'],'DESIGNED_NOT_HCL_VALIDATED')
        self.assertEqual(self.manifest['current_execution']['domain_evidence'][1]['mechanisms'],['M13'])
        self.assertFalse(self.manifest['current_execution']['domain_evidence'][1]['stage_complete'])
