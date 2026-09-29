"""Known calibration exposure is excluded even from confirmation-only catalogs."""

import json
import hashlib
import unittest
from pathlib import Path

from scripts.i02_source_lineage import (
    load_lineage, require_confirmation_disjoint, validate_i02_confirmation_candidate)
from scripts.serious_eval_contract import ARMS, FIELDS, validate_candidate


FREEZE = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())


def candidate(**overrides):
    ordinary = {'question': 'What did Ada report?', 'source_text': 'Ada reported a goal.'}
    row = {'case_id': 'fictional-confirmation-shape',
           'task_family': 'MULTIPARTY_INFORMATION_STRATEGY',
           'split': 'CONFIRMATION',
           'source_origin': 'INDEPENDENT_NON_HCL_AUTHOR',
           'source_license_status': 'VERIFIED_FOR_THIS_EVALUATION',
           'source_access_status': 'AUTHORIZED_FOR_EVERY_ARM',
           'longmemeval': 'NOT_USED',
           'writing_system_id': 'fictional-new-system',
           'author_id': 'fictional-new-author',
           'template_id': 'fictional-new-template',
           'source_group_id': 'fictional-new-group',
           'question': ordinary['question'], 'source_text': ordinary['source_text'],
           'arm_inputs': {arm: ordinary.copy() for arm in ARMS},
           'answer_fields': list(FIELDS),
           'repository_wide_exposure_audit': 'PASS_DISJOINT',
           'item_level_source_validity': 'PASS_SOURCE_FIRST'}
    row.update(overrides)
    return row


