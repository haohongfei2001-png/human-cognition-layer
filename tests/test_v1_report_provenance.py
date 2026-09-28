"""B04 provenance contraction, epistemic channel and resource boundaries."""
import json
import unittest
from hcl.cognition import CognitionWorkspace, CommunicationScene
from hcl.cognition.report_provenance import prepare_reports

N = 'Noor said, "Mira believes the gate is open."'
K = 'Kai said, "Mira believes the gate is open."'
L = 'Lena said, "Mira believes the gate is open."'
M = 'Mira said, "I do not believe the gate is open."'
COPY_K = "Narrator: Kai's last statement repeats Noor's last statement."
COPY_L = "Narrator: Lena's last statement was copied from Kai's last statement."


class ReportProvenanceTests(unittest.TestCase):
    def run_scene(self, text, query='What does Mira believe?', **kwargs):
        w = CognitionWorkspace()
        w.put_source('scene', text)
        report = prepare_reports(w, query, source_id='scene', **kwargs)
        return w, report, report.current(w.core)

    def test_three_copies_one_family_and_conflicting_self_report(self):
        w, report, payload = self.run_scene('\n'.join((N, K, COPY_K, L, COPY_L, M)))
        self.assertEqual(payload['report_occurrences'], 4)
        self.assertEqual(payload['current_provenance_family_count'], 2)
        family = next(f for f in payload['provenance_families'] if f['relatedness'] == 'REPORTED_SHARED_ORIGIN')
        self.assertEqual(family['report_occurrences'], 3)
        self.assertEqual(payload['assessment'][0]['status'], 'REPORT_CONFLICT')
        self.assertIsNone(payload['independent_support_count'])
        self.assertEqual(json.loads(report.messages(w.core)[-1]['content'])['cognition'], payload)

    def test_more_copies_do_not_create_a_majority_or_private_belief(self):
        _, _, before = self.run_scene(N + '\n' + M)
        _, _, after = self.run_scene('\n'.join((N, K, COPY_K, L, COPY_L, M)))
        self.assertEqual(before['assessment'][0]['status'], after['assessment'][0]['status'])
        self.assertEqual(before['current_provenance_family_count'], after['current_provenance_family_count'])
        self.assertTrue(all(r['private_belief'] == 'NOT_ESTABLISHED' for r in after['assessment']))

    def test_unlinked_reports_do_not_become_independent_support(self):
        _, _, row = self.run_scene('\n'.join((N, K, L)))
        self.assertEqual(row['current_provenance_family_count'], 3)
        self.assertEqual(row['assessment'][0]['status'], 'INDIRECT_REPORTS_ONLY')
        self.assertEqual(row['independence'], 'NOT_ESTABLISHED')
        self.assertIsNone(row['independent_support_count'])

    def test_duplicate_same_reporter_collapses_occurrences_but_keeps_receipts(self):
        _, _, row = self.run_scene(N + '\n' + N)
        self.assertEqual(row['report_occurrences'], 2)
        self.assertEqual(row['current_provenance_family_count'], 1)
        self.assertEqual(row['provenance_families'][0]['relatedness'], 'REPEATED_SAME_REPORTER')

    def test_character_uncertainty_not_system_missing_or_indirect_uncertainty(self):
        _, _, explicit = self.run_scene('Mira said, "I am unsure whether the gate is open."')
        _, _, missing = self.run_scene('Noor said, "I believe the gate is open."')
        _, _, indirect = self.run_scene('Noor said, "Mira is unsure whether the gate is open."')
        self.assertEqual(explicit['assessment'][0]['status'], 'CHARACTER_REPORTED_UNCERTAINTY')
        self.assertEqual(missing['missing_evidence'], 'SYSTEM_INSUFFICIENT')
        self.assertEqual(indirect['assessment'][0]['status'], 'INDIRECT_REPORTS_ONLY')

    def test_third_order_query_expands_only_requested_path(self):
        text = 'Mira said, "I believe Noor believes Kai believes the gate is open."'
        _, _, row = self.run_scene(text, 'What does Mira think Noor thinks Kai believes?')
        self.assertEqual(len(row['reports']), 1)
        self.assertEqual(row['reports'][0]['holders'], ['Mira', 'Noor', 'Kai'])
        _, _, other = self.run_scene(text, 'What does Kai believe?')
        self.assertFalse(other['reports'])
        with self.assertRaises(ValueError):
            self.run_scene(text, 'What does Mira think Noor thinks Kai thinks Lena believes?')

    def test_outer_denial_not_inner_denial_or_uncertainty(self):
        _, _, denied = self.run_scene('Mira said, "I do not believe Noor believes the gate is open."',
            'What does Mira think Noor believes?')
        self.assertEqual(denied['assessment'][0]['status'], 'OUTER_MODAL_SCOPE_UNRESOLVED')
        self.assertEqual(denied['reports'][0]['content'], 'the gate is open')
        self.assertNotIn('SOURCE_REPORTED_DENY', str(denied['assessment']))

    def test_copy_disagreement_is_one_conflicted_family_not_extra_vote(self):
        text = '\n'.join((N, 'Kai said, "Mira does not believe the gate is open."', COPY_K))
        _, _, row = self.run_scene(text)
        self.assertEqual(row['current_provenance_family_count'], 1)
        self.assertEqual(row['assessment'][0]['status'], 'REPORT_CONFLICT')

    def test_unknown_future_and_self_copy_references_fail_closed(self):
        for text in (COPY_K, K + '\n' + COPY_K + '\n' + N, '\n'.join((K, N, COPY_K)),
                N + "\nNarrator: Noor's last statement repeats Noor's last statement."):
            with self.assertRaises(ValueError):
                self.run_scene(text)

    def test_hidden_source_is_not_parsed_or_included(self):
        w = CognitionWorkspace()
        w.put_source('scene', 'SECRET\n' + COPY_K, permitted_observers=('Mira',))
        report = prepare_reports(w, 'What does Mira believe?', source_id='scene', observer='Kai')
        self.assertEqual(report.current(w.core)['missing_evidence'], 'SYSTEM_INSUFFICIENT')
        self.assertNotIn('SECRET', str(report.messages(w.core)))

    def test_b02_composition_receipt_does_not_create_listener_belief(self):
        view = CommunicationScene(N + "\nNarrator: Kai heard Noor's last statement.").view('Kai')
        w = view.workspace()
        report = prepare_reports(w, 'What does Mira believe?', source_id=view.source_id, observer='Kai')
        self.assertEqual(report.current(w.core)['assessment'][0]['status'], 'INDIRECT_REPORTS_ONLY')
        listener = prepare_reports(w, 'What does Kai believe?', source_id=view.source_id, observer='Kai')
        self.assertFalse(listener.current(w.core)['reports'])

    def test_source_revision_invalidates_old_report_and_relation_claims(self):
        w, report, _ = self.run_scene('\n'.join((N, K, COPY_K)))
        w.put_source('scene', 'Noor said, "Mira is unsure whether the gate is open."')
        old = report.current(w.core)
        self.assertEqual(old['report_occurrences'], 0)
        self.assertEqual(old['current_provenance_family_count'], 0)
        new = prepare_reports(w, 'What does Mira believe?', source_id='scene').current(w.core)
        self.assertEqual(new['report_occurrences'], 1)
        self.assertEqual(new['reports'][0]['result'], 'SOURCE_REPORTED_UNCERTAIN')

    def test_retiring_origin_never_promotes_copies_to_independent_sources(self):
        w, report, payload = self.run_scene('\n'.join((N, K, COPY_K)))
        origin = next(r['expression_id'] for r in payload['reports'] if r['reporter'] == 'Noor')
        w.core.withdraw(origin)
        current = report.current(w.core)
        self.assertEqual(current['report_occurrences'], 1)
        self.assertEqual(current['current_provenance_family_count'], 0)
        self.assertIsNone(current['independent_support_count'])
        self.assertEqual(len(current['provenance_families']), 1)

    def test_resource_budget_and_wrong_operator_do_not_silently_collapse(self):
        with self.assertRaises(ValueError):
            self.run_scene(N + '\n' + K, max_reports=1)
        w, report, row = self.run_scene('Mira said, "I know the gate is open."')
        self.assertFalse(row['reports'])
        with self.assertRaises(ValueError):
            report.messages(w.core, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
