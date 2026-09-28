"""Lossless per-stage audit encoding is not aggregate cost or shared access."""
from copy import deepcopy
import json
import unittest
from hcl.v1 import (HCLCognitionLayer, prepare_composed_answer, expand_composed_sources,
    pool_composed_sources, PerspectiveMode)
from hcl.v1.context import NARRATIVE_ACCESS_POLICY
from hcl.v1.source_pool import ENCODING, ENCODING_WITH_PREPARATION
from tests.test_v1_composition import requests, QUERY
from tests.test_v1_source_access import preference, concept, P, D, HEAR, PROP


def body(p):
    return json.loads(p.messages[-1]['content'])['composed_cognition']


class SharedPreparationTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def test_actual_input_round_trip_and_per_stage_zero_counts_not_aggregate(self):
        old = prepare_composed_answer(self.layer, QUERY, requests(), pool_sources=True, pool_preparation=False)
        new = prepare_composed_answer(self.layer, QUERY, requests(), pool_sources=True)
        self.assertEqual(body(old)['source_pool_encoding'], ENCODING)
        self.assertEqual(body(new)['source_pool_encoding'], ENCODING_WITH_PREPARATION)
        self.assertEqual(expand_composed_sources(body(new)), expand_composed_sources(body(old)))
        for op in expand_composed_sources(body(new))['operation_contexts']:
            self.assertEqual(op['cognition_context']['preparation']['answer_provider_calls'], 0)
            self.assertEqual(op['cognition_context']['preparation']['extraction_provider_calls'], 0)
        self.assertEqual(new.preparation_receipt['answer_provider_calls'], 1)
        self.assertLess(len(json.dumps(new.messages)), len(json.dumps(old.messages)))

    def test_failure_method_time_and_local_validator_metadata_stay_literal(self):
        state = body(prepare_composed_answer(self.layer, QUERY, requests()))
        before = deepcopy(state)
        prep = state['operation_contexts'][0]['cognition_context']['preparation']
        prep.update(failure='source_failure', local_validator_calls=2, private_marker='unchanged')
        encoded = pool_composed_sources(state)
        self.assertEqual(expand_composed_sources(encoded), state)
        row = encoded['operation_contexts'][0]['cognition_context']['preparation']
        self.assertEqual(row['failure'], 'source_failure')
        self.assertEqual(row['local_validator_calls'], 2)
        self.assertEqual(row['private_marker'], 'unchanged')
        self.assertEqual(before['operation_contexts'][0]['cognition_context']['preparation']['failure'], None)

    def test_nonzero_missing_or_float_counter_never_replaced_by_zero_defaults(self):
        for mutate in ('nonzero', 'missing', 'float'):
            state = body(prepare_composed_answer(self.layer, QUERY, requests()))
            prep = state['operation_contexts'][0]['cognition_context']['preparation']
            if mutate == 'nonzero':
                prep['extraction_provider_calls'] = 1
            elif mutate == 'missing':
                del prep['extraction_provider_calls']
            else:
                prep['extraction_spend_usd'] = 0.0
            encoded = pool_composed_sources(state)
            self.assertNotIn('preparation_defaults', encoded['operation_contexts'][0]['cognition_context'])
            self.assertEqual(json.dumps(expand_composed_sources(encoded), sort_keys=True), json.dumps(state, sort_keys=True))

    def test_invalid_marker_duplicate_fields_and_old_version_mismatch_fail(self):
        good = body(prepare_composed_answer(self.layer, QUERY, requests(), pool_sources=True))
        for marker in (False, None, 1):
            bad = deepcopy(good)
            bad['operation_contexts'][0]['cognition_context']['preparation_defaults'] = marker
            with self.assertRaises(ValueError):
                expand_composed_sources(bad)
        bad = deepcopy(good)
        bad['operation_contexts'][0]['cognition_context']['preparation']['answer_provider_calls'] = 1
        with self.assertRaises(ValueError):
            expand_composed_sources(bad)
        bad = deepcopy(good)
        bad['source_pool_encoding'] = ENCODING
        with self.assertRaises(ValueError):
            expand_composed_sources(bad)
        bad = deepcopy(good)
        del bad['source_pool_encoding']
        with self.assertRaises(ValueError):
            expand_composed_sources(bad)

    def test_tighter_budget_keeps_all_operations_and_unchanged_checked_state(self):
        new = prepare_composed_answer(self.layer, QUERY, requests(), pool_sources=True)
        bound = len(json.dumps(body(new), ensure_ascii=False, sort_keys=True))
        old = prepare_composed_answer(self.layer, QUERY, requests(), pool_sources=True,
            pool_preparation=False, max_context_chars=bound)
        useful = prepare_composed_answer(self.layer, QUERY, requests(), pool_sources=True, max_context_chars=bound)
        self.assertFalse(body(old)['operation_contexts'])
        self.assertEqual(len(body(useful)['operation_contexts']), 3)
        self.assertEqual(expand_composed_sources(body(useful)), expand_composed_sources(body(new)))

    def test_shared_access_policy_once_and_no_private_source_promotion(self):
        text = '\n'.join((P, HEAR, D, HEAR, PROP))
        reqs = (preference(text, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE),
                concept(text, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        p = prepare_composed_answer(self.layer, QUERY, reqs, pool_sources=True)
        self.assertEqual(p.messages[0]['content'].count(NARRATIVE_ACCESS_POLICY), 1)
        self.assertNotIn(PROP, p.messages[-1]['content'])
        decoded = expand_composed_sources(body(p))
        self.assertTrue(all(op['cognition_context']['preparation']['source_access_status'] ==
            'EXPLICIT_REPORTED_EXPOSURE_CHECKED' for op in decoded['operation_contexts']))

    def test_literal_unique_state_and_encoding_flag_bounds(self):
        state = body(prepare_composed_answer(self.layer, QUERY, requests()))
        for op in state['operation_contexts']:
            op['cognition_context']['evidence'] = []
        self.assertEqual(pool_composed_sources(state), state)
        with self.assertRaises(ValueError):
            pool_composed_sources(state, preparation_defaults=1)
        with self.assertRaises(ValueError):
            prepare_composed_answer(self.layer, QUERY, requests(), pool_preparation=1)
