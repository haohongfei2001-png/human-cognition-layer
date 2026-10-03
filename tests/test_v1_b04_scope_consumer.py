"""B04 links only exact eligible A02 cue occurrences from its single preparation."""
import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from hcl.cognition import ClaimKind, CognitionWorkspace
from hcl.cognition.report_provenance import prepare_reports
from tests.test_v1_report_provenance import N, K, COPY_K

QUERY = 'What does Mira believe?'
BASE = N + '\n' + K + '\n'


def cue_candidates(core):
    return [key for key, claim in core.claims.items()
            if claim.content.get('kind') == 'event'
            and claim.content['proposal'].get('speaker_surface') == 'Narrator'
            and core.spans[claim.content['source_span_id']].quote.strip() == COPY_K]


def prepare(text, transform=None):
    workspace = CognitionWorkspace()
    workspace.put_source('scene', text)
    original = workspace.prepare_semantic
    def once(*args, **kwargs):
        result = original(*args, **kwargs)
        return transform(workspace, result) if transform else result
    with patch.object(workspace, 'prepare_semantic', side_effect=once) as call:
        result = prepare_reports(workspace, QUERY, source_id='scene')
    if call.call_count != 1:
        raise AssertionError('copy cue must reuse one A02 preparation')
    return workspace, result, result.current(workspace.core)


def relation_ids(payload):
    return [key for family in payload['provenance_families'] for key in family['relation_claim_ids']]


