"""Concept boundaries and actual ordinary-text treatment, without providers."""
from dataclasses import replace
from datetime import datetime, timedelta
import json
import unittest

from hcl.v1 import (CognitionRequest, CognitionRouter, HCLCognitionLayer, PerspectiveMode,
    check_concepts, project_concepts, prepare_concept_narrative)

D = 'Alice: In team, by fair I mean transparent is true and consent is true.'
B = 'Bob: In team, by fair I mean consent is true.'
T = 'Narrator: In team, proposal has transparent true.'
F = 'Narrator: In team, proposal has consent false.'
REV = 'Alice: In team, I now use fair to mean consent is true instead of transparent is true and consent is true.'


def prep(text):
    return prepare_concept_narrative(text, 'Alice', 'team', 'fair', 'proposal')


def check(text, **scope):
    p = prep(text)
    if p.failure:
        raise AssertionError(p.failure)
    return check_concepts(p.case, p.events, **scope)


def request(text=D, **kwargs):
    return CognitionRequest('Explain the local meaning of fair', target_actor='Alice',
        narrative=text, concept_analysis=True, concept_context='team', concept_term='fair',
        concept_item='proposal', **kwargs)


class ConceptChecks(unittest.TestCase):
    def test_two_speakers_same_word_different_readings(self):
        r = check(D + '\n' + B + '\n' + T + '\nNarrator: In team, proposal has consent true.')
        self.assertEqual([d['state'] for d in r['readings']], ['CRITERIA_MET'] * 2)
        self.assertEqual(r['reading_relation'], 'MULTIPLE_LOCAL_READINGS')
        self.assertEqual(r['focal_reading_ids'], ['def-1'])
        self.assertEqual(r['shared_meaning'], 'NOT_ESTABLISHED')
        self.assertEqual(r['moral_truth'], 'NOT_INFERRED')
        self.assertEqual(r['misunderstanding_or_deception'], 'NOT_INFERRED')

    def test_applicability_met_not_met_unknown_contested(self):
        for source, state, criteria in ((D, 'CRITERIA_UNRESOLVED', ['UNKNOWN', 'UNKNOWN']),
            (D + '\n' + T, 'CRITERIA_UNRESOLVED', ['MET_BY_SOURCE_CLAIM', 'UNKNOWN']),
            (D + '\n' + T + '\n' + F, 'CRITERIA_NOT_MET', ['MET_BY_SOURCE_CLAIM', 'NOT_MET_BY_SOURCE_CLAIM']),
            (D + '\n' + T + '\n' + F + '\nNarrator: In team, proposal has consent true.',
             'CRITERIA_UNRESOLVED', ['MET_BY_SOURCE_CLAIM', 'CONTESTED'])):
            with self.subTest(state=state):
                r = check(source)['readings'][0]
                self.assertEqual(r['state'], state)
                self.assertEqual([c['state'] for c in r['criterion_checks']], criteria)

    def test_false_criterion_supported_explicitly(self):
        r = check('Alice: In team, by fair I mean consent is false.\n' + F)
        self.assertEqual(r['readings'][0]['state'], 'CRITERIA_MET')

    def test_counterexample_preserved_without_general_redefinition(self):
        r = check(D + '\n' + T + '\nNarrator: In team, proposal has consent true.\n'
            'Alice: In team, proposal is not fair.')['readings'][0]
        self.assertEqual(r['state'], 'DECLARED_COUNTEREXAMPLE')
        self.assertTrue(r['counterexample_conflicts_with_criteria'])
        self.assertEqual(len(r['criteria']), 2)

    def test_usage_cannot_fill_missing_properties_or_become_definition(self):
        r = check(D + '\nAlice: In team, proposal is fair.')['readings'][0]
        self.assertEqual(r['state'], 'CRITERIA_UNRESOLVED')
        self.assertIsNone(prep('Alice: In team, proposal is fair.').case)
        self.assertEqual(check(D + '\n' + F + '\nAlice: In team, proposal is fair.')['readings'][0]['state'],
                         'CONTESTED_APPLICATION')

    def test_opposed_application_is_contested(self):
        r = check(D + '\nAlice: In team, proposal is fair.\nAlice: In team, proposal is not fair.')
        self.assertEqual(r['readings'][0]['state'], 'CONTESTED_APPLICATION')

    def test_revision_preserves_other_actor_scope_and_term(self):
        other = 'Alice: In family, by fair I mean consent is true.'
        term = 'Alice: In team, by safe I mean transparent is true.'
        r = check('\n'.join((D, B, other, term, REV, F)))
        self.assertEqual([d['state'] for d in r['readings']],
            ['SUPERSEDED_LOCAL', 'CRITERIA_NOT_MET', 'OTHER_SCOPE', 'OTHER_SCOPE', 'CRITERIA_NOT_MET'])
        self.assertEqual(r['readings'][-1]['supersedes_id'], 'def-1')

    def test_different_later_definition_is_not_implicit_revision(self):
        r = check(D + '\nAlice: In team, by fair I mean consent is false.')
        self.assertEqual(r['reading_relation'], 'MULTIPLE_LOCAL_READINGS')
        self.assertTrue(all(d['state'] == 'CRITERIA_UNRESOLVED' for d in r['readings']))

    def test_third_party_definition_attribution_only(self):
        r = check('Bob: In team, Alice uses fair to mean consent is true.\n' + F)
        self.assertEqual(r['readings'][0]['state'], 'ATTRIBUTED_ONLY')
        self.assertEqual(r['focal_reading_ids'], [])
        self.assertEqual(r['reading_relation'], 'NO_SOURCE_READING')

    def test_prior_application_does_not_follow_revised_meaning(self):
        r = check(D + '\nAlice: In team, proposal is not fair.\n' + REV)
        self.assertEqual(r['readings'][-1]['state'], 'CRITERIA_UNRESOLVED')
        self.assertEqual(r['readings'][-1]['application_source_ids'], [])

    def test_other_item_and_context_cannot_fill_properties(self):
        r = check(D + '\nNarrator: In family, proposal has consent true.\n'
            'Narrator: In team, alternative has transparent true.')
        self.assertTrue(all(c['state'] == 'UNKNOWN' for c in r['readings'][0]['criterion_checks']))

    def test_source_actor_definition_and_property_spoofing_rejected(self):
        p = prep(D + '\n' + T)
        for d in (replace(p.case.definitions[0], actor_id='Bob'),
                  replace(p.case.definitions[0], term='safe'),
                  replace(p.case.definitions[0], authority='EXPLICIT_NARRATOR')):
            with self.subTest(d=d), self.assertRaises(ValueError):
                check_concepts(replace(p.case, definitions=(d,)), p.events)
        with self.assertRaises(ValueError):
            check_concepts(replace(p.case, properties=(replace(p.case.properties[0], value=False),)), p.events)
        with self.assertRaises(ValueError):
            check_concepts(p.case, (replace(p.events[0], raw_text='This is false: ' + D), p.events[1]))

    def test_revision_missing_ambiguous_cross_actor_and_future_rejected(self):
        for source in (REV, D + '\n' + D + '\n' + REV, B + '\n' + REV):
            self.assertIsNone(prep(source).case)
        p = prep(D + '\n' + REV)
        with self.assertRaises(ValueError):
            check_concepts(p.case, (p.events[0], replace(p.events[1], valid_time=p.events[0].valid_time)))

    def test_partial_grammar_fails_closed_and_keeps_full_source(self):
        p = prep(D + '\nAlice: In team, by fair I mean perhaps consent.\n' + F)
        self.assertIsNone(p.case)
        self.assertEqual(len(p.events), 3)
        self.assertEqual(p.events[-1].raw_text, F)

    def test_bounds_duplicates_wrong_types_rejected(self):
        p = prep(D)
        with self.assertRaises(ValueError):
            check_concepts(p.case, p.events * 2)
        with self.assertRaises(ValueError):
            replace(p.case, definitions=tuple(replace(p.case.definitions[0], definition_id=f'd-{i}',
                source_event_id=f'e-{i}') for i in range(9)))
        self.assertIsNone(prep('Alice: In team, by fair I mean consent is true and consent is false.').case)


