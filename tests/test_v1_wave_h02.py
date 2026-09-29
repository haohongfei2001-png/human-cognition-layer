"""H02 finite source-discriminating retrieval for two rival arguments."""
import unittest

from hcl.cognition.discriminating_evidence import DiscriminatingEvidenceWorkspace


ARGUMENTS = '''Mira: In choice, I conclude choice is free because Mira could leave.
Noor: In choice, I conclude choice is not free because Mira was pressured.'''
EVIDENCE = '''Narrator: In choice, Mira could leave.
Narrator: In choice, Mira was not pressured.'''
QUESTION = 'Why do Mira and Noor disagree about freedom?'


def workspace(evidence=EVIDENCE, acl=('Analyst',), argument=ARGUMENTS):
    w = DiscriminatingEvidenceWorkspace('argument-source')
    w.put_source(argument, recorded_at='2026-04-01T00:00:00Z', permitted_observers=('Analyst',))
    if evidence:
        w.put_evidence_source('chapter-evidence', evidence, recorded_at='2026-04-02T00:00:00Z',
                              permitted_observers=acl)
    return w


class H02Tests(unittest.TestCase):
    def test_positive_discriminating_retrieval_and_conditional_rivals(self):
        w = workspace()
        prepared = w.prepare_evidence(QUESTION, observer='Analyst')
        view = prepared.payload
        self.assertEqual(len(view['rivals']), 2)
        self.assertEqual([x['conditional_status'] for x in view['rivals']],
                         ['ALL_PREMISES_SOURCE_SUPPORTED', 'WEAKENED_BY_COUNTEREVIDENCE'])
        self.assertEqual([step['gain'][0]['gain'] for step in view['retrieval_steps']],
                         ['SOURCE_REPORTED_SUPPORT', 'SOURCE_REPORTED_COUNTEREVIDENCE'])
        self.assertEqual(view['winner'], 'NOT_AUTOMATICALLY_SELECTED')
        self.assertEqual(view['unique_relevant_events'], 2)
        self.assertEqual(view['rivals'][0]['premises'][0]['supporting_events'][0]['excerpt'],
                         EVIDENCE.splitlines()[0])
        self.assertEqual(len(prepared.messages(w)), 2)

    def test_no_gain_stops_without_search_loop(self):
        view = workspace('Narrator: In choice, Mira visited town.').prepare_evidence(
            QUESTION, observer='Analyst').payload
        self.assertEqual(view['stop_reason'], 'NO_INFORMATION_GAIN_STOP')
        self.assertEqual(view['budgets']['used_retrievals'], 1)
        self.assertEqual(view['rivals'][1]['conditional_status'], 'UNRESOLVED')
        self.assertEqual(view['unique_relevant_events'], 0)

    def test_retrieval_miss_is_not_absence(self):
        view = workspace('').prepare_evidence(QUESTION, observer='Analyst').payload
        self.assertEqual(view['rivals'][0]['premises'][0]['state'], 'UNRESOLVED_NOT_ABSENT')
        self.assertEqual(view['evidence_completeness'], 'PARTIAL_RETRIEVAL_NOT_WORLD_COMPLETENESS')

    def test_third_party_quote_only_sharpens_attribution(self):
        view = workspace('Noor said, "Mira could leave."').prepare_evidence(
            QUESTION, observer='Analyst').payload
        self.assertEqual(view['rivals'][0]['premises'][0]['state'], 'ATTRIBUTED_ONLY_UNRESOLVED')
        self.assertEqual(view['retrieval_steps'][0]['gain'][0]['gain'], 'ATTRIBUTION_ONLY_UNCERTAINTY')
        self.assertEqual(view['rivals'][0]['conditional_status'], 'UNRESOLVED')

    def test_hidden_source_noninterference(self):
        w = workspace(EVIDENCE, acl=('Kai',))
        view = w.prepare_evidence(QUESTION, observer='Analyst').payload
        self.assertEqual(view['unique_relevant_events'], 0)
        self.assertEqual(view['evidence_versions'], [])

    def test_known_at_blocks_later_evidence(self):
        w = workspace()
        view = w.prepare_evidence(QUESTION, observer='Analyst',
                                  known_at='2026-04-01T12:00:00Z').payload
        self.assertEqual(view['evidence_versions'], [])
        self.assertEqual(view['rivals'][0]['conditional_status'], 'UNRESOLVED')

    def test_correction_changes_status_and_invalidates_old_input(self):
        w = workspace()
        before = w.prepare_evidence(QUESTION, observer='Analyst')
        w.put_evidence_source('chapter-evidence',
            'Narrator: In choice, Mira could not leave.\nNarrator: In choice, Mira was not pressured.',
            recorded_at='2026-04-03T00:00:00Z', permitted_observers=('Analyst',))
        with self.assertRaises(ValueError):
            before.messages(w)
        after = w.prepare_evidence(QUESTION, observer='Analyst').payload
        self.assertEqual(after['rivals'][0]['conditional_status'], 'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertEqual(after['evidence_versions'], [['chapter-evidence', 2]])

    def test_access_revocation_invalidates_saved_input(self):
        w = workspace()
        before = w.prepare_evidence(QUESTION, observer='Analyst')
        w.put_evidence_source('chapter-evidence', EVIDENCE,
            recorded_at='2026-04-03T00:00:00Z', permitted_observers=('Kai',))
        with self.assertRaises(ValueError):
            before.messages(w)
        self.assertEqual(w.prepare_evidence(QUESTION, observer='Analyst').payload['unique_relevant_events'], 0)

    def test_retrieval_budget_is_partial_not_full_answer(self):
        view = workspace().prepare_evidence(QUESTION, observer='Analyst', max_retrievals=1).payload
        self.assertEqual(view['stop_reason'], 'RETRIEVAL_BUDGET_REACHED')
        self.assertEqual(view['rivals'][1]['conditional_status'], 'UNRESOLVED')

    def test_truncation_refuses_to_hide_counterevidence(self):
        with self.assertRaises(ValueError):
            workspace().prepare_evidence(QUESTION, observer='Analyst', max_events=1)

    def test_explicit_negated_premise_accepts_positive_counterevidence(self):
        argument = '''Mira: In choice, I conclude choice is free because Mira was not pressured.
Noor: In choice, I conclude choice is not free because Mira could not leave.'''
        evidence = 'Narrator: In choice, Mira was pressured.'
        view = workspace(evidence, argument=argument).prepare_evidence(QUESTION, observer='Analyst').payload
        self.assertEqual(view['rivals'][0]['premises'][0]['state'], 'WEAKENED_BY_SOURCE_COUNTEREVIDENCE')

    def test_unsupported_query_and_argument_source_access_refused(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.prepare_evidence('What did the narrator report about Mira?', observer='Analyst')
        with self.assertRaises(ValueError):
            w.prepare_evidence(QUESTION, observer='Kai')

    def test_unrelated_evidence_does_not_change_existing_receipt(self):
        w = workspace()
        before = w.prepare_evidence(QUESTION, observer='Analyst')
        w.put_evidence_source('private', 'Kai said, "A private thought."',
                              recorded_at='2026-04-03T00:00:00Z', permitted_observers=('Kai',))
        self.assertEqual(before.messages(w), before.messages(w))
        self.assertEqual(before.evidence_versions, w._selected_versions('Analyst', before.cutoffs))

    def test_final_context_budget_refuses(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.prepare_evidence(QUESTION, observer='Analyst').messages(w, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
