import json
import unittest
from decimal import Decimal
from scripts.development_mindgames_protocol import prepare_case, request, reserve, score, build_protocol, MAX_REQUEST_BYTES, PROPOSED_CAP, RATES, OUTPUT_TOKENS, MARGIN

class MindGamesProtocolTests(unittest.TestCase):
    def test_complete_input_no_metadata_no_extraction(self):
        ordinary = dict(premise='Eva said, “I believe the gate is clear.”', hypothesis='Does Eva publicly express that the gate is clear?')
        arms, receipt = prepare_case(ordinary)
        self.assertEqual(receipt['extraction_calls'], 0)
        self.assertFalse(receipt['allow_translation'])
        self.assertTrue(receipt['checked_treatment_present'])
        self.assertEqual(arms['Base']['model'], arms['HCL']['model'])
        for arm in arms.values():
            self.assertGreater(Decimal(reserve(arm)['reservation_usd']), 0)
        with self.assertRaises(ValueError): prepare_case(dict(ordinary, native_label='entailment'))

    def test_budget_ceiling_and_overflow(self):
        ceiling = 12 * ((2*MAX_REQUEST_BYTES+2048)*Decimal(RATES['input']) + (OUTPUT_TOKENS+MARGIN)*Decimal(RATES['output'])) / 1000000
        self.assertEqual(ceiling, Decimal('1.5637248'))
        self.assertLess(ceiling, Decimal(PROPOSED_CAP))
        with self.assertRaises(ValueError): reserve(request([dict(role='user', content='x'*MAX_REQUEST_BYTES)]))

    def test_exact_label_scorer_and_invalid_output(self):
        arms, _ = prepare_case(dict(premise='Eva saw the red card.', hypothesis='Eva saw the red card.'))
        obj = dict(answer='entailment', source_citations=[], uncertainty='', assumptions='')
        def raw(v, finish='stop'):
            return dict(choices=[dict(finish_reason=finish, message=dict(content=json.dumps(v)))])
        self.assertTrue(score(raw(obj), 'entailment', arms['Base']['messages'])['native_correct'])
        self.assertFalse(score(raw(obj), 'not_entailment', arms['Base']['messages'])['native_correct'])
        for value in [dict(obj,answer='ENTAILMENT'), dict(obj,extra='x'), dict(obj,uncertainty=[]), []]:
            self.assertFalse(score(raw(value),'entailment',arms['Base']['messages'])['format_valid'])
        self.assertFalse(score(raw(obj,'length'),'entailment',arms['Base']['messages'])['native_correct'])
        self.assertFalse(score({},'entailment',arms['Base']['messages'])['native_correct'])

    def test_native_identity_drift_rejected(self):
        with self.assertRaises(ValueError): build_protocol([])
        rows=[dict(index=i,premise='synthetic',hypothesis='synthetic',label='entailment') for i in [3274,41454,41671,54915,65380,1556]]
        with self.assertRaisesRegex(ValueError,'reviewed source'): build_protocol(rows)

if __name__ == '__main__': unittest.main()