class ConceptViews(unittest.TestCase):
    def test_character_and_observer_do_not_receive_reader_sources(self):
        p = prep(D + '\n' + T)
        for mode, kwargs in (('CHARACTER_PERSPECTIVE', {}),
                             ('OBSERVER_ABOUT_TARGET', {'observer_actor': 'Bob'})):
            r = project_concepts(p.case, p.events, mode=mode, **kwargs)
            self.assertEqual(r['definitions'], [])
            self.assertEqual(r['properties'], [])
        events = tuple(replace(e, metadata={'public': True}) for e in p.events)
        self.assertEqual(len(project_concepts(p.case, events, mode='CHARACTER_PERSPECTIVE')['definitions']), 1)

    def test_hidden_property_unknown_and_hidden_revision_reference_removed(self):
        p = prep(D + '\n' + T + '\n' + REV)
        events = (p.events[0], p.events[1], replace(p.events[2], metadata={'public': True}))
        r = check_concepts(p.case, events, mode='CHARACTER_PERSPECTIVE')
        self.assertNotIn('def-1', json.dumps(r))
        self.assertNotIn('transparent', json.dumps(r))
        self.assertEqual(r['readings'][0]['state'], 'CRITERIA_UNRESOLVED')

    def test_event_and_record_cutoffs_preserve_earlier_meaning(self):
        p = prep(D + '\n' + REV)
        r = check_concepts(p.case, p.events, event_time=p.events[0].valid_time)
        self.assertEqual(len(r['readings']), 1)
        self.assertEqual(r['readings'][0]['state'], 'CRITERIA_UNRESOLVED')
        late = (datetime.fromisoformat(p.events[1].recorded_at) + timedelta(days=1)).isoformat()
        r = check_concepts(p.case, (p.events[0], replace(p.events[1], recorded_at=late)),
                           knowledge_cutoff=p.events[1].recorded_at)
        self.assertEqual(len(r['readings']), 1)


