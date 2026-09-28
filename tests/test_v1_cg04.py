"""Contextual preference correctness, ordinary input and bounded-view privacy."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v1 import (CognitionRequest, CognitionRouter, HCLCognitionLayer, PerspectiveMode,
    PreferenceCase, PreferenceCondition, PreferenceStatement, ContextConditionClaim,
    check_preferences, project_preferences, prepare_preference_narrative)


SELF = 'Alice: As medic in fieldwork, I prefer safety over speed'
OTHER = 'Alice: As courier in deliveries, I prefer speed over safety.'


def prepared(text, role='medic', context='fieldwork'):
    return prepare_preference_narrative(text, 'Alice', role, context)


def checked(text, role='medic', context='fieldwork'):
    p = prepared(text, role, context)
    if p.failure:
        raise AssertionError(p.failure)
    return check_preferences(p.case, p.events)


class PreferenceChecks(unittest.TestCase):
    def test_scope_locality_and_no_cross_context_conflict(self):
        row = checked(SELF + '.\n' + OTHER)
        self.assertEqual([r['state'] for r in row['statements']],
            ['APPLICABLE_SOURCE_CLAIM', 'OTHER_SCOPE'])
        self.assertEqual(row['conflict_state'], 'NO_OBSERVED_CONFLICT')
        courier = checked(SELF + '.\n' + OTHER, 'courier', 'deliveries')
        self.assertEqual([r['state'] for r in courier['statements']],
            ['OTHER_SCOPE', 'APPLICABLE_SOURCE_CLAIM'])
        self.assertEqual(row['global_value_ranking'], 'NOT_INFERRED')

    def test_condition_supported_false_unknown_and_contested(self):
        source = SELF + ' if rain is true.'
        for tail, state, cond in (
            ('', 'CONDITION_UNRESOLVED', 'UNKNOWN'),
            ('\nNarrator: In fieldwork, rain is true.', 'APPLICABLE_SOURCE_CLAIM', 'MET_BY_SOURCE_CLAIM'),
            ('\nNarrator: In fieldwork, rain is false.', 'CONDITION_NOT_MET', 'NOT_MET_BY_SOURCE_CLAIM'),
            ('\nNarrator: In fieldwork, rain is true.\nNarrator: In fieldwork, rain is false.',
             'CONDITION_UNRESOLVED', 'CONTESTED')):
            with self.subTest(state=state):
                row = checked(source + tail)['statements'][0]
                self.assertEqual(row['state'], state)
                self.assertEqual(row['condition_checks'][0]['state'], cond)

    def test_multiple_conditions_and_other_context_not_used(self):
        text = (SELF + ' if rain is true and delay is false.\n'
            'Narrator: In deliveries, rain is true.\nNarrator: In fieldwork, delay is false.')
        row = checked(text)['statements'][0]
        self.assertEqual(row['state'], 'CONDITION_UNRESOLVED')
        self.assertEqual([r['state'] for r in row['condition_checks']], ['UNKNOWN', 'MET_BY_SOURCE_CLAIM'])

    def test_explicit_revision_changes_only_its_scope(self):
        row = checked(SELF + '.\n' + OTHER + '\n'
            'Alice: As medic in fieldwork, I now prefer speed over safety instead of safety over speed.')
        self.assertEqual([r['state'] for r in row['statements']],
            ['SUPERSEDED_LOCAL', 'OTHER_SCOPE', 'APPLICABLE_SOURCE_CLAIM'])
        self.assertEqual(row['statements'][2]['supersedes_id'], 'pref-1')
        self.assertEqual(row['conflict_state'], 'NO_OBSERVED_CONFLICT')

    def test_new_opposed_statement_does_not_implicitly_revise(self):
        row = checked(SELF + '.\nAlice: As medic in fieldwork, I prefer speed over safety.')
        self.assertEqual([r['state'] for r in row['statements']], ['APPLICABLE_SOURCE_CLAIM'] * 2)
        self.assertEqual(row['conflict_state'], 'UNRESOLVED_CONFLICT')
        self.assertEqual(row['conflicts'][0]['statement_ids'], ['pref-1', 'pref-2'])
        self.assertEqual(row['moral_winner'], 'NOT_INFERRED')

    def test_longer_cycle_is_conflict_without_transitive_ranking(self):
        text = '\n'.join('Alice: As medic in fieldwork, I prefer ' + a + ' over ' + b + '.'
            for a, b in [('safety', 'speed'), ('speed', 'privacy'), ('privacy', 'safety')])
        row = checked(text)
        self.assertEqual(row['conflict_state'], 'UNRESOLVED_CONFLICT')
        self.assertEqual(row['uncompared_values'], 'UNRESOLVED_NO_TRANSITIVE_RANKING')

    def test_third_party_attribution_is_not_actor_preference(self):
        row = checked('Bob: In fieldwork, Alice as medic prefers safety over speed.')
        self.assertEqual(row['statements'][0]['state'], 'ATTRIBUTED_ONLY')
        narrator = checked('Narrator: In fieldwork, Alice as medic prefers safety over speed.')
        self.assertEqual(narrator['statements'][0]['authority'], 'EXPLICIT_NARRATOR')
        self.assertEqual(narrator['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')

    def test_observed_choice_does_not_generate_preference(self):
        p = prepared('Alice: I chose the safer route.')
        self.assertEqual(p.failure, 'no_explicit_preference')
        self.assertIsNone(p.case)
        row = checked(SELF + '.\nAlice: I chose speed today.')
        self.assertEqual(len(row['statements']), 1)

    def test_ambiguous_revision_and_unsupported_prose_fail_closed(self):
        for text in (SELF + '.', SELF + '.\n' + SELF + '.', OTHER):
            bad = prepared(text + '\nAlice: As medic in fieldwork, I now prefer speed over safety instead of safety over speed.')
            if text == SELF + '.':
                self.assertIsNone(bad.failure)
            else:
                self.assertIsNone(bad.case)
        for text in ('Alice: As medic in fieldwork, I now prefer speed over safety.',
                     'Alice: My global preference weights are safety 9 and speed 2.',
                     SELF + ' if perhaps it rains.'):
            self.assertIsNone(prepared(text).case)

    def test_typed_payload_cannot_invert_source_or_fabricate_revision(self):
        p = prepared(SELF + '.')
        statement = p.case.statements[0]
        for fake in (replace(statement, preferred='speed', over='safety'),
                     replace(statement, quote=OTHER),
                     replace(statement, authority='EXPLICIT_NARRATOR'),
                     replace(statement, supersedes_id='secret'),
                     replace(statement, conditions=(PreferenceCondition('rain', True),))):
            with self.subTest(fake=fake), self.assertRaises(ValueError):
                check_preferences(replace(p.case, statements=(fake,)), p.events)

    def test_missing_duplicate_and_large_input_rejected(self):
        p = prepared(SELF + '.')
        with self.assertRaises(ValueError):
            check_preferences(p.case, ())
        with self.assertRaises(ValueError):
            check_preferences(p.case, p.events + p.events)
        with self.assertRaises(ValueError):
            replace(p.case, statements=tuple(replace(p.case.statements[0], statement_id=f'p-{i}') for i in range(9)))
        with self.assertRaises(ValueError):
            PreferenceCondition('rain', 1)

    def test_spoofed_role_context_and_surrounding_negation_rejected(self):
        p = prepared(SELF + '.')
        for fake in (replace(p.case.statements[0], role='courier'),
                     replace(p.case.statements[0], context='deliveries')):
            with self.assertRaises(ValueError):
                check_preferences(replace(p.case, statements=(fake,)), p.events)
        negated = replace(p.events[0], raw_text='This quoted sentence is false: ' + p.events[0].raw_text)
        with self.assertRaises(ValueError):
            check_preferences(p.case, (negated,))

    def test_revision_cannot_point_to_other_scope_or_future(self):
        p = prepared(SELF + '.\n' + OTHER + '\n'
            'Alice: As medic in fieldwork, I now prefer speed over safety instead of safety over speed.')
        bad = replace(p.case.statements[-1], supersedes_id='pref-2')
        with self.assertRaises(ValueError):
            check_preferences(replace(p.case, statements=p.case.statements[:2] + (bad,)), p.events)
        earlier = replace(p.events[-1], valid_time=p.events[0].valid_time)
        with self.assertRaises(ValueError):
            check_preferences(p.case, p.events[:2] + (earlier,))


class PreferenceViews(unittest.TestCase):
    def test_reader_character_observer_sources(self):
        p = prepared(SELF + ' if rain is true.\nNarrator: In fieldwork, rain is true.')
        for mode, kwargs in [('CHARACTER_PERSPECTIVE', {}),
                             ('OBSERVER_ABOUT_TARGET', {'observer_actor': 'Bob'})]:
            row = project_preferences(p.case, p.events, mode=mode, **kwargs)
            self.assertEqual(row['statements'], [])
            self.assertEqual(row['conditions'], [])
        public = tuple(replace(e, metadata={'public': True}) for e in p.events)
        self.assertEqual(check_preferences(p.case, public, mode='CHARACTER_PERSPECTIVE')['statements'][0]['state'],
                         'APPLICABLE_SOURCE_CLAIM')

    def test_hidden_condition_is_unknown_not_false(self):
        p = prepared(SELF + ' if rain is true.\nNarrator: In fieldwork, rain is true.')
        events = (replace(p.events[0], metadata={'public': True}), p.events[1])
        row = check_preferences(p.case, events, mode='CHARACTER_PERSPECTIVE')
        self.assertEqual(row['statements'][0]['state'], 'CONDITION_UNRESOLVED')
        self.assertNotIn(p.events[1].event_id, json.dumps(row))

    def test_hidden_prior_pointer_and_later_revision_not_leaked(self):
        p = prepared(SELF + '.\nAlice: As medic in fieldwork, I now prefer speed over safety instead of safety over speed.')
        events = (p.events[0], replace(p.events[1], metadata={'public': True}))
        row = project_preferences(p.case, events, mode='CHARACTER_PERSPECTIVE')
        self.assertIsNone(row['statements'][0]['supersedes_id'])
        self.assertNotIn('pref-1', json.dumps(row))
        earlier = check_preferences(p.case, p.events, event_time=p.events[0].valid_time)
        self.assertEqual(earlier['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertNotIn('pref-2', json.dumps(earlier))

    def test_late_record_is_excluded_without_retrospective_revision(self):
        p = prepared(SELF + '.\nAlice: As medic in fieldwork, I now prefer speed over safety instead of safety over speed.')
        later = (datetime.fromisoformat(p.events[1].recorded_at) + timedelta(days=1)).isoformat()
        events = (p.events[0], replace(p.events[1], recorded_at=later))
        row = check_preferences(p.case, events, knowledge_cutoff=p.events[1].recorded_at)
        self.assertEqual(len(row['statements']), 1)
        self.assertEqual(row['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')

    def test_condition_claim_cannot_invert_or_use_other_speaker(self):
        p = prepared(SELF + ' if rain is true.\nNarrator: In fieldwork, rain is true.')
        c = p.case.conditions[0]
        with self.assertRaises(ValueError):
            check_preferences(replace(p.case, conditions=(replace(c, value=False),)), p.events)
        with self.assertRaises(ValueError):
            check_preferences(p.case, (p.events[0], replace(p.events[1], actor_id='Bob')))

    def test_future_condition_does_not_fill_an_earlier_view(self):
        p = prepared(SELF + ' if rain is true.\nNarrator: In fieldwork, rain is true.')
        row = check_preferences(p.case, p.events, event_time=p.events[0].valid_time)
        self.assertEqual(row['statements'][0]['state'], 'CONDITION_UNRESOLVED')
        self.assertEqual(row['statements'][0]['condition_checks'][0]['source_event_ids'], [])


class PreferenceIntegration(unittest.TestCase):
    def request(self, text=SELF + '.', **kwargs):
        return CognitionRequest('Explain contextual preference', target_actor='Alice',
            narrative=text, preference_analysis=True, preference_role='medic',
            preference_context='fieldwork', **kwargs)

    def test_explicit_route_and_unrelated_tasks_direct(self):
        for query in ('What values do people have?', '情境中的价值冲突是什么？', 'What is your preference?'):
            self.assertTrue(CognitionRouter().plan(CognitionRequest(query)).direct)
        p = CognitionRouter().plan(self.request())
        self.assertTrue(p.contextual_preference)
        self.assertFalse(p.explanation or p.social_commitment or p.responsibility_structure)
        self.assertIn('cg04_contextual_preference', p.optional_capabilities)
        with self.assertRaises(ValueError):
            self.request(social_analysis=True)
        with self.assertRaises(ValueError):
            CognitionRequest('preferences', preference_analysis=True)

    def test_ordinary_input_debug_and_real_ablation(self):
        calls = []
        result = HCLCognitionLayer(lambda messages: calls.append(messages) or 'bounded answer').answer(self.request(), debug=True)
        self.assertEqual(len(calls), 1)
        p = result.prepared
        self.assertEqual(p.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(p.preparation_receipt['input']['narrative'], SELF + '.')
        self.assertEqual(p.context.preferences['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        off = HCLCognitionLayer(lambda _: '', preference_checker_enabled=False).prepare(self.request())
        self.assertEqual(p.messages[0], off.messages[0])
        left, right = json.loads(p.messages[1]['content']), json.loads(off.messages[1]['content'])
        self.assertEqual(left['cognition_context']['preferences']['case_input'], right['cognition_context']['preferences']['case_input'])
        left['cognition_context']['preferences']['checked'] = {}
        self.assertEqual(left, right)

    def test_final_messages_do_not_expose_hidden_statement(self):
        p = HCLCognitionLayer(lambda _: '').prepare(self.request(
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertNotIn(SELF, p.messages[-1]['content'])
        self.assertEqual(p.context.preferences['case_input']['statements'], [])
        self.assertTrue(p.context.uncertainty)

    def test_typed_route_and_bounded_context_fail_closed(self):
        parsed = prepared(SELF + '.')
        req = CognitionRequest('Explain preference', evidence=parsed.events, target_actor='Alice',
            preference_case=parsed.case)
        self.assertTrue(HCLCognitionLayer(lambda _: '').prepare(req).context.preferences['checked'])
        limited = HCLCognitionLayer(lambda _: '').prepare(replace(req, max_context_chars=512))
        self.assertEqual(limited.context.preferences, {})
        self.assertNotIn(SELF, limited.messages[-1]['content'])
