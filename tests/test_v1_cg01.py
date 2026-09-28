"""Provider-free CG-01 capability and end-to-end boundary tests."""
from dataclasses import replace
import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind
from hcl.v07 import HCLV07Runtime, IntentionEvidenceEvent, IntentionSignal
from hcl.v1 import CognitionRequest, CognitionRouter, HCLCognitionLayer, SemanticPreparation
from hcl.v1.router import PerspectiveMode
from hcl.v1.cg01 import (ConditionFact, ConditionKind, ExplanationCandidate,
                         FactAuthority, RequiredCondition, check_explanations,
                         revise_explanations)


T0 = '2026-01-01T00:00:00+00:00'
T1 = '2026-01-01T00:01:00+00:00'
T2 = '2026-01-01T00:02:00+00:00'


def event(eid, text, actor=None, when=T0, observers=(), metadata=None):
    return EventRecord(eid, when, text, 'authorized-source', when, actor,
                       tuple(observers), metadata=metadata or {})


KNOW = RequiredCondition(ConditionKind.KNOWLEDGE, 'meeting')
GOAL = RequiredCondition(ConditionKind.GOAL, 'opposition')
CHOICE = RequiredCondition(ConditionKind.OPPORTUNITY, 'attend')


class Routing(unittest.TestCase):
    def test_generic_why_is_direct_in_english_and_chinese(self):
        for query in ('Why is the sky blue?', '为什么会下雨？'):
            plan = CognitionRouter().plan(CognitionRequest(query))
            self.assertTrue(plan.direct)
            self.assertNotIn('intention', plan.optional_capabilities)

    def test_three_modes_and_ordinary_explanation(self):
        router = CognitionRouter()
        reader = router.plan(CognitionRequest('Why did Alice miss the meeting?'))
        self.assertEqual(reader.perspective_mode, PerspectiveMode.READER_ANALYSIS)
        self.assertTrue(reader.explanation)
        character = router.plan(CognitionRequest('What does Alice know?', target_actor='Alice'))
        self.assertEqual(character.perspective_mode, PerspectiveMode.CHARACTER_PERSPECTIVE)
        observer = router.plan(CognitionRequest('What does Bob know?', target_actor='Bob', observer_actor='Alice'))
        self.assertEqual(observer.perspective_mode, PerspectiveMode.OBSERVER_ABOUT_TARGET)
        chinese = router.plan(CognitionRequest('Alice 为什么没参加会议？', target_actor='Alice'))
        self.assertTrue(chinese.explanation)


