"""Paired ordinary-entry diagnostics; synthetic ports only, no model transport."""
from contextlib import ExitStack
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

from hcl.cognition import universal_entry as current
from scripts import development_explicit_citation_amendment as amendment
from scripts import development_final_delivery_amendment as diagnostic_amendment
from hcl.cognition.reader_entry import _FINAL_ANSWER_POLICY, _EXPLICIT_CITATION_FINAL_ANSWER_POLICY
from scripts.run_four_comparison import accepted, final_fields

SOURCE = 'Mara heard the notice.'
QUESTION = 'What does the source report?'
CANARY = 'SYNTHETIC_PRIVATE_CANARY_NOT_DIAGNOSTIC_TEXT'
CODES = {'NOT_REACHED', 'RETURNED_UNVALIDATED', 'JSON_INVALID', 'SCHEMA_INVALID',
         'ANSWER_BLANK', 'SOURCE_REVIEW_REJECTED', 'DELIVERED'}


class Clock:
    @staticmethod
    def now(tz):
        return datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)


def body(**changes):
    value = dict(answer='Mara reportedly heard the notice.',
                 source_citations=[dict(source_id='s', version=1, quote=SOURCE)],
                 uncertainty='Source report only.', assumptions='No comprehension established.')
    value.update(changes)
    return value


def raw_body(**changes):
    return json.dumps(body(**changes), ensure_ascii=False)


def baseline_module():
    amendment.validate_current()  # Also enforce unchanged dependencies in standalone paired runs.
    root = Path(__file__).resolve().parents[1]
    name = 'hcl/cognition/universal_entry.py'
    raw = subprocess.check_output(['git', 'show', amendment.BASELINE + ':' + name], cwd=root)
    if hashlib.sha256(raw).hexdigest() != amendment.PREVIOUS_FILES[name]:
        raise ValueError('exact previous ordinary runtime required')
    name = 'hcl.cognition._final_delivery_frozen_baseline'
    module = types.ModuleType(name)
    module.__package__ = 'hcl.cognition'
    sys.modules[name] = module
    exec(compile(raw, amendment.BASELINE + ':' + name, 'exec'), module.__dict__)
    return module


def execute(module, raw, *, event=None, sourced=True, invalid_plan=False, no_native=False,
            parser_error=False, auditor_error=False, journal_error=False):
    """Use identical authored data, real native B01/G01 and metering on each side."""
    calls, journal = [], []
    with ExitStack() as stack:
        stack.enter_context(patch.object(module, 'datetime', Clock))
        session = module.UniversalHCL()
        if sourced:
            session.put_source('s', SOURCE)
        question = QUESTION if sourced else 'For this analysis, responsibility requires control.'
        operation = dict(capability='B01' if sourced else 'G01', question=question,
                         source_ids=['s'] if sourced else [], bindings=[])
        planner = json.dumps(dict(task='Source-bounded analysis', operations=[] if no_native else [operation], limitations=[]))
        if invalid_plan:
            planner = '{invalid planner JSON'

        class Port:
            provider_free = True
            def reservation_usd(self, phase, messages):
                return '0.10'  # Synthetic metering units; no paid transport.
            def complete(self, phase, messages):
                calls.append((phase, copy.deepcopy(messages)))
                if phase == 'answer':
                    if event == 'transport_error':
                        raise RuntimeError(CANARY)
                    if event == 'source_revision':
                        session.put_source('s', SOURCE + ' A later correction.')
                    if event == 'support_withdrawal':
                        session.workspace.core.withdraw(session.workspace._spans['s'])
                value = dict(text=planner if phase == 'planning' else raw,
                             actual_usd='0.01', usage={'input_tokens': 10, 'output_tokens': 5})
                if phase == 'answer' and event == 'invalid_usage':
                    value['usage']['input_tokens'] = CANARY
                return value

        def record(value):
            journal.append(copy.deepcopy(value))
            if journal_error and value['attempts'][-1]['phase'] == 'answer' and value['attempts'][-1]['status'] == 'RETURNED':
                raise RuntimeError(CANARY)

        if parser_error:
            original = json.loads
            def parse(value, *args, **kwargs):
                if value == raw:
                    raise RuntimeError(CANARY)
                return original(value, *args, **kwargs)
            stack.enter_context(patch.object(module.json, 'loads', parse))
        if auditor_error:
            stack.enter_context(patch.object(module, 'audit_supplied_source_citations', side_effect=RuntimeError(CANARY)))
        port = Port()
        allowance = module.CallAllowance(2, '.20', 'SYNTHETIC_OFFLINE_NO_PROVIDER', journal=record)
        result = session.answer(question, planner_backend=port, answer_backend=port, allowance=allowance)
        return dict(receipt=result, calls=calls, journal=journal, closed=allowance.closed,
                    reserved_usd=str(allowance.reserved_usd), attempts=copy.deepcopy(allowance.attempts))


class FinalDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = baseline_module()

    def pair(self, expected, raw=None, **options):
        raw = raw_body() if raw is None else raw
        before = execute(self.previous, raw, **options)
        after = execute(current, raw, **options)
        self.assertEqual(set(after['receipt']), set(before['receipt']))
        code = after['receipt']['final_delivery_code']
        self.assertIn(code, CODES)
        self.assertEqual(code, expected)
        self.assertEqual(before['receipt']['final_delivery_code'], expected)
        # Only the disclosed contract prefix changes. Original question, source,
        # native state and the orchestration-policy suffix remain exact.
        compared = copy.deepcopy(after)
        frames = [messages for phase, messages in compared['calls'] if phase == 'answer']
        if 'actual_final_messages' in compared['receipt']:
            frames.append(compared['receipt']['actual_final_messages'])
        for frame in frames:
            policy = frame[0]['content']
            self.assertTrue(policy.startswith(_EXPLICIT_CITATION_FINAL_ANSWER_POLICY))
            frame[0]['content'] = _FINAL_ANSWER_POLICY + policy[len(_EXPLICIT_CITATION_FINAL_ANSWER_POLICY):]
        # Malformed fields already refused by the source auditor now have a
        # shape-specific refusal. Their failure outcome/raw bytes are unchanged.
        if compared['receipt'].get('source_review', {}).get('status') == 'INVALID_EXPLICIT_CITATION_SHAPE':
            self.assertFalse(before['receipt']['source_review']['deliverable'])
            self.assertEqual(compared['receipt']['source_review'], dict(
                status='INVALID_EXPLICIT_CITATION_SHAPE', deliverable=False,
                semantic_certification=False, anchors=[], raw_output_rewritten=False,
                source_identity_substituted=False))
            compared['receipt']['source_review'] = before['receipt']['source_review']
        self.assertEqual(compared, before)  # All other fields/raw output/calls/journals/holds.
        self.assertEqual(after['receipt']['provider_calls'], 0)
        self.assertLessEqual(len(after['calls']), 2)
        self.assertNotIn(CANARY, code)
        return after

    def test_valid_raw_json_and_unicode_are_delivered_without_rewriting(self):
        for raw in (raw_body(), ' \t\r\n' + raw_body() + '\n ',
                    raw_body(answer='报告：Mara 听到了。🙂'),
                    json.dumps(body(answer='报告：Mara 听到了。🙂')),
                    raw_body(answer='\u2003 可能。 \n'), raw_body(answer='\u200b'),
                    raw_body(answer='JSON_INVALID is ordinary answer text.'),
                    '{"answer":"discarded",' + raw_body()[1:]):
            with self.subTest(raw=raw[:35]):
                result = self.pair('DELIVERED', raw)
                self.assertEqual(result['receipt']['answer'], raw)

    def test_all_failed_final_gates_have_fixed_codes_and_same_precedence(self):
        cases = [
            ('JSON_INVALID', '{bad ' + CANARY),
            ('JSON_INVALID', '```json\n' + raw_body() + '\n```'),
            ('SCHEMA_INVALID', 'null'), ('SCHEMA_INVALID', '[]'),
            ('SCHEMA_INVALID', '{}'),
            ('SCHEMA_INVALID', raw_body(answer=7)),
            ('SCHEMA_INVALID', raw_body(answer='', source_citations='wrong type')),
            ('SCHEMA_INVALID', json.dumps(dict(body(), final_delivery_code='DELIVERED'))),
            ('ANSWER_BLANK', raw_body(answer='')),
            ('ANSWER_BLANK', raw_body(answer=' \t\n\u3000\u00a0')),
            ('ANSWER_BLANK', raw_body(answer='', source_citations=[dict(quote='invented')])) ,
            ('SOURCE_REVIEW_REJECTED', raw_body(source_citations=[dict(source_id='other', version=1, quote=SOURCE)])),
            ('SOURCE_REVIEW_REJECTED', raw_body(source_citations=[dict(source_id='s', version=2, quote=SOURCE)])),
            ('SOURCE_REVIEW_REJECTED', raw_body(source_citations=[dict(source_id='s', version=1, quote=SOURCE, end=len(SOURCE))])),
            ('SOURCE_REVIEW_REJECTED', raw_body(source_citations=[dict(source_id='s', quote=float('nan'))])),
            ('RETURNED_UNVALIDATED', '[' * 20000 + ']' * 20000),
        ]
        for code, raw in cases:
            with self.subTest(code=code, raw=raw[:25]):
                result = self.pair(code, raw)
                self.assertNotIn('answer', result['receipt'])
                self.assertEqual(result['receipt']['answer_raw'], raw)

    def test_metered_return_source_changes_and_unexpected_errors_are_not_misclassified(self):
        for event in ('source_revision', 'support_withdrawal'):
            with self.subTest(event=event):
                self.pair('RETURNED_UNVALIDATED', '{invalid', event=event)
        for options in ({'parser_error': True}, {'auditor_error': True}):
            result = self.pair('RETURNED_UNVALIDATED', **options)
            self.assertNotIn(CANARY, json.dumps(result))
        for options in ({'event': 'transport_error'}, {'event': 'invalid_usage'}, {'journal_error': True}):
            result = self.pair('NOT_REACHED', **options)
            self.assertNotIn(CANARY, json.dumps(result))
            self.assertNotIn('answer_raw', result['receipt'])

    def test_pre_final_failure_does_not_imply_a_returned_final_answer(self):
        for options in ({'invalid_plan': True}, {'no_native': True}):
            result = self.pair('NOT_REACHED', **options)
            self.assertEqual([phase for phase, _ in result['calls']], ['planning'])

    def test_exact_final_character_bound_and_oversize_keep_existing_metering(self):
        raw = raw_body(answer='x')
        for length, expected in ((64000, 'DELIVERED'), (64001, 'NOT_REACHED')):
            padded = raw_body(answer='x' * (length - len(raw) + 1))
            self.assertEqual(len(padded), length)
            result = self.pair(expected, padded)
            self.assertEqual(len(result['attempts']), 2)
            self.assertEqual(result['reserved_usd'], '0.20')

    def test_source_free_native_analysis_obeys_same_empty_citation_rule(self):
        self.pair('DELIVERED', raw_body(source_citations=[]), sourced=False)
        self.pair('ANSWER_BLANK', raw_body(answer=' ', source_citations=[]), sourced=False)
        self.pair('SOURCE_REVIEW_REJECTED', sourced=False)

    def test_legacy_shapes_cannot_claim_delivery_under_the_explicit_contract(self):
        permitted = ([dict(source_id='s', quote=SOURCE)], [SOURCE],
                     [dict(source_id='s', version=1, quote=SOURCE, start=None)])
        for citations in permitted:
            raw = raw_body(source_citations=citations)
            before = execute(self.previous, raw)
            result = execute(current, raw)
            self.assertEqual(before['receipt']['final_delivery_code'], 'DELIVERED')
            self.assertEqual(result['receipt']['final_delivery_code'], 'SOURCE_REVIEW_REJECTED')
            self.assertEqual(result['receipt']['source_review']['status'], 'INVALID_EXPLICIT_CITATION_SHAPE')
            self.assertNotIn('answer', result['receipt'])
            self.assertEqual(result['receipt']['answer_raw'], raw)
            self.assertEqual(result['journal'], before['journal'])
            self.assertEqual(result['attempts'], before['attempts'])
            self.assertEqual(result['reserved_usd'], before['reserved_usd'])
            self.assertEqual([phase for phase, _ in result['calls']], ['planning', 'answer'])
            self.assertEqual(result['receipt']['provider_calls'], 0)
            self.assertIsNone(final_fields(raw))
            self.assertFalse(accepted(result['calls'][-1][1], raw))
        raw = raw_body(source_citations=[])
        result = self.pair('DELIVERED', raw)
        self.assertIsNotNone(final_fields(raw))
        self.assertFalse(accepted(result['calls'][-1][1], raw))

    def test_invalid_entry_arguments_still_raise_before_receipt_creation(self):
        for question, kwargs in (('', {}), (None, {}), ('Question', {'maximum_context_chars': 1})):
            errors = []
            for module in (self.previous, current):
                try:
                    module.UniversalHCL().answer(question, **kwargs)
                except module.HCLBoundaryError as error:
                    errors.append((type(error).__name__, str(error)))
                else:
                    self.fail('invalid entry argument unexpectedly returned a receipt')
            self.assertEqual(errors[0], errors[1])


class FinalDeliveryAmendmentTests(unittest.TestCase):
    def test_current_runtime_and_consumed_history_are_pinned(self):
        self.assertTrue(amendment.validate_current())
        original = Path.read_bytes
        for name in json.loads(diagnostic_amendment.PINS.read_text())['files_sha256']:
            with self.subTest(path=name):
                def drift(path):
                    raw = original(path)
                    return raw + b' ' if str(path) == name else raw
                with patch.object(Path, 'read_bytes', drift):
                    with self.assertRaisesRegex(ValueError, 'historical amendment'):
                        amendment.validate_current()

    def test_new_pin_manifest_cannot_silently_rebaseline_history(self):
        original = Path.read_bytes
        def drift(path):
            raw = original(path)
            return raw + b'\n' if path == diagnostic_amendment.PINS else raw
        with patch.object(Path, 'read_bytes', drift):
            with self.assertRaisesRegex(ValueError, 'pin manifest drift'):
                amendment.validate_current()


if __name__ == '__main__':
    unittest.main()
