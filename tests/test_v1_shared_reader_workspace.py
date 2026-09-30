"""Shared ordinary reader state, revision, composition and no inferred truth."""
import json
import unittest
from hcl.cognition import CognitionWorkspace, ClaimKind

SOURCE = '\n\n'.join(('_Dana._ I want to protect the gate.',
    '_Dana._ I plan to call Noor in order to protect the gate if the gate is clear.',
    '_Dana._ I have an opportunity to call Noor.',
    '_Dana._ I believe the gate is clear.',
    'Narrator: In the declared model, it is false that the gate is clear.'))
QUERY = 'Which actions are supported and what limits remain?'

def wire(result):
    return json.loads(result.messages[-1]['content'])

class SharedReaderTests(unittest.TestCase):
    def workspace(self, text=SOURCE):
        w = CognitionWorkspace(); w.put_source('meeting', text)
        return w

    def test_actual_reader_state_reaches_shared_core_and_final_input(self):
        w = self.workspace(); r = w.prepare(QUERY, source_ids=('meeting',))
        self.assertEqual(w.core.claims[r.claim_ids[0]].content['state'], wire(r))
        self.assertEqual(wire(r)['sources'][0]['text'], SOURCE)
        plan = wire(r)['checked_plan_feasibility'][0]['plans'][0]
        self.assertEqual(plan['subjective_feasibility'], 'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(plan['model_condition_check'], 'MODEL_CONDITION_CONTRADICTED')
        self.assertEqual(plan['deliberate_impossibility'], 'NOT_INFERRED')
        claim = w.core.claims[r.claim_ids[0]]
        self.assertEqual(claim.kind, ClaimKind.SYSTEM_INTERPRETATION)
        self.assertIn('NOT_PRIVATE_OR_WORLD_TRUTH', claim.content['semantic_boundary'])
        self.assertEqual(w.receipt(r)['actual_final_messages'], r.messages)

    def test_local_revision_changes_composed_condition_and_invalidates_old_answer(self):
        w = self.workspace(); before = w.prepare(QUERY, source_ids=('meeting',))
        text = SOURCE + '\n\n_Dana._ I now believe it is false that the gate is clear instead of the gate is clear.'
        invalidated = w.put_source('meeting', text)
        self.assertTrue(set(before.claim_ids) <= invalidated)
        with self.assertRaisesRegex(ValueError, 'support changed'): before.current_messages(w)
        after = w.prepare(QUERY, source_ids=('meeting',))
        self.assertEqual(wire(after)['checked_plan_feasibility'][0]['plans'][0]['subjective_feasibility'],
            'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(after.current_messages(w), after.messages)
        self.assertFalse(w.receipt(before)['current'])

    def test_zero_treatment_prose_is_complete_without_private_or_normative_verdict(self):
        text = 'Dana waited outside. Noor later heard a rumor about the closed gate.'
        w = self.workspace(text); r = w.prepare('What did Dana know and intend?', source_ids=('meeting',))
        p = wire(r)
        self.assertEqual(p['sources'][0]['text'], text)
        self.assertNotIn('checked_epistemic', p); self.assertNotIn('checked_agency', p)
        self.assertNotIn('checked_plan_feasibility', p)
        prep = json.loads(r.preparation_json)
        self.assertFalse(prep['specialized_cognition_treatment'])
        self.assertFalse(prep['agency_treatment']['private_intention_established'])

    def test_statement_snapshot_excludes_later_knowledge_and_event_time(self):
        w = self.workspace('Mira said, "I believe the gate is clear."\nLater Noor corrected the report.')
        r = w.prepare('Summarize the reported beliefs.', source_ids=('meeting',), through_order=1)
        p = wire(r)
        self.assertNotIn('Later Noor', json.dumps(p))
        self.assertEqual(p['source_order_scope']['through_statement'], 1)
        self.assertIsNone(r.scope.event_time); self.assertIsNone(r.scope.access_time)

    def test_invalid_snapshot_creates_no_partial_claims_or_answer_call(self):
        w = self.workspace('One line.'); before = set(w.core.claims); calls = []
        with self.assertRaises(ValueError):
            w.answer(QUERY, lambda m: calls.append(m), source_ids=('meeting',), through_order=2)
        self.assertEqual(set(w.core.claims), before); self.assertFalse(calls)

    def test_unrelated_update_and_noop_preserve_cache_and_original_receipt(self):
        w = self.workspace(); r = w.prepare(QUERY, source_ids=('meeting',))
        self.assertEqual(w.put_source('meeting', SOURCE), frozenset())
        w.put_source('elsewhere', 'Noor stayed at home.')
        self.assertIs(w.prepare(QUERY, source_ids=('meeting',)), r)
        self.assertEqual(r.current_messages(w), r.messages)
        self.assertEqual(w.executions, 1)

    def test_removal_and_readd_cannot_revive_old_receipt(self):
        w = self.workspace(); r = w.prepare(QUERY, source_ids=('meeting',))
        w.remove_source('meeting'); w.put_source('meeting', SOURCE)
        with self.assertRaises(ValueError): r.current_messages(w)
        self.assertNotEqual(w.prepare(QUERY, source_ids=('meeting',)).source_versions, r.source_versions)

    def test_dependency_challenge_prevents_cached_state_answer(self):
        w = self.workspace(); r = w.prepare(QUERY, source_ids=('meeting',))
        key = r.claim_ids[0]
        challenger = w.core.claim(r.scope, ClaimKind.SYSTEM_INTERPRETATION, {'disputed': True})
        w.core.support(challenger, w._spans['meeting']); w.core.challenge(key, challenger)
        calls = []
        self.assertFalse(w.receipt(r)['current'])
        with self.assertRaises(ValueError):
            w.answer(QUERY, lambda m: calls.append(m), source_ids=('meeting',))
        self.assertFalse(calls)
        w.core.withdraw(challenger)
        self.assertTrue(w.receipt(r)['current'])
        self.assertEqual(r.current_messages(w), r.messages)

    def test_ordinary_smoke_one_final_call_no_extraction_and_no_retry(self):
        w = self.workspace(); calls = []
        receipt = w.answer(QUERY, lambda m: calls.append(m) or 'correctness stub', source_ids=('meeting',))
        self.assertEqual(calls, [receipt['prepared'].messages])
        self.assertEqual(receipt['actual_final_messages'], calls[0])
        self.assertEqual(receipt['answer_adapter_calls'], 1)
        self.assertEqual(receipt['preparation_provider_calls'], 0)
        def failed(m): calls.append(m); raise RuntimeError('transport failed')
        with self.assertRaises(RuntimeError): w.answer(QUERY, failed, source_ids=('meeting',))
        self.assertEqual(len(calls), 2)

    def test_multiple_documents_cannot_silently_join_same_named_actors(self):
        w = self.workspace('Dana heard the bell.')
        w.put_source('other', 'Noor heard a different bell.')
        before = set(w.core.claims); calls = []
        with self.assertRaisesRegex(ValueError, 'identity binding'):
            w.answer('Compare the reported scenes.', lambda m: calls.append(m), source_ids=('meeting','other'))
        self.assertFalse(calls); self.assertEqual(set(w.core.claims), before)

if __name__ == '__main__': unittest.main()
