"""Existing capability composition: actual ordinary input and no boundary bridges."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from hcl.v1 import (CognitionRequest, HCLCognitionLayer, PerspectiveMode,
    expand_cognition_context)
from hcl.v1.composition import prepare_composed_answer, answer_composed
from hcl.v1.cg04 import prepare_preference_narrative
from hcl.v1.cg05 import prepare_concept_narrative
from scripts.cg03_external_package import CASES, _premise

P = 'Alice: As medic in team, I prefer safety over speed if rain is true.'
D = 'Alice: In team, by fair I mean consent is true.'
TAIL = '\n'.join((P, 'Narrator: In team, rain is true.', D,
    'Narrator: In team, proposal has consent true.', 'Alice: In team, proposal is not fair.'))
SOURCE = CASES[-1]['narrative'] + '\n' + TAIL
QUERY = 'Explain the expressed preference, local meaning of fair, and conditional responsibility basis separately.'


def requests(text=SOURCE):
    return (CognitionRequest('Explain responsibility basis', narrative=text, target_actor='Alice',
        responsibility_analysis=True, responsibility_premises=(_premise(CASES[-1]),)),
        CognitionRequest('Explain preference', narrative=text, target_actor='Alice',
        preference_analysis=True, preference_role='medic', preference_context='team'),
        CognitionRequest('Interpret fair', narrative=text, target_actor='Alice',
        concept_analysis=True, concept_context='team', concept_term='fair', concept_item='proposal'))


def transmitted(prepared):
    return json.loads(prepared.messages[-1]['content'])['composed_cognition']


def states(prepared):
    return {r['operation']: expand_cognition_context(r['cognition_context'])
            for r in transmitted(prepared)['operation_contexts']}


class CompositionTests(unittest.TestCase):
    def test_one_ordinary_source_three_real_checks_one_actual_answer_call(self):
        calls = []
        layer = HCLCognitionLayer(lambda messages: calls.append(messages) or 'separate source explanations')
        result = answer_composed(layer, QUERY, requests(), debug=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], list(result.prepared.messages))
        self.assertEqual(result.prepared.preparation_receipt['actual_final_messages'], calls[0])
        self.assertEqual(result.prepared.preparation_receipt['extraction_provider_calls'], 0)
        row = states(result.prepared)
        self.assertEqual(row['responsibility']['responsibility']['checked']['status'], 'SOURCE_FACTORS_CHECKED')
        self.assertEqual(row['preferences']['preferences']['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertEqual(row['concepts']['concepts']['checked']['readings'][0]['state'], 'DECLARED_COUNTEREXAMPLE')
        self.assertEqual(row['concepts']['concepts']['checked']['moral_truth'], 'NOT_INFERRED')
        factor = {f['factor']: f['state'] for f in row['responsibility']['responsibility']['checked']['factors']}
        self.assertEqual(factor['CONTROL'], 'CONTRADICTED_CLAIM')
        self.assertEqual(factor['STATED_INTENTION'], 'UNKNOWN')
        self.assertEqual(row['responsibility']['responsibility']['checked']['premise_assessments'][0]['result'],
                         'CONDITIONALLY_NOT_SUPPORTED')

    def test_local_counterexample_does_not_rewrite_preference_or_responsibility(self):
        layer = HCLCognitionLayer(lambda _: '')
        before = states(prepare_composed_answer(layer, QUERY, requests(SOURCE.rsplit('\n', 1)[0])))
        after = states(prepare_composed_answer(layer, QUERY, requests()))
        self.assertEqual(before['concepts']['concepts']['checked']['readings'][0]['state'], 'CRITERIA_MET')
        self.assertEqual(after['concepts']['concepts']['checked']['readings'][0]['state'], 'DECLARED_COUNTEREXAMPLE')
        self.assertEqual(before['responsibility']['responsibility']['checked']['factors'][3]['state'],
                         after['responsibility']['responsibility']['checked']['factors'][3]['state'])
        self.assertEqual(before['preferences']['preferences']['checked']['statements'][0]['state'],
                         after['preferences']['preferences']['checked']['statements'][0]['state'])

    def test_one_operation_parse_failure_is_preserved_not_borrowed_support(self):
        text = SOURCE.replace(D, 'Alice: In team, by fair I mean perhaps consent.')
        result = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests(text))
        row = states(result)
        self.assertNotIn('concepts', row['concepts'])
        self.assertTrue(row['concepts']['uncertainty'])
        self.assertEqual(row['concepts']['preparation']['failure'], 'invalid_or_ambiguous_concept_source')
        self.assertTrue(row['preferences']['preferences']['checked']['statements'])
        self.assertIn('Failure or missing state in one operation is unresolved', result.messages[0]['content'])

    def test_independent_concept_revision_does_not_break_preference_preparation(self):
        text = SOURCE + '\nAlice: In team, I now use fair to mean consent is false instead of consent is true.'
        result = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests(text))
        row = states(result)
        self.assertEqual(row['preferences']['preferences']['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertEqual([d['state'] for d in row['concepts']['concepts']['checked']['readings']],
                         ['SUPERSEDED_LOCAL', 'CRITERIA_NOT_MET'])

    def test_context_condition_is_not_an_object_property_or_narrator_usage(self):
        row = states(prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests()))
        self.assertEqual([p['key'] for p in row['concepts']['concepts']['case_input']['properties']], ['consent'])
        self.assertTrue(all(u['actor_id'] != 'Narrator' for u in row['concepts']['concepts']['case_input']['uses']))

    def test_mixed_actor_source_time_and_perspective_rejected_before_preparation(self):
        layer = HCLCognitionLayer(lambda _: '')
        original = requests()
        bad_cases = (replace(original[1], target_actor='Bob'),
                     replace(original[1], narrative=TAIL),
                     replace(original[1], perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        for bad in bad_cases:
            with self.subTest(bad=bad), patch.object(layer, 'prepare') as prepare, self.assertRaises(ValueError):
                prepare_composed_answer(layer, QUERY, (original[0], bad))
            prepare.assert_not_called()

    def test_ordinary_character_access_not_inferred_by_composition(self):
        reqs = tuple(replace(r, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE) for r in requests())
        with self.assertRaises(ValueError):
            prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, reqs)

    def test_typed_character_views_keep_hidden_sources_out_of_all_operations(self):
        text = P + '\n' + D + '\nNarrator: In team, rain is true.\nNarrator: In team, proposal has consent true.'
        pp = prepare_preference_narrative(text, 'Alice', 'medic', 'team')
        cp = prepare_concept_narrative(text, 'Alice', 'team', 'fair', 'proposal')
        # Identical upstream records for both operations, with explicit alias
        # alignment of the already source-validated semantic case.
        aliases = {c.event_id: p.event_id for c, p in zip(cp.events, pp.events)}
        definition = replace(cp.case.definitions[0], source_event_id=aliases[cp.case.definitions[0].source_event_id])
        properties = tuple(replace(p, source_event_id=aliases[p.source_event_id]) for p in cp.case.properties)
        concept = replace(cp.case, definitions=(definition,), properties=properties)
        evidence = tuple(replace(e, metadata={'public': True}) if e.raw_text in (P, D) else e for e in pp.events)
        reqs = (CognitionRequest('Preference', target_actor='Alice', evidence=evidence, preference_case=pp.case,
                perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE),
            CognitionRequest('Concept', target_actor='Alice', evidence=evidence, concept_case=concept,
                perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        p = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, reqs)
        body = p.messages[1]['content']
        self.assertNotIn('Narrator: In team, rain is true.', body)
        self.assertNotIn(evidence[2].event_id, body)
        self.assertNotIn('Narrator: In team, proposal has consent true.', body)
        self.assertNotIn(evidence[3].event_id, body)
        row = states(p)
        self.assertEqual(row['preferences']['preferences']['checked']['statements'][0]['state'], 'CONDITION_UNRESOLVED')
        self.assertEqual(row['concepts']['concepts']['checked']['readings'][0]['state'], 'CRITERIA_UNRESOLVED')

    def test_duplicate_operation_and_non_person_direct_task_rejected(self):
        layer = HCLCognitionLayer(lambda _: '')
        for reqs in ((requests()[1], requests()[1]), (requests()[1], CognitionRequest('Translate hello'))):
            with self.assertRaises(ValueError):
                prepare_composed_answer(layer, QUERY, reqs)

    def test_total_budget_fail_closed_without_partial_operation_selection(self):
        result = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), QUERY, requests(), max_context_chars=512)
        self.assertEqual(transmitted(result)['operation_contexts'], [])
        self.assertEqual(result.preparation_receipt['failure'], 'composition_context_budget_exceeded')
        self.assertNotIn(P, result.messages[1]['content'])
        self.assertNotIn(D, result.messages[1]['content'])
