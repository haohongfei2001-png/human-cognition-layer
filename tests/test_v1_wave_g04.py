"""G04 source-local philosophical argument boundaries and composition."""
import unittest

from hcl.cognition.argument_analysis import ArgumentWorkspace, _opposed


TEXT = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.
Noor: In choice, I challenge the fact that Mira could leave.
Noor: In choice, pressured exit is a counterexample to choice is free.
Mira: In choice, this choice is like earlier choice because both allowed exit.'''


def workspace(text=TEXT, observers=('Analyst',)):
    w = ArgumentWorkspace('argument-scene')
    w.put_source(text, recorded_at='2026-02-10T00:00:00Z',
                 event_time='2026-02-01T00:00:00Z', permitted_observers=observers)
    return w


class G04Tests(unittest.TestCase):
    def test_positive_pivotal_fact_concept_value_and_counterexample(self):
        view = workspace().prepare_argument('Where do Mira and Noor disagree?', observer='Analyst').payload
        self.assertEqual(len(view['arguments']), 2)
        self.assertEqual(len(view['disagreements']), 1)
        dispute = view['disagreements'][0]
        self.assertEqual(dispute['fact_challenges'][0]['premise'], 'Mira could leave')
        self.assertEqual(dispute['concept_reading_differences'][0]['relation'],
                         'SAME_WORD_DIFFERENT_READING')
        self.assertEqual(len(dispute['explicit_value_conflicts']), 1)
        self.assertEqual(dispute['winner'], 'NOT_SELECTED')
        mira = view['arguments'][0]
        self.assertEqual(mira['premise_checks'][0]['status'], 'CHALLENGED_SOURCE_REPORT')
        self.assertEqual(mira['targeted_counterexamples'][0]['case'], 'pressured exit')
        self.assertEqual(mira['proposed_analogies'][0]['feature'], 'both allowed exit')
        self.assertEqual(mira['conditional_form']['then'], 'choice is free')
        self.assertEqual(view['formal_solver'], 'NOT_CALLED_NO_EXPLICIT_FORMAL_MODEL')

    def test_unopposed_conclusions_do_not_create_dispute(self):
        text = '''Mira: In choice, I conclude choice is free because Mira could leave.
Noor: In choice, I conclude choice is good because Mira could leave.'''
        view = workspace(text).prepare_argument('Compare claims', observer='Analyst').payload
        self.assertFalse(view['disagreements'])

    def test_identical_claims_never_imply_opposition(self):
        for claim in ('choice is free', 'choice is not free', 'not choice is free',
                      'exit remains possible', 'notable choices matter'):
            with self.subTest(claim=claim):
                self.assertFalse(_opposed(claim, claim))
                text = (f'Mira: In choice, I conclude {claim} because exit is possible.\n'
                        f'Noor: In choice, I conclude {claim} because safety matters.')
                view = workspace(text).prepare_argument('Compare claims', observer='Analyst').payload
                self.assertEqual(len(view['arguments']), 2)
                self.assertEqual(view['disagreements'], [])

    def test_only_explicit_supported_negation_marks_opposition_symmetrically(self):
        for left, right in (('choice is free', 'choice is not free'),
                            ('exit remains possible', 'not exit remains possible')):
            self.assertTrue(_opposed(left, right));self.assertTrue(_opposed(right, left))
            for a, b in ((left, right), (right, left)):
                text = (f'Mira: In choice, I conclude {a} because one premise.\n'
                        f'Noor: In choice, I conclude {b} because another premise.')
                view = workspace(text).prepare_argument('Compare claims', observer='Analyst').payload
                self.assertEqual(len(view['disagreements']), 1)
        for left, right in (('choice is free', 'choice is good'),
                            ('exit remains possible', 'exit remains impossible')):
            self.assertFalse(_opposed(left, right));self.assertFalse(_opposed(right, left))

    def test_unlocated_opposition_is_explicitly_unresolved(self):
        text = '''Mira: In choice, I conclude choice is free because Mira could leave.
Noor: In choice, I conclude choice is not free because Mira faced pressure.'''
        dispute = workspace(text).prepare_argument('Why?', observer='Analyst').payload['disagreements'][0]
        self.assertEqual(dispute['unresolved'], 'NO_PIVOTAL_BASIS_LOCALIZED')

    def test_unrelated_concept_or_value_does_not_become_pivotal(self):
        text = '''Mira: In choice, for loyal consent is true is necessary.
