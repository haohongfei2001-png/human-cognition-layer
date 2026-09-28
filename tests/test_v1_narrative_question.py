"""Ordinary multi-event integration uses only the requested existing operations."""
import json
import unittest
from hcl.v1 import (HCLCognitionLayer, PerspectiveMode, prepare_narrative_context,
    answer_narrative_context, expand_cognition_context, expand_composed_sources)

D = 'Alice: In team, by fair I mean consent is true and transparent is true.'
F = 'Narrator: In team, proposal has consent true.'
B = 'Alice: In team, I believe proposal is fair.'
P = 'Alice: As medic in team, I prefer safety over speed.'
BR = 'Alice: In team, I now believe proposal is unfair instead of proposal is fair.'
DR = 'Alice: In team, I now use fair to mean consent is true instead of consent is true and transparent is true.'
PR = 'Alice: As medic in team, I now prefer speed over safety instead of safety over speed.'
SOURCE = '\n'.join(('Event briefing:', D, F, B, P, 'Event decision:', DR, BR, PR))
INNER = "Explain Alice's belief, meaning of fair for proposal and preferences as medic in team."
QUERY = 'Across events, ' + INNER


def wire(p):
    return json.loads(p.messages[-1]['content'])['narrative_cognition']


def contexts(snapshot):
    state = expand_composed_sources(snapshot['state'])
    return {r['operation']: expand_cognition_context(r['cognition_context']) for r in state['operation_contexts']}


class NarrativeQuestionTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def test_three_operations_across_events_keep_real_local_revision_and_provenance(self):
        p = prepare_narrative_context(self.layer, QUERY, SOURCE)
        a, b = wire(p)['snapshots']
        self.assertEqual(list(contexts(a)), ['belief', 'concepts', 'preferences'])
        old, new = contexts(a), contexts(b)
        self.assertEqual(old['belief']['belief'][0]['status'], 'AFFIRMED')
        self.assertEqual({r['proposition_key']: r['status'] for r in new['belief']['belief']},
            {'team/proposal/fair': 'SUPERSEDED', 'team/proposal/unfair': 'AFFIRMED'})
        self.assertTrue(any(r['state'] == 'SUPERSEDED_LOCAL' for r in new['concepts']['concepts']['checked']['readings']))
        pref = new['preferences']['preferences']['checked']['statements']
        self.assertTrue(any(r['preferred'] == 'speed' and r['state'] == 'APPLICABLE_SOURCE_CLAIM' for r in pref))
        self.assertTrue(any(r['state'] == 'SUPERSEDED_LOCAL' for r in pref))
        self.assertNotIn(BR, json.dumps(a))
        self.assertEqual(b['source_path'], ['briefing', 'decision'])
        self.assertEqual(wire(p)['event_selection']['calendar_time'], 'NOT_ESTABLISHED')
        for s in wire(p)['snapshots']:
            bound = {(r['operation'], r['source_event_id']) for r in s['source_bindings']}
            for op, c in contexts(s).items():
                self.assertTrue(all((op, e['event_id']) in bound for e in c['evidence']))

    def test_question_selects_minimum_two_operations_despite_three_present(self):
        queries = (("Explain Alice's belief and preferences as medic in team.", ['belief', 'preferences']),
            ("Explain Alice's meaning of fair for proposal and preferences as medic in team.", ['concepts', 'preferences']),
            ("Compare Alice's belief and meaning of fair for proposal in team.", ['belief', 'concepts']))
        for inner, expected in queries:
            p = prepare_narrative_context(self.layer, 'Across events, ' + inner, SOURCE)
            self.assertTrue(all(list(contexts(s)) == expected for s in wire(p)['snapshots']))
            self.assertNotIn('responsibility', contexts(wire(p)['snapshots'][-1]))
            self.assertEqual(p.preparation_receipt['extraction_provider_calls'], 0)

    def test_selected_earlier_event_excludes_later_revision_and_malformed_semantics(self):
        future = SOURCE + '\nEvent later:\nAlice: In team, I perhaps believe proposal is unfair.'
        p = prepare_narrative_context(self.layer, 'At event briefing, ' + INNER, future)
        self.assertEqual(wire(p)['event_selection']['selected_event_ids'], ['briefing'])
        self.assertEqual(len(wire(p)['snapshots']), 1)
        self.assertEqual(contexts(wire(p)['snapshots'][0])['belief']['belief'][0]['status'], 'AFFIRMED')
        self.assertNotIn(BR, p.messages[-1]['content'])
        self.assertNotIn('perhaps believe', p.messages[-1]['content'])
        self.assertNotIn(p.preparation_receipt['original_source_sha256'], p.messages[-1]['content'])

    def test_private_exposure_cross_event_only_changes_later_view(self):
        inner = "Explain Alice's belief and preferences as medic in team."
        source = '\n'.join(('Event hidden:', P, 'Narrator: Alice and Bob heard the previous statement.',
            B, 'Event exposure:', 'Narrator: Alice and Bob heard the previous statement.'))
        p = prepare_narrative_context(self.layer, 'Across events, ' + inner, source,
            narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob')
        a, b = wire(p)['snapshots']
        self.assertFalse(contexts(a)['belief']['belief'])
        self.assertNotIn(B, json.dumps(a))
        self.assertEqual(contexts(b)['belief']['belief'][0]['status'], 'AFFIRMED')
        p = prepare_narrative_context(self.layer, 'Across events, ' + inner, source,
            narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Carol')
        self.assertNotIn(B, p.messages[-1]['content'])
        self.assertNotIn(P, p.messages[-1]['content'])

    def test_missing_operation_stays_unresolved_not_borrowed_from_other(self):
        source = '\n'.join(('Event first:', B, 'Event later:', BR))
        p = prepare_narrative_context(self.layer, 'Across events, Explain Alice\'s belief and preferences as medic in team.', source)
        self.assertTrue(contexts(wire(p)['snapshots'][-1])['belief']['belief'])
        self.assertTrue(all('preferences' not in contexts(s)['preferences'] for s in wire(p)['snapshots']))
        self.assertTrue(all(contexts(s)['preferences']['uncertainty'] for s in wire(p)['snapshots']))

    def test_action_choice_and_concept_do_not_supply_preference_or_intention(self):
        source = '\n'.join(('Event briefing:', D, F, B, 'Event action:', 'Alice: I chose speed.', 'Alice: I opened the gate.'))
        p = prepare_narrative_context(self.layer, 'Across events, Explain Alice\'s belief and preferences as medic in team.', source)
        c = contexts(wire(p)['snapshots'][-1])
        self.assertNotIn('preferences', c['preferences'])
        self.assertEqual(c['belief']['belief'][0]['status'], 'AFFIRMED')
        self.assertNotIn('intention', list(c))

    def test_unaffected_actor_role_and_context_do_not_follow_focal_revision(self):
        source = SOURCE.replace('Event decision:', 'Alice: As courier in home, I prefer safety over speed.\nEvent decision:')
        p = prepare_narrative_context(self.layer, QUERY, source)
        pref = contexts(wire(p)['snapshots'][-1])['preferences']['preferences']['checked']['statements']
        self.assertTrue(any(r['role'] == 'courier' and r['context'] == 'home' and r['preferred'] == 'safety' and
            r['state'] != 'SUPERSEDED_LOCAL' for r in pref))

    def test_invalid_or_missing_event_scope_refuses_full_narrative_fallback(self):
        for q, source, kw in (('At event missing, ' + INNER, SOURCE, {}),
            (QUERY, SOURCE.replace('Event decision:', 'Event briefing:'), {}),
            (QUERY, SOURCE.replace('Event briefing:', ''), {}),
            (QUERY, SOURCE.replace('Event decision:', 'Event ???:'), {}),
            (QUERY, 'Event first:\n' + B, {}),
            ('Across events, Explain Alice\'s belief.', SOURCE, {}),
            (QUERY, SOURCE, {'as_of_statement': 1})):
            p = prepare_narrative_context(self.layer, q, source, **kw)
            self.assertFalse(p.context.evidence)
            self.assertNotIn(B, p.messages[-1]['content'])

    def test_total_budget_counts_event_scope_and_drops_all_snapshots(self):
        for q in (QUERY, 'At event briefing, ' + INNER):
            p = prepare_narrative_context(self.layer, q, SOURCE, max_context_chars=512)
            self.assertEqual(wire(p)['snapshots'], [])
            self.assertLessEqual(len(json.dumps(wire(p), ensure_ascii=False, sort_keys=True)), 512)

    def test_chinese_event_and_question_run_exactly_one_final_answer(self):
        calls = []
        def adapter(messages):
            calls.append(messages)
            return 'bounded multi-event cognition'
        source = SOURCE.replace('Event briefing:', '事件 briefing：').replace('Event decision:', '事件 decision：')
        q = '按事件变化，解释 Alice 在 team 中的信念、对 proposal 的 fair 词义与 medic 角色偏好。'
        r = answer_narrative_context(HCLCognitionLayer(adapter), q, source, debug=True)
        self.assertEqual(calls, [list(r.prepared.messages)])
        self.assertEqual(r.prepared.preparation_receipt['actual_final_messages'], list(r.prepared.messages))
        self.assertEqual(r.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(len(wire(r.prepared)['snapshots']), 2)
