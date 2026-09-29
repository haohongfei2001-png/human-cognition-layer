"""I01 guard prevents contaminated or unfair evaluation before provider calls."""
import copy
import json
import unittest
from pathlib import Path

from scripts.serious_eval_contract import (ARMS, FAMILIES, FIELDS,
    runtime_digest, validate_candidate, validate_catalog, validate_freeze)


FREEZE = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())


def case(n, family, split='CONFIRMATION'):
    # Authored structural witness only; this text is never an evaluation item.
    question = f'What remains uncertain about the reported interaction {n}?'
    text = f'Witness {n} reported an interaction, then corrected its timing.'
    ordinary = dict(question=question, source_text=text)
    return dict(case_id=f'fixture-{n}', task_family=family, split=split,
        source_origin='INDEPENDENT_NON_HCL_AUTHOR',
        source_license_status='VERIFIED_FOR_THIS_EVALUATION',
        source_access_status='AUTHORIZED_FOR_EVERY_ARM', longmemeval='NOT_USED',
        writing_system_id=f'system-{n % 3}', author_id=f'author-{n}',
        template_id=f'template-{n}', source_group_id=f'source-{n}',
        question=question, source_text=text,
        arm_inputs={arm: ordinary.copy() for arm in ARMS},
        answer_fields=list(FIELDS))


class I01EvaluationContractTests(unittest.TestCase):
    def test_positive_freeze_and_four_family_composition(self):
        self.assertTrue(validate_freeze(FREEZE))
        self.assertEqual(FREEZE['hcl_runtime_sha256'], runtime_digest())
        self.assertTrue(validate_catalog(FREEZE,
            [case(i, family) for i, family in enumerate(FAMILIES)]))

    def test_authored_fixture_or_oracle_input_cannot_be_confirmation(self):
        item = case(0, FAMILIES[0])
        item['source_origin'] = 'HCL_AUTHORED_SYNTHETIC'
        with self.assertRaisesRegex(ValueError, 'development evidence'):
            validate_candidate(FREEZE, item)
        item['source_origin'] = 'INDEPENDENT_NON_HCL_AUTHOR'
        item['mental_state_labels'] = {'actor': 'oracle'}
        with self.assertRaisesRegex(ValueError, 'oracle state'):
            validate_candidate(FREEZE, item)

    def test_unfair_generic_arm_or_answer_vocabulary_is_rejected(self):
        item = case(0, FAMILIES[0])
        item['arm_inputs']['G']['source_text'] = 'shortened source'
        with self.assertRaisesRegex(ValueError, 'same question and source'):
            validate_candidate(FREEZE, item)
        item = case(0, FAMILIES[0])
        item['answer_fields'].append('hcl_private_state')
        with self.assertRaisesRegex(ValueError, 'identical non-HCL'):
            validate_candidate(FREEZE, item)

    def test_access_and_license_refusal(self):
        item = case(0, FAMILIES[0])
        item['source_access_status'] = 'H_ONLY'
        with self.assertRaisesRegex(ValueError, 'fair'):
            validate_candidate(FREEZE, item)
        item['source_access_status'] = 'AUTHORIZED_FOR_EVERY_ARM'
        item['source_license_status'] = 'UNKNOWN'
        with self.assertRaisesRegex(ValueError, 'rights'):
            validate_candidate(FREEZE, item)

    def test_source_family_and_writing_system_cannot_cross_splits(self):
        items = [case(i, family) for i, family in enumerate(FAMILIES)]
        items.append(case(4, FAMILIES[0], split='CALIBRATION'))
        with self.assertRaisesRegex(ValueError, 'writing_system_id crosses'):
            validate_catalog(FREEZE, items)
        items[-1]['writing_system_id'] = 'calibration-only-system'
        items[-1]['source_group_id'] = items[0]['source_group_id']
        with self.assertRaisesRegex(ValueError, 'source_group_id crosses'):
            validate_catalog(FREEZE, items)

    def test_freeze_cannot_silently_add_provider_spend_or_drop_family(self):
        changed = copy.deepcopy(FREEZE)
        changed['provider_calls'] = 1
        with self.assertRaisesRegex(ValueError, 'provider-free'):
            validate_freeze(changed)
        changed = copy.deepcopy(FREEZE)
        changed['task_families'].pop()
        with self.assertRaisesRegex(ValueError, 'four prespecified'):
            validate_freeze(changed)


if __name__ == '__main__':
    unittest.main()
