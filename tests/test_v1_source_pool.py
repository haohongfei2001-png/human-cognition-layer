"""Source-pool storage identity must never create shared epistemic access."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from hcl.v1 import (HCLCognitionLayer, prepare_composed_answer, expand_composed_sources,
    expand_cognition_context, pool_composed_sources, PerspectiveMode)
from tests.test_v1_composition import requests, QUERY
from tests.test_v1_source_access import preference, concept, P, D, HEAR, PROP, RAIN


def body(prepared):
    return json.loads(prepared.messages[1]['content'])['composed_cognition']


class ComposedSourcePoolTests(unittest.TestCase):
    def test_lossless_actual_three_operation_input_and_local_source_ids(self):
        layer = HCLCognitionLayer(lambda _: '')
        plain = prepare_composed_answer(layer, QUERY, requests())
        pooled = prepare_composed_answer(layer, QUERY, requests(), pool_sources=True)
        full, encoded = body(plain), body(pooled)
        self.assertEqual(expand_composed_sources(encoded), full)
        self.assertTrue(encoded['source_records'])
        for before, after in zip(full['operation_contexts'], encoded['operation_contexts']):
            self.assertEqual([e['event_id'] for e in before['cognition_context']['evidence']],
                             [e['event_id'] for e in after['cognition_context']['evidence']])
            self.assertEqual([e['source_id'] for e in before['cognition_context']['evidence']],
                             [e['source_id'] for e in after['cognition_context']['evidence']])
        self.assertLess(len(json.dumps(pooled.messages)), len(json.dumps(plain.messages)))
        self.assertEqual(pooled.preparation_receipt['actual_final_messages'], list(pooled.messages))

    def test_tighter_context_budget_carries_all_operations_without_selection(self):
        layer = HCLCognitionLayer(lambda _: '')
        encoded = body(prepare_composed_answer(layer, QUERY, requests(), pool_sources=True))
        bound = len(json.dumps(encoded, ensure_ascii=False, sort_keys=True))
        refused = prepare_composed_answer(layer, QUERY, requests(), max_context_chars=bound)
        useful = prepare_composed_answer(layer, QUERY, requests(), max_context_chars=bound, pool_sources=True)
        self.assertEqual(body(refused)['operation_contexts'], [])
        self.assertEqual(len(body(useful)['operation_contexts']), 3)
        decoded = expand_composed_sources(body(useful))
        for op in decoded['operation_contexts']:
            expanded = expand_cognition_context(op['cognition_context'])
            self.assertTrue(expanded[op['operation']]['checked'])

    def test_private_pool_contains_only_already_visible_records_and_links(self):
        text = '\n'.join((P, HEAR, D, HEAR, PROP))
        reqs = (preference(text, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE),
                concept(text, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        result = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, reqs, pool_sources=True)
        encoded = body(result)
        self.assertNotIn(PROP, result.messages[1]['content'])
        self.assertNotIn(HEAR, result.messages[1]['content'])
        for op in expand_composed_sources(encoded)['operation_contexts']:
            row = expand_cognition_context(op['cognition_context'])
            if op['operation'] == 'concepts':
                self.assertEqual(row['concepts']['checked']['readings'][0]['state'], 'CRITERIA_UNRESOLVED')

    def test_source_actor_time_and_record_time_differences_never_coalesce(self):
        state = body(prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests()))
        first, second = state['operation_contexts'][:2]
        for field in ('actor_id', 'valid_time', 'recorded_at'):
            changed = deepcopy(state)
            e = changed['operation_contexts'][1]['cognition_context']['evidence'][0]
            e[field] = 'different-scoped-source'
            pooled = pool_composed_sources(changed)
            self.assertEqual(expand_composed_sources(pooled), changed)
            self.assertNotIn('source_record_ref', pooled['operation_contexts'][1]['cognition_context']['evidence'][0])

    def test_missing_reference_and_template_drift_fail_instead_of_inventing_source(self):
        encoded = body(prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests(), pool_sources=True))
        bad = deepcopy(encoded)
        bad['source_records'].pop(next(iter(bad['source_records'])))
        with self.assertRaises(ValueError):
            expand_composed_sources(bad)
        bad = deepcopy(encoded)
        next(iter(bad['source_records'].values()))['raw_text'] = 'invented source'
        with self.assertRaises(ValueError):
            expand_composed_sources(bad)

    def test_no_duplication_keeps_literal_state_and_does_not_mutate_input(self):
        state = body(prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests()))
        original = deepcopy(state)
        for op in state['operation_contexts']:
            op['cognition_context']['evidence'] = []
        before = deepcopy(state)
        self.assertEqual(pool_composed_sources(state), before)
        self.assertEqual(state, before)
        self.assertEqual(expand_composed_sources(original), original)

    def test_whole_budget_refusal_has_no_partial_pool_or_hidden_residue(self):
        p = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests(), pool_sources=True, max_context_chars=512)
        self.assertEqual(body(p)['operation_contexts'], [])
        self.assertNotIn('source_records', body(p))
        with self.assertRaises(ValueError):
            prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests(), pool_sources=1)
