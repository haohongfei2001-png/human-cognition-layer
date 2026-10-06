"""Independent adversarial checks; all transports and receipts are synthetic.

These tests never create a live grant, fetch prices, activate a workflow, or call
the model provider.  Evidence fixtures deliberately preserve the exact frozen
source while changing one admission fact at a time.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import run_two_stage_once as r
from scripts import two_stage_price as price
from scripts import two_stage_public as public
from tests.test_two_stage import Client, execute, exported


NOW = datetime(2026, 10, 6, 19, tzinfo=timezone.utc)
IDENTITY = dict(run_id='731', head_sha='a' * 40)
REASONING_CANARY = 'PRIVATE_REASONING_CANARY_DO_NOT_RETAIN'
ENVELOPE_CANARY = 'PRIVATE_ENVELOPE_CANARY_DO_NOT_RETAIN'


@contextmanager
def phase1_package_read(package):
    """Supply the frozen package in memory, without touching live report files."""
    original = Path.read_text

    def read(path, *args, **kwargs):
        if path == Path('reports/HCL_TWO_STAGE_CNY_1_PACKAGE.json'):
            return json.dumps(package)
        return original(path, *args, **kwargs)

    with patch.object(Path, 'read_text', read):
        yield


def phase1_fixture():
    r.configure(1)
    package = r.build_package()
    case = r.load_frozen()[0]['cases'][0]
    source = case['sources'][0]
    raw = json.dumps(dict(
        answer='Rowan believes Wednesday; Mara believes Thursday. The source does not establish the actual date because it includes no published schedule.',
        source_citations=[dict(source_id=source['source_id'], version=1, quote=source['text'])],
        uncertainty='The actual seminar date is unresolved.',
        assumptions='Neither speaker is treated as an authoritative schedule.'), ensure_ascii=False)
    calls = []
    for phase, reserve in [('planning', r.MAX_PLANNING_CNY), ('answer', r.MAX_ANSWER_CNY)]:
        frozen = package['requests'].get('SMOKE1:HCL:' + phase)
        calls.append(dict(
            call_id='SMOKE1:HCL:' + phase, case_id='SMOKE1', arm='HCL', phase=phase,
            request_sha256=frozen['request_sha256'] if frozen else 'b' * 64,
            request_bytes=frozen['request_bytes'] if frozen else 12000,
            reserved_cny=str(reserve),
            exact_request_reservation_cny=frozen['reservation_cny'] if frozen else str(
                ((2 * 12000 + 2048) * r.CNY_INPUT_RATE + (8192 + 32) * r.CNY_OUTPUT_RATE) / 1000000),
            status='RETURNED', invocation_status='RETURNED', provider_call=True,
            usage=dict(prompt_tokens=100, completion_tokens=100),
            usage_rated_cny=str((100 * r.CNY_INPUT_RATE + 100 * r.CNY_OUTPUT_RATE) / 1000000)))
    arm = dict(case_id='SMOKE1', arm='HCL', status='ANSWER_ACCEPTED',
               final_text=raw, final_fields=json.loads(raw),
               final_answer_sha256=hashlib.sha256(raw.encode()).hexdigest(),
               citations_accepted=True, selected_capabilities=['B01'],
               executed_capabilities=['B01'], checked_treatment=['B01'],
               native_results=1, final_delivery_code='DELIVERED')
    evidence = dict(
        schema='hcl-two-stage-cny-public-evidence-v1', currency='CNY', stage=1, **IDENTITY,
        authorization_ref=r.AUTH, package_sha256=r.digest(package), runtime_sha256=r.RUNTIME,
        model=r.MODEL, planning_tokens=16384, answer_tokens=8192, production_planning_tokens=4096,
        cases=[case], status='COMPLETED_ONE_PASS', calls=calls, arms=[arm],
        provider_calls=2, reserved_cny=str(r.MAX_PLANNING_CNY + r.MAX_ANSWER_CNY), usage_complete=True,
        usage_rated_cny=str(sum(Decimal(c['usage_rated_cny']) for c in calls)),
        budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0,
        remaining_authorized_cny='0', invoice_cost_cny=None, elapsed_seconds=1,
        stage1_semantic_gate='PENDING_INDEPENDENT_SOURCE_REVIEW', efficacy_verified=False,
        i02_certified=False)
    review = dict(
        schema='hcl-two-stage-cny-phase1-source-review-v1', authorization_ref=r.AUTH,
        evidence_sha256=r.digest(evidence), source_sha256=hashlib.sha256(source['text'].encode()).hexdigest(),
        final_answer_sha256=arm['final_answer_sha256'],
        reviewer_role='INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT', overall_pass=True,
        criteria=[dict(id=i + 1, passed=True, reason=reason) for i, reason in enumerate([
            'The answer attributes Wednesday to Rowan and Thursday to Mara without swapping them.',
            'Both dates are attributed beliefs, not an established actual date.',
            'The answer explicitly says the source includes no published schedule.',
            'The exact original source is quoted and the actual date remains unresolved.'
        ])])
    return package, evidence, review


class Phase1GateAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.package, self.evidence, self.review = phase1_fixture()

    def validate(self, evidence=None, review=None):
        with phase1_package_read(self.package):
            return public.validate_phase1_gate(
                self.evidence if evidence is None else evidence,
                self.review if review is None else review)

    def reject_evidence(self, mutate):
        evidence, review = copy.deepcopy(self.evidence), copy.deepcopy(self.review)
        mutate(evidence)
        # A fresh reviewer signature cannot legitimize failed machine gates.
        review['evidence_sha256'] = r.digest(evidence)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            self.validate(evidence, review)

    def test_exact_complete_source_first_fixture_passes_in_both_stage_contexts(self):
        self.assertTrue(self.validate())
        r.configure(2)
        self.assertTrue(self.validate())

    def test_source_text_identity_question_version_and_timestamp_are_exact(self):
        for key, value in [('text', 'Rewritten source'), ('source_id', 'other'),
                           ('version', 2), ('recorded_at', '2026-10-06T17:00:00Z')]:
            with self.subTest(key=key):
                self.reject_evidence(lambda e: e['cases'][0]['sources'][0].update({key: value}))
        for mutation in [lambda e: e['cases'][0].update(question='A substituted question'),
                         lambda e: e['cases'][0]['sources'][0].update(
                             text=e['cases'][0]['sources'][0]['text'] + '\nNarrator: An added conclusion.'),
                         lambda e: e['cases'].append(copy.deepcopy(e['cases'][0])),
                         lambda e: e['cases'][0]['sources'].clear()]:
            self.reject_evidence(mutation)

    def test_final_text_hash_fields_and_original_quote_must_agree(self):
        for mutate in [lambda e: e['arms'][0].update(final_answer_sha256='f' * 64),
                       lambda e: e['arms'][0].update(final_text=e['arms'][0]['final_text'] + ' '),
                       lambda e: e['arms'][0]['final_fields'].update(answer='different'),
                       lambda e: e['arms'][0].update(final_text='{malformed final JSON')]:
            self.reject_evidence(mutate)
        for citation in [dict(source_id='seminar-notes', version=2, quote='Rowan'),
                         dict(source_id='seminar-notes', version=1, quote='Friday'),
                         dict(source_id='different-source', version=1, quote='Rowan'),
                         dict(source_id='seminar-notes', version=1, quote='Rowan', start=99)]:
            def mutate(e):
                fields = copy.deepcopy(e['arms'][0]['final_fields'])
                fields['source_citations'] = [citation]
                raw = json.dumps(fields)
                e['arms'][0].update(final_text=raw, final_fields=fields,
                                    final_answer_sha256=hashlib.sha256(raw.encode()).hexdigest())
            self.reject_evidence(mutate)

    def test_native_result_and_delivery_are_mandatory(self):
        for field, value in [('native_results', 0), ('native_results', True),
                             ('native_results', 4), ('citations_accepted', False),
                             ('final_delivery_code', 'JSON_INVALID'),
                             ('status', 'FINAL_SCHEMA_OR_CITATIONS_REJECTED')]:
            with self.subTest(field=field, value=value):
                self.reject_evidence(lambda e: e['arms'][0].update({field: value}))
        self.reject_evidence(lambda e: e['arms'][0].pop('native_results'))

    def test_complete_known_exact_two_call_usage_is_mandatory(self):
        for mutate in [lambda e: e.update(usage_complete=False),
                       lambda e: e.update(provider_calls=1),
                       lambda e: e['calls'].pop(),
                       lambda e: e['calls'].reverse(),
                       lambda e: e['calls'].append(copy.deepcopy(e['calls'][0])),
                       lambda e: e.update(status='STOPPED_NO_RETRY'),
                       lambda e: e.update(remaining_authorized_cny='0.01'),
                       lambda e: e.update(remaining_authorized_calls=1)]:
            self.reject_evidence(mutate)
        for index in (0, 1):
            for change in [dict(status='FAILED_OR_UNKNOWN'), dict(provider_call=False),
                           dict(invocation_status='INVOKED_OR_SEND_UNKNOWN'),
                           dict(usage={}), dict(usage=dict(prompt_tokens=True, completion_tokens=100)),
                           dict(usage=dict(prompt_tokens=100, completion_tokens=0)),
                           dict(usage=dict(prompt_tokens=100000, completion_tokens=100)),
                           dict(usage_rated_cny='0'), dict(reserved_cny='0.01')]:
                with self.subTest(call=index, change=change):
                    self.reject_evidence(lambda e: e['calls'][index].update(change))
        for field in ('usage', 'usage_rated_cny'):
            self.reject_evidence(lambda e: e['calls'][0].pop(field))

    def test_model_phase_and_planning_request_identity_cannot_be_relabelled(self):
        for field, value in [('model', 'different-model'), ('planning_tokens', 32768),
                             ('answer_tokens', 16384)]:
            with self.subTest(field=field):
                self.reject_evidence(lambda e: e.update({field: value}))
        for change in [dict(phase='answer'), dict(case_id='PAIR1'), dict(arm='Base'),
                       dict(request_sha256='f' * 64)]:
            with self.subTest(change=change):
                self.reject_evidence(lambda e: e['calls'][0].update(change))
        self.reject_evidence(lambda e: e['calls'][0].pop('request_sha256'))
        self.reject_evidence(lambda e: e['calls'][1].update(request_sha256='not-a-hash'))
        self.reject_evidence(lambda e: e['calls'][1].update(exact_request_reservation_cny='0'))

    def test_review_requires_exact_evidence_source_final_and_independent_role(self):
        for field, value in [('evidence_sha256', 'f' * 64), ('source_sha256', 'f' * 64),
                             ('final_answer_sha256', 'f' * 64), ('overall_pass', False),
                             ('overall_pass', 1), ('reviewer_role', 'CASE_AUTHOR'),
                             ('authorization_ref', 'OLD_GRANT')]:
            review = copy.deepcopy(self.review)
            review[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(review=review)
        for field in self.review:
            review = copy.deepcopy(self.review)
            review.pop(field)
            with self.subTest(missing=field), self.assertRaises((ValueError, KeyError)):
                self.validate(review=review)

    def test_each_of_four_semantic_checks_is_required_independently(self):
        for index in range(4):
            for mode in ('missing', 'false', 'unknown', 'no_reason', 'empty_reason', 'extra_field'):
                review = copy.deepcopy(self.review)
                check = review['criteria'][index]
                if mode == 'missing':
                    review['criteria'].pop(index)
                elif mode == 'false':
                    check['passed'] = False
                elif mode == 'unknown':
                    check['passed'] = None
                elif mode == 'no_reason':
                    check.pop('reason')
                elif mode == 'empty_reason':
                    check['reason'] = ''
                else:
                    check['derived_from_score'] = True
                with self.subTest(index=index, mode=mode), self.assertRaises(ValueError):
                    self.validate(review=review)
        review = copy.deepcopy(self.review)
        review['criteria'][3]['id'] = 3
        with self.assertRaises(ValueError):
            self.validate(review=review)

    def test_empty_or_boolean_semantic_criterion_is_not_an_independent_review(self):
        for field, value in [('reason', ' \n\t '), ('id', True)]:
            review = copy.deepcopy(self.review)
            review['criteria'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(review=review)


class PricePreflightAdversarialTests(unittest.TestCase):
    @staticmethod
    def html():
        return '''<table><tr><th>模型</th><td>deepseek-flash</td><td>deepseek-v4-pro</td></tr>
<tr><th>模型版本</th><td>flash</td><td>DeepSeek-V4-Pro-0813</td></tr>
<tr><th>高峰时段</th><td>0.04元</td><td>0.30元</td></tr>
<tr><th>高峰时段</th><td>2元</td><td>9.0元</td></tr>
<tr><th>高峰时段</th><td>8元</td><td>27.0元</td></tr></table>'''.encode()

    def evidence(self):
        return dict(**IDENTITY, url=price.URL, checked_at=NOW.isoformat(),
                    sha256=hashlib.sha256(self.html()).hexdigest(), rates=dict(price.RATES))

    def test_exact_official_table_parses_without_a_network_request(self):
        self.assertEqual(price.parse_price(self.html()), price.RATES)
        self.assertTrue(price.validate_price_evidence(self.evidence(), IDENTITY, NOW))

    def test_price_model_column_version_currency_and_table_drift_fail_closed(self):
        raw = self.html()
        changes = [b'', b'x' * 512001, raw.decode(), b'\xff',
                   raw.replace('9.0元'.encode(), '9.1元'.encode()), raw.replace('27.0元'.encode(), '28.0元'.encode()),
                   raw.replace('元'.encode(), b'USD'), raw.replace('高峰时段'.encode(), '低峰时段'.encode()),
                   raw.replace(b'DeepSeek-V4-Pro-0813', b'DeepSeek-V4-Pro-1006'),
                   raw.replace(b'deepseek-v4-pro</td>', b'deepseek-chat</td>'),
                   raw.replace(b'<td>deepseek-flash</td><td>deepseek-v4-pro</td>',
                               b'<td>deepseek-v4-pro</td><td>deepseek-flash</td>'),
                   raw.replace(b'</table>', '<tr><td>高峰时段</td><td>2元</td><td>9.0元</td></tr></table>'.encode())]
        for index, changed in enumerate(changes):
            with self.subTest(change=index), self.assertRaises((ValueError, UnicodeError)):
                price.parse_price(changed)

    def test_price_receipt_is_exact_same_run_and_exact_frozen_rates(self):
        for change in [dict(run_id='732'), dict(head_sha='b' * 40),
                       dict(url='https://untrusted.invalid/pricing'), dict(sha256='g' * 64),
                       dict(sha256='a' * 63), dict(rates=dict(price.RATES, output='0.01')),
                       dict(private_data=ENVELOPE_CANARY)]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                price.validate_price_evidence(dict(self.evidence(), **change), IDENTITY, NOW)
        for key in self.evidence():
            evidence = self.evidence()
            evidence.pop(key)
            with self.subTest(missing=key), self.assertRaises((ValueError, KeyError)):
                price.validate_price_evidence(evidence, IDENTITY, NOW)

    def test_frozen_version_in_another_column_cannot_mask_pro_version_drift(self):
        raw = self.html().replace(
            b'<td>flash</td><td>DeepSeek-V4-Pro-0813</td>',
            b'<td>DeepSeek-V4-Pro-0813</td><td>DeepSeek-V4-Pro-1006</td>')
        with self.assertRaises(ValueError):
            price.parse_price(raw)

    def test_chinese_price_receipt_cannot_use_english_usd_table_or_rates(self):
        self.assertEqual(price.URL, 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/')
        self.assertEqual(price.RATES['currency'], 'CNY')
        self.assertEqual((price.RATES['input'], price.RATES['output']), ('9.0', '27.0'))
        wrong_prices = self.html().replace('9.0元'.encode(), '1.32元'.encode()).replace(
            '27.0元'.encode(), '3.96元'.encode())
        with self.assertRaises(ValueError):
            price.parse_price(wrong_prices)
        english = self.html().replace('模型版本'.encode(), b'MODEL VERSION').replace(
            '模型'.encode(), b'MODEL').replace('高峰时段'.encode(), b'PEAK')
        with self.assertRaises(ValueError):
            price.parse_price(english)
        for change in [dict(url='https://api-docs.deepseek.com/quick_start/pricing/'),
                       dict(rates=dict(price.RATES, currency='USD')),
                       dict(rates=dict(price.RATES, input='1.32', output='3.96'))]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                price.validate_price_evidence(dict(self.evidence(), **change), IDENTITY, NOW)

    def test_price_receipt_freshness_boundary_future_and_naive_time(self):
        for elapsed in (timedelta(0), timedelta(minutes=10)):
            evidence = dict(self.evidence(), checked_at=(NOW - elapsed).isoformat())
            self.assertTrue(price.validate_price_evidence(evidence, IDENTITY, NOW))
        for checked in [NOW + timedelta(microseconds=1), NOW - timedelta(minutes=10, microseconds=1),
                        NOW.replace(tzinfo=None)]:
            with self.subTest(checked=checked), self.assertRaises(ValueError):
                price.validate_price_evidence(dict(self.evidence(), checked_at=checked.isoformat()), IDENTITY, NOW)


class AuthorizationAndLaunchAdversarialTests(unittest.TestCase):
    def setUp(self):
        r.configure(1)
        self.package = r.build_package()
        self.grant = r.expected_grant(self.package, True)

    def test_prepared_historical_extended_or_cross_stage_grants_never_admit(self):
        bad = [r.expected_grant(self.package)]
        bad += [dict(self.grant, **change) for change in [
            dict(authorization_ref='HISTORICAL_CONSUMED_GRANT'), dict(authorized_cny='14'),
            dict(authorized_calls=14), dict(stage=2), dict(retries=1),
            dict(historical_budget_transfer=True), dict(other_stage_budget_transfer=True),
            dict(expires_at='2027-01-01T00:00:00Z'), dict(approved_at='2026-10-01T00:00:00Z')]]
        for grant in bad:
            with self.subTest(grant=grant), self.assertRaises(ValueError):
                r.require_grant(self.package, grant, NOW)
        r.require_grant(self.package, self.grant, NOW)

    def test_package_and_each_authorized_ceiling_are_exact(self):
        for change in [dict(maximum_calls=3), dict(maximum_cny='2.01'),
                       dict(maximum_aggregate_calls=15), dict(maximum_aggregate_cny='14.01'),
                       dict(runtime_sha256='b' * 64), dict(planning_tokens=32768),
                       dict(answer_tokens=16384), dict(case_substitution=True)]:
            package = dict(self.package, **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.require_grant(package, r.expected_grant(package, True), NOW)

    def test_authorization_start_expiry_and_full_send_margin_are_enforced(self):
        start = datetime.fromisoformat(r.APPROVED.replace('Z', '+00:00'))
        end = datetime.fromisoformat(r.EXPIRES.replace('Z', '+00:00'))
        for now in [start - timedelta(microseconds=1), end, end - timedelta(seconds=r.WAIT),
                    NOW.replace(tzinfo=None), '2026-10-06T17:40:00Z']:
            with self.subTest(now=now), self.assertRaises(ValueError):
                r.require_time(now)
        r.require_time(start)
        r.require_time(end - timedelta(seconds=r.WAIT, microseconds=1))

    def test_phase2_grant_must_resolve_exact_passing_phase1_review(self):
        r.configure(2)
        package = r.build_package()
        with tempfile.TemporaryDirectory() as root:
            review_path, evidence_path = Path(root) / 'review.json', Path(root) / 'evidence.json'
            with patch.object(r, 'PHASE1_REVIEW', review_path), patch.object(r, 'PHASE1_EVIDENCE', evidence_path):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    r.require_grant(package, r.expected_grant(package, True), NOW)
                evidence_path.write_text(json.dumps(dict(status='STOPPED_NO_RETRY')))
                review_path.write_text(json.dumps(dict(overall_pass=False)))
                grant = r.expected_grant(package, True, r.file_sha(review_path))
                with phase1_package_read(self.package), self.assertRaises(ValueError):
                    r.require_grant(package, grant, NOW)
                grant['phase1_source_review_sha256'] = 'f' * 64
                with self.assertRaises(ValueError):
                    r.require_grant(package, grant, NOW)

    def test_marker_history_attempt_event_parent_and_only_changed_path_are_bound(self):
        parent = 'c' * 40
        marker = dict(schema='hcl-two-stage-cny-marker-v1', stage=1, authorization_ref=r.AUTH,
                      package_sha256=r.digest(self.package), grant_sha256=r.digest(self.grant),
                      executor_commit=parent)
        arguments = dict(run_id='731', attempt='1', runs=[dict(id=731, event='push', created_at=NOW.isoformat())],
                         event='push', parent=parent, paths=[str(r.MARKER)], marker=marker,
                         package=self.package, grant=self.grant, now=NOW)
        r.verify_launch(**arguments)
        variants = [dict(run_id='732'), dict(attempt='2'), dict(runs=[]), dict(event='workflow_dispatch'),
                    dict(event='pull_request'), dict(parent='x' * 40), dict(parent='c' * 39),
                    dict(paths=[str(r.MARKER), 'scripts/run_two_stage_once.py']), dict(paths=[]),
                    dict(marker=dict(marker, stage=2)), dict(marker=dict(marker, executor_commit='d' * 40)),
                    dict(marker=dict(marker, grant_sha256='e' * 64)),
                    dict(runs=arguments['runs'] + [dict(id=730, event='push', created_at=(NOW - timedelta(seconds=1)).isoformat())]),
                    dict(runs=arguments['runs'] + [dict(id=730, event='workflow_dispatch', created_at=(NOW - timedelta(seconds=1)).isoformat())]),
                    dict(runs=[dict(id='731', event='push', created_at=NOW.isoformat())])]
        for change in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                r.verify_launch(**dict(arguments, **change))

    def test_stage_budgets_are_disjoint_and_full_reservations_fit_owner_cap(self):
        stage1 = self.package
        r.configure(2)
        stage2 = r.build_package()
        self.assertEqual((stage1['maximum_calls'], stage2['maximum_calls']), (2, 12))
        self.assertEqual((stage1['maximum_cny'], stage2['maximum_cny']), ('2', '12'))
        total = sum(Decimal(p['maximum_schedule_reservation_cny']) for p in (stage1, stage2))
        self.assertEqual(total, Decimal('13.544640'))
        self.assertLess(total, Decimal('14'))
        self.assertTrue(all(not r.expected_grant(p, True)['historical_budget_transfer'] for p in (stage1, stage2)))


class LedgerIsolationAdversarialTests(unittest.TestCase):
    def setUp(self):
        r.configure(1)
        self.package = r.build_package()
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.ticks = [0]
        self.now = [NOW]
        self.ledger = r.Ledger(Path(self.root.name) / 'run', self.package,
                               r.expected_grant(self.package, True), lambda: self.now[0],
                               lambda: self.ticks[0])
        self.ledger.active = 'SMOKE1:HCL'
        self.case = r.load_frozen()[0]['cases'][0]

    def planning(self):
        port = r.validator()
        prompt = r.messages(self.case, 'HCL')
        request, encoded = port.request('planning', prompt)
        quote = Decimal(port.reservation_usd('planning', prompt))
        return request, quote, len(encoded)

    def answer(self):
        payload = dict(question=self.case['question'], sources=[
            {k: s[k] for k in ('source_id', 'version', 'text')} for s in self.case['sources']])
        prompt = [dict(role='user', content=json.dumps(payload))]
        port = r.validator()
        request, encoded = port.request('answer', prompt)
        return request, Decimal(port.reservation_usd('answer', prompt)), len(encoded)

    def test_low_known_usage_does_not_recycle_reserved_phase_money(self):
        planning, quote, size = self.planning()
        held = self.ledger.reserve('SMOKE1:HCL', 'planning', planning, quote, size)
        self.assertEqual(held, r.MAX_PLANNING)
        self.ledger.value['calls'][0].update(status='RETURNED', usage_rated_usd='0.00000528',
                                           usage_rated_cny='0.000036')
        answer, quote, size = self.answer()
        held = self.ledger.reserve('SMOKE1:HCL', 'answer', answer, quote, size)
        self.assertEqual(held, r.MAX_ANSWER)
        self.assertLess(quote, held)
        self.assertEqual(Decimal(self.ledger.value['reserved_usd']), r.MAX_PLANNING + r.MAX_ANSWER)
        self.assertEqual(Decimal(self.ledger.value['reserved_cny']), r.MAX_PLANNING_CNY + r.MAX_ANSWER_CNY)
        self.ledger.close()
        self.assertEqual(self.ledger.value['remaining_authorized_usd'], '0')
        self.assertEqual(self.ledger.value['remaining_authorized_cny'], '0')
        self.assertEqual(self.ledger.value['remaining_authorized_calls'], 0)
        self.assertEqual(self.ledger.value['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
        with self.assertRaises(ValueError):
            self.ledger.reserve('SMOKE1:HCL', 'answer', answer, quote, size)

    def test_missing_or_unknown_planning_cannot_spend_answer_slot(self):
        answer, quote, size = self.answer()
        for status in (None, 'FAILED_OR_UNKNOWN', 'RETURNED_REJECTED', 'RESERVED_BEFORE_CALL'):
            self.ledger.stopped = False
            self.ledger.value['calls'] = [] if status is None else [dict(
                call_id='SMOKE1:HCL:planning', case_id='SMOKE1', status=status,
                reserved_usd=str(r.MAX_PLANNING), reserved_cny=str(r.MAX_PLANNING_CNY))]
            self.ledger.value['reserved_cny'] = '0' if status is None else str(r.MAX_PLANNING_CNY)
            with self.subTest(status=status), self.assertRaises(ValueError):
                self.ledger.reserve('SMOKE1:HCL', 'answer', answer, quote, size)
            self.assertTrue(self.ledger.stopped)

    def test_dynamic_answer_keeps_original_source_question_and_per_phase_cap(self):
        planning, quote, size = self.planning()
        self.ledger.reserve('SMOKE1:HCL', 'planning', planning, quote, size)
        self.ledger.value['calls'][0]['status'] = 'RETURNED'
        original, quote, size = self.answer()
        for field in ('source_text', 'source_version', 'question', 'reserve'):
            self.ledger.stopped = False
            request = copy.deepcopy(original)
            payload = json.loads(request['messages'][-1]['content'])
            if field == 'source_text':
                payload['sources'][0]['text'] += ' Another source sentence.'
            elif field == 'source_version':
                payload['sources'][0]['version'] += 1
            elif field == 'question':
                payload['question'] += ' An extra task.'
            request['messages'][-1]['content'] = json.dumps(payload)
            reserve = r.MAX_ANSWER + Decimal('0.00000001') if field == 'reserve' else quote
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.ledger.reserve('SMOKE1:HCL', 'answer', request, reserve, size)
            self.assertEqual(len(self.ledger.value['calls']), 1)

    def test_duplicate_call_and_cross_stage_or_undeclared_identity_are_rejected(self):
        request, quote, size = self.planning()
        self.ledger.reserve('SMOKE1:HCL', 'planning', request, quote, size)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_CALL'):
            self.ledger.reserve('SMOKE1:HCL', 'planning', request, quote, size)
        self.assertEqual(len(self.ledger.value['calls']), 1)
        for name, phase in [('PAIR1:HCL', 'planning'), ('SMOKE1:Base', 'planning'),
                            ('SMOKE1:HCL', 'repair')]:
            self.ledger.stopped = False
            with self.subTest(name=name, phase=phase), self.assertRaises(ValueError):
                self.ledger.reserve(name, phase, request, quote, size)
        self.assertEqual(len(self.ledger.value['calls']), 1)

    def test_deadline_and_expiry_are_rechecked_before_each_reservation(self):
        request, quote, size = self.planning()
        self.ticks[0] = r.ELAPSED - r.WAIT
        with self.assertRaisesRegex(ValueError, 'BATCH_DEADLINE'):
            self.ledger.reserve('SMOKE1:HCL', 'planning', request, quote, size)
        self.assertEqual(self.ledger.value['calls'], [])
        self.ledger.stopped = False
        self.ticks[0] = 0
        self.now[0] = datetime.fromisoformat(r.EXPIRES.replace('Z', '+00:00'))
        with self.assertRaisesRegex(ValueError, 'AUTHORIZATION_TIME'):
            self.ledger.reserve('SMOKE1:HCL', 'planning', request, quote, size)
        self.assertEqual(self.ledger.value['calls'], [])

    def test_aggregate_and_case_limits_cannot_spend_another_stage_headroom(self):
        request, quote, size = self.planning()
        for field in ('stage_money', 'stage_call_count', 'case_money'):
            self.ledger.stopped = False
            self.ledger.value['calls'] = []
            self.ledger.value['reserved_usd'] = '0'
            self.ledger.value['reserved_cny'] = '0'
            if field == 'stage_money':
                self.ledger.value['reserved_usd'] = str(r.CAP)
            elif field == 'stage_call_count':
                self.ledger.value['calls'] = [dict(call_id='reserved-' + str(i) + ':Base:answer', case_id='OTHER',
                                                 reserved_usd='0', reserved_cny=str(r.MAX_ANSWER_CNY))
                                             for i in range(r.MAX_CALLS)]
                self.ledger.value['reserved_cny'] = str(r.MAX_CALLS * r.MAX_ANSWER_CNY)
            else:
                self.ledger.value['calls'] = [dict(call_id='SMOKE1:HCL:answer', case_id='SMOKE1',
                                                 reserved_usd=str(r.MAX_SCHEDULE), reserved_cny=str(r.MAX_ANSWER_CNY))]
                self.ledger.value['reserved_cny'] = str(r.MAX_ANSWER_CNY)
            original = copy.deepcopy(self.ledger.value['calls'])
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.ledger.reserve('SMOKE1:HCL', 'planning', request, quote, size)
            self.assertEqual(self.ledger.value['calls'], original)

    def test_post_reservation_prompt_mutation_never_reaches_transport(self):
        self.ledger.value['arms'] = [dict(case_id='SMOKE1', arm='HCL')]
        client = Client()
        port = r.Port(client, self.ledger, 'SMOKE1:HCL')
        prompt = r.messages(self.case, 'HCL')
        port.reservation_usd('planning', prompt)
        prompt[-1]['content'] += ' substituted content'
        with self.assertRaises(ValueError):
            port.complete('planning', prompt)
        self.assertEqual(client.calls, [])
        self.assertTrue(self.ledger.stopped)
        self.assertEqual(Decimal(self.ledger.value['reserved_usd']), r.MAX_PLANNING)


class FinalRetentionAdversarialTests(unittest.TestCase):
    def execute(self, client, stage=1):
        # Keep tests independent of whether the parent has refreshed package
        # reports after the most recent test-file edit.
        r.configure(1)
        package = r.build_package()
        with phase1_package_read(package):
            result, package = execute(client, stage)
            return result, exported(result, package)

    def test_noncanonical_and_malformed_raw_final_survives_unchanged_without_envelope(self):
        for raw in [' \n{ malformed "final": "中文 🌿"  ', '{"answer":"partial',
                    'null', '["unexpected schema"]']:
            def mutate(value, index, request):
                value['provider_private_metadata'] = ENVELOPE_CANARY
                value['usage']['reasoning_content'] = REASONING_CANARY
                value['choices'][0]['message']['reasoning_content'] = REASONING_CANARY
                if request['max_tokens'] == 16384:
                    plan = json.loads(value['choices'][0]['message']['content'])
                    plan['task'] = ENVELOPE_CANARY
                    value['choices'][0]['message']['content'] = json.dumps(plan)
                else:
                    value['choices'][0]['message']['content'] = raw
            client = Client(mutate)
            result, output = self.execute(client)
            with self.subTest(raw=raw):
                self.assertEqual(len(client.calls), 2)
                self.assertEqual(output['arms'][0]['final_text'], raw)
                self.assertEqual(output['arms'][0]['final_answer_sha256'], hashlib.sha256(raw.encode()).hexdigest())
                self.assertIsNone(output['arms'][0]['final_fields'])
                self.assertFalse(output['arms'][0]['citations_accepted'])
                self.assertEqual(output['status'], 'STOPPED_NO_RETRY')
                self.assertTrue(output['usage_complete'])
                for value in (result, output):
                    text = json.dumps(value)
                    self.assertNotIn(REASONING_CANARY, text)
                    self.assertNotIn(ENVELOPE_CANARY, text)
                    self.assertNotIn('reasoning_content', text)
                    self.assertNotIn('choices', text)

    def test_finish_length_retains_complete_looking_final_as_failure_without_retry(self):
        originals = []
        def mutate(value, index, request):
            if request['max_tokens'] == 8192:
                originals.append(value['choices'][0]['message']['content'])
                value['choices'][0]['finish_reason'] = 'length'
        for stage, calls in ((1, 2), (2, 12)):
            originals.clear()
            client = Client(mutate)
            result, output = self.execute(client, stage)
            with self.subTest(stage=stage):
                self.assertEqual(len(client.calls), calls)
                self.assertEqual([a['final_text'] for a in output['arms']], originals)
                self.assertTrue(all(a['status'] == 'INCOMPLETE_ANSWER_NO_RETRY' for a in output['arms']))
                # A citation may still pass its source audit; it cannot turn a
                # length-truncated response into a delivered answer.
                self.assertTrue(all(a.get('final_delivery_code') != 'DELIVERED' for a in output['arms']))
                self.assertTrue(output['usage_complete'])
                self.assertEqual(output['remaining_authorized_calls'], 0)
                self.assertEqual(len({c['call_id'] for c in output['calls']}), calls)

    def test_missing_usage_keeps_final_but_closes_unknown_cost_and_all_later_slots(self):
        raw = '{"answer":"visible, usage unknown"}'
        def mutate(value, index, request):
            if request['max_tokens'] == 8192:
                value['choices'][0]['message']['content'] = raw
                value.pop('usage')
        client = Client(mutate)
        result, output = self.execute(client, 2)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(output['arms'][0]['final_text'], raw)
        self.assertFalse(output['usage_complete'])
        self.assertIsNone(output['usage_rated_cny'])
        self.assertEqual(Decimal(output['reserved_cny']), r.MAX_ANSWER_CNY)
        self.assertEqual(output['status'], 'STOPPED_NO_RETRY')
        self.assertTrue(all(a['status'] == 'NOT_ATTEMPTED' for a in output['arms'][1:]))
        self.assertNotIn('HIDDEN_', json.dumps(result))

    def test_retention_bound_is_exact_and_does_not_silently_truncate(self):
        for size in (64000, 64001):
            raw = 'x' * size
            def mutate(value, index, request):
                if request['max_tokens'] == 8192:
                    value['choices'][0]['message']['content'] = raw
            client = Client(mutate)
            result, output = self.execute(client)
            with self.subTest(size=size):
                self.assertEqual(len(client.calls), 2)
                self.assertEqual(output['arms'][0]['final_text'], raw if size == 64000 else None)
                self.assertEqual(output['arms'][0]['status'],
                                 'FINAL_SCHEMA_OR_CITATIONS_REJECTED' if size == 64000 else 'CONTENT_BOUND_EXCEEDED')
                self.assertTrue(output['usage_complete'])

    def test_public_export_refuses_changed_raw_final_hash_and_parsed_fields(self):
        r.configure(1)
        result, package = execute(Client())
        for change in [dict(final_text='rewritten final'), dict(final_answer_sha256='f' * 64),
                       dict(final_fields=dict(answer='altered')), dict(final_text='x' * 64001)]:
            changed = copy.deepcopy(result)
            changed['arms'][0].update(change)
            with self.subTest(change=list(change)), self.assertRaises(ValueError):
                exported(changed, package)

    def test_late_timeout_thread_cannot_mutate_closed_memory_or_receipt_bytes(self):
        r.configure(1)
        package = r.build_package()
        release, returned = threading.Event(), threading.Event()
        client = Client()
        original_create = client.chat.completions.create
        def delayed(**request):
            if request['max_tokens'] == 8192:
                release.wait(timeout=5)
            value = original_create(**request)
            if request['max_tokens'] == 8192:
                value['choices'][0]['message']['content'] = 'LATE_FINAL_MUST_NOT_BE_WRITTEN'
                returned.set()
            return value
        client.chat.completions.create = delayed
        original_init = r.OutputLimitPort.__init__
        original_thread, workers = threading.Thread, []
        def tracked_thread(*args, **kwargs):
            worker = original_thread(*args, **kwargs)
            workers.append(worker)
            return worker
        def short_wait(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            self.maximum_wait_seconds = .05
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'run'
            try:
                with patch.object(r.OutputLimitPort, '__init__', short_wait), \
                     patch('scripts.bounded_diagnostic_port.threading.Thread', tracked_thread):
                    result = r.run(client, package, r.expected_grant(package, True), path, clock=lambda: NOW)
                snapshot = copy.deepcopy(result)
                receipt_before = (path / 'receipt.json').read_bytes()
                self.assertEqual(result['status'], 'STOPPED_NO_RETRY')
                self.assertFalse(exported(result, package)['usage_complete'])
                release.set()
                self.assertTrue(returned.wait(timeout=2))
                for worker in workers:
                    worker.join(timeout=2)
                    self.assertFalse(worker.is_alive())
                self.assertEqual(result, snapshot)
                self.assertEqual((path / 'receipt.json').read_bytes(), receipt_before)
                self.assertNotIn(b'LATE_FINAL_MUST_NOT_BE_WRITTEN', receipt_before)
                self.assertEqual(result['remaining_authorized_calls'], 0)
            finally:
                release.set()


class NativeCNYIsolationAdversarialTests(unittest.TestCase):
    """CNY is the sole authority; USD remains truthful adapter bookkeeping."""

    def setUp(self):
        r.configure(1)
        self.package = r.build_package()

    def ledger(self, stage=1):
        r.configure(stage)
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        package = r.build_package()
        ledger = r.Ledger(Path(root.name) / 'run', package,
                          r.expected_grant(package, True, 'b' * 64 if stage == 2 else None),
                          lambda: NOW, lambda: 0)
        case_id, arm = r.ORDER[0]
        ledger.active = case_id + ':' + arm
        ledger.value['arms'] = [dict(case_id=case_id, arm=arm)]
        return ledger, r.load_frozen()[0]['cases'][0], arm

    def test_native_rates_and_hard_caps_are_exact_not_dollar_relabels(self):
        self.assertEqual((r.CNY_INPUT_RATE, r.CNY_OUTPUT_RATE), (Decimal('9'), Decimal('27')))
        self.assertEqual((r.INPUT_RATE, r.OUTPUT_RATE), (Decimal('1.32'), Decimal('3.96')))
        self.assertEqual(r.MAX_PLANNING_CNY, Decimal('1.109664'))
        self.assertEqual(r.MAX_ANSWER_CNY, Decimal('0.888480'))
        self.assertEqual(r.TOTAL_CAP_CNY, Decimal('14'))
        for stage, cap, full in [(1, '2', '1.998144'), (2, '12', '11.546496')]:
            r.configure(stage)
            package = r.build_package()
            with self.subTest(stage=stage):
                self.assertEqual(package['currency'], 'CNY')
                self.assertIs(package['usd_reference_only'], True)
                self.assertEqual(package['maximum_cny'], cap)
                self.assertEqual(Decimal(package['maximum_schedule_reservation_cny']), Decimal(full))
                self.assertEqual(package['maximum_aggregate_cny'], '14')
                self.assertNotIn('maximum_usd', package)
                self.assertNotIn('maximum_aggregate_usd', package)
                self.assertEqual(Decimal(package['maximum_reference_usd']), r.CAP)
                self.assertEqual(Decimal(package['maximum_schedule_reference_usd']), r.MAX_SCHEDULE)
                for request in package['requests'].values():
                    input_bound = 2 * request['request_bytes'] + 2048
                    output_bound = request['max_tokens'] + 32
                    native = (input_bound * Decimal('9') + output_bound * Decimal('27')) / 1000000
                    reference = (input_bound * Decimal('1.32') + output_bound * Decimal('3.96')) / 1000000
                    self.assertEqual(Decimal(request['reservation_cny']), native)
                    self.assertEqual(Decimal(request['reservation_usd']), reference)
                    self.assertNotEqual(native, reference)

    def test_grant_requires_native_currency_no_usd_or_stage_headroom_transfer(self):
        for stage, cap in ((1, '2'), (2, '12')):
            r.configure(stage)
            package = r.build_package()
            grant = r.expected_grant(package, True, 'b' * 64 if stage == 2 else None)
            self.assertEqual(grant['currency'], 'CNY')
            self.assertEqual(grant['authorized_cny'], cap)
            self.assertNotIn('authorized_usd', grant)
            for change in [dict(currency='USD'), dict(authorized_cny='14'),
                           dict(authorized_usd='2.00'), dict(historical_budget_transfer=True),
                           dict(other_stage_budget_transfer=True),
                           dict(authorized_cny=str(Decimal(cap) + Decimal('0.001856'))),
                           dict(schema='hcl-two-stage-grant-v1'),
                           dict(authorization_ref='OWNER_APPROVED_TWO_STAGE_20261006_173248_14_CALLS_2_USD')]:
                with self.subTest(stage=stage, change=change), self.assertRaisesRegex(ValueError, 'EXACT_NEW_OWNER_GRANT'):
                    r.require_grant(package, dict(grant, **change), NOW)
            old_units = copy.deepcopy(grant)
            old_units['authorized_usd'] = old_units.pop('authorized_cny')
            with self.assertRaisesRegex(ValueError, 'EXACT_NEW_OWNER_GRANT'):
                r.require_grant(package, old_units, NOW)

    def test_cny_approval_does_not_extend_expiry_or_rewrite_frozen_input_time(self):
        self.assertEqual(r.APPROVED, '2026-10-06T18:21:19Z')
        self.assertEqual(r.EXPIRES, '2026-10-07T17:32:48Z')
        self.assertEqual(r.FIXTURE_RECORDED_AT, '2026-10-06T17:32:48Z')
        self.assertNotEqual(r.APPROVED, r.FIXTURE_RECORDED_AT)
        with self.assertRaises(ValueError):
            r.require_time(datetime(2026, 10, 6, 18, 21, 18, tzinfo=timezone.utc))
        for stage in (1, 2):
            r.configure(stage)
            for case in r.load_frozen()[0]['cases']:
                self.assertTrue(all(source['recorded_at'] == r.FIXTURE_RECORDED_AT for source in case['sources']))
            self.assertEqual(str(r.PACKAGE), f'reports/HCL_TWO_STAGE_CNY_{stage}_PACKAGE.json')
            self.assertEqual(str(r.GRANT), f'.github/HCL_TWO_STAGE_CNY_{stage}_GRANT.json')
            self.assertEqual(str(r.MARKER), f'.github/HCL_TWO_STAGE_CNY_{stage}_TRIGGER.json')
            self.assertIn(f'hcl-two-stage-cny-{stage}-once.yml', str(r.WORKFLOW))

    def test_old_usd_grants_are_zero_superseded_and_cannot_authorize_cny(self):
        for stage in (1, 2):
            r.configure(stage)
            package = r.build_package()
            legacy = json.loads(Path(f'.github/HCL_TWO_STAGE_{stage}_GRANT.json').read_text())
            with self.subTest(stage=stage):
                self.assertEqual(legacy['status'], 'SUPERSEDED_BY_CNY_REPLACEMENT_ZERO_MODEL_CALLS')
                self.assertEqual(legacy['authorized_calls'], 0)
                self.assertEqual(legacy['authorized_usd'], '0')
                self.assertEqual(legacy['provider_calls'], 0)
                self.assertEqual(legacy['remaining_authorized_calls'], 0)
                self.assertEqual(legacy['remaining_authorized_usd'], '0')
                self.assertEqual(legacy['superseded_by'], r.AUTH)
                with self.assertRaisesRegex(ValueError, 'EXACT_NEW_OWNER_GRANT'):
                    r.require_grant(package, legacy, NOW)

    def test_cny_cap_blocks_reservation_even_when_usd_reference_has_headroom(self):
        for stage in (1, 2):
            ledger, case, arm = self.ledger(stage)
            phase = 'planning' if arm == 'HCL' else 'answer'
            held_native = r.MAX_PLANNING_CNY if phase == 'planning' else r.MAX_ANSWER_CNY
            client = Client()
            port = r.Port(client, ledger, ledger.active)
            prompt = r.messages(case, arm)
            reference = Decimal(port.inner.reservation_usd(phase, prompt))
            self.assertLess(reference, r.CAP)
            with patch.object(r, 'CAP_CNY', held_native - Decimal('0.000001')):
                with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'CNY_CAP_EXCEEDED'):
                    port.reservation_usd(phase, prompt)
            self.assertEqual(client.calls, [])
            self.assertEqual(ledger.value['calls'], [])
            self.assertEqual(ledger.value['reserved_usd'], '0')
            self.assertEqual(ledger.value['reserved_cny'], '0')
            self.assertTrue(ledger.stopped)

    def test_cny_cap_is_checked_again_after_reservation_before_sdk_dispatch(self):
        for stage in (1, 2):
            ledger, case, arm = self.ledger(stage)
            phase = 'planning' if arm == 'HCL' else 'answer'
            client = Client()
            port = r.Port(client, ledger, ledger.active)
            prompt = r.messages(case, arm)
            port.reservation_usd(phase, prompt)
            native_hold = Decimal(ledger.value['reserved_cny'])
            reference_hold = Decimal(ledger.value['reserved_usd'])
            self.assertLess(reference_hold, r.CAP)
            with patch.object(r, 'CAP_CNY', native_hold - Decimal('0.000001')):
                with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'NATIVE_CNY_LEDGER_CAP_EXCEEDED'):
                    port.complete(phase, prompt)
            self.assertEqual(client.calls, [])
            self.assertEqual(Decimal(ledger.value['reserved_cny']), native_hold)
            self.assertEqual(Decimal(ledger.value['reserved_usd']), reference_hold)
            self.assertEqual(ledger.value['calls'][0]['invocation_status'], 'NOT_INVOKED')

    def test_stage2_aggregate_cny_gate_keeps_stage1_full_reservation(self):
        ledger, case, arm = self.ledger(2)
        client = Client()
        port = r.Port(client, ledger, ledger.active)
        prior_stage_hold = r.MAX_PLANNING_CNY + r.MAX_ANSWER_CNY
        reduced_total = prior_stage_hold + r.MAX_ANSWER_CNY - Decimal('0.000001')
        # USD's 1.70 reference and the stage-two CNY 12 limit both have
        # headroom; the aggregate native gate alone must prevent dispatch.
        with patch.object(r, 'TOTAL_CAP_CNY', reduced_total):
            with self.assertRaisesRegex(ValueError, 'AGGREGATE_CNY_CAP_EXCEEDED'):
                port.reservation_usd('answer', r.messages(case, arm))
        self.assertEqual(client.calls, [])
        self.assertEqual(ledger.value['calls'], [])

    def test_native_hold_cannot_be_recycled_from_lower_known_usage_or_usd_value(self):
        for replacement in ('usage', 'usd', 'zero'):
            ledger, case, arm = self.ledger()
            port = r.Port(Client(), ledger, ledger.active)
            prompt = r.messages(case, arm)
            port.reservation_usd('planning', prompt)
            row = ledger.value['calls'][0]
            row['usage_rated_cny'] = '0.000036'
            native = row['usage_rated_cny'] if replacement == 'usage' else row['reserved_usd'] if replacement == 'usd' else '0'
            row['reserved_cny'] = native
            ledger.value['reserved_cny'] = native
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, 'NATIVE_CNY_RESERVATION_REQUIRED'):
                ledger.admit()

    def test_provider_usage_records_two_true_units_and_public_exposes_only_cny(self):
        def mutate(value, index, request):
            value['usage'].update(prompt_tokens=1234, completion_tokens=100, total_tokens=1334)
        result, package = execute(Client(mutate))
        output = exported(result, package)
        native = (Decimal('1234') * 9 + 100 * 27) / 1000000
        reference = (Decimal('1234') * Decimal('1.32') + 100 * Decimal('3.96')) / 1000000
        self.assertNotEqual(native, reference)
        self.assertEqual(result['currency'], 'CNY')
        self.assertIs(result['usd_reference_only'], True)
        self.assertEqual(output['currency'], 'CNY')
        self.assertEqual(Decimal(output['usage_rated_cny']), 2 * native)
        self.assertIsNone(output['invoice_cost_cny'])
        for private, published in zip(result['calls'], output['calls'], strict=True):
            self.assertEqual(Decimal(private['usage_rated_cny']), native)
            self.assertEqual(Decimal(private['usage_rated_usd']), reference)
            self.assertEqual(Decimal(published['usage_rated_cny']), native)
            self.assertEqual(Decimal(private['reserved_cny']),
                             r.MAX_PLANNING_CNY if private['phase'] == 'planning' else r.MAX_ANSWER_CNY)
            self.assertEqual(Decimal(private['reserved_usd']),
                             r.MAX_PLANNING if private['phase'] == 'planning' else r.MAX_ANSWER)
        def check_keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn('usd', key.lower())
                    check_keys(child)
            elif isinstance(value, list):
                for child in value:
                    check_keys(child)
        check_keys(output)

    def test_public_export_refuses_wrong_or_missing_private_receipt_currency(self):
        result, package = execute(Client())
        for field, value in [('currency', 'USD'), ('currency', None), ('usd_reference_only', False)]:
            changed = copy.deepcopy(result)
            if value is None:
                changed.pop(field)
            else:
                changed[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                exported(changed, package)

    def test_phase1_cannot_pass_with_usd_evidence_or_usd_values_labelled_cny(self):
        package, evidence, review = phase1_fixture()
        mutations = [lambda e: e.update(currency='USD'), lambda e: e.pop('currency'),
                     lambda e: e.update(schema='hcl-two-stage-public-evidence-v1'),
                     lambda e: e.update(reserved_cny=str(r.MAX_PLANNING + r.MAX_ANSWER)),
                     lambda e: e['calls'][0].update(reserved_cny=str(r.MAX_PLANNING)),
                     lambda e: e['calls'][0].update(usage_rated_cny=str((100 * r.INPUT_RATE + 100 * r.OUTPUT_RATE) / 1000000))]
        for mutate in mutations:
            changed = copy.deepcopy(evidence)
            mutate(changed)
            changed_review = dict(review, evidence_sha256=r.digest(changed))
            with phase1_package_read(package), self.assertRaises((ValueError, KeyError)):
                public.validate_phase1_gate(changed, changed_review)


if __name__ == '__main__':
    unittest.main()
