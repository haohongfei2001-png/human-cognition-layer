"""Independent participant views expose source limits, never mind transfer."""
from dataclasses import replace
import json
import unittest
from hcl.v04.model import EventRecord
from hcl.v1 import (HCLCognitionLayer, prepare_perspective_contrast, answer_perspective_contrast,
                    expand_cognition_context)

QUERY = "Contrast Alice and Bob's views of proposal as fair in team."
A = 'Alice: In team, I believe proposal is fair.'
B = 'Bob: In team, I do not believe proposal is fair.'
AH = 'Narrator: Alice heard the previous statement.'
BH = 'Narrator: Bob heard the previous statement.'
SOURCE = '\n'.join((A, AH, B, BH))


def wire(p):
    return json.loads(p.messages[-1]['content'])['perspective_contrast']


def context(p, i):
    return expand_cognition_context(wire(p)['participants'][i]['cognition_context'])


def event(eid, text, actor, time='2026-01-01T00:00:01+00:00', **kwargs):
    return EventRecord(eid, time, text, 'authorized-raw-source', time, actor, **kwargs)


class PerspectiveContrastTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def test_ordinary_two_participant_contrast_keeps_actual_distinct_stances(self):
        p = prepare_perspective_contrast(self.layer, QUERY, SOURCE)
        state = wire(p)
        self.assertEqual(state['relation'], 'DIFFERENT_EXPLICIT_SELF_REPORT_STANCES')
        self.assertEqual(context(p, 0)['belief'][0]['status'], 'AFFIRMED')
        self.assertEqual(context(p, 1)['belief'][0]['status'], 'DENIED')
        self.assertNotIn(B, json.dumps(state['participants'][0]))
        self.assertNotIn(A, json.dumps(state['participants'][1]))
        self.assertEqual(state['shared_available_source_event_ids'], [])
        self.assertEqual(state['world_truth'], 'NOT_ESTABLISHED')
        self.assertEqual(state['moral_blame'], 'NOT_INFERRED')

    def test_unmentioned_bob_access_and_belief_stay_unknown(self):
        p = prepare_perspective_contrast(self.layer, QUERY, A + '\n' + AH)
        self.assertFalse(context(p, 1)['belief'])
        self.assertFalse(context(p, 1)['evidence'])
        self.assertEqual(wire(p)['relation'], 'UNRESOLVED_PARTICIPANT_COMPARISON')
        self.assertEqual(wire(p)['participants'][1]['evidence_boundary']['unmentioned_access'], 'UNKNOWN')

    def test_shared_exposure_is_not_shared_acceptance_or_character_uncertainty(self):
        source = A + '\nNarrator: Alice and Bob heard the previous statement.'
        p = prepare_perspective_contrast(self.layer, QUERY, source)
        self.assertEqual(len(wire(p)['shared_available_source_event_ids']), 1)
        self.assertFalse(context(p, 1)['belief'])
        self.assertEqual(context(p, 1)['uncertainty'][0]['status'], 'SYSTEM_INSUFFICIENT')
        self.assertEqual(wire(p)['relation'], 'UNRESOLVED_PARTICIPANT_COMPARISON')
        self.assertFalse(wire(p)['participants'][1]['evidence_boundary']['exposure_implies_belief'])

    def test_typed_public_evidence_remains_distinct_from_nonpublic_sources(self):
        public = event('public', A, 'Alice', metadata={'public': True})
        private = event('bob-own', B, 'Bob', '2026-01-01T00:00:02+00:00')
        p = prepare_perspective_contrast(self.layer, QUERY, (public, private))
        a, b = wire(p)['participants']
        self.assertEqual(a['evidence_boundary']['public_source_event_ids'], ['public'])
        self.assertEqual(a['evidence_boundary']['nonpublic_available_source_event_ids'], [])
        self.assertEqual(b['evidence_boundary']['public_source_event_ids'], ['public'])
        self.assertEqual(b['evidence_boundary']['nonpublic_available_source_event_ids'], ['bob-own'])
        self.assertEqual(wire(p)['shared_available_source_event_ids'], ['public'])
        self.assertNotIn(B, json.dumps(a))

    def test_narrator_and_third_party_are_not_direct_private_self_report(self):
        for report in ('Narrator: In team, Alice believes proposal is fair.',
                       'Bob: In team, Alice believes proposal is fair.'):
            p = prepare_perspective_contrast(self.layer, QUERY,
                report + '\nNarrator: Alice and Bob heard the previous statement.')
            self.assertFalse(wire(p)['participants'][0]['direct_self_report'])
            self.assertEqual(wire(p)['relation'], 'UNRESOLVED_PARTICIPANT_COMPARISON')
        p = prepare_perspective_contrast(self.layer, QUERY,
            SOURCE + '\nNarrator: In team, proposal has consent false.')
        self.assertNotIn('proposal has consent false', p.messages[-1]['content'])

    def test_explicit_character_uncertainty_separate_from_missing_system_evidence(self):
        source = SOURCE.replace('I do not believe', 'I am unsure whether')
        p = prepare_perspective_contrast(self.layer, QUERY, source)
        self.assertEqual(context(p, 1)['belief'][0]['status'], 'CHARACTER_UNCERTAIN')
        self.assertTrue(wire(p)['participants'][1]['direct_self_report'])
        self.assertEqual(wire(p)['relation'], 'DIFFERENT_EXPLICIT_SELF_REPORT_STANCES')

    def test_observer_cannot_receive_reader_or_other_participant_private_source(self):
        p = prepare_perspective_contrast(self.layer, QUERY, SOURCE, observer_actor='Carol')
        self.assertTrue(all(not context(p, i)['evidence'] for i in range(2)))
        self.assertNotIn(A, p.messages[-1]['content'])
        self.assertNotIn(B, p.messages[-1]['content'])
        p = prepare_perspective_contrast(self.layer, QUERY, SOURCE, observer_actor='Alice')
        self.assertEqual(context(p, 0)['belief'][0]['status'], 'AFFIRMED')
        self.assertFalse(context(p, 1)['belief'])
        self.assertNotIn(B, p.messages[-1]['content'])

    def test_earlier_source_and_record_time_do_not_borrow_later_view(self):
        p = prepare_perspective_contrast(self.layer, 'At statement 2, ' + QUERY, SOURCE)
        self.assertEqual(context(p, 0)['belief'][0]['status'], 'AFFIRMED')
        self.assertFalse(context(p, 1)['belief'])
        self.assertNotIn(B, p.messages[-1]['content'])
        self.assertEqual(wire(p)['source_order_scope']['through_statement'], 2)
        a = event('a', A, 'Alice')
        b = event('b', B, 'Bob', '2026-01-01T00:00:02+00:00')
        for kw in ({'event_time': a.valid_time}, {'knowledge_cutoff': a.recorded_at}):
            p = prepare_perspective_contrast(self.layer, QUERY, (a, b), **kw)
            self.assertFalse(context(p, 1)['belief'])
            self.assertNotIn(B, p.messages[-1]['content'])
        late = replace(b, valid_time=a.valid_time)
        p = prepare_perspective_contrast(self.layer, QUERY, (a, late), knowledge_cutoff=a.recorded_at)
        self.assertNotIn(B, p.messages[-1]['content'])

    def test_invalid_scope_fallback_is_private_and_total_budget_refuses_both(self):
        for q, kw in ((QUERY.replace('Bob', 'Alice'), {}), (QUERY.replace('Bob', 'Narrator'), {}),
                      ('Contrast their minds.', {}), ('At statement 99, ' + QUERY, {}),
                      (QUERY, {'as_of_statement': True})):
            p = prepare_perspective_contrast(self.layer, q, SOURCE, **kw)
            self.assertFalse(p.context.evidence)
            self.assertNotIn(A, p.messages[-1]['content'])
        p = prepare_perspective_contrast(self.layer, QUERY, SOURCE, max_context_chars=512)
        self.assertEqual(wire(p)['participants'], [])
        self.assertLessEqual(len(json.dumps(wire(p), sort_keys=True)), 512)
        p = prepare_perspective_contrast(self.layer, QUERY, (event('bad', A, 'Alice', metadata={'public': 'yes'}),))
        self.assertFalse(p.context.evidence)

    def test_chinese_query_has_one_actual_answer_input_and_only_retained_operation(self):
        calls = []
        def adapter(messages):
            calls.append(messages)
            return 'bounded participant contrast'
        r = answer_perspective_contrast(HCLCognitionLayer(adapter),
            '比较 Alice 与 Bob 在 team 中对 proposal 是否 fair 的视角。', SOURCE, debug=True)
        self.assertEqual(calls, [list(r.prepared.messages)])
        self.assertEqual(r.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(r.prepared.preparation_receipt['actual_final_messages'], list(r.prepared.messages))
        self.assertTrue(all(plan.belief_preparation and not plan.concept_interpretation and
            not plan.responsibility_structure for plan in r.prepared.plans))
