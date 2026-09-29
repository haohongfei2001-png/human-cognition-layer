"""G05 controlled premise, reading and counterfactual sensitivity."""
import unittest

from hcl.cognition.argument_sensitivity import ArgumentSensitivityWorkspace


TEXT = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.'''
QUERY = '''If Mira could leave were false, what changes?
If Mira used Noor's reading of free, what changes?
If Mira valued safety over autonomy instead, what changes?'''


def workspace(text=TEXT):
    w = ArgumentSensitivityWorkspace('choice-scene')
    w.put_source(text, recorded_at='2026-02-10T00:00:00Z',
                 event_time='2026-02-01T00:00:00Z', permitted_observers=('Analyst',))
    return w


class G05Tests(unittest.TestCase):
    def test_positive_three_one_factor_variants_and_robust_path(self):
        prepared = workspace().compare(QUERY, observer='Analyst')
        view = prepared.payload
        self.assertEqual([v['kind'] for v in view['variants']],
                         ['FACT_COUNTERFACTUAL', 'CONCEPT_READING_SWITCH', 'VALUE_PREMISE_REVERSAL'])
        self.assertEqual([v['comparisons'][0]['sensitivity'] for v in view['variants']],
                         ['SUPPORT_REMOVED_UNDER_ASSUMPTION',
                          'READING_CHANGED_CONCLUSION_UNRESOLVED',
                          'VALUE_PREMISE_CHANGED_CONCLUSION_UNRESOLVED'])
        self.assertTrue(all(v['comparisons'][1]['sensitivity'] ==
                            'STRUCTURALLY_UNAFFECTED_BY_THIS_VARIANT' for v in view['variants']))
        self.assertTrue(all(v['source_modified'] is False and v['only_one_factor_changed']
                            for v in view['variants']))
        self.assertEqual(view['moral_truth'], 'NOT_INFERRED')

    def test_fact_already_contested_remains_unresolved(self):
        text = TEXT + '\nNoor: In choice, I challenge the fact that Mira could leave.'
        variant = workspace(text).compare(QUERY.splitlines()[0], observer='Analyst').payload['variants'][0]
        self.assertEqual(variant['comparisons'][0]['sensitivity'],
                         'ALREADY_CONTESTED_REMAINS_UNRESOLVED')

    def test_unreported_fact_stays_unresolved(self):
        text = '\n'.join(TEXT.splitlines()[1:])
        variant = workspace(text).compare(QUERY.splitlines()[0], observer='Analyst').payload['variants'][0]
        self.assertEqual(variant['comparisons'][0]['sensitivity'],
                         'UNSUPPORTED_PREMISE_REMAINS_UNRESOLVED')

    def test_concept_equal_readings_do_not_claim_change(self):
        text = TEXT.replace('pressure_absent is true', 'alternatives is true')
        variant = workspace(text).compare(QUERY.splitlines()[1], observer='Analyst').payload['variants'][0]
        self.assertEqual(variant['comparisons'][0]['sensitivity'], 'OBSERVED_CRITERIA_UNCHANGED')

    def test_unmatched_concept_refused(self):
        text = TEXT.replace('Noor: In choice, for free pressure_absent is true is necessary.\n', '')
        with self.assertRaises(ValueError):
            workspace(text).compare(QUERY.splitlines()[1], observer='Analyst')

    def test_unmatched_value_and_fact_refused(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.compare('If Mira valued status over duty instead, what changes?', observer='Analyst')
        with self.assertRaises(ValueError):
            w.compare('If the bridge collapsed were false, what changes?', observer='Analyst')

    def test_fact_counterfactual_does_not_cross_contexts(self):
        text = TEXT + '\nNoor: In work, I conclude work is risky because Mira could leave.'
        with self.assertRaises(ValueError):
            workspace(text).compare(QUERY.splitlines()[0], observer='Analyst')

    def test_unrelated_value_not_upgraded(self):
        text = TEXT.replace('autonomy matters', 'Mira had another option')
        with self.assertRaises(ValueError):
            workspace(text).compare(QUERY.splitlines()[2], observer='Analyst')

    def test_unsupported_question_and_budget_refused(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.compare('If Mira is secretly malicious, what changes?', observer='Analyst')
        with self.assertRaises(ValueError):
            w.compare('\n'.join([QUERY.splitlines()[0]] * 2), observer='Analyst')
        with self.assertRaises(ValueError):
            w.compare('\n'.join([QUERY.splitlines()[0]] * 4), observer='Analyst')

    def test_access_time_and_stale_final_input(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.compare(QUERY, observer='Noor')
        with self.assertRaises(ValueError):
            w.compare(QUERY, observer='Analyst', known_at='2026-02-09T00:00:00Z')
        prepared = w.compare(QUERY, observer='Analyst')
        self.assertEqual(len(prepared.messages(w)), 2)
        w.put_source(TEXT.replace('Mira could leave', 'Mira could stay'),
                     recorded_at='2026-02-11T00:00:00Z', permitted_observers=('Analyst',))
        with self.assertRaises(ValueError):
            prepared.messages(w)

    def test_prefix_replay_does_not_backfill_value_or_argument(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.compare(QUERY.splitlines()[2], observer='Analyst', through_order=3)
        earlier = w.compare(QUERY.splitlines()[0], observer='Analyst', through_order=6).payload
        self.assertEqual(len(earlier['base']['arguments']), 1)
        self.assertEqual(earlier['through_order'], 6)

    def test_evidence_and_context_size(self):
        w = workspace()
        prepared = w.compare(QUERY, observer='Analyst')
        row = prepared.payload['variants'][0]['basis'][0]
        self.assertEqual(row['reported_sources'][0]['quote'], TEXT.splitlines()[0])
        with self.assertRaises(ValueError):
            prepared.messages(w, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
