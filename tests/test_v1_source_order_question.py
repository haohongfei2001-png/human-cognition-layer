"""Earlier ordinary source snapshots cannot consume later semantic/access state."""
import hashlib
import json
import unittest
from hcl.v1 import (HCLCognitionLayer, PerspectiveMode, prepare_person_context,
    answer_person_context, expand_composed_sources, expand_cognition_context)

D = 'Alice: In team, by fair I mean consent is true.'
F = 'Narrator: In team, proposal has consent false.'
B = 'Alice: In team, I believe proposal is fair.'
R = 'Alice: In team, I now believe proposal is unfair instead of proposal is fair.'
M = 'Alice: In team, I now use fair to mean consent is false instead of consent is true.'
HEAR = 'Narrator: Alice and Bob heard the previous statement.'
QUERY = "Compare Alice's belief and meaning of fair for proposal in team."
SOURCE = '\n'.join((D, F, B, R, M))


def payload(p):
    return json.loads(p.messages[-1]['content'])


def belief_rows(p):
    row = payload(p)
    if 'cognition_context' in row:
        return expand_cognition_context(row['cognition_context'])['belief']
    state = expand_composed_sources(row['composed_cognition'])
    belief = next(r for r in state['operation_contexts'] if r['operation'] == 'belief')
    return expand_cognition_context(belief['cognition_context'])['belief']


class SourceOrderQuestionTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def test_prior_snapshot_belief_and_comparison_do_not_use_later_revisions(self):
        prior = prepare_person_context(self.layer, 'At statement 3, ' + QUERY, SOURCE)
        state = payload(prior)['composed_cognition']
        self.assertEqual(state['belief_concept_comparison']['rows'][0]['relation'], 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA')
        self.assertEqual(belief_rows(prior)[0]['status'], 'AFFIRMED')
        self.assertNotIn('unfair', prior.messages[-1]['content'])
        self.assertNotIn(M, prior.messages[-1]['content'])
        full = prepare_person_context(self.layer, QUERY, SOURCE)
        self.assertEqual({b['status'] for b in belief_rows(full)}, {'AFFIRMED', 'SUPERSEDED'})
        self.assertEqual(payload(prior)['source_order_scope']['calendar_time'], 'NOT_ESTABLISHED')

    def test_source_alone_before_self_report_never_creates_a_belief(self):
        p = prepare_person_context(self.layer, QUERY, SOURCE, as_of_statement=2)
        self.assertFalse(belief_rows(p))
        self.assertFalse(payload(p)['composed_cognition']['belief_concept_comparison']['rows'])
        self.assertNotIn(B, p.messages[-1]['content'])

    def test_concept_snapshot_keeps_prior_local_meaning_before_explicit_revision(self):
        query = "Interpret Alice's meaning of fair for proposal in team."
        prior = prepare_person_context(self.layer, query, SOURCE, as_of_statement=3)
        after = prepare_person_context(self.layer, query, SOURCE, as_of_statement=5)
        self.assertEqual(prior.context.concepts['checked']['readings'][0]['state'], 'CRITERIA_NOT_MET')
        self.assertEqual([r['state'] for r in after.context.concepts['checked']['readings']],
            ['SUPERSEDED_LOCAL', 'CRITERIA_MET'])
        self.assertNotIn(M, prior.messages[-1]['content'])

    def test_future_malformed_semantics_cannot_poison_valid_earlier_snapshot(self):
        source = B + '\nAlice: In team, I perhaps believe proposal is unsafe.'
        prior = prepare_person_context(self.layer, "Explain Alice's belief.", source, as_of_statement=1)
        self.assertEqual(belief_rows(prior)[0]['status'], 'AFFIRMED')
        self.assertNotIn('unsafe', prior.messages[-1]['content'])
        full = prepare_person_context(self.layer, "Explain Alice's belief.", source)
        self.assertFalse(belief_rows(full))
        self.assertEqual(full.preparation_receipt['failure'], 'unsupported_or_ambiguous_belief_source')

    def test_private_snapshot_before_later_exposure_cannot_receive_self_report(self):
        source = '\n'.join((D, HEAR, F, HEAR, B, HEAR))
        kwargs = dict(narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob')
        before = prepare_person_context(self.layer, QUERY, source, as_of_statement=5, **kwargs)
        after = prepare_person_context(self.layer, QUERY, source, as_of_statement=6, **kwargs)
        self.assertFalse(belief_rows(before))
        self.assertNotIn(B, before.messages[-1]['content'])
        self.assertEqual(payload(after)['composed_cognition']['belief_concept_comparison']['rows'][0]['relation'],
            'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA')

    def test_prefix_chinese_and_argument_choose_same_authorized_nonblank_statement(self):
        source = D + '\n\n  ' + F + '  \n' + B + '\n' + R
        en = prepare_person_context(self.layer, 'At statement 3, ' + QUERY, source)
        cn = prepare_person_context(self.layer, '截至第 3 条陈述，比较 Alice 在 team 中对 proposal 是否 fair 的信念与词义标准。', source)
        arg = prepare_person_context(self.layer, QUERY, source, as_of_statement=3)
        self.assertEqual(belief_rows(en), belief_rows(cn))
        self.assertEqual(belief_rows(en), belief_rows(arg))
        receipt = en.preparation_receipt['source_selection']
        self.assertEqual(receipt['original_source_sha256'], hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(receipt['selected_source_sha256'], hashlib.sha256('\n'.join((D, F, B)).encode()).hexdigest())
        self.assertEqual(receipt['source_statement_numbers'], [1, 2, 3])
        self.assertNotIn(receipt['original_source_sha256'], en.messages[-1]['content'])

    def test_invalid_conflicting_nested_or_future_scope_never_exposes_full_source(self):
        for query, kwargs in (('At statement 99, ' + QUERY, {}), ('At statement 0, ' + QUERY, {}),
            ('At statement two, ' + QUERY, {}), ('At statement 2, ' + QUERY, {'as_of_statement': 3}),
            ('At statement 3, At statement 2, ' + QUERY, {})):
            p = prepare_person_context(self.layer, query, SOURCE, **kwargs)
            self.assertFalse(p.context.evidence)
            self.assertFalse(belief_rows(p))
            self.assertNotIn(R, p.messages[-1]['content'])
        for index in (0, 25, True, '3'):
            with self.assertRaises(ValueError):
                prepare_person_context(self.layer, QUERY, SOURCE, as_of_statement=index)

    def test_unknown_question_after_valid_scope_preserves_only_reader_prefix(self):
        p = prepare_person_context(self.layer, 'At statement 1, Explain their secret motive.', SOURCE)
        self.assertEqual(json.loads(p.messages[-1]['content'])['sources'][0]['text'], D)
        self.assertNotIn(F, p.messages[-1]['content'])
        self.assertFalse(p.preparation_receipt['specialized_cognition_treatment'])
        self.assertNotIn('checked_epistemic', json.loads(p.messages[-1]['content']))

    def test_ordinal_scope_is_counted_in_whole_state_budget(self):
        p = prepare_person_context(self.layer, QUERY, SOURCE, as_of_statement=3, max_context_chars=512)
        wire = payload(p)
        self.assertFalse(wire['composed_cognition']['operation_contexts'])
        size = sum(len(json.dumps(wire[k], ensure_ascii=False, sort_keys=True)) for k in ('composed_cognition', 'source_order_scope'))
        self.assertLessEqual(size, 512)
        self.assertNotIn(B, p.messages[-1]['content'])

    def test_one_final_call_only_selected_source_enters_all_actual_messages(self):
        calls = []
        result = answer_person_context(HCLCognitionLayer(lambda m: calls.append(m) or 'earlier source state'),
            'At statement 3, ' + QUERY, SOURCE, debug=True)
        self.assertEqual(calls, [list(result.prepared.messages)])
        self.assertEqual(result.prepared.preparation_receipt['actual_final_messages'], calls[0])
        self.assertFalse(result.prepared.preparation_receipt['source_selection']['future_source_enters_preparation'])
        self.assertEqual(result.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertNotIn(R, str(calls))
