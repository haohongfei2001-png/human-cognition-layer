"""Ordinary prose enters shared cognitive state without hidden-state input."""
import json
import unittest
from dataclasses import replace

from hcl.cognition import CognitionWorkspace, EvidenceCore, Scope
from hcl.cognition.semantic import AuthorizedText, prepare_semantics, _local_candidates

TEXT = ('Mira said, “I believe the door is open.” '
        'Noor replied, “I am unsure whether the door is open.” '
        'She added, “I do not believe the door is open.”')


def contents(core, result, kind):
    return [core.claims[k].content['proposal'] for k in result.candidate_ids
            if core.claims[k].content['kind'] == kind]


class Replay:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete_json(self, messages, **options):
        self.calls.append((messages, options))
        return self.response


class SemanticEntryTests(unittest.TestCase):
    def test_positive_prose_first_person_binding_and_uncertainty_without_flags(self):
        core = EvidenceCore()
        r = prepare_semantics('Who expressed belief or uncertainty about the door?',
            (AuthorizedText('dialogue', TEXT),), core=core)
        states = contents(core, r, 'proposition')
        self.assertEqual([p['signal'] for p in states], ['AFFIRM', 'UNCERTAIN', 'DENY'])
        self.assertEqual(states[0]['subject_candidates'], ['Mira'])
        self.assertEqual(states[1]['subject_candidates'], ['Noor'])
        self.assertEqual(states[2]['subject_candidates'], ['Mira', 'Noor'])
        self.assertEqual(states[2]['reference_binding'], 'UNRESOLVED')
        self.assertEqual(states[0]['proposition'], 'the door is open')
        self.assertTrue(all(p['modality'] == 'EXPRESSED_BELIEF_NOT_PRIVATE_TRUTH' for p in states))
        self.assertEqual(r.backend_calls, 0)
        self.assertTrue(set(r.candidate_ids) <= core.grounded())
        wire = json.loads(r.messages[-1]['content'])
        self.assertEqual(len(wire['cognitive_candidates']), len(r.candidate_ids))
        self.assertTrue(all(d['quotation'] == 'EXACT' for d in r.diagnostics))

    def test_rename_and_paraphrase_preserve_subject_signal_separation(self):
        for name, verb in [('Elena', 'stated'), ('Quinn', 'wrote'), ('Mira Chen', 'explained')]:
            core = EvidenceCore()
            text = f'{name} {verb}, "I think that the entrance is closed."'
            r = prepare_semantics('What did the speaker express?', (AuthorizedText('s', text),), core=core)
            p = contents(core, r, 'proposition')[0]
            self.assertEqual(p['subject_candidates'], [name])
            self.assertEqual(p['proposition'], 'the entrance is closed')
            self.assertEqual(p['signal'], 'AFFIRM')

    def test_narrative_connectives_are_not_part_of_actor_identity(self):
        core = EvidenceCore()
        r = prepare_semantics('Who spoke?', (AuthorizedText('s', 'Then Mira said, "I believe the gate is open."'),), core=core)
        self.assertEqual(contents(core, r, 'proposition')[0]['subject_candidates'], ['Mira'])

    def test_conditional_speech_is_not_an_actual_private_stance(self):
        core = EvidenceCore()
        r = prepare_semantics('What is supported?',
            (AuthorizedText('s', 'If Mira said, "I believe the gate is open."'),), core=core)
        p = contents(core, r, 'proposition')[0]
        self.assertEqual(p['assertion_scope'], 'CONDITIONAL_OR_EMBEDDED')
        self.assertEqual(p['reference_binding'], 'UNRESOLVED')

    def test_quote_and_structure_pass_do_not_certify_backend_semantics(self):
        source = AuthorizedText('s', 'Mira opened the door.')
        backend = Replay(json.dumps(dict(candidates=[dict(source_id='s', quote=source.text,
            kind='proposition', content=dict(private_intention='deceive Noor'))])))
        core = EvidenceCore()
        r = prepare_semantics('Why did Mira act?', (source,), core=core, backend=backend)
        self.assertEqual(r.diagnostics[0]['semantic_support'], 'UNVERIFIED_CANDIDATE')
        self.assertIn('Never use UNVERIFIED_CANDIDATE as a settled premise', r.messages[0]['content'])
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(r.backend_calls, 1)  # simulated adapter, not a paid provider
        self.assertEqual(core.claims[r.candidate_ids[0]].kind.value, 'SYSTEM_INTERPRETATION')

    def test_replay_candidates_can_be_verified_only_against_local_literal_form(self):
        source = AuthorizedText('s', 'Mira said, "I do not believe the gate is safe."')
        backend = Replay(json.dumps(dict(candidates=_local_candidates(source))))
        r = prepare_semantics('What was expressed?', (source,), backend=backend)
        self.assertTrue(all(x['semantic_support'] == 'BOUNDED_LITERAL_FORM' for x in r.diagnostics))
        self.assertEqual(r.raw_response, backend.response)
        self.assertNotIn('LIVE_SMOKE_VERIFIED', r.backend_status)

    def test_duplicate_quotes_require_exact_offset_and_nonexistent_quotes_fail(self):
        source = AuthorizedText('s', 'Mira said yes. Mira said yes.')
        proposal = dict(source_id='s', quote='Mira said yes.', kind='event', content={})
        for candidate in (proposal, dict(proposal, quote='Noor said yes.'), dict(proposal, start=1)):
            core = EvidenceCore()
            backend = Replay(json.dumps(dict(candidates=[candidate])))
            with self.assertRaises(ValueError):
                prepare_semantics('What happened?', (source,), core=core, backend=backend)
            self.assertFalse(core.claims)
        r = prepare_semantics('What happened?', (source,), backend=Replay(json.dumps(
            dict(candidates=[dict(proposal, start=15)]))))
        self.assertEqual(r.diagnostics[0]['quotation'], 'EXACT')

    def test_hidden_sources_filtered_before_backend_and_final_state(self):
        public = AuthorizedText('public', 'Mira said, "I believe the gate is open."', permitted_observers=('Noor',))
        secret = AuthorizedText('secret', 'Private secret of Kai', permitted_observers=('Mira',))
        backend = Replay('{"candidates": []}')
        r = prepare_semantics('What could Noor see?', (public, secret),
            scope=Scope(observer='Noor', source_ids=('public', 'secret')), backend=backend)
        self.assertNotIn('secret', json.dumps(backend.calls))
        self.assertNotIn('secret', r.final_messages_json)
        self.assertEqual(r.scope.source_ids, ('public',))
        empty = Replay('{"candidates": []}')
        r = prepare_semantics('What could Kai see?', (public, secret),
            scope=Scope(observer='Kai', source_ids=('public', 'secret')), backend=empty)
        self.assertFalse(empty.calls)
        self.assertEqual(r.backend_calls, 0)

    def test_hidden_changes_do_not_change_visible_actual_input(self):
        visible = AuthorizedText('v', 'Mira said, "I believe the gate is open."', permitted_observers=('Noor',))
        hidden = AuthorizedText('h', 'Old private detail')
        scope = Scope(observer='Noor', source_ids=('v', 'h'))
        before = prepare_semantics('What was expressed?', (visible, hidden), scope=scope)
        after = prepare_semantics('What was expressed?', (visible, replace(hidden, text='Changed secret', version=2)), scope=scope)
        self.assertEqual(before.messages, after.messages)
        self.assertEqual(before.extraction_messages_json, after.extraction_messages_json)

    def test_future_time_or_unknown_access_time_never_sent_to_backend(self):
        text = 'Mira said, "I believe the gate is open."'
        source = AuthorizedText('s', text, event_time='2026-01-01T00:00:00Z',
            record_time='2026-01-03T00:00:00Z')
        for scope in (Scope(source_ids=('s',), record_time='2026-01-02T00:00:00Z'),
                      Scope(source_ids=('s',), access_time='2026-01-02T00:00:00Z')):
            backend = Replay('{"candidates": []}')
            r = prepare_semantics('What was known then?', (source,), scope=scope, backend=backend)
            self.assertFalse(backend.calls)
            self.assertNotIn(text, r.final_messages_json)

    def test_source_order_relation_not_event_chronology_or_receipt_time(self):
        core = EvidenceCore()
        r = prepare_semantics('How are these reports ordered?', (AuthorizedText('s', TEXT),), core=core)
        relations = contents(core, r, 'relation')
        self.assertEqual(len(relations), 2)
        self.assertTrue(all(x['event_chronology'] == 'NOT_ESTABLISHED' for x in relations))
        self.assertTrue(all(x['event_time'] is None and x['access_time'] is None
                            for x in contents(core, r, 'event')))

    def test_narrative_relation_depends_on_both_utterances(self):
        core = EvidenceCore()
        r = prepare_semantics('What follows what?', (AuthorizedText('s', TEXT),), core=core)
        relation = next(k for k in r.candidate_ids if core.claims[k].content['kind'] == 'relation')
        first_span = next(k for k, span in core.spans.items() if span.start == 0)
        self.assertIn(relation, core.withdraw(first_span))
        self.assertTrue(any(core.claims[k].content['proposal'].get('subject_candidates') == ['Noor']
            for k in r.candidate_ids if k in core.grounded()))

    def test_source_update_invalidates_semantics_but_preserves_other_person(self):
        w = CognitionWorkspace()
        w.put_source('mira', 'Mira said, "I believe the gate is open."')
        w.put_source('noor', 'Noor said, "I believe the door is shut."')
        first = w.prepare_semantic('What did Mira express?', source_ids=('mira',))
        other = w.prepare_semantic('What did Noor express?', source_ids=('noor',))
        invalidated = w.put_source('mira', 'Mira said, "I am unsure whether the gate is open."')
        self.assertTrue(set(first.candidate_ids) <= invalidated)
        self.assertFalse(set(other.candidate_ids) & invalidated)
        after = w.prepare_semantic('What did Mira express?', source_ids=('mira',))
        self.assertEqual(contents(w.core, after, 'proposition')[0]['signal'], 'UNCERTAIN')
        self.assertTrue(set(other.candidate_ids) <= w.core.grounded())

    def test_malformed_output_and_budget_failure_never_retry(self):
        source = AuthorizedText('s', TEXT)
        for raw in ('not JSON', '{"candidates": "wrong"}', '{"candidates": [{"source_id":"hidden"}]}'):
            backend = Replay(raw)
            with self.assertRaises(ValueError):
                prepare_semantics('What happened?', (source,), backend=backend)
            self.assertEqual(len(backend.calls), 1)
        with self.assertRaises(ValueError):
            prepare_semantics('What happened?', (source,), max_candidates=1)