class CopyCueScopeTests(unittest.TestCase):
    def assert_rejected(self, text, transform=None):
        workspace, result, payload = prepare(text, transform)
        self.assertEqual(payload['current_provenance_family_count'], 2)
        self.assertFalse(relation_ids(payload))
        self.assertTrue(any(row['reason'].startswith('COPY_CUE_') for row in json.loads(result.diagnostics_json)))
        self.assertIsNone(payload['independent_support_count'])
        self.assertEqual(payload['provider_calls'], 0)
        return workspace, result, payload

    def test_two_frozen_original_scope_blockers_remain_separate_families(self):
        for case in json.loads(Path('reports/HCL_RETAINED_ENTRY_SCOPE_BLOCKERS.json').read_text())['cases'][:2]:
            with self.subTest(case=case['case_id']):
                self.assert_rejected(case['source'])

    def test_actual_copy_preserves_full_line_crlf_and_trailing_space(self):
        for newline, suffix in (('\n', ''), ('\r\n', ''), ('\n', '  '), ('\r\n', '  ')):
            text = newline.join((N, K, COPY_K + suffix)) + newline
            workspace, _, payload = prepare(text)
            self.assertEqual(payload['current_provenance_family_count'], 1)
            link = workspace.core.claims[relation_ids(payload)[0]]
            cue = link.content['cue_candidate_id']
            span = workspace.core.spans[workspace.core.claims[cue].content['source_span_id']]
            expected = COPY_K + suffix + ('\r' if newline == '\r\n' else '')
            self.assertEqual(span.quote, expected)
            self.assertEqual(text[span.start:span.end], expected)
            self.assertEqual(span.version, 1)

    def test_embedded_unclosed_and_indented_cues_do_not_authorize_links(self):
        for suffix in ('```example\n' + COPY_K + '\n```', '```example\n' + COPY_K,
                       '[Stage direction.\n' + COPY_K + '\n]',
                       '“Quoted example.\n' + COPY_K + '\n”',
                       'The following scene is hypothetical.\n' + COPY_K,
                       '  ' + COPY_K):
            with self.subTest(suffix=suffix):
                self.assert_rejected(BASE + suffix)

    def test_real_resumption_and_fake_resumption_keep_source_authority(self):
        prefix = BASE + 'Narrator: In a hypothetical scene:\n'
        workspace, _, payload = prepare(prefix + 'Narrator: In reality.\n' + COPY_K)
        self.assertEqual(payload['current_provenance_family_count'], 1)
        self.assertTrue(relation_ids(payload))
        for fake in ('Mira: In reality.', '“Narrator: In reality.”',
                     '```example\nNarrator: In reality.\n```'):
            self.assert_rejected(prefix + fake + '\n' + COPY_K)

    def test_identical_embedded_and_literal_cues_use_exact_occurrence(self):
        embedded = '```example\n' + COPY_K + '\n```'
        for suffix in (embedded + '\n' + COPY_K, COPY_K + '\n' + embedded):
            text = BASE + suffix
            workspace, result, payload = prepare(text)
            self.assertEqual(payload['current_provenance_family_count'], 1)
            self.assertEqual(len(relation_ids(payload)), 1)
            cue_id = workspace.core.claims[relation_ids(payload)[0]].content['cue_candidate_id']
            cue = workspace.core.claims[cue_id].content
            span = workspace.core.spans[cue['source_span_id']]
            self.assertEqual(cue['proposal']['assertion_scope'], 'SOURCE_REPORT')
            self.assertEqual(span.start, text.rindex(COPY_K) if suffix.startswith('```') else len(BASE))
            self.assertTrue(any(row['reason'].startswith('COPY_CUE_') for row in json.loads(result.diagnostics_json)))

    def test_missing_or_unverified_prepared_cue_has_no_raw_fallback(self):
        def missing(workspace, result):
            keys = set(cue_candidates(workspace.core))
            return replace(result, candidate_ids=tuple(k for k in result.candidate_ids if k not in keys))
        self.assert_rejected(BASE + COPY_K, missing)
        for field, value in (('validation', 'UNVERIFIED_CANDIDATE'),
                             ('speaker_surface', 'Mira'), ('assertion_scope', 'CONDITIONAL_OR_EMBEDDED')):
            def invalid(workspace, result):
                key = cue_candidates(workspace.core)[0]
                content = workspace.core.claims[key].content
                if field == 'validation':content['validation']['semantic_support'] = value
                else:content['proposal'][field] = value
                replacement = workspace.core.claim(result.scope, ClaimKind.SYSTEM_INTERPRETATION, content)
                workspace.core.support(replacement, key)
                return replace(result, candidate_ids=tuple(replacement if k == key else k for k in result.candidate_ids))
            self.assert_rejected(BASE + COPY_K, invalid)

    def test_wrong_source_revision_or_span_has_no_raw_fallback(self):
        for change in ('source', 'version', 'start', 'end'):
            def wrong(workspace, result):
                key = cue_candidates(workspace.core)[0]
                content = workspace.core.claims[key].content
                span = workspace.core.spans[content['source_span_id']]
                content['source_span_id'] = workspace.core.add_span(BASE + COPY_K,
                    source_id='other' if change == 'source' else 'scene',
                    version=2 if change == 'version' else 1,
                    start=span.start + (change == 'start'), end=span.end - (change == 'end'))
                replacement = workspace.core.claim(result.scope, ClaimKind.SYSTEM_INTERPRETATION, content)
                workspace.core.support(replacement, key)
                return replace(result, candidate_ids=tuple(replacement if k == key else k for k in result.candidate_ids))
            self.assert_rejected(BASE + COPY_K, wrong)

    def test_withdrawn_or_challenged_cue_cannot_authorize_link(self):
        for challenge in (False, True):
            def invalidate(workspace, result):
                key = cue_candidates(workspace.core)[0]
                if challenge:
                    counter = workspace.core.claim(result.scope, ClaimKind.SOURCE_REPORT, {'challenge': 'Cue is disputed.'})
                    workspace.core.support(counter, workspace._spans['scene'])
                    workspace.core.challenge(key, counter)
                else:workspace.core.withdraw(key)
                return result
            self.assert_rejected(BASE + COPY_K, invalidate)

    def test_each_eligible_occurrence_has_its_own_relation_dependency(self):
        workspace, result, payload = prepare(BASE + COPY_K + '\n' + COPY_K)
        links = relation_ids(payload)
        self.assertEqual(len(links), 2)
        self.assertEqual(len(set(links)), 2)
        cues = [workspace.core.claims[key].content['cue_candidate_id'] for key in links]
        self.assertEqual(len(set(cues)), 2)
        for key, cue in zip(links, cues):
            self.assertTrue(all(cue in supports for supports in workspace.core.dependencies[key]))
        workspace.core.withdraw(cues[0])
        statuses = workspace.core.support_statuses()
        self.assertEqual(statuses[links[0]], 'UNSUPPORTED')
        self.assertEqual(statuses[links[1]], 'SUPPORT_AVAILABLE')
        self.assertEqual(result.current(workspace.core)['current_provenance_family_count'], 0)

    def test_cue_and_both_antecedents_are_conjunctive_obligations(self):
        for obligation in ('cue_candidate_id', 'copier_expression', 'origin_expression'):
            workspace, result, payload = prepare(BASE + COPY_K)
            link = relation_ids(payload)[0]
            key = workspace.core.claims[link].content[obligation]
            self.assertTrue(all(key in supports for supports in workspace.core.dependencies[link]))
            workspace.core.withdraw(key)
            self.assertEqual(workspace.core.support_statuses()[link], 'UNSUPPORTED')
            self.assertEqual(result.current(workspace.core)['current_provenance_family_count'], 0)
            self.assertIsNone(result.current(workspace.core)['independent_support_count'])


if __name__ == '__main__':
    unittest.main()
