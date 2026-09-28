"""Provider-free CG-02 route, source and expectation checks."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from hcl.v04.model import EventRecord
from hcl.v1 import (AccessStatement, CognitionRequest, CognitionRouter,
    HCLCognitionLayer,
    ParticipantInterpretation, PerspectiveMode, SocialAct, SocialActKind,
    SocialCondition, check_social_exchange)


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stamp(index):
    return (BASE + timedelta(seconds=index)).isoformat()


def event(event_id, index, text, actor=None, recipients=(), reader_only=False):
    return EventRecord(event_id, stamp(index), text, 'cg02-test',
        stamp(index), actor, recipient_ids=recipients,
        metadata={'reader_only': reader_only})


class SocialRoute(unittest.TestCase):
    def test_explicit_social_route_preserves_direct_non_social_tasks(self):
        router = CognitionRouter()
        self.assertTrue(router.plan(CognitionRequest('What is 2 + 2?')).direct)
        self.assertTrue(router.plan(CognitionRequest('promise')).direct)
        planned = router.plan(CognitionRequest(
            'What did Alice promise Bob?', target_actor='Alice'))
        self.assertTrue(planned.social_commitment)
        self.assertIn('cg02_social_commitment', planned.capabilities)
        self.assertFalse(planned.explanation)
        self.assertTrue(router.plan(CognitionRequest(
            'Alice 对 Bob 的承诺是什么？', target_actor='Alice')).social_commitment)
        with self.assertRaises(ValueError):
            CognitionRequest('Assess this conversation', social_analysis=True)


class GroundedExchange(unittest.TestCase):
    def setUp(self):
        self.source = event('offer', 0,
            'Alice to Bob: "If I finish by Friday, I can go with you."',
            'Alice', ('Bob',))
        self.report = event('report', 1,
            'Bob: "Alice promised to go with me Friday."', 'Bob')
        condition = SocialCondition('If I finish by Friday',
                                    'If I finish by Friday', 'offer')
        self.act = SocialAct('a1', SocialActKind.CONDITIONAL_COMMITMENT,
            'Alice', 'Bob', 'I can go with you',
            '"If I finish by Friday, I can go with you."',
            'offer', stamp(0), (condition,))
        self.interpretation = ParticipantInterpretation('i1', 'Bob', 'a1',
            'Alice promised to go with me Friday', (),
            '"Alice promised to go with me Friday."', 'report', stamp(1))

    def check(self, **kwargs):
        return check_social_exchange((self.act,), (self.interpretation,), (),
            (self.source, self.report), **kwargs)

    def test_conditional_act_and_omitted_condition_are_checked(self):
        result = self.check()
        self.assertEqual(result['acts'][0]['kind'], 'CONDITIONAL_COMMITMENT')
        self.assertEqual(result['checked_act_count'], 1)
        comparison = result['expectation_comparisons'][0]
        self.assertEqual(comparison['relation'], 'STRONGER_THAN_SOURCE')
        self.assertEqual(comparison['omitted_condition_keys'],
                         ['If I finish by Friday'])
        self.assertEqual(comparison['condition_access']['If I finish by Friday'],
                         'DIRECT_ACCESS')
        self.assertEqual(comparison['content_relation'],
                         'PARAPHRASE_NOT_VERIFIED')
        self.assertNotIn('trust_score', result)
        self.assertIn('REPORTED_EXPECTATION_OMITS_SOURCE_CONDITION',
                      comparison['explanation_factors'])

    def test_missing_access_is_unknown_and_explicit_denial_is_distinct(self):
        unseen = replace(self.source, recipient_ids=('Cara',))
        unknown = check_social_exchange((self.act,), (self.interpretation,), (),
            (unseen, self.report))
        self.assertEqual(unknown['expectation_comparisons'][0]['condition_access'][
            'If I finish by Friday'], 'UNKNOWN_ACCESS')
        denial_source = event('denial', 2,
            'Bob did not hear the condition Alice stated.', None,
            reader_only=True)
        denial = AccessStatement('access1', 'Bob', 'offer', 'denial', False)
        explicit = check_social_exchange((self.act,), (self.interpretation,),
            (denial,), (unseen, self.report, denial_source))
        self.assertEqual(explicit['expectation_comparisons'][0]['condition_access'][
            'If I finish by Friday'], 'EXPLICIT_NO_ACCESS')
        bad_source = replace(denial_source,
            raw_text='A third party guessed Bob was unaware.')
        with self.assertRaises(ValueError):
            check_social_exchange((self.act,), (self.interpretation,),
                (denial,), (unseen, self.report, bad_source))

    def test_reader_character_and_observer_do_not_share_hidden_source(self):
        reader = self.check(mode='READER_ANALYSIS')
        bob = self.check(mode='CHARACTER_PERSPECTIVE', target_actor='Bob')
        cara = self.check(mode='OBSERVER_ABOUT_TARGET',
                          target_actor='Bob', observer_actor='Cara')
        self.assertEqual(len(reader['acts']), 1)
        self.assertEqual(len(bob['acts']), 1)
        self.assertEqual(cara['acts'], [])
        self.assertEqual(cara['expectation_comparisons'], [])
        hidden = replace(self.source, recipient_ids=(), metadata={'reader_only': True})
        bob_hidden = check_social_exchange((self.act,), (self.interpretation,), (),
            (hidden, self.report), mode='CHARACTER_PERSPECTIVE',
            target_actor='Bob')
        self.assertEqual(bob_hidden['acts'], [])
        self.assertEqual(bob_hidden['expectation_comparisons'], [])

    def test_acceptance_reference_and_withdrawal_timing(self):
        accept_source = event('accept', 2, 'Bob to Alice: "Yes, I accept."',
                              'Bob', ('Alice',))
        accept = SocialAct('a2', SocialActKind.ACCEPTANCE, 'Bob', 'Alice',
                           'Yes, I accept', '"Yes, I accept."',
                           'accept', stamp(2), refers_to='a1')
        withdrawal_source = event('withdraw', 3,
            'Alice to Bob: "I withdraw my offer."', 'Alice', ('Bob',))
        withdrawal = SocialAct('a3', SocialActKind.WITHDRAWAL, 'Alice', 'Bob',
            'I withdraw my offer', '"I withdraw my offer."',
            'withdraw', stamp(3), refers_to='a1')
        result = check_social_exchange((self.act, accept, withdrawal),
            (self.interpretation,), (),
            (self.source, self.report, accept_source, withdrawal_source))
        self.assertEqual(result['acts'][1]['reference_status'], 'VISIBLE_PRIOR_ACT')
        self.assertEqual(result['expectation_comparisons'][0]['withdrawal_order'],
                         'AFTER_REPORTED_EXPECTATION')
        with self.assertRaises(ValueError):
            check_social_exchange((self.act, replace(withdrawal, speaker='Bob')),
                (), (), (self.source, withdrawal_source))

    def test_unanchored_or_future_claims_fail_closed(self):
        with self.assertRaises(ValueError):
            check_social_exchange((replace(self.act,
                quote='Alice silently promised to go.'),), (), (),
                (self.source,))
        with self.assertRaises(ValueError):
            check_social_exchange((replace(self.act,
                conditions=(SocialCondition('invented', 'invented', 'offer'),)),),
                (), (), (self.source,))
        future = replace(self.interpretation, formed_time=stamp(0))
        with self.assertRaises(ValueError):
            check_social_exchange((self.act,), (future,), (),
                (self.source, self.report))


class SocialEndToEnd(unittest.TestCase):
    narrative = ('Alice to Bob: "If I finish by Friday, I can go with you."\n'
                 'Bob: "Alice promised to go with me Friday."')

    def request(self, **kwargs):
        return CognitionRequest('What did Alice promise Bob?', target_actor='Alice',
            narrative=self.narrative, **kwargs)

    def test_real_preparation_checker_and_ablation_change_final_input(self):
        h = HCLCognitionLayer(lambda messages: 'answer').prepare(self.request())
        h_new = HCLCognitionLayer(lambda messages: 'answer',
            social_checker_enabled=False).prepare(self.request())
        self.assertEqual(h.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(h.context.social['checked_act_count'], 1)
        self.assertEqual(h.context.social['checked_expectation_count'], 1)
        self.assertEqual(h.context.social['expectation_comparisons'][0]['relation'],
                         'STRONGER_THAN_SOURCE')
        self.assertEqual(h_new.context.social, {})
        self.assertNotEqual(h.messages[-1]['content'], h_new.messages[-1]['content'])
        self.assertEqual(h.context.evidence, h_new.context.evidence)
        self.assertIn('If I finish by Friday', h.messages[-1]['content'])

    def test_character_and_observer_views_do_not_leak_report(self):
        bob = HCLCognitionLayer(lambda messages: 'answer').prepare(
            CognitionRequest('What did Bob expect?', target_actor='Bob',
                perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE,
                narrative=self.narrative))
        alice = HCLCognitionLayer(lambda messages: 'answer').prepare(
            CognitionRequest('What did Alice promise?', target_actor='Alice',
                perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE,
                narrative=self.narrative))
        cara = HCLCognitionLayer(lambda messages: 'answer').prepare(
            CognitionRequest('What did Bob expect?', target_actor='Bob',
                observer_actor='Cara',
                perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,
                narrative=self.narrative))
        self.assertEqual(bob.context.social['checked_expectation_count'], 1)
        self.assertEqual(alice.context.social['checked_expectation_count'], 0)
        self.assertEqual(cara.context.social['checked_act_count'], 0)
        self.assertNotIn('Alice promised to go', alice.messages[-1]['content'])
        self.assertNotIn('If I finish by Friday', cara.messages[-1]['content'])

    def test_unrecognized_text_and_bad_adapter_fail_closed(self):
        source = 'Alice privately considered helping Bob.'
        request = CognitionRequest('What did Alice promise Bob?',
            target_actor='Alice', narrative=source,
            allow_semantic_preparation=True)
        failed = HCLCognitionLayer(lambda messages: 'answer',
            semantic_preparer=lambda inputs: object()).prepare(request)
        self.assertEqual(failed.preparation_receipt['failure'],
                         'invalid_social_semantic_preparation')
        self.assertEqual(failed.context.social['checked_act_count'], 0)
        self.assertEqual(failed.context.social['checked_expectation_count'], 0)
        self.assertNotIn('CONDITIONAL_COMMITMENT', failed.messages[-1]['content'])


if __name__ == '__main__':
    unittest.main()
