"""Multiple authorized source paths retain revision and access boundaries."""
import json
import unittest
from hcl.v1 import (AuthorizedSourceRecord, HCLCognitionLayer, PerspectiveMode,
    prepare_source_revision, answer_source_revision, expand_cognition_context,
    expand_composed_sources, NarrativePremise, FactorRequirement, ResponsibilityFactor)

B = 'Alice: In team, I believe proposal is fair.'
R = 'Alice: In team, I now believe proposal is unfair instead of proposal is fair.'
D = 'Alice: In team, by fair I mean consent is true and transparent is true.'
F = 'Narrator: In team, proposal has consent true.'
HEAR = 'Narrator: Alice and Bob heard the previous statement.'
QUERY = "Across sources, Explain Alice's belief."


def record(sid, text, after=None):
    return AuthorizedSourceRecord(sid, text, 'CALLER_AUTHORIZED', after)


def wire(prepared):
    return json.loads(prepared.messages[-1]['content'])['source_revision_cognition']


def contexts(snapshot):
    if snapshot['state_kind'] == 'composed_cognition':
        state = expand_composed_sources(snapshot['state'])
        return {r['operation']: expand_cognition_context(r['cognition_context']) for r in state['operation_contexts']}
    return {'single': expand_cognition_context(snapshot['state'])}


def beliefs(snapshot):
    return {(r['subject_agent_id'], r['proposition_key']): r['status']
        for c in contexts(snapshot).values() for r in c['belief']}


class SourceRevisionTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def test_real_before_after_belief_revision_and_unaffected_actor_context(self):
        old = '\n'.join((B, 'Bob: In team, I believe proposal is fair.',
            'Alice: In school, I believe proposal is fair.'))
        p = prepare_source_revision(self.layer, QUERY, (record('first', old), record('revision', R, 'first')))
        a, b = wire(p)['snapshots']
        self.assertEqual(beliefs(a)[('Alice', 'team/proposal/fair')], 'AFFIRMED')
        self.assertEqual(beliefs(b)[('Alice', 'team/proposal/fair')], 'SUPERSEDED')
        self.assertEqual(beliefs(b)[('Alice', 'team/proposal/unfair')], 'AFFIRMED')
        self.assertNotIn(('Bob', 'team/proposal/fair'), beliefs(b))
        bob = prepare_source_revision(self.layer, QUERY.replace('Alice', 'Bob'),
            (record('first', old), record('revision', R, 'first')))
        self.assertTrue(all(beliefs(s)[('Bob', 'team/proposal/fair')] == 'AFFIRMED'
            for s in wire(bob)['snapshots']))
        self.assertEqual(beliefs(b)[('Alice', 'school/proposal/fair')], 'AFFIRMED')
        self.assertEqual(b['source_conflicts'], [])
        self.assertNotIn(R, json.dumps(a))
        self.assertEqual(b['source_path'], ['first', 'revision'])
        self.assertEqual(wire(p)['calendar_time'], 'NOT_ESTABLISHED')

    def test_local_meaning_revision_and_contested_property_remain_separate(self):
        q = 'Across sources, Interpret Alice\'s meaning of fair for proposal in team.'
        revision = 'Alice: In team, I now use fair to mean consent is true instead of consent is true and transparent is true.'
        p = prepare_source_revision(self.layer, q, (record('old', D + '\n' + F),
            record('new', revision, 'old'), record('contested', F.replace('true', 'false'), 'new')))
        a, b, c = wire(p)['snapshots']
        self.assertEqual(contexts(a)['single']['concepts']['checked']['readings'][0]['state'], 'CRITERIA_UNRESOLVED')
        rows = contexts(b)['single']['concepts']['checked']['readings']
        self.assertTrue(any(r['state'] == 'SUPERSEDED_LOCAL' for r in rows))
        self.assertTrue(any(r['state'] == 'CRITERIA_MET' for r in rows))
        rows = contexts(c)['single']['concepts']['checked']['readings']
        self.assertTrue(any(r['state'] == 'CRITERIA_UNRESOLVED' for r in rows))
        self.assertNotIn(revision, json.dumps(a))

    def test_complete_provenance_survives_actual_compact_final_input(self):
        q = "Across sources, Compare Alice's belief and meaning of fair for proposal in team."
        p = prepare_source_revision(self.layer, q, (record('definitions', D + '\n' + F), record('belief', B, 'definitions')))
        for s in wire(p)['snapshots']:
            bound = {(r['operation'], r['source_event_id']) for r in s['source_bindings']}
            for op, ctx in contexts(s).items():
                self.assertTrue(all((op, e['event_id']) in bound for e in ctx['evidence']))
                self.assertTrue(all(pv['source_event_id'] in {e['event_id'] for e in ctx['evidence']}
                    for pv in ctx['provenance']))
        self.assertEqual(p.preparation_receipt['actual_final_messages'], list(p.messages))

    def test_later_narrated_exposure_does_not_backfill_earlier_view(self):
        p = prepare_source_revision(self.layer, QUERY, (record('unseen', B), record('exposure', HEAR, 'unseen')),
            narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob')
        a, b = wire(p)['snapshots']
        self.assertFalse(beliefs(a))
        self.assertNotIn(B, json.dumps(a))
        self.assertEqual(beliefs(b)[('Alice', 'team/proposal/fair')], 'AFFIRMED')
        hidden = prepare_source_revision(self.layer, QUERY, (record('unseen', B), record('exposure', HEAR, 'unseen')),
            narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Carol')
        self.assertNotIn(B, hidden.messages[-1]['content'])
        self.assertTrue(all(not s['source_bindings'] for s in wire(hidden)['snapshots']))

    def test_later_learning_cannot_establish_action_time_knowledge(self):
        rules = (NarrativePremise('rule', 'Knowledge required for this caller rule.',
            (FactorRequirement(ResponsibilityFactor.KNOWLEDGE, True),)),)
        q = "Across sources, Explain Alice's belief and conditional responsibility."
        first = '\n'.join((B, 'Alice: I opened the gate.', 'Narrator: The animals escaped.'))
        p = prepare_source_revision(self.layer, q, (record('episode', first),
            record('learning', 'Alice: I learned the latch was weak later.', 'episode')),
            responsibility_premises=rules, premise_scope='FOCAL_EPISODE')
        for s in wire(p)['snapshots']:
            r = contexts(s)['responsibility']['responsibility']['checked']
            self.assertEqual(next(f['state'] for f in r['factors'] if f['factor'] == 'KNOWLEDGE'), 'UNKNOWN')
            self.assertEqual(r['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_opposite_unrevised_sources_expose_conflict_not_last_writer_resolution(self):
        deny = B.replace('I believe', 'I do not believe')
        p = prepare_source_revision(self.layer, QUERY, (record('affirm', B), record('deny', deny, 'affirm')))
        a, b = wire(p)['snapshots']
        self.assertFalse(a['source_conflicts'])
        self.assertEqual(b['source_conflicts'][0]['status'], 'UNRESOLVED_CONTRADICTORY_SOURCE_ASSERTIONS')
        self.assertEqual({r['source_statements'][0]['source_id'] for r in b['source_conflicts'][0]['witnesses']}, {'affirm', 'deny'})
        self.assertIn('do not resolve', p.messages[0]['content'])

    def test_incomparable_branches_never_share_revision_or_exposure(self):
        p = prepare_source_revision(self.layer, QUERY, (record('first', B), record('independent', R)))
        self.assertEqual(wire(p)['source_relation'], 'INCOMPARABLE_SOURCE_BRANCHES_NO_MERGED_STATE')
        a, b = wire(p)['snapshots']
        self.assertEqual(b['source_path'], ['independent'])
        self.assertNotIn(('Alice', 'team/proposal/fair'), beliefs(b))
        self.assertEqual(beliefs(a)[('Alice', 'team/proposal/fair')], 'AFFIRMED')
        p = prepare_source_revision(self.layer, QUERY, (record('first', B), record('independent', HEAR)),
            narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob')
        self.assertTrue(all(not beliefs(s) for s in wire(p)['snapshots']))

    def test_missing_authority_bad_order_duplicate_identity_fail_without_library_fallback(self):
        for records in ((record('first', B), AuthorizedSourceRecord('no-grant', R)),
            (record('first', B), record('later', R, 'missing')),
            (record('first', B, 'later'), record('later', R)),
            (record('same', B), record('same', R)),
            (record('first', B), record('cycle', R, 'cycle'))):
            p = prepare_source_revision(self.layer, QUERY, records)
            self.assertEqual(p.preparation_receipt['failure'], 'invalid_or_missing_source_authority_identity_order')
            self.assertFalse(p.context.evidence)
            self.assertNotIn(B, p.messages[-1]['content'])

    def test_total_budget_drops_all_snapshots_and_scope_cannot_bypass_authority(self):
        records = (record('first', B), record('later', R, 'first'))
        p = prepare_source_revision(self.layer, QUERY, records, max_context_chars=512)
        state = wire(p)
        self.assertEqual(state['snapshots'], [])
        self.assertLessEqual(len(json.dumps(state, ensure_ascii=False, sort_keys=True)), 512)
        for q, kw in (("At statement 1, " + QUERY, {}), (QUERY, {'as_of_statement': 1}),
                      ('Across sources, At statement 1, Explain Alice\'s belief.', {})):
            p = prepare_source_revision(self.layer, q, records, **kw)
            self.assertFalse(p.context.evidence)

    def test_chinese_question_actual_single_answer_call_and_zero_extraction(self):
        calls = []
        def adapter(messages):
            calls.append(messages)
            return 'before/after source-grounded explanation'
        r = answer_source_revision(HCLCognitionLayer(adapter), '按来源变化，解释 Alice 的信念。',
            (record('first', B), record('revision', R, 'first')), debug=True)
        self.assertEqual(calls, [list(r.prepared.messages)])
        self.assertEqual(r.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(len(wire(r.prepared)['snapshots']), 2)