class SourceLineageTests(unittest.TestCase):
    def test_known_exposure_receipts_and_screened_metadata_are_not_qualification(self):
        lineage = load_lineage()
        self.assertEqual({x['calibration_run_id'] for x in lineage['exposed_systems']},
                         {36561878435, 36566850936})
        self.assertEqual({x['id'] for x in lineage['historical_exposed_systems']},
                         {'cogtom-historical', 'sotopia-hard-historical',
                          'fantom-historical', 'hitom-historical', 'saga-historical'})
        self.assertGreaterEqual(lineage['screened_not_qualified'][0]['content_rows_seen_at_least'], 1)
        with self.assertRaisesRegex(ValueError, 'screened source system'):
            require_confirmation_disjoint(candidate(
                writing_system_id='hendrycks-ethics-short-scenario-system',
                author_id='hendrycks-ethics-original-authors',
                source_license_status='PROVISIONAL_METADATA_ONLY'))

    def test_historical_fresh_label_cannot_requalify_exposed_writing_system(self):
        for exposed in load_lineage()['historical_exposed_systems']:
            with self.subTest(system=exposed['id']):
                row = candidate(writing_system_id=exposed['writing_system_id'],
                                source_group_id='previously-unseen-row-in-same-system')
                self.assertTrue(validate_candidate(FREEZE, row))
                with self.assertRaisesRegex(ValueError, 'historical source system'):
                    validate_i02_confirmation_candidate(FREEZE, row)

    def test_different_musr_row_still_reuses_exposed_writing_system(self):
        row = candidate(writing_system_id='TAUR_MUSR_OBJECT_PLACEMENT_GENERATED_NARRATIVE',
                        source_group_id='some-other-narrative-hash')
        self.assertTrue(validate_candidate(FREEZE, row))
        with self.assertRaisesRegex(ValueError, 'writing_system_id reuses'):
            validate_i02_confirmation_candidate(FREEZE, row)

    def test_different_moral_story_still_reuses_exposed_author_or_template(self):
        row = candidate(author_id='moral-stories-original-authors',
                        source_group_id='some-other-story-id')
        with self.assertRaisesRegex(ValueError, 'author_id reuses'):
            require_confirmation_disjoint(row)
        row = candidate(template_id='moral-stories-full-alternative-paths')
        with self.assertRaisesRegex(ValueError, 'template_id reuses'):
            require_confirmation_disjoint(row)

    def test_bounded_source_screens_are_not_unseen_confirmation(self):
        lineage = load_lineage()
        self.assertEqual({x['id'] for x in lineage['screened_not_qualified']},
            {'hendrycks-ethics-author-team-hf',
             'quality-nesta-women-on-the-march-dev',
             'gutenberg-hannes-bok-62314-catalog-summary',
             'narrativeqa-amy-foster-development-screen',
             'narrative-crossroads-two-modules-development-screen',
             'squality-gutenberg-63833-catalog-summary',
             'tru-social-contract-development-screen',
             'ethics-bowl-canada-harm-case-search-exposure',
             'rebus-kao-social-contract-development-screen'})
        with self.assertRaisesRegex(ValueError, 'screened source system'):
            require_confirmation_disjoint(candidate(
                template_id='quality-v1.0.1-human-mcq-questions'))
        with self.assertRaisesRegex(ValueError, 'screened source system'):
            require_confirmation_disjoint(candidate(
                author_id='hannes-bok-original-author'))
        with self.assertRaisesRegex(ValueError, 'screened source author'):
            require_confirmation_disjoint(candidate(
                author_id='joseph-conrad'))
        with self.assertRaisesRegex(ValueError, 'screened source author'):
            require_confirmation_disjoint(candidate(
                author_id='hector-hugh-munro-saki'))
        with self.assertRaisesRegex(ValueError, 'screened source system'):
            require_confirmation_disjoint(candidate(
                template_id='ethics-bowl-canada-what-is-harm-case-discussion'))
        with self.assertRaisesRegex(ValueError, 'screened source author'):
            require_confirmation_disjoint(candidate(author_id='ya-yun-sherry-kao'))

    def test_exact_exposed_content_cannot_pass_under_renamed_lineage(self):
        lineage = load_lineage()
        quality = next(x for x in lineage['screened_not_qualified']
            if x['id'] == 'quality-nesta-women-on-the-march-dev')
        report = json.loads(Path('reports/HCL_I02_QUALITY_BOUNDED_SCREEN.json').read_text())
        self.assertEqual(quality['source_sha256s'], [report['selected_article_sha256']])
        synthetic = 'The same exposed original text under an invented author.'
        screened = {'id': 'synthetic-exposure', 'source_sha256s': [
            hashlib.sha256(synthetic.encode()).hexdigest()],
            'writing_system_id': 'other-system', 'author_id': 'other-author',
            'template_id': 'other-template'}
        lineage['screened_not_qualified'].append(screened)
        with self.assertRaisesRegex(ValueError, 'source_text reuses screened source content'):
            require_confirmation_disjoint(candidate(source_text=synthetic), lineage)
        self.assertTrue(require_confirmation_disjoint(candidate(), lineage))

    def test_exposure_receipt_rejects_invalid_and_duplicated_screen_metadata(self):
        lineage = json.loads(Path('reports/HCL_I02_EXPOSURE_LINEAGE.json').read_text())
        screened = lineage['screened_not_qualified']
        self.assertEqual(8, next(x for x in screened if x['id'].startswith('narrativeqa'))[
            'native_labels_opened'])
        screened.append(dict(screened[0]))
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lineage.json'
            path.write_text(json.dumps(lineage))
            with self.assertRaisesRegex(ValueError, 'screened source cannot be promoted'):
                load_lineage(path)

    def test_independent_shape_still_requires_separate_actual_rights_and_semantic_audit(self):
        row = candidate()
        self.assertTrue(validate_candidate(FREEZE, row))
        self.assertTrue(validate_i02_confirmation_candidate(FREEZE, row))
        with self.assertRaisesRegex(ValueError, 'historical exposure audit'):
            require_confirmation_disjoint(candidate(repository_wide_exposure_audit='NOT_DONE'))
        with self.assertRaisesRegex(ValueError, 'item-level semantics'):
            require_confirmation_disjoint(candidate(item_level_source_validity='NOT_AUDITED'))


if __name__ == '__main__':
    unittest.main()