class Conditions(unittest.TestCase):
    def setUp(self):
        self.action = event('action', 'Alice missed the meeting.', 'Alice')
        self.candidate = ExplanationCandidate('oppose', 'Alice', 'action', T0,
            'Alice deliberately opposed Bob', 'action', (KNOW, GOAL, CHOICE))

    def test_positive_is_conditional_not_motive_truth(self):
        sources = (self.action, event('k', 'Alice knew about the meeting before it began.', when=T1),
                   event('g', 'Alice stated that she wanted to oppose Bob.', when=T1),
                   event('o', 'Alice could have attended.', when=T1))
        facts = tuple(ConditionFact(eid, eid, 'Alice', condition, True, T0,
                     FactAuthority.EXPLICIT_NARRATOR) for eid, condition in
                     (('k', KNOW), ('g', GOAL), ('o', CHOICE)))
        result = check_explanations((self.candidate,), facts, sources)[0]
        self.assertEqual(result['status'], 'CONSISTENT_CONDITIONAL')
        self.assertIn('not establish', result['caution'])

    def test_missing_knowledge_is_unknown(self):
        result = check_explanations((self.candidate,), (), (self.action,))[0]
        self.assertEqual(result['conditions'][0]['state'], 'UNKNOWN')
        self.assertEqual(result['status'], 'UNRESOLVED')

    def test_later_first_learning_invalidates_only_dependent_candidate(self):
        later = event('later', 'Alice first learned of the meeting after it ended.', when=T2)
        unrelated = ExplanationCandidate('traffic', 'Alice', 'action', T0,
            'a possible travel obstacle', 'action', (CHOICE,))
        fact = ConditionFact('first', 'later', 'Alice', KNOW, False, T2,
                             FactAuthority.EXPLICIT_NARRATOR, first_learning_time=T2)
        change = revise_explanations((self.candidate, unrelated), (), (fact,),
                                     (self.action, later))
        self.assertEqual(change['changed_candidate_ids'], ('oppose',))
        self.assertEqual(change['after'][0]['status'], 'INVALIDATED')
        self.assertEqual(change['after'][1]['status'], 'UNRESOLVED')
        character = check_explanations((self.candidate,), (fact,), (self.action, later),
                                        mode='CHARACTER_PERSPECTIVE')[0]
        self.assertEqual(character['conditions'][0]['state'], 'UNKNOWN')

    def test_third_party_denial_is_challenge_and_narrator_scope_is_enforced(self):
        report = event('report', 'Bob said Alice had not heard.', actor='Bob', when=T1,
                       observers=('Charlie',))
        alleged = ConditionFact('alleged', 'report', 'Alice', KNOW, False, T0,
                                FactAuthority.THIRD_PARTY_ATTRIBUTION)
        self.assertEqual(check_explanations((self.candidate,), (alleged,),
                         (self.action, report))[0]['conditions'][0]['state'], 'CHALLENGED')
        observer = check_explanations((self.candidate,), (alleged,),
             (self.action, report), mode='OBSERVER_ABOUT_TARGET', observer_actor='Charlie')
        self.assertEqual(observer, ())  # Charlie has no evidence of the action.
        with self.assertRaises(ValueError):
            check_explanations((self.candidate,), (replace(alleged,
                authority=FactAuthority.EXPLICIT_NARRATOR),), (self.action, report))

    def test_observer_and_temporal_cutoffs_do_not_import_later_narration(self):
        action = replace(self.action, observer_ids=('Bob',))
        later = event('later', 'Alice first learned of the meeting later.',
                      when=T2, observers=('Bob',))
        fact = ConditionFact('first', 'later', 'Alice', KNOW, False, T2,
                             FactAuthority.EXPLICIT_NARRATOR, first_learning_time=T2)
        visible = check_explanations((self.candidate,), (fact,), (action, later),
            mode='OBSERVER_ABOUT_TARGET', observer_actor='Bob')[0]
        self.assertEqual(visible['status'], 'INVALIDATED')
        cutoff = check_explanations((self.candidate,), (fact,), (action, later),
            mode='OBSERVER_ABOUT_TARGET', observer_actor='Bob', event_time=T1)[0]
        self.assertEqual(cutoff['conditions'][0]['state'], 'UNKNOWN')
        hidden = check_explanations((self.candidate,), (fact,),
            (action, replace(later, observer_ids=())), mode='OBSERVER_ABOUT_TARGET',
            observer_actor='Bob')[0]
        self.assertEqual(hidden['conditions'][0]['state'], 'UNKNOWN')


