"""Explicit actual-scene resumption applies to literal narrator reports too."""
import json
import unittest

from hcl.cognition import CognitionWorkspace


QUERY = 'Which views does this account report?'
HYPOTHETICAL = 'The following conversation was imagined.\n\n'
REPORT = 'Noor believes the gate is clear.'
RESUMPTION = 'In reality, a bell rang.\n\n'


def prepare(source):
    workspace = CognitionWorkspace()
    workspace.put_source('scene', source)
    entry = workspace.prepare_reader_entry(QUERY, source_ids=('scene',))
    return workspace, entry, json.loads(entry.messages[-1]['content'])


def narrator_objects(payload):
    return [row for row in payload.get('checked_epistemic', {}).get('epistemic_objects', [])
            if row['public_expression']['channel'] == 'SOURCE_NARRATOR_ATTRIBUTION']


class NarratorActualScopeTests(unittest.TestCase):
    def test_actual_narrator_resumption_restores_existing_named_report(self):
        for transition in (RESUMPTION, 'In the actual conversation, a bell rang.\n\n'):
            with self.subTest(transition=transition):
                source = HYPOTHETICAL + transition + REPORT
                workspace, entry, payload = prepare(source)
                reports = narrator_objects(payload)
                self.assertEqual(len(reports), 1)
                self.assertIsNone(reports[0]['private_interpretation'])
                self.assertEqual(payload['sources'][0]['text'], source)
                self.assertEqual(entry.receipt['extraction_calls'], 0)
                for row in payload['cognitive_candidates']:
                    span = workspace.core.spans[row['source_span_id']]
                    self.assertEqual(source[span.start:span.end], span.quote)

    def test_prior_hypothetical_report_is_not_retroactively_restored(self):
        source = HYPOTHETICAL + 'Eva believes the gate is blocked.\n\n' + RESUMPTION + REPORT
        _, _, payload = prepare(source)
        reports = narrator_objects(payload)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]['public_expression']['expressed_content']['content']['holder'], 'Noor')

    def test_spoken_reality_cannot_restore_narrator_report(self):
        for spoken in (
            'Eva said, “In reality, a bell rang.”',
            'Eva: In reality, a bell rang.',
            '_Eva._ In reality, a bell rang.',
        ):
            with self.subTest(spoken=spoken):
                source = HYPOTHETICAL + spoken + '\n\n' + REPORT
                _, entry, payload = prepare(source)
                self.assertEqual(narrator_objects(payload), [])
                self.assertFalse(entry.receipt['checked_treatment_present'])

    def test_embedded_directions_do_not_restore_narrator_report(self):
        for embedded in ('[Stage note. In reality, a bell rang.]',
                         '```\nIn reality, a bell rang.\n```'):
            with self.subTest(embedded=embedded):
                _, _, payload = prepare(HYPOTHETICAL + embedded + '\n\n' + REPORT)
                self.assertEqual(narrator_objects(payload), [])

    def test_later_hypothetical_declaration_suspends_reports_again(self):
        source = HYPOTHETICAL + RESUMPTION + REPORT + '\n\n' + \
            'This scenario is counterfactual.\n\nEva believes the gate is blocked.'
        _, _, payload = prepare(source)
        self.assertEqual(len(narrator_objects(payload)), 1)

    def test_source_revision_removing_transition_invalidates_restored_report(self):
        source = HYPOTHETICAL + RESUMPTION + REPORT
        workspace, before, _ = prepare(source)
        workspace.put_source('scene', HYPOTHETICAL + REPORT)
        with self.assertRaises(ValueError):
            before.current_messages(workspace)
        after = workspace.prepare_reader_entry(QUERY, source_ids=('scene',))
        payload = json.loads(after.messages[-1]['content'])
        self.assertEqual(narrator_objects(payload), [])
        self.assertEqual(payload['sources'][0]['version'], 2)

    def test_resumed_narrator_belief_does_not_become_subject_plan_belief(self):
        source = HYPOTHETICAL + RESUMPTION + REPORT + '\n\n' + (
            'Noor said, “I want to protect the garden.”\n'
            'Noor said, “I plan to call Eva in order to protect the garden if the gate is clear.”\n'
            'Noor said, “I have an opportunity to call Eva.”')
        _, _, payload = prepare(source)
        self.assertEqual(len(narrator_objects(payload)), 1)
        plans = payload['checked_plan_feasibility'][0]['plans']
        self.assertEqual(plans[0]['subjective_condition'], 'UNKNOWN')
        self.assertEqual(plans[0]['subjective_feasibility'], 'BELIEF_CONDITION_UNRESOLVED')
        self.assertEqual(plans[0]['world_feasibility'], 'NOT_ESTABLISHED')

    def test_resumed_report_final_delivery_preserves_raw_and_original_source(self):
        source = HYPOTHETICAL + RESUMPTION + REPORT
        workspace, _, _ = prepare(source)
        raw = json.dumps(dict(answer='The account attributes a belief to Noor.',
            source_citations=[dict(source_id='scene', quote=REPORT)],
            uncertainty='Private truth is not independently established.',
            assumptions='This is a source-relative report.'))
        calls = []
        result = workspace.answer_reader_entry(QUERY, lambda m: calls.append(m) or raw,
            source_ids=('scene',))
        self.assertEqual(result['answer'], raw)
        self.assertEqual(result['answer_raw'], raw)
        self.assertEqual(result['preparation_provider_calls'], 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0][-2]['content'])['sources'][0]['text'], source)
        self.assertFalse(result['source_citation_audit']['semantic_certification'])

    def test_ordinary_report_remains_source_attribution_not_private_truth(self):
        _, entry, payload = prepare(REPORT)
        self.assertTrue(entry.receipt['checked_treatment_present'])
        reports = narrator_objects(payload)
        self.assertEqual(len(reports), 1)
        self.assertIsNone(reports[0]['private_interpretation'])

    def test_closed_embedded_transition_is_not_a_later_actual_transition(self):
        for embedded in ('“In reality, a bell rang.”',
                         '"In reality, a bell rang."',
                         '[Direction. In reality, a bell rang.]',
                         '```text\nIn reality, a bell rang.\n```'):
            _, _, payload = prepare(HYPOTHETICAL + embedded + '\n\n' + REPORT)
            self.assertEqual(narrator_objects(payload), [])

    def test_repeated_scene_transitions_restore_only_later_actual_reports(self):
        source = HYPOTHETICAL + 'Eva believes the gate is blocked.\n\n' + RESUMPTION + REPORT
        source += '\n\nThis scene is hypothetical.\n\nKai believes the gate is shut.'
        source += '\n\nIn the actual scene, a bell rang.\n\nLina believes the gate is open.'
        _, _, payload = prepare(source)
        holders = [r['public_expression']['expressed_content']['content']['holder']
                   for r in narrator_objects(payload)]
        self.assertEqual(holders, ['Noor', 'Lina'])

    def test_resumption_does_not_erase_literal_report_qualifications(self):
        for report in ('Perhaps Noor believes the gate is clear.',
                       'If Noor believes the gate is clear.',
                       'Noor believes the gate is clear. Eva doubted the report.'):
            _, _, payload = prepare(HYPOTHETICAL + RESUMPTION + report)
            self.assertEqual(narrator_objects(payload), [])


if __name__ == '__main__':
    unittest.main()
