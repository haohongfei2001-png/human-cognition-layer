"""G03 local concept criteria, counterexample and revision boundaries."""
import unittest

from hcl.cognition import ConceptCriteriaWorkspace


TEXT = '''Mira: In team, for fair consent is true is necessary.
Mira: In team, for fair transparency is true is typical.
Mira: In team, for equitable consent is true is necessary.
Mira: In team, I use fair and equitable interchangeably.
Noor: In team, for fair transparency is true is sufficient.
Mira: In home, for fair care is true is sufficient.
Narrator: In team, proposal has consent false.
Narrator: In team, proposal has transparency true.
Mira: In team, proposal is fair.
Mira: In team, I now use fair with consent is true as sufficient instead of consent is true as necessary.
Narrator: In team, proposal has consent true.
Mira: In team, proposal is not fair.'''


def workspace(text=TEXT, observers=('Analyst',)):
    w = ConceptCriteriaWorkspace('scene')
    w.put_source(text, recorded_at='2026-01-10T00:00:00Z',
                 permitted_observers=observers, event_time='2026-01-01T00:00:00Z',
                 access_time='2026-01-02T00:00:00Z')
    return w


def reading(view, actor, context, term, kind, item='proposal'):
    return next(r for r in view['readings'] if (r['actor'], r['context'], r['term'], r['kind'], r['item']) ==
                (actor, context, term, kind, item))


