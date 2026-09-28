"""A03 positive challenge/retraction witness through ordinary input."""
import unittest
import json
from hcl.cognition import (ClaimKind, EvidenceCore, Scope, AuthorizedText,
                           prepare_semantics, assess_positions)


class InterpretationRevisionTests(unittest.TestCase):
    def setUp(self):
        self.core = EvidenceCore()
        self.scope = Scope(actor='Mira', source_ids=('s',))
        self.root = self.core.add_span('Mira expressed a doubt.', source_id='s', version=1)

    def make(self, name, kind=ClaimKind.SYSTEM_INTERPRETATION):
        return self.core.claim(self.scope, kind, dict(name=name))

    def test_challenge_propagates_but_clean_alternative_preserves_other_derivation(self):
        a, b, c, evidence = [self.make(s) for s in ('a', 'b', 'c', 'counterevidence')]
        self.core.support(a, self.root)
        self.core.support(evidence, self.root)
        self.core.support(b, a)
        self.core.support(c, a)
        self.core.support(c, self.root)
        self.core.challenge(a, evidence)
        self.assertEqual(self.core.support_statuses()[a], 'CHALLENGED')
        self.assertEqual(self.core.support_statuses()[b], 'DEPENDENCY_CONTESTED')
        self.assertEqual(self.core.support_statuses()[c], 'SUPPORT_AVAILABLE')
        self.core.withdraw(evidence)
        self.assertEqual(self.core.support_statuses()[a], 'SUPPORT_AVAILABLE')
        self.assertEqual(self.core.support_statuses()[b], 'SUPPORT_AVAILABLE')

    def test_challenge_never_erases_source_and_mutual_challenge_is_bounded(self):
        a, b, source = self.make('a'), self.make('b'), self.make('source', ClaimKind.SOURCE_REPORT)
        for node in (a, b, source):
            self.core.support(node, self.root)
        self.core.challenge(a, b)
        self.core.challenge(b, a)
        self.assertEqual(self.core.support_statuses()[a], 'CHALLENGED')
        self.assertEqual(self.core.support_statuses()[b], 'CHALLENGED')
        with self.assertRaises(ValueError):
            self.core.challenge(source, a)
        self.assertEqual(self.core.spans[self.root].quote, 'Mira expressed a doubt.')

    def test_unrooted_challenge_cannot_dispute_supported_interpretation(self):
        a, b = self.make('a'), self.make('unsupported')
        self.core.support(a, self.root)
        self.core.challenge(a, b)
        self.assertEqual(self.core.support_statuses()[a], 'SUPPORT_AVAILABLE')

    def test_replace_interpretation_retires_dependents_and_keeps_history(self):
        a, b, child, reason = [self.make(s) for s in ('old', 'new', 'child', 'reason')]
        for node in (a, b, reason):
            self.core.support(node, self.root)
        self.core.support(child, a)
        self.assertEqual(self.core.replace_interpretation(a, b, reasons=(reason,)), {a, child})
        self.assertIn(a, self.core.claims)
        self.assertIn(b, self.core.grounded())
        self.assertEqual(self.core.revisions[0]['kind'], 'ANALYST_INTERPRETATION_REVISION_NOT_CHARACTER_CHANGE')

    def test_self_supporting_replacement_rejected_without_mutation(self):
        a, b = self.make('old'), self.make('new')
        self.core.support(a, self.root)
        self.core.support(b, a)
        before = self.core.grounded()
        with self.assertRaises(ValueError):
            self.core.replace_interpretation(a, b, reasons=(a,))
        self.assertEqual(self.core.grounded(), before)
        self.assertFalse(self.core.revisions)

    def test_ordinary_counterstatement_challenges_only_related_person_then_withdraws(self):
        text = ('Mira said, "I believe the gate is open." '
                'Mira added, "I do not believe the gate is open." '
                'Noor said, "I believe the door is shut."')
        result = prepare_semantics('Compare their expressed positions.', (AuthorizedText('s', text),), core=self.core)
        assessment = assess_positions(self.core, result)
        before = assessment.current(self.core)
        self.assertEqual([r['support_status'] for r in before if r['actor'] == 'Mira'], ['CHALLENGED', 'CHALLENGED'])
        noor = [r for r in before if r['actor'] == 'Noor']
        denial_span = next(k for k, s in self.core.spans.items() if 'do not believe' in s.quote)
        self.core.withdraw(denial_span)
        after = assessment.current(self.core)
        self.assertEqual([r['support_status'] for r in after if r['actor'] == 'Mira'], ['SUPPORT_AVAILABLE', 'UNSUPPORTED'])
        self.assertEqual([r for r in after if r['actor'] == 'Noor'], noor)
        # The surviving positive expression still does not establish private belief.
        self.assertIn('NOT_PRIVATE_BELIEF', after[0]['limit'])
        wire = json.loads(assessment.messages(self.core, 'Explain the current evidence.')[-1]['content'])
        self.assertEqual(wire['positions'], after)
        self.assertTrue(any(not span['active'] for span in wire['evidence']['spans']))
        with self.assertRaises(ValueError):
            assessment.messages(self.core, 'Explain.', max_chars=128)

    def test_duplicate_positive_support_survives_one_quote_withdrawal(self):
        text = 'Mira said, "I believe the gate is open." Mira added, "I think the gate is open."'
        r = prepare_semantics('What did Mira express?', (AuthorizedText('s', text),), core=self.core)
        a = assess_positions(self.core, r)
        first = next(k for k, span in self.core.spans.items() if 'I believe' in span.quote)
        self.core.withdraw(first)
        self.assertEqual(a.current(self.core)[0]['support_status'], 'SUPPORT_AVAILABLE')

    def test_pronoun_conditional_and_same_name_elsewhere_do_not_cross_scope(self):
        sources = (AuthorizedText('a', 'Mira said, "I believe the gate is open." She added, "I do not believe the gate is open."'),
                   AuthorizedText('b', 'Mira said, "I do not believe the gate is open."'),
                   AuthorizedText('c', 'If Mira said, "I do not believe the gate is open."'))
        r = prepare_semantics('What is supported?', sources, core=self.core)
        a = assess_positions(self.core, r)
        self.assertEqual(len(a.interpretation_ids), 2)
        self.assertTrue(all(row['support_status'] == 'SUPPORT_AVAILABLE' for row in a.current(self.core)))
