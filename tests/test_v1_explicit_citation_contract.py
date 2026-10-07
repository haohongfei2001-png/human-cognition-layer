"""Source-driven synthetic generation through runtime and the frozen consumer.

No model, historical failed output, paid grant or semantic-quality claim is used.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition.reader_entry import (
    _FINAL_ANSWER_POLICY, _FINAL_ANSWER_MEANING_POLICY,
    _EXPLICIT_CITATION_FINAL_ANSWER_POLICY,
)
from scripts import development_explicit_citation_amendment as amendment
from scripts.development_planner_lifecycle_amendment import validate_current
from scripts.run_four_comparison import accepted, final_fields
from tests.test_v1_universal_question import Stub, operation, plan
from tests.test_v1_final_delivery_diagnostics import Clock


class SourceDrivenPort(Stub):
    """A deterministic stand-in that reads the actual answer request, not a model."""
    def __init__(self, ids, transform=None):
        operations = [operation('B01', 'What does the original source report?', [sid]) for sid in ids]
        super().__init__(plan(*(operations or [operation('G01', 'Prepare the caller condition.', [])])))
        self.transform = transform
        self.raw = None

    def complete(self, phase, messages):
        result = super().complete(phase, messages)
        if phase == 'answer':
            policy = messages[0]['content']
            if not policy.startswith(_EXPLICIT_CITATION_FINAL_ANSWER_POLICY):
                raise AssertionError('actual generation request lacks the explicit contract')
            sources = json.loads(messages[-1]['content'])['sources']
            citations = [dict(source_id=s['source_id'], version=s['version'],
                              quote=s['text'], start=0) for s in sources]
            value = dict(answer='A bounded source report: 灯🙂.', source_citations=citations,
                         uncertainty='Only the supplied reports.', assumptions='No unstated facts.')
            if self.transform:
                self.transform(value)
            self.raw = ' \n' + json.dumps(value, ensure_ascii=False) + '\t'
            result['text'] = self.raw
        return result


def execute(sources, transform=None, *, maximum=128000):
    session = UniversalHCL()
    for sid, texts in sources.items():
        for text in texts:
            session.put_source(sid, text)
    port = SourceDrivenPort(list(sources), transform)
    journal = []
    allowance = CallAllowance(2, 0, 'SYNTHETIC_CONTRACT_ONLY',
                              journal=lambda row: journal.append(copy.deepcopy(row)))
    question = 'What does the original source report?' if sources else 'For this analysis, responsibility requires control.'
    receipt = session.answer(question, planner_backend=port, answer_backend=port,
                             allowance=allowance, maximum_context_chars=maximum)
    return receipt, port, journal


class ExplicitCitationContractTests(unittest.TestCase):
    def test_generation_contract_and_legacy_meaning_are_exact(self):
        raw = subprocess.check_output(['git', 'show', amendment.BASELINE + ':hcl/cognition/reader_entry.py'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), amendment.PREVIOUS_FILES['hcl/cognition/reader_entry.py'])
        original = next(n.value for n in ast.parse(raw).body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == '_FINAL_ANSWER_POLICY' for t in n.targets))
        self.assertEqual(_FINAL_ANSWER_POLICY, ast.literal_eval(original))
        policy_names = {'_FINAL_ANSWER_POLICY', '_FINAL_ANSWER_MEANING_POLICY', '_EXPLICIT_CITATION_FINAL_ANSWER_POLICY'}
        def nonpolicy(tree):
            tree.body = [n for n in tree.body if not (isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id in policy_names for t in n.targets))]
            return ast.dump(tree, include_attributes=False)
        self.assertEqual(nonpolicy(ast.parse(raw)),
                         nonpolicy(ast.parse(Path('hcl/cognition/reader_entry.py').read_text())))
        self.assertTrue(_FINAL_ANSWER_POLICY.startswith(_FINAL_ANSWER_MEANING_POLICY))
        self.assertTrue(_EXPLICIT_CITATION_FINAL_ANSWER_POLICY.startswith(_FINAL_ANSWER_MEANING_POLICY))
        for text in ('required source_id, version and quote', 'only optional field is start',
                     'Do not infer or invent either field', 'not null or a boolean',
                     'A quote string alone is not a citation object', 'zero-based Unicode character offset'):
            self.assertIn(text, _EXPLICIT_CITATION_FINAL_ANSWER_POLICY)
        for text in ('optional fields are version', 'a quote string alone is also accepted', 'a non-null start'):
            self.assertNotIn(text, _EXPLICIT_CITATION_FINAL_ANSWER_POLICY)

    def test_actual_generation_frame_delivers_same_raw_bytes_through_both_gates(self):
        for sources in ({'s': ['Mara heard the notice.']},
                        {'record-a': ['Old notice.', '灯🙂 Mara heard the notice.'],
                         'record-b': ['Sol reported that the door was closed.']}):
            with self.subTest(sources=list(sources)):
                receipt, port, journal = execute(sources)
                self.assertEqual(receipt['final_delivery_code'], 'DELIVERED')
                self.assertEqual(receipt['answer'], port.raw)
                self.assertEqual(receipt['answer_raw'], port.raw)
                frame = port.calls[-1][1]
                parsed = final_fields(port.raw)
                self.assertEqual(parsed, json.loads(port.raw))
                self.assertTrue(accepted(frame, port.raw))
                self.assertFalse(receipt['source_review']['raw_output_rewritten'])
                self.assertFalse(receipt['source_review']['semantic_certification'])
                self.assertEqual(receipt['provider_calls'], 0)
                self.assertEqual(receipt['backend_calls'], 2)
                self.assertEqual([p for p, _ in port.calls], ['planning', 'answer'])
                self.assertTrue(journal)
                supplied = json.loads(frame[-1]['content'])['sources']
                self.assertEqual([(s['source_id'], s['version'], s['text']) for s in supplied],
                                 [(sid, len(texts), texts[-1]) for sid, texts in sources.items()])
                self.assertEqual(parsed['source_citations'], [dict(source_id=s['source_id'],
                    version=s['version'], quote=s['text'], start=0) for s in supplied])

    def test_missing_fields_wrong_shapes_and_null_offsets_are_not_repaired(self):
        changes = [lambda v: v['source_citations'][0].pop('version'),
                   lambda v: v['source_citations'][0].pop('source_id'),
                   lambda v: v['source_citations'][0].pop('quote'),
                   lambda v: v.update(source_citations=['Mara heard the notice.'])]
        for key, value in [('start', None), ('start', -1), ('start', True), ('start', '0'),
                           ('start', 0.0), ('version', True), ('version', '1'), ('version', 1.0),
                           ('end', 22), ('confidence', 1), ('source_id', 1), ('quote', None)]:
            changes.append(lambda v, k=key, x=value: v['source_citations'][0].update({k: x}))
        for change in changes:
            with self.subTest(change=changes.index(change)):
                receipt, port, _ = execute({'s': ['Mara heard the notice.']}, change)
                self.assertEqual(receipt['final_delivery_code'], 'SOURCE_REVIEW_REJECTED')
                self.assertEqual(receipt['source_review']['status'], 'INVALID_EXPLICIT_CITATION_SHAPE')
                self.assertNotIn('answer', receipt)
                self.assertEqual(receipt['answer_raw'], port.raw)
                self.assertFalse(accepted(port.calls[-1][1], port.raw))
                self.assertEqual(receipt['backend_calls'], 2)
                self.assertEqual(receipt['provider_calls'], 0)

    def test_shape_valid_but_false_identity_version_or_quote_still_fails_source_audit(self):
        for change in (dict(source_id='unknown'), dict(version=0), dict(version=2),
                       dict(quote='Mara understood the notice.'), dict(quote=''), dict(quote='  ')):
            with self.subTest(change=change):
                receipt, port, _ = execute({'s': ['Mara heard the notice.']},
                    lambda v: v['source_citations'][0].update(change))
                self.assertEqual(receipt['final_delivery_code'], 'SOURCE_REVIEW_REJECTED')
                self.assertNotEqual(receipt['source_review']['status'], 'INVALID_EXPLICIT_CITATION_SHAPE')
                self.assertNotIn('answer', receipt)
                self.assertEqual(receipt['answer_raw'], port.raw)
                self.assertIsNotNone(final_fields(port.raw))
                self.assertFalse(accepted(port.calls[-1][1], port.raw))

    def test_omitted_offsets_and_existing_unique_quote_relocation_remain_explicit(self):
        for change in (lambda v: v['source_citations'][0].pop('start'),
                       lambda v: v['source_citations'][0].update(start=999)):
            receipt, port, _ = execute({'s': ['Mara heard the notice.']}, change)
            self.assertEqual(receipt['final_delivery_code'], 'DELIVERED')
            self.assertTrue(accepted(port.calls[-1][1], port.raw))
            self.assertEqual(receipt['answer'], port.raw)
            self.assertEqual(receipt['source_review']['anchors'][0]['start'], 0)

    def test_existing_whitespace_only_source_audit_is_not_mislabeled_exact(self):
        receipt, port, _ = execute({'s': ['Mara saw the blue\n  door.']},
            lambda v: v['source_citations'][0].update(quote='blue door.', start=999))
        self.assertEqual(receipt['final_delivery_code'], 'DELIVERED')
        self.assertTrue(accepted(port.calls[-1][1], port.raw))
        self.assertEqual(receipt['answer'], port.raw)
        anchor = receipt['source_review']['anchors'][0]
        self.assertEqual(anchor['location_rule'], 'UNIQUE_WHITESPACE_LAYOUT_ONLY')
        self.assertEqual(anchor['submitted_quote'], 'blue door.')
        self.assertEqual(anchor['original_quote'], 'blue\n  door.')

    def test_repeated_quote_unicode_offsets_still_need_an_unambiguous_location(self):
        source = '灯🙂 Echo. Echo.'
        for offset, expected in ((9, True), (3, True), (None, False), (4, False),
                                 (len(source[:9].encode('utf-16-le')) // 2, False),
                                 (len(source[:9].encode()), False)):
            def change(value):
                value['source_citations'][0].update(quote='Echo.')
                if offset is None:
                    value['source_citations'][0].pop('start')
                else:
                    value['source_citations'][0]['start'] = offset
            receipt, port, _ = execute({'s': [source]}, change)
            self.assertEqual(receipt['final_delivery_code'] == 'DELIVERED', expected)
            self.assertEqual(accepted(port.calls[-1][1], port.raw), expected)
            self.assertEqual(receipt['answer_raw'], port.raw)

    def test_existing_citation_count_and_quote_bounds_are_not_relaxed(self):
        for count, expected in ((32, True), (33, False)):
            receipt, port, _ = execute({'s': ['Mara heard the notice.']},
                lambda v: v.update(source_citations=v['source_citations'] * count))
            self.assertEqual(receipt['final_delivery_code'] == 'DELIVERED', expected)
            self.assertEqual(accepted(port.calls[-1][1], port.raw), expected)
        for length, expected in ((4000, True), (4001, False)):
            receipt, port, _ = execute({'s': ['x' * length]})
            self.assertEqual(receipt['final_delivery_code'] == 'DELIVERED', expected)
            self.assertEqual(accepted(port.calls[-1][1], port.raw), expected)

    def test_empty_citations_preserve_ordinary_and_cited_trial_distinction(self):
        for sources in ({}, {'s': ['Mara heard the notice.']}):
            receipt, port, _ = execute(sources, lambda v: v.update(source_citations=[]))
            self.assertEqual(receipt['final_delivery_code'], 'DELIVERED')
            self.assertEqual(receipt['answer'], port.raw)
            self.assertIsNotNone(final_fields(port.raw))
            self.assertFalse(accepted(port.calls[-1][1], port.raw))
        receipt, port, _ = execute({}, lambda v: v.update(source_citations=[
            dict(source_id='invented', version=1, quote='Unsupported.')]))
        self.assertEqual(receipt['final_delivery_code'], 'SOURCE_REVIEW_REJECTED')
        self.assertNotIn('answer', receipt)

    def test_full_new_generation_contract_is_budgeted_before_answer_transport(self):
        sources = {str(i): ['Mara heard the notice.' + 'x' * 1800] for i in range(3)}
        def quotes(value):
            for citation in value['source_citations']:
                citation['quote'] = 'Mara heard the notice.'
        with patch('hcl.cognition.universal_entry.datetime', Clock):
            receipt, port, _ = execute(sources, quotes)
            self.assertEqual(receipt['final_delivery_code'], 'DELIVERED')
            final = port.calls[-1][1]
            exact = len(json.dumps(final, ensure_ascii=False))
            self.assertGreater(exact, len(json.dumps(port.calls[0][1], ensure_ascii=False)))
            receipt, port, _ = execute(sources, quotes, maximum=exact)
            self.assertEqual(receipt['final_delivery_code'], 'DELIVERED')
            self.assertEqual(port.calls[-1][1], final)
            self.assertTrue(accepted(final, port.raw))
            receipt, port, _ = execute(sources, quotes, maximum=exact - 1)
            self.assertEqual(receipt['failure_reason'], 'complete context exceeds budget; no truncation')
            self.assertEqual([phase for phase, _ in port.calls], ['planning'])
            self.assertNotIn('answer_raw', receipt)
            self.assertEqual(receipt['provider_calls'], 0)

    def test_current_contract_and_historical_freeze_reject_mutations(self):
        self.assertTrue(validate_current())
        original = Path.read_bytes
        for target in (*amendment.REVIEWED_FILES, 'hcl/cognition/retained.py',
                       'scripts/run_four_comparison.py', 'scripts/four_comparison_public.py',
                       'reports/HCL_FOUR_COMPARISON_RESULTS.json', '.github/HCL_FOUR_COMPARISON_GRANT.json'):
            with self.subTest(path=target):
                def changed(path):
                    raw = original(path)
                    return raw + b' ' if str(path) == target else raw
                with patch.object(Path, 'read_bytes', changed), self.assertRaises(ValueError):
                    validate_current()
        with self.assertRaises(ValueError):
            validate_current(current_digest='0' * 64)


if __name__ == '__main__':
    unittest.main()