class OrdinaryNarrative(unittest.TestCase):
    NARRATIVE = ("Alice missed Bob's meeting. Bob thought Alice stayed away to oppose him. "
                 "Alice first learned about the meeting after it ended.")

    def test_reader_receipt_preserves_actual_context_and_one_answer_call(self):
        messages_seen = []
        def answer(messages):
            messages_seen.append(messages)
            return 'The deliberate-opposition explanation is weakened.'
        receipt = HCLCognitionLayer(answer).answer(CognitionRequest(
            'Why did Alice miss the meeting?', narrative=self.NARRATIVE), debug=True)
        self.assertEqual(len(messages_seen), 1)
        self.assertEqual(receipt.prepared.context.explanations[1]['status'], 'INVALIDATED')
        self.assertEqual(receipt.prepared.context.preparation['extraction_provider_calls'], 0)
        payload = json.loads(messages_seen[0][1]['content'])['cognition_context']
        self.assertEqual(payload, json.loads(receipt.prepared.context.serialized()))
        self.assertIn('first learned', str(payload['evidence']))
        self.assertEqual(payload['open_unknown_candidate']['status'], 'OPEN')

    def test_reader_narrator_evidence_never_enters_character_view(self):
        reader = HCLCognitionLayer(lambda _: 'ok').prepare(CognitionRequest(
            'Why did Alice miss the meeting?', narrative=self.NARRATIVE))
        character = HCLCognitionLayer(lambda _: 'ok').prepare(CognitionRequest(
            'Why did Alice miss the meeting?', narrative=self.NARRATIVE,
            target_actor='Alice', perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertIn('first learned', reader.context.serialized())
        self.assertNotIn('first learned', character.context.serialized())
        self.assertNotIn('first learned', str(character.messages))
        self.assertEqual(character.context.explanations, [])
        self.assertEqual(character.context.evidence, [])

    def test_optional_semantic_adapter_is_explicit_and_audited(self):
        calls = []
        source = event('s', 'Alice mailed a letter.', 'Alice', metadata={'reader_only': True})
        candidate = ExplanationCandidate('mail-choice', 'Alice', 's', T0,
            'deliberate mailing', 's', (RequiredCondition(ConditionKind.OPPORTUNITY, 'mail'),))
        def prepare(payload):
            calls.append(payload)
            return SemanticPreparation((source,), (candidate,), (),
                'source-anchored typed output', 'provider-free-test-stub', 0, 0.0)
        layer = HCLCognitionLayer(lambda _: 'ok', semantic_preparer=prepare)
        request = CognitionRequest('Why did Alice mail the letter?',
            narrative='Alice mailed a letter.')
        layer.prepare(request)
        self.assertEqual(calls, [])
        prepared = layer.prepare(replace(request, allow_semantic_preparation=True))
        self.assertEqual(len(calls), 1)
        self.assertEqual(prepared.context.explanations[0]['status'], 'UNRESOLVED')
        self.assertEqual(prepared.context.preparation['semantic_preparer_calls'], 1)
        self.assertEqual(prepared.context.preparation['extraction_provider_calls'], 0)
        self.assertEqual(prepared.preparation_receipt['input']['narrative'], 'Alice mailed a letter.')
        self.assertEqual(prepared.preparation_receipt['output'], 'source-anchored typed output')

    def test_invalid_semantic_result_keeps_actual_paid_output_and_cost(self):
        source = event('s', 'Invented source text.', 'Alice',
                       metadata={'reader_only': True})
        def prepare(_payload):
            return SemanticPreparation((source,), (), (), 'raw model output',
                'paid-model', 1, 0.002)
        result = HCLCognitionLayer(lambda _: 'unused',
            semantic_preparer=prepare).prepare(CognitionRequest(
            'Why did Alice mail the letter?', narrative='Alice mailed a letter.',
            target_actor='Alice', allow_semantic_preparation=True))
        receipt = result.preparation_receipt
        self.assertEqual(receipt['failure'], 'invalid_semantic_preparation')
        self.assertEqual(receipt['output'], 'raw model output')
        self.assertEqual(receipt['extraction_provider_calls'], 1)
        self.assertEqual(receipt['extraction_spend_usd'], 0.002)

    def test_narrator_intention_is_reader_evidence_not_character_knowledge(self):
        runtime = HCLV07Runtime()
        narrator = event('n', 'Alice stated an intention to leave.', when=T1,
                         metadata={'reader_only': True})
        runtime.ingest_event(narrator)
        runtime.ingest_intention_evidence(IntentionEvidenceEvent('i', 'n', 'Alice',
            'leave', IntentionSignal.EXPLICIT_INTENTION,
            BeliefEvidenceKind.NARRATOR_ASSERTION, T1, T1, narrator.raw_text))
        layer = HCLCognitionLayer(lambda _: 'ok', intentions=runtime)
        reader = layer.prepare(CognitionRequest('What is Alice’s intention?',
            target_actor='Alice', perspective_mode=PerspectiveMode.READER_ANALYSIS))
        character = layer.prepare(CognitionRequest('What is Alice’s intention?',
            target_actor='Alice', perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertEqual(len(reader.context.explicit_intention), 1)
        self.assertEqual(character.context.explicit_intention, [])
        self.assertNotIn('leave', str(character.messages))

    def test_direct_nonperson_task_does_not_prepare_narrative(self):
        prepared = HCLCognitionLayer(lambda _: 'Paris').prepare(CognitionRequest(
            'What city is mentioned?', narrative='Paris is mentioned.'))
        self.assertTrue(prepared.plan.direct)
        self.assertIsNone(prepared.context)


if __name__ == '__main__':
    unittest.main()