class G03Tests(unittest.TestCase):
    def test_positive_necessary_typical_counterexample_and_composition(self):
        view = workspace().prepare('How does Mira use fair?', observer='Analyst', through_order=9).payload
        necessary = reading(view, 'Mira', 'team', 'fair', 'NECESSARY')
        self.assertEqual(necessary['conditional_result'], 'REFUTED_BY_SOURCE_CLAIM')
        self.assertTrue(necessary['source_reported_counterexample'])
        self.assertEqual(necessary['checks'][0]['status'], 'FAILED_BY_SOURCE')
        self.assertEqual(necessary['source']['quote'], TEXT.splitlines()[0])
        self.assertEqual(reading(view, 'Mira', 'team', 'fair', 'TYPICAL')['conditional_result'],
                         'TYPICAL_MATCH_NO_ENTAILMENT')
        self.assertIn('SAME_WORD_DIFFERENT_READING', [r['relation'] for r in view['relations']])
        self.assertIn('DIFFERENT_WORDS_UNRESOLVED',
                      [r['relation'] for r in view['relations']])
        self.assertEqual(view['moral_truth'], 'NOT_INFERRED')

    def test_revision_does_not_rewrite_old_application(self):
        w = workspace()
        old = w.prepare('Was proposal fair?', observer='Analyst', through_order=9).payload
        new = w.prepare('Was proposal fair?', observer='Analyst').payload
        self.assertEqual(reading(old, 'Mira', 'team', 'fair', 'NECESSARY')['conditional_result'],
                         'REFUTED_BY_SOURCE_CLAIM')
        self.assertEqual(reading(new, 'Mira', 'team', 'fair', 'SUFFICIENT')['conditional_result'],
                         'NOT_ESTABLISHED')  # opposing narrator claims are contested
        self.assertFalse(reading(new, 'Mira', 'team', 'fair', 'SUFFICIENT')['source_reported_counterexample'])
        self.assertEqual(new['prior_commitments'], 'NOT_REWRITTEN')
        self.assertEqual(old['through_order'], 9)

    def test_sufficient_success_and_negative_use_is_counterexample(self):
        text = '''Mira: In team, for fair consent is true is sufficient.
Narrator: In team, proposal has consent true.
Mira: In team, proposal is not fair.'''
        row = reading(workspace(text).prepare('Is it fair?', observer='Analyst').payload,
                      'Mira', 'team', 'fair', 'SUFFICIENT')
        self.assertEqual(row['conditional_result'], 'SUPPORTED_BY_SOURCE_CLAIM')
        self.assertTrue(row['source_reported_counterexample'])

    def test_necessary_met_is_not_sufficient(self):
        text = '''Mira: In team, for fair consent is true is necessary.
Narrator: In team, proposal has consent true.'''
        row = reading(workspace(text).prepare('Is it fair?', observer='Analyst').payload,
                      'Mira', 'team', 'fair', 'NECESSARY')
        self.assertEqual(row['conditional_result'], 'NOT_REFUTED')

    def test_unknown_and_contested_source_claims(self):
        text = '''Mira: In team, for fair consent is true is sufficient.
Narrator: In team, proposal has consent true.
Narrator: In team, proposal has consent false.'''
        row = reading(workspace(text).prepare('Is it fair?', observer='Analyst').payload,
                      'Mira', 'team', 'fair', 'SUFFICIENT')
        self.assertEqual(row['checks'][0]['status'], 'CONTESTED')
        self.assertEqual(row['conditional_result'], 'NOT_ESTABLISHED')

    def test_different_words_require_explicit_equivalence(self):
        text = '''Mira: In team, for fair consent is true is necessary.
Mira: In team, for equitable consent is true is necessary.
Narrator: In team, proposal has consent true.'''
        view = workspace(text).prepare('Compare fair and equitable', observer='Analyst').payload
        self.assertIn('DIFFERENT_WORDS_UNRESOLVED', [r['relation'] for r in view['relations']])

    def test_different_words_same_reading_with_source_equivalence(self):
        text = '''Mira: In team, for fair consent is true is necessary.
Mira: In team, for equitable consent is true is necessary.
Mira: In team, I use fair and equitable interchangeably.
Narrator: In team, proposal has consent true.'''
        view = workspace(text).prepare('Compare fair and equitable', observer='Analyst').payload
        self.assertIn('REPORTED_INTERCHANGEABLE_MATCHING_CRITERIA',
                      [r['relation'] for r in view['relations']])

    def test_same_word_actor_and_context_boundaries(self):
        view = workspace().prepare('Compare readings', observer='Analyst', through_order=9).payload
        self.assertIn('SAME_WORD_CONTEXT_SEPARATE', [r['relation'] for r in view['relations']])
        self.assertEqual(view['shared_meaning'], 'NOT_INFERRED')

    def test_unmatched_revision_stays_unresolved(self):
        text = '''Mira: In team, for fair consent is true is necessary.
Mira: In team, I now use fair with consent is true as sufficient instead of transparency is true as necessary.
Narrator: In team, proposal has consent true.'''
        view = workspace(text).prepare('fair?', observer='Analyst').payload
        self.assertEqual(len(view['diagnostics']), 1)
        self.assertEqual(reading(view, 'Mira', 'team', 'fair', 'NECESSARY')['conditional_result'], 'NOT_REFUTED')

    def test_acl_time_and_stale_input(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.prepare('fair?', observer='Noor')
        with self.assertRaises(ValueError):
            w.prepare('fair?', observer='Analyst', known_at='2026-01-09T00:00:00Z')
        with self.assertRaises(ValueError):
            w.prepare('fair?', observer='Analyst', access_through='2026-01-01T00:00:00Z')
        prepared = w.prepare('fair?', observer='Analyst')
        self.assertEqual(len(prepared.messages(w)), 2)
        w.put_source(TEXT.replace('consent false', 'consent true'), recorded_at='2026-01-11T00:00:00Z',
                     permitted_observers=('Analyst',))
        with self.assertRaises(ValueError):
            prepared.messages(w)

    def test_unsupported_text_no_inference(self):
        view = workspace('Narrator: Mira is secretly unfair.').prepare('Is Mira fair?', observer='Analyst').payload
        self.assertFalse(view['readings'])
        self.assertEqual(view['diagnostics'][0]['status'], 'UNRESOLVED_SOURCE_FORM')

    def test_source_order_not_calendar_and_budget_refusal(self):
        w = workspace()
        self.assertEqual(w.prepare('fair?', observer='Analyst').payload['line_order'], 'SOURCE_LOCAL_NOT_CALENDAR_TIME')
        with self.assertRaises(ValueError):
            w.prepare('fair?', observer='Analyst').messages(w, max_chars=1000)
        with self.assertRaises(ValueError):
            w.prepare('fair?', observer='Analyst', through_order=65)


if __name__ == '__main__':
    unittest.main()
