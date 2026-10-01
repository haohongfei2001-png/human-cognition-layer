"""Exact-slot spending gates, crash recovery and mock-only execution."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_source_inference_synthetic_once as m


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = json.loads(m.protocol.PACKAGE.read_text())
        cls.plan = m.slots(cls.package)
        cls.runner = json.loads(m.MANIFEST.read_text())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'ledger.sqlite3'
        self.identity = dict(mode='SIMULATION', protocol_sha256=m.PROTOCOL_SHA)
        self.addCleanup(self.tmp.cleanup)

    def ledger(self):
        ledger = m.Ledger(self.path, self.identity, self.plan)
        self.addCleanup(ledger.close)
        return ledger

    def test_exact_frozen_requests_order_and_decimal_reservations(self):
        expected = [row['arms'][arm]['request'] for row in self.package['inputs'] for arm in row['execution_order']]
        self.assertEqual([s['request'] for s in self.plan], expected)
        self.assertEqual(len(self.plan), 36)
        self.assertEqual(sum(m.Decimal(s['reserve_usd']) for s in self.plan), m.Decimal('1.45776312'))
        self.assertLess(sum(m.Decimal(s['reserve_usd']) for s in self.plan), m.CAP)
        changed = copy.deepcopy(self.package)
        changed['inputs'][0]['arms']['Base']['request']['messages'][0]['content'] += ' drift'
        with self.assertRaises(m.GateError):
            m.slots(changed)

    def test_no_authority_default_old_consumed_and_partial_grants_refuse(self):
        for grant in (None, {}, {'status': 'CLOSED', 'remaining_usd': 0},
                      dict(m.authorized_grant(self.runner), maximum_calls=37),
                      dict(m.authorized_grant(self.runner), hard_cap_usd='3.00')):
            with self.subTest(grant=grant), self.assertRaises(m.GateError):
                m.require_grant(self.runner, grant)
        m.require_grant(self.runner, m.authorized_grant(self.runner))

    def env_and_runs(self):
        env = dict(GITHUB_EVENT_NAME='push', GITHUB_REF=m.RUN_REF,
            GITHUB_RUN_ATTEMPT='1', GITHUB_RUN_ID='123', GITHUB_SHA='a' * 40,
            GITHUB_REPOSITORY='haohongfei2001-png/human-cognition-layer')
        runs = dict(total_count=1, workflow_runs=[dict(id=123, head_sha='a' * 40, event='push', run_attempt=1)])
        return env, runs

    def test_first_workflow_only_refuses_rerun_duplicates_missing_pages_and_other_heads(self):
        env, runs = self.env_and_runs()
        m.require_unique_run(env, runs)
        for key, value in [('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_REF', 'refs/heads/main'),
                           ('GITHUB_EVENT_NAME', 'pull_request'), ('GITHUB_RUN_ID', '124'),
                           ('GITHUB_REPOSITORY', 'other/fork')]:
            with self.subTest(key=key), self.assertRaises(m.GateError):
                m.require_unique_run(dict(env, **{key: value}), runs)
        for change in ({}, dict(runs, total_count=2), dict(runs, workflow_runs=[]),
                       dict(runs, workflow_runs=[dict(runs['workflow_runs'][0], head_sha='b'*40)])):
            with self.assertRaises(m.GateError):
                m.require_unique_run(env, change)

    def test_reservation_durable_before_each_call_exact_36_and_no_replay(self):
        ledger = self.ledger()
        seen = []
        def transport(req):
            connection = sqlite3.connect(self.path)
            rows = connection.execute('SELECT state FROM attempts ORDER BY slot').fetchall()
            connection.close()
            self.assertEqual(rows[-1][0], 'RESERVED')
            self.assertEqual(len(rows), len(seen) + 1)
            seen.append(req)
            return m.mock_response(req)
        receipt = ledger.run(transport)
        self.assertEqual(receipt['status'], 'COMPLETE')
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertEqual(receipt['simulated_calls'], 36)
        self.assertEqual(receipt['reserved_usd'], '1.45776312')
        self.assertEqual(receipt['remaining_authority_usd'], '0')
        self.assertIsNone(receipt['actual_invoice_cost_usd'])
        ledger.run(lambda _: self.fail('completed ledger must not call'))
        self.assertEqual(seen, [s['request'] for s in self.plan])

    def test_transport_failure_stops_unknown_cost_no_retry_or_next_slot(self):
        ledger = self.ledger()
        calls = []
        def transport(req):
            calls.append(req)
            raise TimeoutError('SYNTHETIC_SECRET_MUST_NOT_BE_WRITTEN')
        with self.assertRaises(m.GateError):
            ledger.run(transport)
        receipt = ledger.receipt()
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt['status'], 'STOPPED_OUTCOME_UNCERTAIN')
        self.assertEqual(receipt['reserved_usd'], self.plan[0]['reserve_usd'])
        self.assertIsNone(receipt['rated_peak_usage_cost_usd'])
        self.assertNotIn('SYNTHETIC_SECRET', json.dumps(receipt))
        with self.assertRaises(m.GateError):
            ledger.run(lambda _: self.fail('uncertain ledger must not call'))

    def test_process_interruption_reserved_slot_is_never_retried(self):
        ledger = m.Ledger(self.path, self.identity, self.plan)
        try:
            with self.assertRaises(KeyboardInterrupt):
                ledger.run(lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
        finally:
            ledger.close()
        reopened = self.ledger()
        with self.assertRaises(m.GateError):
            reopened.run(lambda _: self.fail('crash outcome must not replay'))
        self.assertEqual(reopened.receipt()['attempted_slots'], 1)
        self.assertEqual(reopened.receipt()['attempts'][0]['state'], 'UNCERTAIN')

    def test_successfully_committed_prefix_resumes_only_remaining_slots(self):
        ledger = self.ledger()
        slot = self.plan[0]
        raw = m.mock_response(slot['request'])
        with ledger.db:
            ledger.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)',
                (0, slot['request_sha256'], slot['reserve_usd'], 'RECEIVED', json.dumps(raw),
                 json.dumps(m.validate_response(raw, slot))))
        seen = []
        receipt = ledger.run(lambda req: (seen.append(req), m.mock_response(req))[1])
        self.assertEqual(len(seen), 35)
        self.assertEqual(seen, [s['request'] for s in self.plan[1:]])
        self.assertEqual(receipt['attempted_slots'], 36)

    def test_two_writers_and_changed_invocation_refuse(self):
        ledger = self.ledger()
        with self.assertRaisesRegex(m.GateError, 'another process'):
            m.Ledger(self.path, self.identity, self.plan)
        other = Path(self.tmp.name) / 'other.sqlite3'
        first = m.Ledger(other, self.identity, self.plan)
        first.close()
        with self.assertRaisesRegex(m.GateError, 'identity drift'):
            m.Ledger(other, dict(self.identity, run_id='different'), self.plan)
        self.assertEqual(ledger.receipt()['attempted_slots'], 0)

    def test_usage_failure_preserves_raw_and_reservation_without_next_call(self):
        for bad in ({'prompt_tokens': -1, 'completion_tokens': 1},
                    {'prompt_tokens': True, 'completion_tokens': 1},
                    {'prompt_tokens': 1, 'completion_tokens': 8225}, {}):
            path = Path(self.tmp.name) / ('usage' + str(len(list(Path(self.tmp.name).iterdir()))) + '.sqlite3')
            ledger = m.Ledger(path, self.identity, self.plan)
            raw = m.mock_response(self.plan[0]['request']); raw['usage'] = bad
            try:
                with self.assertRaises(m.GateError):
                    ledger.run(lambda _: raw)
                receipt = ledger.receipt()
                self.assertEqual(receipt['attempted_slots'], 1)
                self.assertEqual(receipt['attempts'][0]['response_raw'], raw)
                self.assertEqual(receipt['status'], 'STOPPED_INVALID_USAGE')
            finally:
                ledger.close()

    def test_format_failure_retained_without_extra_or_replacement_answer(self):
        ledger = self.ledger()
        def transport(req):
            raw = m.mock_response(req); raw['choices'][0]['finish_reason'] = 'length'
            return raw
        receipt = ledger.run(transport)
        self.assertEqual(receipt['attempted_slots'], 36)
        self.assertTrue(all(not a['detail']['format_valid'] for a in receipt['attempts']))
        self.assertTrue(all(a['detail']['semantic_score'] is None for a in receipt['attempts']))

    def test_nested_citation_shape_is_not_mislabeled_as_valid(self):
        slot = self.plan[0]
        raw = m.mock_response(slot['request'])
        content = json.loads(raw['choices'][0]['message']['content'])
        for citations in ([42], [{}], ['invented citation'], [{'source_id': 's', 'quote': 9}],
                          [{'source_id': 's', 'quote': 'q', 'version': True}],
                          [{'source_id': 's', 'quote': 'q', 'start': -1}],
                          [{'source_id': 's', 'quote': 'q', 'extra': 'field'}]):
            content['source_citations'] = citations
            raw['choices'][0]['message']['content'] = json.dumps(content)
            self.assertFalse(m.validate_response(raw, slot)['format_valid'])
        # A shaped invented quote is format-valid, never semantic-certified.
        content['source_citations'] = [{'source_id': 's', 'quote': 'invented', 'version': 1, 'start': 0}]
        raw['choices'][0]['message']['content'] = json.dumps(content)
        result = m.validate_response(raw, slot)
        self.assertTrue(result['format_valid'])
        self.assertIsNone(result['semantic_score'])

    def test_failed_reservation_write_prevents_transport(self):
        ledger = self.ledger()
        ledger.db.execute('PRAGMA query_only=ON')
        with self.assertRaises(sqlite3.OperationalError):
            ledger.run(lambda _: self.fail('commit failure must not call'))

    def test_ledger_tamper_blocks_call(self):
        ledger = self.ledger()
        with ledger.db:
            ledger.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)', (0, 'wrong', '0', 'RECEIVED', '{}', '{}'))
        with self.assertRaises(m.GateError):
            ledger.run(lambda _: self.fail('drift must not call'))

    def test_missing_success_response_or_false_completion_blocks_resume(self):
        ledger = self.ledger()
        slot = self.plan[0]
        with ledger.db:
            ledger.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?)',
                (0, slot['request_sha256'], slot['reserve_usd'], 'RECEIVED', None, None))
        with self.assertRaises(m.GateError):
            ledger.run(lambda _: self.fail('missing response cannot resume'))
        with ledger.db:
            ledger.db.execute('DELETE FROM attempts')
            ledger.db.execute("UPDATE meta SET status='COMPLETE' WHERE id=1")
        with self.assertRaises(m.GateError):
            ledger.run(lambda _: self.fail('false completion cannot resume'))

    def test_real_execution_default_fails_before_price_credential_sdk(self):
        with patch.object(m, 'refresh_price', side_effect=AssertionError('no network')):
            with self.assertRaisesRegex(m.GateError, 'approval grant'):
                m.execute(self.tmp.name)

    def test_dry_run_with_fake_environment_never_accesses_network_or_sdk(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'fake-not-a-secret', 'HCL_AUTHORIZED': 'YES'}):
            with patch.object(m.urllib.request, 'urlopen', side_effect=AssertionError('no network')):
                receipt = m.execute(self.tmp.name, simulation=True)
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertEqual(receipt['simulated_calls'], 36)
        self.assertNotIn('fake-not-a-secret', (Path(self.tmp.name) / 'receipt.json').read_text())

    def test_exact_protocol_and_runner_pins(self):
        self.assertEqual(m.verify_manifest(), self.runner)
        self.assertEqual(m.protocol.digest(m.protocol.verify_package()), m.PROTOCOL_SHA)
        self.assertEqual(json.loads(m.GRANT.read_text())['maximum_calls'], 0)
        self.assertFalse(m.LIVE.exists())


if __name__ == '__main__':
    unittest.main()
