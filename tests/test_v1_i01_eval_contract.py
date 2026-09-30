"""I01 guard prevents contaminated or unfair evaluation before provider calls."""
import copy
import json
import unittest
from pathlib import Path

from scripts.serious_eval_contract import (ARMS, FAMILIES, FIELDS,
    runtime_digest, validate_candidate, validate_catalog, validate_freeze,
    validate_runtime_amendment, validate_runtime_amendment_v2)
from scripts.i02_runtime_amendment_v3 import validate_runtime_amendment_v3
from scripts.i02_runtime_amendment_v4 import validate_runtime_amendment_v4
from scripts.i02_runtime_amendment_v5 import validate_runtime_amendment_v5


FREEZE = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
AMENDMENT = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT.json').read_text())
AMENDMENT_V2 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V2.json').read_text())
AMENDMENT_V3 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V3.json').read_text())
AMENDMENT_V4 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V4.json').read_text())
AMENDMENT_V5 = json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V5.json').read_text())


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
        self.assertTrue(validate_runtime_amendment(FREEZE, AMENDMENT,
            current_digest=AMENDMENT['amended_hcl_runtime_sha256']))
        self.assertTrue(validate_runtime_amendment_v2(FREEZE, AMENDMENT, AMENDMENT_V2,
            current_digest=AMENDMENT_V2['amended_hcl_runtime_sha256']))
        self.assertTrue(validate_runtime_amendment_v3(FREEZE, AMENDMENT,
            AMENDMENT_V2, AMENDMENT_V3,
            current_digest=AMENDMENT_V3['amended_hcl_runtime_sha256']))
        self.assertTrue(validate_runtime_amendment_v4(FREEZE, AMENDMENT,
            AMENDMENT_V2, AMENDMENT_V3, AMENDMENT_V4,
            current_digest=AMENDMENT_V4['amended_hcl_runtime_sha256']))
        self.assertTrue(validate_runtime_amendment_v5(FREEZE, AMENDMENT,
            AMENDMENT_V2, AMENDMENT_V3, AMENDMENT_V4, AMENDMENT_V5,
            current_digest=AMENDMENT_V5['amended_hcl_runtime_sha256']))
        self.assertNotEqual(FREEZE['hcl_runtime_sha256'], runtime_digest())
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

    def test_runtime_amendment_cannot_hide_another_runtime_change(self):
        changed = copy.deepcopy(AMENDMENT)
        changed['amended_hcl_runtime_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'disclosed I02 amendment'):
            validate_runtime_amendment(FREEZE, changed,
                current_digest=AMENDMENT['amended_hcl_runtime_sha256'])
        changed = copy.deepcopy(AMENDMENT)
        changed['confirmation_items_inspected'] = 1
        with self.assertRaisesRegex(ValueError, 'invalid I02 runtime amendment'):
            validate_runtime_amendment(FREEZE, changed,
                current_digest=AMENDMENT['amended_hcl_runtime_sha256'])
        changed = copy.deepcopy(AMENDMENT_V2)
        changed['previous_hcl_runtime_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'invalid I02 v2'):
            validate_runtime_amendment_v2(FREEZE, AMENDMENT, changed)
        changed = copy.deepcopy(AMENDMENT_V3)
        changed['specialized_cognition_treatment_claimed'] = True
        with self.assertRaisesRegex(ValueError, 'invalid I02 v3'):
            validate_runtime_amendment_v3(FREEZE, AMENDMENT, AMENDMENT_V2, changed,
                current_digest=AMENDMENT_V3['amended_hcl_runtime_sha256'])
        changed = copy.deepcopy(AMENDMENT_V3)
        changed['amended_hcl_runtime_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'disclosed I02 v3'):
            validate_runtime_amendment_v3(FREEZE, AMENDMENT, AMENDMENT_V2, changed,
                current_digest=AMENDMENT_V3['amended_hcl_runtime_sha256'])
        changed = copy.deepcopy(AMENDMENT_V4)
        changed['provider_calls'] = 1
        with self.assertRaisesRegex(ValueError, 'invalid I02 v4'):
            validate_runtime_amendment_v4(FREEZE, AMENDMENT, AMENDMENT_V2,
                AMENDMENT_V3, changed, current_digest=AMENDMENT_V4['amended_hcl_runtime_sha256'])
        changed = copy.deepcopy(AMENDMENT_V5)
        changed['confirmation_items_inspected'] = 1
        with self.assertRaisesRegex(ValueError, 'invalid I02 v5'):
            validate_runtime_amendment_v5(FREEZE, AMENDMENT, AMENDMENT_V2,
                AMENDMENT_V3, AMENDMENT_V4, changed)


if __name__ == '__main__':
    unittest.main()