class ConceptIntegration(unittest.TestCase):
    def test_explicit_route_ordinary_queries_stay_direct(self):
        for q in ('What is fairness?', '概念与人的语境', 'Define a concept'):
            self.assertTrue(CognitionRouter().plan(CognitionRequest(q)).direct)
        p = CognitionRouter().plan(request())
        self.assertTrue(p.concept_interpretation)
        self.assertFalse(p.contextual_preference or p.social_commitment or p.responsibility_structure)
        self.assertEqual(p.optional_capabilities, ('cg05_local_concept',))
        with self.assertRaises(ValueError):
            request(social_analysis=True)
        with self.assertRaises(ValueError):
            CognitionRequest('Meaning', concept_analysis=True)

    def test_ordinary_text_actual_model_messages_and_mechanism_only_ablation(self):
        calls = []
        receipt = HCLCognitionLayer(lambda messages: calls.append(messages) or 'local reading').answer(request(D + '\n' + T), debug=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], list(receipt.prepared.messages))
        self.assertEqual(receipt.prepared.preparation_receipt['extraction_provider_calls'], 0)
        on = json.loads(receipt.prepared.messages[1]['content'])
        off = HCLCognitionLayer(lambda _: '', concept_checker_enabled=False).prepare(request(D + '\n' + T))
        self.assertEqual(receipt.prepared.messages[0], off.messages[0])
        self.assertTrue(on['cognition_context']['concepts']['checked'])
        on['cognition_context']['concepts']['checked'] = {}
        self.assertEqual(on, json.loads(off.messages[1]['content']))

    def test_hidden_source_and_low_budget_not_in_final_context(self):
        p = HCLCognitionLayer(lambda _: '').prepare(request(perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertNotIn(D, p.messages[-1]['content'])
        self.assertEqual(p.context.concepts['case_input']['definitions'], [])
        p = HCLCognitionLayer(lambda _: '').prepare(request(max_context_chars=512))
        self.assertFalse(p.context.concepts)
        self.assertNotIn(D, p.messages[-1]['content'])

    def test_typed_view_does_not_infer_access_from_actor_name(self):
        p = prep(D)
        req = CognitionRequest('Local concept', evidence=p.events, target_actor='Alice', concept_case=p.case,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE)
        row = HCLCognitionLayer(lambda _: '').prepare(req)
        self.assertEqual(row.context.concepts['checked']['reading_relation'], 'NO_SOURCE_READING')
