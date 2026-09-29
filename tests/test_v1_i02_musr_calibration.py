"""Native-source grouping and calibration gold firewall, without network calls."""
import csv
import hashlib
import io
import json
import unittest
from unittest.mock import patch
from pathlib import Path

from scripts import i02_musr_calibration as musr
from scripts.serious_eval_contract import validate_candidate


def fake_csv():
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=[
        'narrative', 'question', 'choices', 'answer_index', 'answer_choice'])
    writer.writeheader()
    for group in range(64):
        for q in range(4):
            writer.writerow(dict(narrative=f'Actor {group} moved a note in plain view.',
                question=f'Where would actor {group} look for the note, question {q}?',
                choices='["table", "shelf"]', answer_index='0', answer_choice='table'))
    return out.getvalue().encode()


class MuSRCalibrationTests(unittest.TestCase):
    def test_four_questions_are_one_source_group_not_four_samples(self):
        raw = fake_csv()
        with patch.object(musr, 'SOURCE_SHA256', hashlib.sha256(raw).hexdigest()):
            rows, groups = musr.parse_pinned(raw)
        self.assertEqual(len(rows), 256)
        self.assertEqual(len(groups), 64)
        self.assertEqual(set(map(len, groups.values())), {4})

    def test_wrong_source_bytes_or_cluster_shape_fail(self):
        raw = fake_csv()
        with self.assertRaisesRegex(ValueError, 'pinned distribution'):
            musr.parse_pinned(raw)
        changed = raw.replace(b'Actor 0 moved', b'Actor 1 moved')
        with patch.object(musr, 'SOURCE_SHA256', hashlib.sha256(changed).hexdigest()):
            with self.assertRaisesRegex(ValueError, '64 four-question'):
                musr.parse_pinned(changed)

    def test_calibration_input_excludes_gold_and_preserves_native_choices(self):
        row = dict(narrative='Mira saw the note on the producer desk.',
            question='Where would Mira look?',
            choices='["piano", "producer\'s desk"]',
            answer_index='1', answer_choice="producer's desk")
        group = hashlib.sha256(row['narrative'].encode()).hexdigest()
        with patch.object(musr, 'FIRST_GROUP_SHA256', group):
            case = musr.calibration_candidate(row, source_group_id=group)
            with self.assertRaisesRegex(ValueError, 'only the inspected'):
                musr.calibration_candidate(row, source_group_id='wrong')
        self.assertTrue(validate_candidate(json.loads(Path(
            'reports/HCL_I01_EVALUATION_FREEZE.json').read_text()), case))
        self.assertEqual(case['split'], 'CALIBRATION')
        self.assertNotIn('answer_index', json.dumps(case))
        self.assertNotIn('answer_choice', json.dumps(case))
        self.assertIn("producer's desk", case['question'])


if __name__ == '__main__':
    unittest.main()
