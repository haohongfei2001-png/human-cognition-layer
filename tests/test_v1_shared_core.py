"""A01 positive revision witness, rooted supports and scope non-interference."""
import json
import unittest

from hcl.cognition import ClaimKind, CognitionWorkspace, EvidenceCore, Scope

D = 'Alice: In team, by fair I mean consent is true.'
F = 'Narrator: In team, proposal has consent false.'
B = 'Alice: In team, I believe proposal is fair.'
QUERY = "Compare Alice's belief and meaning of fair for proposal in team."


def relation(result):
    return json.loads(result.messages[-1]['content'])['composed_cognition']['belief_concept_comparison']['rows'][0]['relation']


class SharedCoreTests(unittest.TestCase):
    def setUp(self):
        self.core = EvidenceCore()
        self.scope = Scope(actor='Alice', context='team', source_ids=('one', 'two'))
        self.one = self.core.add_span('Alice says yes.', source_id='one', version=1)
        self.two = self.core.add_span('Alice repeats yes.', source_id='two', version=1)

    def claim(self, label, kind=ClaimKind.SYSTEM_INTERPRETATION, scope=None):
        return self.core.claim(scope or self.scope, kind, dict(label=label))

    def test_alternative_support_survives_local_withdrawal_and_then_invalidates(self):
        p, q, other = [self.claim(k) for k in ('p', 'q', 'other')]
        self.core.support(p, self.one)
        self.core.support(p, self.two)
        self.core.support(q, p)
        self.core.support(other, self.two)
        self.assertEqual(self.core.withdraw(self.one), {self.one})
        self.assertIn(q, self.core.grounded())
        self.assertEqual(self.core.withdraw(self.two), {self.two, p, q, other})
        self.assertEqual(len(self.core.spans), 2)  # withdrawal preserves history

    def test_rootless_cycle_never_supports_itself_and_root_loss_propagates(self):
        a, b = self.claim('a'), self.claim('b')
        self.core.support(a, b)
        self.core.support(b, a)
        self.assertNotIn(a, self.core.grounded())
        self.core.support(a, self.one)
        self.assertIn(b, self.core.grounded())
        self.assertEqual(self.core.withdraw(self.one), {self.one, a, b})

    def test_and_obligations_are_not_alternative_supports(self):
        a = self.claim('both required')
        self.core.support(a, self.one, self.two)
        self.assertIn(a, self.core.withdraw(self.one))

    def test_source_reports_cannot_be_manufactured_from_tool_or_interpretation(self):
        a = self.claim('reported', ClaimKind.SOURCE_REPORT)
        b = self.claim('assumed', ClaimKind.CONDITIONAL_TOOL_RESULT)
        with self.assertRaises(ValueError):
            self.core.support(a, b)
        self.core.support(b, self.one)
        self.assertEqual(self.core.claims[b].kind, ClaimKind.CONDITIONAL_TOOL_RESULT)

    def test_actor_context_time_assumption_and_source_boundaries(self):
        a = self.claim('Alice')
        for scope in (Scope(actor='Bob', source_ids=('one', 'two')),
                      Scope(actor='Alice', context='home', source_ids=('one', 'two')),
                      Scope(actor='Alice', context='team', source_ids=('one', 'two'), event_time='yesterday'),
                      Scope(actor='Alice', context='team', source_ids=('one', 'two'), assumptions=('if accepted',))):
            b = self.claim('other', scope=scope)
            with self.assertRaises(ValueError):
                self.core.support(b, a)
        b = self.claim('unavailable source', scope=Scope(source_ids=('other',)))
        with self.assertRaises(ValueError):
            self.core.support(b, self.one)

    def test_hidden_and_future_sources_are_filtered_before_interpretation(self):
        late = self.core.add_span('private later report', source_id='one', version=2, order=3,
                                  permitted_observers=('Alice',))
        for scope in (Scope(observer='Bob', source_ids=('one',)),
                      Scope(observer='Alice', source_ids=('one',), through_order=1)):
            a = self.claim('unsafe', scope=scope)
            with self.assertRaises(ValueError):
                self.core.support(a, late)
            self.assertNotIn('private later report', json.dumps(self.core.receipt(scope)))

    def test_each_time_cutoff_requires_known_ordered_evidence(self):
        early, late = '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z'
        root = self.core.add_span('later recorded', source_id='one', version=3,
            event_time=early, access_time=late, record_time=late)
        allowed = Scope(source_ids=('one',), event_time=early, access_time=late, record_time=late)
        self.assertTrue(self.core.spans[root].permits(allowed))
        for scope in (Scope(source_ids=('one',), access_time=early),
                      Scope(source_ids=('one',), record_time=early),
                      Scope(source_ids=('one',), event_time='yesterday')):
            self.assertFalse(self.core.spans[root].permits(scope))
        self.assertFalse(self.core.spans[self.one].permits(allowed))

    def test_time_dimensions_unknowns_and_exact_quote_identity(self):
        span = self.core.add_span('prefix quoted suffix', source_id='one', version=3,
            start=7, end=13, order=4, event_time='Tuesday', access_time='Wednesday', record_time=None)
        row = self.core.spans[span]
        self.assertEqual((row.quote, row.event_time, row.access_time, row.record_time, row.order),
                         ('quoted', 'Tuesday', 'Wednesday', None, 4))
        with self.assertRaises(ValueError):
            self.core.add_span('short', source_id='one', version=1, start=4, end=99)

    def test_interpretation_premise_is_required_and_not_promoted_to_fact(self):
        a, b = self.claim('hypothesis'), self.claim('premise')
        self.core.support(a, self.one)
        self.core.interpret(a, required_premises=(b,), unknown_conditions=('actual intention',))
        self.assertNotIn(a, self.core.grounded())
        self.core.support(b, self.two)
        self.assertIn(a, self.core.grounded())
        self.assertIn(a, self.core.withdraw(self.two))


class SharedWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.workspace = CognitionWorkspace()
        self.workspace.put_source('meeting', '\n'.join((D, F, B)))
        self.workspace.put_source('home', 'Bob: In home, I believe dinner is good.')

    def test_positive_actual_belief_concept_revision_and_unaffected_person(self):
        w = self.workspace
        before = w.prepare(QUERY, source_ids=('meeting',))
        bob = w.prepare("What does Bob believe?", source_ids=('home',))
        self.assertEqual(relation(before), 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA')
        invalidated = w.put_source('meeting', '\n'.join((D, F.replace('false', 'true'), B)))
        self.assertTrue(set(before.claim_ids) <= invalidated)
        self.assertFalse(set(bob.claim_ids) & invalidated)
        after = w.prepare(QUERY, source_ids=('meeting',))
        self.assertEqual(relation(after), 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA')
        self.assertIs(w.prepare("What does Bob believe?", source_ids=('home',)), bob)
        self.assertEqual(w.executions, 3)
        self.assertFalse(w.receipt(before)['current'])
        self.assertTrue(w.receipt(after)['current'])
        self.assertEqual(w.receipt(after)['actual_final_messages'], after.messages)
        supports = [w.core.dependencies[c] for c in after.claim_ids]
        self.assertEqual(supports[0], supports[1])  # one shared evidence identity
        self.assertIsNone(after.scope.event_time)
        self.assertIsNone(after.scope.access_time)

    def test_missing_evidence_then_added_evidence_recomputes_old_unknown(self):
        w = CognitionWorkspace()
        w.put_source('s', 'No belief has been stated.')
        before = w.prepare("What does Alice believe?", source_ids=('s',))
        w.put_source('s', B)
        after = w.prepare("What does Alice believe?", source_ids=('s',))
        self.assertNotEqual(before.messages, after.messages)
        self.assertIn('AFFIRMED', after.messages[-1]['content'])
        self.assertEqual(w.executions, 2)

    def test_snapshot_does_not_transmit_later_material_in_state_or_receipt(self):
        w = self.workspace
        result = w.prepare("What does Alice believe?", source_ids=('meeting',), through_order=1)
        self.assertNotIn(B, json.dumps(w.receipt(result)))
        self.assertFalse(w.core.claims[result.claim_ids[0]].content['state']['belief'])
        w.put_source('meeting', D + '\n' + B)
        self.assertFalse(set(result.claim_ids) & w.core.grounded())

    def test_invalid_revision_does_not_destroy_current_and_removal_prevents_cache_use(self):
        w = self.workspace
        before = w.prepare(QUERY, source_ids=('meeting',))
        with self.assertRaises(ValueError):
            w.put_source('meeting', '')
        self.assertIs(w.prepare(QUERY, source_ids=('meeting',)), before)
        w.remove_source('meeting')
        self.assertFalse(w.receipt(before)['current'])
        with self.assertRaises(ValueError):
            w.prepare(QUERY, source_ids=('meeting',))

    def test_noop_revision_no_reexecution_and_third_party_not_private_belief(self):
        w = self.workspace
        w.put_source('report', 'Bob: In team, Alice believes proposal is fair.')
        p = w.prepare("What does Alice believe?", source_ids=('report',))
        self.assertIn('SYSTEM_INSUFFICIENT', p.messages[-1]['content'])
        self.assertEqual(w.put_source('report', 'Bob: In team, Alice believes proposal is fair.'), frozenset())
        self.assertIs(w.prepare("What does Alice believe?", source_ids=('report',)), p)