Noor: In choice, for loyal approval is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave.
Noor: In choice, I conclude choice is not free because Mira faced pressure.'''
        dispute = workspace(text).prepare_argument('Why?', observer='Analyst').payload['disagreements'][0]
        self.assertFalse(dispute['concept_reading_differences'])
        self.assertFalse(dispute['explicit_value_conflicts'])
        self.assertEqual(dispute['unresolved'], 'NO_PIVOTAL_BASIS_LOCALIZED')

    def test_reported_fact_not_world_truth(self):
        view = workspace(TEXT.splitlines()[0] + '\n' + TEXT.splitlines()[5]).prepare_argument(
            'Was choice free?', observer='Analyst').payload
        self.assertEqual(view['arguments'][0]['premise_checks'][0]['status'], 'REPORTED_FACT_NOT_WORLD_VERIFIED')
        self.assertEqual(view['world_truth'], 'NOT_ESTABLISHED')

    def test_unreported_premise_does_not_become_fact(self):
        view = workspace('Mira: In choice, I conclude choice is free because Mira could leave.').prepare_argument(
            'Was choice free?', observer='Analyst').payload
        self.assertEqual(view['arguments'][0]['premise_checks'][0]['status'], 'UNRESOLVED_PREMISE')

    def test_counterexample_and_analogy_do_not_transfer_truth(self):
        view = workspace().prepare_argument('Is the analogy valid?', observer='Analyst').payload
        self.assertEqual(view['arguments'][0]['conditional_form']['status'],
                         'SOURCE_REPORTED_INFERENCE_NOT_FORMAL_PROOF')
        self.assertEqual(view['disagreements'][0]['moral_truth'], 'NOT_INFERRED')

    def test_source_prefix_preserves_prior_argument(self):
        w = workspace()
        early = w.prepare_argument('Before the challenge?', observer='Analyst', through_order=7).payload
        later = w.prepare_argument('After the challenge?', observer='Analyst').payload
        self.assertEqual(early['arguments'][0]['premise_checks'][0]['status'],
                         'REPORTED_FACT_NOT_WORLD_VERIFIED')
        self.assertEqual(later['arguments'][0]['premise_checks'][0]['status'],
                         'CHALLENGED_SOURCE_REPORT')
        self.assertEqual(early['through_order'], 7)

    def test_actor_context_boundaries(self):
        text = '''Mira: In choice, I conclude choice is free because Mira could leave.
Noor: In work, I conclude choice is not free because Mira was pressured.'''
        self.assertFalse(workspace(text).prepare_argument('Compare', observer='Analyst').payload['disagreements'])

    def test_acl_time_and_correction_invalidate_final_input(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.prepare_argument('Why?', observer='Noor')
        with self.assertRaises(ValueError):
            w.prepare_argument('Why?', observer='Analyst', known_at='2026-02-09T00:00:00Z')
        before = w.prepare_argument('Why?', observer='Analyst')
        self.assertEqual(len(before.messages(w)), 2)
        w.put_source(TEXT.replace('Mira could leave', 'Mira could stay'),
                     recorded_at='2026-02-11T00:00:00Z', permitted_observers=('Analyst',))
        with self.assertRaises(ValueError):
            before.messages(w)

    def test_malformed_source_and_premise_budget_refused(self):
        text = '''Mira: In choice, I secretly know everything.
Mira: In choice, I conclude x because a and b and c and d.'''
        view = workspace(text).prepare_argument('Why?', observer='Analyst').payload
        self.assertFalse(view['arguments'])
        self.assertEqual({d['status'] for d in view['diagnostics']},
                         {'UNRESOLVED_ARGUMENT_FORM', 'UNRESOLVED_PREMISE_SPLIT'})

    def test_exact_source_span_and_context_budget(self):
        w = workspace()
        prepared = w.prepare_argument('Why?', observer='Analyst')
        row = prepared.payload['arguments'][0]['source']
        self.assertEqual(TEXT[row['start']:row['end']], row['quote'])
        self.assertEqual(row['version'], 1)
        with self.assertRaises(ValueError):
            prepared.messages(w, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
