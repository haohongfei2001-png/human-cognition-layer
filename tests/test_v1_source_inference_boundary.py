"""Authored delivery contrasts only; stubs never count as semantic validation."""
import json
import unittest

from hcl.cognition import ClaimKind, CognitionWorkspace
from hcl.cognition.reader_entry import _SOURCE_INFERENCE_POLICY
from tests.test_v1_conditional_reader_entry import Backend, SOURCE, proposals

QUERY = 'Explain what the source supports and which interpretations remain open.'
CONTRASTS = (
    'Lena moved a crate. The lamp broke.',
    'Lena said, "I intended to break the lamp." Lena moved a crate. The lamp broke.',
    'Omar said, "Lena intended to break the lamp." Lena moved a crate. The lamp broke.',
    'Lena denied intending to break the lamp. Later, Omar learned that the lamp broke.',
)
CHECKED = ('Lena believes the corridor is clear. '
           'Lena said, "I do not believe the corridor is clear." '
           'Lena said, "I plan to carry the crate in order to clear the room if the corridor is clear."')


def workspace(source):
    result = CognitionWorkspace()
    result.put_source('scene', source)
    return result


class NoExtraction:
    def complete_json(self, *args, **kwargs):
        raise AssertionError('unexpected provider extraction')


class SourceInferenceBoundaryTests(unittest.TestCase):
    def test_authored_action_self_report_third_party_and_time_contrasts_stay_distinct(self):
        wires = []
        for source in CONTRASTS:
            with self.subTest(source=source):
                w = workspace(source)
                p = w.prepare_reader_entry(QUERY, source_ids=('scene',), backend=NoExtraction())
                payload = json.loads(p.messages[-1]['content'])
                self.assertEqual(payload['sources'], [dict(source_id='scene', version=1, text=source)])
                self.assertEqual(payload['query'], QUERY)
                self.assertIn(_SOURCE_INFERENCE_POLICY, p.messages[0]['content'])
                self.assertFalse(p.receipt['private_state_established'])
                self.assertFalse(p.receipt['semantic_certification'])
                self.assertEqual(p.receipt['extraction_calls'], 0)
                wires.append(p.messages[-1])
        self.assertEqual(len({json.dumps(w) for w in wires}), 4)

    def test_contract_preserves_reports_without_inventing_or_suppressing_psychology(self):
        p = workspace(CONTRASTS[1]).prepare_reader_entry(QUERY, source_ids=('scene',))
        policy = p.messages[0]['content']
        for clause in ('explicit source report from interpretation',
                       'actor, speaker, negation, qualification and time',
                       'without erasing it or promoting it to private truth',
                       'stable traits, inborn nature or hidden motives',
                       'state its missing premise', 'alternatives unresolved',
                       'action-time knowledge, foreseeability, control and stated intention',
                       'correct abstract lesson does not certify an explanation'):
            self.assertIn(clause, policy)

    def test_checked_b01_c01_c03_state_and_source_are_unchanged(self):
        w = workspace(CHECKED)
        p = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        self.assertTrue(p.receipt['checked_treatment_present'])
        self.assertEqual(p.messages[1:], p.prepared.messages[1:])
        payload = json.loads(p.messages[-1]['content'])
        self.assertTrue(payload['checked_epistemic']['comparisons'])
        self.assertTrue(payload['checked_agency'])
        self.assertTrue(payload['checked_plan_feasibility'])
        self.assertEqual(p.messages[0]['content'], p.prepared.messages[0]['content'] + ' ' + _SOURCE_INFERENCE_POLICY)

    def test_checked_reported_receipt_state_is_unchanged_and_not_knowledge(self):
        source = 'Lena said, "I believe the corridor is clear." Omar heard Lena\'s last statement.'
        p = workspace(source).prepare_reader_entry(QUERY, source_ids=('scene',))
        payload = json.loads(p.messages[-1]['content'])
        self.assertTrue(payload['checked_reported_communication']['views'])
        self.assertEqual(p.messages[1:], p.prepared.messages[1:])
        self.assertFalse(p.receipt['local_preparation']['communication_treatment']['knowledge_established'])
        self.assertIn(_SOURCE_INFERENCE_POLICY, p.messages[0]['content'])

    def test_optional_translation_receives_same_boundary_without_promoting_assumptions(self):
        w = workspace(SOURCE)
        rows = proposals()
        for row in rows:
            row['source_id'] = 'scene'
        b = Backend(rows)
        p = w.prepare_reader_entry(QUERY, source_ids=('scene',), backend=b, allow_translation=True)
        self.assertEqual(p.receipt['selection'], 'CONDITIONAL_TRANSLATION')
        self.assertEqual(len(b.calls), 1)
        self.assertIn(_SOURCE_INFERENCE_POLICY, p.messages[0]['content'])
        self.assertTrue(json.loads(p.messages[-1]['content'])['shared_semantic_binding']['assumptions'])
        self.assertEqual(p.messages[1:], p.prepared.messages[1:])
        self.assertFalse(p.receipt['answer_inference_boundary']['semantic_certification'])

    def test_unusable_translation_fallback_keeps_boundary_and_whole_source(self):
        w = workspace(SOURCE)
        p = w.prepare_reader_entry(QUERY, source_ids=('scene',), backend=Backend([]), allow_translation=True)
        self.assertEqual(p.receipt['selection'], 'COMPLETE_SOURCE_AFTER_UNUSABLE_TRANSLATION')
        self.assertIn(_SOURCE_INFERENCE_POLICY, p.messages[0]['content'])
        self.assertEqual(json.loads(p.messages[-1]['content'])['sources'][0]['text'], SOURCE)

    def test_wire_receipt_and_context_overhead_are_exact_without_token_savings_claim(self):
        w = workspace(CONTRASTS[0])
        p = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        boundary = p.receipt['answer_inference_boundary']
        self.assertEqual(boundary['status'], 'DELIVERY_INSTRUCTION_NOT_SEMANTIC_CHECK')
        delta = len(json.dumps(p.messages, ensure_ascii=False)) - len(json.dumps(p.prepared.messages, ensure_ascii=False))
        self.assertEqual(boundary['additional_context_characters'], delta)
        self.assertGreater(delta, 0)
        self.assertEqual(p.receipt['actual_final_messages'], p.messages)
        self.assertEqual(p.current_messages(w), p.messages)
        self.assertFalse(boundary['answer_gain_established'])

    def test_policy_budget_rejected_before_optional_extraction(self):
        w = workspace(CONTRASTS[0])
        p = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        budget = len(json.dumps(p.messages, ensure_ascii=False)) - 1
        self.assertGreater(budget, len(json.dumps(p.prepared.messages, ensure_ascii=False)))
        with self.assertRaisesRegex(ValueError, 'source-inference contract exceeds'):
            w.prepare_reader_entry(QUERY, source_ids=('scene',), backend=NoExtraction(), allow_translation=True, max_chars=budget)

    def test_final_json_contract_budget_is_checked_before_answer_call(self):
        w = workspace(CONTRASTS[0])
        entry = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        budget = len(json.dumps(entry.messages, ensure_ascii=False))
        calls = []
        with self.assertRaisesRegex(ValueError, 'context budget'):
            w.answer_reader_entry(QUERY, lambda m: calls.append(m), source_ids=('scene',), max_chars=budget)
        self.assertFalse(calls)

    def test_known_final_instruction_is_reserved_before_opted_in_extraction(self):
        w = workspace(SOURCE)
        entry = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        budget = len(json.dumps(entry.messages, ensure_ascii=False))
        rows = proposals()
        for row in rows:
            row['source_id'] = 'scene'
        backend = Backend(rows)
        calls = []
        with self.assertRaisesRegex(ValueError, 'context budget'):
            w.answer_reader_entry(QUERY, lambda m: calls.append(m), source_ids=('scene',),
                backend=backend, allow_translation=True, max_chars=budget)
        self.assertFalse(backend.calls)
        self.assertFalse(calls)

    def test_final_budget_exact_fit_and_one_character_short_preserve_wire(self):
        # Unicode, escaping and the separating comma all use the same JSON
        # serialization as the real final wire, not a token/byte estimate.
        for source in (CONTRASTS[0], '风 moved a curtain. A cabinet remained shut.\n', CHECKED):
            with self.subTest(source=source):
                w = workspace(source)
                raw = json.dumps(dict(answer='Source report only.',
                    source_citations=[dict(source_id='scene', version=1, quote=source)],
                    uncertainty='Private state unverified.', assumptions='No additional facts.'))
                result = w.answer_reader_entry(QUERY, lambda _: raw, source_ids=('scene',), backend=NoExtraction())
                messages = result['actual_final_messages']
                budget = len(json.dumps(messages, ensure_ascii=False))
                calls = []
                exact = w.answer_reader_entry(QUERY, lambda m: calls.append(m) or raw,
                    source_ids=('scene',), backend=NoExtraction(), max_chars=budget)
                self.assertEqual(calls, [messages])
                self.assertEqual(exact['answer_raw'], raw)
                self.assertEqual(exact['preparation_provider_calls'], 0)
                receipt = exact['answer_context_budget']
                self.assertEqual(receipt['actual_message_characters'], budget)
                self.assertEqual(receipt['prepared_message_budget_characters'],
                    len(json.dumps(exact['prepared'].messages, ensure_ascii=False)))
                self.assertEqual(receipt['reserved_final_instruction_characters'],
                    budget - receipt['prepared_message_budget_characters'])
                with self.assertRaises(ValueError):
                    w.answer_reader_entry(QUERY, lambda m: calls.append(m), source_ids=('scene',),
                        backend=NoExtraction(), allow_translation=True, max_chars=budget - 1)
                self.assertEqual(len(calls), 1)

    def test_sufficient_final_budget_preserves_opt_in_translation_and_fallback(self):
        for translated in (False, True):
            with self.subTest(translated=translated):
                rows = proposals() if translated else []
                for row in rows:
                    row['source_id'] = 'scene'
                backend = Backend(rows)
                calls = []
                raw = json.dumps(dict(answer='Conditional source report only.',
                    source_citations=[dict(source_id='scene', version=1, quote=SOURCE)],
                    uncertainty='Translation remains unverified.', assumptions='No private state.'))
                result = workspace(SOURCE).answer_reader_entry(QUERY, lambda m: calls.append(m) or raw,
                    source_ids=('scene',), backend=backend, allow_translation=True)
                self.assertEqual(len(backend.calls), 1)
                self.assertEqual(len(calls), 1)
                self.assertEqual(result['preparation_provider_calls'], 1)
                self.assertEqual(result['answer_raw'], raw)
                self.assertEqual(result['prepared'].receipt['selection'],
                    'CONDITIONAL_TRANSLATION' if translated else 'COMPLETE_SOURCE_AFTER_UNUSABLE_TRANSLATION')
                self.assertLessEqual(result['answer_context_budget']['actual_message_characters'], 64000)
                self.assertFalse(result['prepared'].receipt['semantic_certification'])

    def test_reservation_preserves_larger_unexecuted_intermediate_capacity(self):
        source = 'Lena wrote "灯".\nThe crate stayed shut.'
        w = workspace(source)
        prepared = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        intermediate = json.loads(prepared.prepared.preparation_json)['actual_final_messages']
        budget = len(json.dumps(intermediate, ensure_ascii=False))
        raw = json.dumps(dict(answer='Source report only.',
            source_citations=[dict(source_id='scene', version=1, quote=source)],
            uncertainty='No mental state established.', assumptions='No invented motive.'))
        baseline = w.answer_reader_entry(QUERY, lambda _: raw, source_ids=('scene',))
        self.assertGreater(budget, len(json.dumps(baseline['actual_final_messages'], ensure_ascii=False)))
        calls = []
        result = w.answer_reader_entry(QUERY, lambda m: calls.append(m) or raw,
            source_ids=('scene',), backend=NoExtraction(), max_chars=budget)
        self.assertEqual(calls, [baseline['actual_final_messages']])
        self.assertEqual(result['preparation_provider_calls'], 0)
        receipt = result['answer_context_budget']
        self.assertEqual(receipt['intermediate_preparation_limit_characters'], budget)
        self.assertLess(receipt['prepared_message_budget_characters'], budget)
        self.assertLessEqual(receipt['actual_message_characters'], budget)

    def test_invalid_or_too_small_final_budgets_never_extract(self):
        for budget in (True, None, '64000', 511, 512, 64001):
            with self.subTest(budget=budget):
                calls = []
                with self.assertRaises(ValueError):
                    workspace(SOURCE).answer_reader_entry(QUERY, lambda m: calls.append(m),
                        source_ids=('scene',), backend=NoExtraction(),
                        allow_translation=True, max_chars=budget)
                self.assertFalse(calls)

    def test_v25_amendment_rejects_runtime_drift(self):
        from scripts.development_runtime_amendment_v25 import validate_current
        self.assertTrue(validate_current())
        with self.assertRaises(ValueError):
            validate_current(current_digest='0' * 64)

    def test_repeated_prepare_does_not_append_twice_or_mutate_cached_wire(self):
        w = workspace(CONTRASTS[0])
        first = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        cached = first.prepared.messages
        second = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        self.assertEqual(first.messages, second.messages)
        self.assertEqual(first.prepared.messages, cached)
        self.assertEqual(second.messages[0]['content'].count(_SOURCE_INFERENCE_POLICY), 1)
        mutated = second.messages
        mutated[0]['content'] = 'replacement'
        self.assertEqual(first.messages, second.messages)

    def test_revision_removal_and_inner_challenge_still_block_delivery(self):
        for kind in ('revision', 'removal', 'challenge'):
            with self.subTest(kind=kind):
                w = workspace(CHECKED)
                p = w.prepare_reader_entry(QUERY, source_ids=('scene',))
                if kind == 'revision':
                    w.put_source('scene', CHECKED + ' Lena left.')
                elif kind == 'removal':
                    w.remove_source('scene')
                else:
                    target = json.loads(p.messages[-1]['content'])['checked_epistemic']['comparisons'][0]['claim_id']
                    source_claim = w.core.claims[target]
                    challenge = w.core.claim(source_claim.scope, ClaimKind.SYSTEM_INTERPRETATION, dict(disputed=True))
                    w.core.support(challenge, w._spans['scene'])
                    w.core.challenge(target, challenge)
                with self.assertRaises(ValueError):
                    p.current_messages(w)

    def test_real_final_adapter_gets_policy_but_exact_quotes_do_not_certify_trait_claim(self):
        # Deliberately unsupported stub: this guard is a delivery instruction,
        # not a semantic detector. Preserve raw evidence of this limitation.
        source = CONTRASTS[0]
        raw = json.dumps(dict(answer='Lena has an inborn destructive nature.',
            source_citations=[dict(source_id='scene', version=1, quote=source)],
            uncertainty='None.', assumptions='None.'))
        calls = []
        result = workspace(source).answer_reader_entry(QUERY, lambda messages: calls.append(messages) or raw, source_ids=('scene',))
        self.assertEqual(calls, [result['actual_final_messages']])
        self.assertIn(_SOURCE_INFERENCE_POLICY, calls[0][0]['content'])
        self.assertEqual(result['answer_raw'], raw)
        self.assertEqual(result['answer'], raw)
        self.assertTrue(result['source_citation_audit']['deliverable'])
        self.assertFalse(result['source_citation_audit']['semantic_certification'])
        self.assertEqual(result['preparation_provider_calls'], 0)
        self.assertEqual(result['answer_adapter_calls'], 1)


if __name__ == '__main__':
    unittest.main()
