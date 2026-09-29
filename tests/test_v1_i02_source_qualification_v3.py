"""Additional source denial and audit binding without changing frozen v2."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts.i02_source_qualification_v3 import (
    load_screens, require_qualified_confirmation_source)


SOURCE = 'Synthetic author reports that Noor heard the message after the meeting.'
QUESTION = 'Could Noor have known the message during the meeting?'


def case():
    ordinary = dict(question=QUESTION, source_text=SOURCE)
    return dict(case_id='synthetic-v3-gate-witness',
        task_family='MULTIPARTY_INFORMATION_STRATEGY', split='CONFIRMATION',
        source_origin='INDEPENDENT_NON_HCL_AUTHOR',
        source_license_status='VERIFIED_FOR_THIS_EVALUATION',
        source_access_status='AUTHORIZED_FOR_EVERY_ARM', longmemeval='NOT_USED',
        writing_system_id='synthetic-unseen-system', author_id='synthetic-author',
        template_id='synthetic-template', source_group_id='synthetic-group',
        source_url='https://example.org/synthetic-source', question=QUESTION,
        source_text=SOURCE, arm_inputs={arm:dict(ordinary)
            for arm in ('C', 'P', 'G', 'H')},
        answer_fields=['answer', 'source_citations', 'uncertainty', 'assumptions'],
        repository_wide_exposure_audit='PASS_DISJOINT',
        item_level_source_validity='PASS_SOURCE_FIRST')


def audit():
    return dict(schema='hcl-i02-source-first-rights-audit-v3',
        source_url='https://example.org/synthetic-source',
        source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        question_sha256=hashlib.sha256(QUESTION.encode()).hexdigest(),
        license_evidence_url='https://example.org/synthetic-license',
        model_ingestion_permission='VERIFIED_FOR_THIS_USE',
        privacy_review='NO_PRIVATE_PERSON_OR_CLEARED_SCOPE',
        native_question_review='SOURCE_FIRST_PASS',
        rights_reviewer_independent_of_model_outcomes=True,
        confirmation_outputs_seen=0, longmemeval='NOT_USED')


class SourceQualificationV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = json.loads(Path(
            'reports/HCL_I01_EVALUATION_FREEZE.json').read_text())

    def test_positive_synthetic_composition_and_historical_exposure_guard(self):
        self.assertTrue(require_qualified_confirmation_source(
            self.freeze, case(), audit()))
        exposed = case()
        historical = json.loads(Path(
            'reports/HCL_I02_EXPOSURE_LINEAGE.json').read_text())
        exposed['writing_system_id'] = historical['exposed_systems'][0][
            'writing_system_id']
        with self.assertRaises(ValueError):
            require_qualified_confirmation_source(self.freeze, exposed, audit())

    def test_screened_publisher_and_sensitive_source_cannot_be_renamed(self):
        screens = load_screens()['screened']
        self.assertEqual(len(screens), 3)
        for row in screens:
            blocked = case()
            blocked['source_url'] = row['publisher_url_prefix'] + 'renamed-row'
            blocked_audit = audit()
            blocked_audit['source_url'] = blocked['source_url']
            with self.assertRaisesRegex(ValueError, 'screened source system'):
                require_qualified_confirmation_source(
                    self.freeze, blocked, blocked_audit)
            blocked = case()
            blocked['writing_system_id'] = row['writing_system_id']
            with self.assertRaisesRegex(ValueError, 'screened source system'):
                require_qualified_confirmation_source(self.freeze, blocked, audit())

    def test_rights_privacy_question_and_digest_fail_closed(self):
        bad = audit()
        bad['model_ingestion_permission'] = 'UNKNOWN'
        with self.assertRaisesRegex(ValueError, 'audit incomplete'):
            require_qualified_confirmation_source(self.freeze, case(), bad)
        bad = audit()
        bad['privacy_review'] = 'UNKNOWN'
        with self.assertRaisesRegex(ValueError, 'audit incomplete'):
            require_qualified_confirmation_source(self.freeze, case(), bad)
        bad = audit()
        bad['source_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'audit incomplete'):
            require_qualified_confirmation_source(self.freeze, case(), bad)
        bad = audit()
        bad['confirmation_outputs_seen'] = 1
        with self.assertRaisesRegex(ValueError, 'audit incomplete'):
            require_qualified_confirmation_source(self.freeze, case(), bad)
        bad_case = case()
        bad_case['source_url'] = 'http://example.org/synthetic-source'
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            require_qualified_confirmation_source(self.freeze, bad_case, audit())


if __name__ == '__main__':
    unittest.main()
