"""H01 question-directed dispatch, budgets and source boundaries."""
import unittest

from hcl.cognition.query_planner import QueryDirectedWorkspace


TEXT = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.
Narrator: In work, Noor finished report.'''
WHAT_IF = 'If Mira could leave were false, what changes?'


def workspace(text=TEXT):
    w = QueryDirectedWorkspace('h01-scene')
    w.put_source(text, recorded_at='2026-03-10T00:00:00Z',
                 event_time='2026-03-01T00:00:00Z', permitted_observers=('Analyst',))
    return w


class H01Tests(unittest.TestCase):
    def test_single_fact_stays_on_direct_source_path(self):
        w = workspace()
        plan = w.plan('What did the narrator report about Mira?', observer='Analyst')
        view = plan.payload
        self.assertEqual(view['operations'], ['DIRECT_SOURCE'])
        self.assertEqual(view['used']['depth'], 0)
        self.assertEqual(view['used']['provider_calls'], 0)
        self.assertEqual(len(view['result']['reports']), 1)
        self.assertEqual(view['result']['reports'][0]['quote'], TEXT.splitlines()[0])
        self.assertEqual(len(plan.messages(w)), 2)

    def test_concept_query_selects_only_g03_and_definition_without_item(self):
        view = workspace().plan('What does Mira mean by free?', observer='Analyst').payload
        self.assertEqual(view['operations'], ['G03_CONCEPT_CRITERIA'])
        self.assertEqual(view['targets'], ['Mira'])
        self.assertEqual(len(view['result']['active_criteria']), 1)
        self.assertEqual(view['result']['active_criteria'][0]['criteria'][0]['feature'], 'alternatives')

    def test_disagreement_selects_g03_g04_without_g05(self):
        view = workspace().plan('Why do Mira and Noor disagree about freedom?', observer='Analyst').payload
        self.assertEqual(view['operations'], ['G03_CONCEPT_CRITERIA', 'G04_ARGUMENT_ANALYSIS'])
        self.assertEqual(view['targets'], ['Mira', 'Noor'])
        self.assertEqual(len(view['result']['disagreements']), 1)
        self.assertEqual(view['used']['depth'], 2)

    def test_hypothetical_selects_minimal_dependency_chain(self):
        view = workspace().plan(WHAT_IF, observer='Analyst').payload
        self.assertEqual(view['operations'], ['G03_CONCEPT_CRITERIA', 'G04_ARGUMENT_ANALYSIS', 'G05_SENSITIVITY'])
        self.assertEqual(view['result']['variants'][0]['comparisons'][0]['sensitivity'],
                         'SUPPORT_REMOVED_UNDER_ASSUMPTION')
        self.assertEqual(view['used']['branches'], 1)

    def test_explicit_time_and_source_prefix_selected_from_question(self):
        w = workspace()
        view = w.plan('What did the narrator report about Mira through line 1 as of 2026-03-11T00:00:00Z?',
                      observer='Analyst').payload
        self.assertEqual(view['time_scope']['through_order'], 1)
        self.assertEqual(view['time_scope']['known_at'], '2026-03-11T00:00:00+00:00')
        self.assertEqual(len(view['result']['reports']), 1)

    def test_missing_fact_not_inferred_absent(self):
        view = workspace().plan('What did the narrator report about Ada?', observer='Analyst').payload
        self.assertEqual(view['result']['status'], 'NO_MATCH_NO_ABSENCE_INFERENCE')

    def test_unsupported_and_unbound_actor_refused(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.plan('What is Mira secretly thinking?', observer='Analyst')
        with self.assertRaises(ValueError):
            w.plan('Why do Mira and Ada disagree?', observer='Analyst')
        with self.assertRaises(ValueError):
            w.plan('What does Ada mean by free?', observer='Analyst')

    def test_budget_refuses_complex_without_silent_downgrade(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Analyst', max_depth=2)
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Analyst', max_operations=2)
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Analyst', max_branches=0)
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Analyst', provider_call_budget=1)

    def test_access_time_and_stale_source(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Noor')
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Analyst', known_at='2026-03-09T00:00:00Z')
        plan = w.plan(WHAT_IF, observer='Analyst')
        w.put_source(TEXT.replace('Mira could leave', 'Mira could stay'),
                     recorded_at='2026-03-11T00:00:00Z', permitted_observers=('Analyst',))
        with self.assertRaises(ValueError):
            plan.messages(w)

    def test_direct_source_limit_and_context_budget(self):
        text = '\n'.join(['Narrator: In choice, Mira could leave.'] * 9)
        with self.assertRaises(ValueError):
            workspace(text).plan('What did the narrator report about Mira?', observer='Analyst')
        w = workspace()
        with self.assertRaises(ValueError):
            w.plan(WHAT_IF, observer='Analyst').messages(w, max_chars=1000)

    def test_temporal_ambiguity_refused(self):
        w = workspace()
        with self.assertRaises(ValueError):
            w.plan('What did the narrator report about Mira as of 2026-03-11T00:00:00Z?',
                   observer='Analyst', known_at='2026-03-12T00:00:00Z')
        with self.assertRaises(ValueError):
            w.plan('What did the narrator report about Mira through line 2?',
                   observer='Analyst', through_order=3)

    def test_later_speaker_not_visible_through_source_prefix(self):
        with self.assertRaises(ValueError):
            workspace().plan('What does Noor mean by free through line 2?', observer='Analyst')


if __name__ == '__main__':
    unittest.main()
