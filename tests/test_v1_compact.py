"""Lossless context transport, retained factor semantics and budget usefulness."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from hcl.v1 import (CognitionRequest, HCLCognitionLayer, PerspectiveMode,
    compact_cognition_context, expand_cognition_context)
from scripts.cg03_external_package import CASES as R_CASES, _premise, _question
from scripts.cg04_external_package import CASES as P_CASES, _TASK as P_TASK
from scripts.cg05_external_package import CASES as C_CASES, _TASK as C_TASK
from tests.test_v1_cg05 import D, T, REV, prep


def responsibility(case):
    return CognitionRequest(_question(case), target_actor=case['target'], narrative=case['narrative'],
        responsibility_analysis=True, responsibility_premises=(_premise(case),))


def requests():
    yield from (responsibility(c) for c in R_CASES)
    yield from (CognitionRequest(P_TASK, target_actor='Alice', narrative=n,
        preference_analysis=True, preference_role='medic', preference_context='fieldwork') for _, n, _ in P_CASES)
    yield from (CognitionRequest(C_TASK, target_actor='Alice', narrative=n,
        concept_analysis=True, concept_context='team', concept_term='fair', concept_item='proposal') for _, n, _ in C_CASES)


def serialized(row):
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


class CompactContextTests(unittest.TestCase):
    def test_all_three_capabilities_lossless_including_retained_factor_distinctions(self):
        for req in requests():
            with self.subTest(query=req.query[:35]):
                prepared = HCLCognitionLayer(lambda _: '').prepare(req)
                source = prepared.context.as_dict()
                compact = compact_cognition_context(source)
                self.assertEqual(expand_cognition_context(compact), source)
                self.assertLess(len(serialized(compact)), len(serialized(source)))
                self.assertEqual(prepared.context.as_dict(), source)  # no mutation

    def test_actual_model_input_round_trip_and_total_message_bytes(self):
        total_full = total_compact = 0
        calls = []
        for req in requests():
            full = HCLCognitionLayer(lambda _: '').prepare(req)
            receipt = HCLCognitionLayer(lambda messages: calls.append(messages) or 'bounded').answer(
                replace(req, compact_context=True), debug=True)
            p = receipt.prepared
            raw = json.loads(p.messages[-1]['content'])['cognition_context']
            self.assertEqual(expand_cognition_context(raw), json.loads(serialized(full.context.as_dict())))
            self.assertEqual(p.context.as_dict(), full.context.as_dict())
            self.assertEqual(p.preparation_receipt, full.preparation_receipt)
            self.assertEqual(calls[-1], list(p.messages))
            total_full += len(serialized(list(full.messages)).encode())
            total_compact += len(serialized(list(p.messages)).encode())
        self.assertEqual(len(calls), 12)
        self.assertLess(total_compact, total_full)  # includes codec policy overhead

    def test_same_context_budget_previously_refused_now_retains_checked_readings(self):
        req = list(requests())[-2]
        full = HCLCognitionLayer(lambda _: '').prepare(req).context.as_dict()
        limit = len(serialized(compact_cognition_context(full)))
        self.assertGreater(len(serialized(full)), limit)
        refused = HCLCognitionLayer(lambda _: '').prepare(replace(req, max_context_chars=limit))
        useful = HCLCognitionLayer(lambda _: '').prepare(replace(req, max_context_chars=limit, compact_context=True))
        self.assertFalse(refused.context.concepts)
        self.assertTrue(useful.context.concepts['checked']['readings'])
        self.assertEqual(expand_cognition_context(json.loads(useful.messages[1]['content'])['cognition_context']), json.loads(serialized(full)))

    def test_hidden_sources_and_hidden_revision_pointer_not_resurrected(self):
        p = prep(D + '\n' + T + '\n' + REV)
        evidence = (p.events[0], p.events[1], replace(p.events[2], metadata={'public': True}))
        req = CognitionRequest('Local concept', evidence=evidence, target_actor='Alice', concept_case=p.case,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE, compact_context=True)
        result = HCLCognitionLayer(lambda _: '').prepare(req)
        text = result.messages[1]['content']
        self.assertNotIn('def-1', text)
        self.assertNotIn(p.events[0].event_id, text)
        self.assertNotIn(p.events[1].event_id, text)
        expanded = expand_cognition_context(json.loads(text)['cognition_context'])
        self.assertIsNone(expanded['concepts']['case_input']['definitions'][0]['supersedes_id'])

    def test_redacted_and_unmatched_quotes_remain_literal(self):
        p = HCLCognitionLayer(lambda _: '').prepare(list(requests())[-1])
        row = p.context.as_dict()
        definition = row['concepts']['case_input']['definitions'][0]
        definition['quote'] = 'source redaction retained exactly'
        small = compact_cognition_context(row)
        self.assertEqual(small['concepts']['case_input']['definitions'][0]['quote'], definition['quote'])
        self.assertEqual(expand_cognition_context(small), row)

    def test_missing_reference_is_an_error_not_invented_evidence(self):
        row = HCLCognitionLayer(lambda _: '').prepare(list(requests())[-1]).context.as_dict()
        small = compact_cognition_context(row)
        bad = deepcopy(small)
        bad['evidence'] = []
        with self.assertRaises(ValueError):
            expand_cognition_context(bad)
        bad = deepcopy(small)
        bad['concepts']['checked']['readings'][0]['definition_id'] = 'invisible-definition'
        with self.assertRaises(ValueError):
            expand_cognition_context(bad)

    def test_unrelated_direct_task_no_encoding_or_extra_calls(self):
        p = HCLCognitionLayer(lambda _: '').prepare(CognitionRequest('Translate hello', compact_context=True))
        self.assertTrue(p.plan.direct)
        self.assertIsNone(p.context)
        self.assertEqual(len(p.messages), 1)
        self.assertNotIn('hcl-source-reference', p.messages[0]['content'])
        with self.assertRaises(ValueError):
            CognitionRequest('Hello', compact_context=1)

    def test_budget_still_fails_closed_without_truncating_a_source(self):
        p = HCLCognitionLayer(lambda _: '').prepare(replace(list(requests())[-1],
            compact_context=True, max_context_chars=512))
        self.assertFalse(p.context.concepts)
        self.assertNotIn('Alice: In team', p.messages[1]['content'])
        self.assertEqual(expand_cognition_context(json.loads(p.messages[1]['content'])['cognition_context']),
                         p.context.as_dict())
