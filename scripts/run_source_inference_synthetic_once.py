"""SID001 exact-slot runner; default is provider-free and has no spending authority."""
import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import urllib.request

from scripts import source_inference_synthetic_diagnostic as protocol

ROOT = Path('reports/source-inference-synthetic-runner')
MANIFEST = ROOT / 'RUNNER_PACKAGE.json'
GRANT = ROOT / 'GRANT.json'
PRICE = ROOT / 'PRICING_REFRESH.json'
TEMPLATE = Path('.github/frozen/hcl-sid001-once.yml')
LIVE = Path('.github/workflows/hcl-sid001-once.yml')
PROTOCOL_SHA = '3f06c553b8cdfc9cb9836e4500f260d84ef67815a8bab6223de6312bdf4e7332'
APPROVAL = 'Sentinel_080af6f2b5ac8191a066eafd4ccafbc8'
RUN_REF = 'refs/heads/codex/sid001-approved-once'
CREDENTIAL_REF = 'github-actions:repository-secret:DEEPSEEK_API_KEY'
CAP = Decimal('2.50')
RATE_IN, RATE_OUT = Decimal('1.32'), Decimal('3.96')
FILES = ('scripts/run_source_inference_synthetic_once.py',
         'tests/test_source_inference_synthetic_runner.py',
         'docs/HCL_SOURCE_INFERENCE_SYNTHETIC_RUNNER.md', str(TEMPLATE),
         '.github/workflows/hcl-source-inference-runner-provider-free.yml', str(PRICE))


class GateError(ValueError):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    """Persist exports atomically; the SQLite ledger is the authority."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def slots(package):
    if protocol.digest(package) != PROTOCOL_SHA:
        raise GateError('exact frozen SID001 package required')
    output = []
    for row in package['inputs']:
        for arm in row['execution_order']:
            frozen = row['arms'][arm]
            req = frozen['request']
            size = len(json.dumps(req, ensure_ascii=False).encode())
            bound = 2 * size + 2048
            reserve = (Decimal(bound) * RATE_IN + Decimal(8224) * RATE_OUT) / 1000000
            if (protocol.digest(req) != frozen['request_sha256'] or size > 12000
                    or req['max_tokens'] != 8192 or req['model'] != 'deepseek-v4-pro'):
                raise GateError('request or reservation drift')
            output.append(dict(index=len(output), case_id=row['case_id'], arm=arm,
                request=copy.deepcopy(req), request_sha256=frozen['request_sha256'],
                input_bound=bound, reserve_usd=str(reserve)))
    if len(output) != 36 or sum(Decimal(x['reserve_usd']) for x in output) > CAP:
        raise GateError('exact 36-slot total reservation exceeds cap')
    return output


def manifest():
    package = protocol.verify_package()
    plan = slots(package)
    return dict(schema='hcl-sid001-runner-v1', protocol_sha256=PROTOCOL_SHA,
        slot_sha256=protocol.digest(plan), maximum_answer_calls=36,
        extraction_calls=0, retries=0, paid_judge_calls=0, hard_cap_usd=str(CAP),
        all_slot_reservation_usd=str(sum(Decimal(x['reserve_usd']) for x in plan)),
        execution_file_sha256={path: sha(path) for path in FILES},
        credential_reference=CREDENTIAL_REF,
        authority='SEPARATE_EXACT_ONE_OFF_GRANT_REQUIRED; MANIFEST_CONFERS_NONE')


def verify_manifest():
    expected = json.loads(MANIFEST.read_text())
    if expected != manifest():
        raise GateError('runner/source/protocol/runtime execution pin drift')
    return expected


def authorized_grant(runner):
    """Expected shape only; never writes or creates authority."""
    return dict(schema='hcl-sid001-one-off-grant-v1', status='READY',
        approval_message=APPROVAL, runner_sha256=protocol.digest(runner),
        protocol_sha256=PROTOCOL_SHA, maximum_calls=36, hard_cap_usd='2.50',
        retries=0, extraction_calls=0, paid_judge_calls=0,
        historical_grant_transfer=False, credential_reference=CREDENTIAL_REF)


def require_grant(runner, grant):
    if grant != authorized_grant(runner):
        raise GateError('fresh exact one-off approval grant required before credential access')


def require_unique_run(env, runs):
    if (env.get('GITHUB_EVENT_NAME') != 'push' or env.get('GITHUB_REF') != RUN_REF
            or env.get('GITHUB_RUN_ATTEMPT') != '1'
            or not env.get('GITHUB_RUN_ID') or not env.get('GITHUB_SHA')
            or env.get('GITHUB_REPOSITORY') != 'haohongfei2001-png/human-cognition-layer'):
        raise GateError('only the approved branch first push invocation may execute')
    rows = runs.get('workflow_runs', [])
    if (runs.get('total_count') != 1 or len(rows) != 1
            or str(rows[0].get('id')) != env['GITHUB_RUN_ID']
            or rows[0].get('head_sha') != env['GITHUB_SHA']
            or rows[0].get('event') != 'push' or rows[0].get('run_attempt') != 1):
        raise GateError('workflow invocation is duplicated or uncertain; refuse all transport')


def refresh_price():
    expected = json.loads(PRICE.read_text())
    with urllib.request.urlopen(expected['url'], timeout=30) as response:
        raw = response.read()
        if response.status != 200 or hashlib.sha256(raw).hexdigest() != expected['html_sha256']:
            raise GateError('official price page changed; re-review before any spend')
    return dict(expected, reverified_at=datetime.now(timezone.utc).isoformat())


def citation_shape(value):
    # Shape only: quote grounding and explanatory support remain separate review.
    return (isinstance(value, dict) and {'source_id', 'quote'} <= set(value)
        and set(value) <= {'source_id', 'quote', 'version', 'start'}
        and all(isinstance(value[k], str) and bool(value[k].strip()) for k in ('source_id', 'quote'))
        and ('version' not in value or type(value['version']) is int and value['version'] >= 1)
        and ('start' not in value or type(value['start']) is int and value['start'] >= 0))


def validate_response(raw, slot):
    """Usage gates spending; format is recorded without silently dropping an arm."""
    if not isinstance(raw, dict):
        raise GateError('provider response lacks auditable usage')
    usage = raw.get('usage') or {}
    inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
    if (raw.get('model') != slot['request']['model'] or type(inp) is not int
            or type(out) is not int or not 0 <= inp <= slot['input_bound']
            or not 0 <= out <= 8224):
        raise GateError('model or usage outside frozen bound; stop, retain reservation')
    rated = (Decimal(inp) * RATE_IN + Decimal(out) * RATE_OUT) / 1000000
    valid = False
    try:
        choice = raw['choices'][0]
        obj = json.loads(choice['message']['content'])
        valid = (choice['finish_reason'] == 'stop' and isinstance(obj, dict)
            and set(obj) == {'answer', 'source_citations', 'uncertainty', 'assumptions'}
            and all(isinstance(obj[k], str) for k in ('answer', 'uncertainty', 'assumptions'))
            and bool(obj['answer'].strip()) and isinstance(obj['source_citations'], list)
            and all(citation_shape(c) for c in obj['source_citations']))
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return dict(rated_peak_usage_cost_usd=str(rated), format_valid=bool(valid),
                semantic_score=None, actual_invoice_cost_usd=None)


class Ledger:
    """Single-writer, synchronous pre-call reservations survive process interruption.

    Missing or RESERVED outcomes are never retried; the whole run then stops.
    A successful persisted prefix can resume on the same authorized run identity.
    Cross-workflow restart is forbidden by the first-invocation gate.
    """
    def __init__(self, path, identity, plan):
        self.path, self.identity, self.plan = Path(path), identity, plan
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.path.with_suffix('.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close()
            raise GateError('another process owns the ledger') from None
        self.db = sqlite3.connect(self.path)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY CHECK (id=1), identity TEXT NOT NULL, status TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS attempts (slot INTEGER PRIMARY KEY, request_sha TEXT NOT NULL, reserve TEXT NOT NULL, state TEXT NOT NULL, raw TEXT, detail TEXT)')
        encoded = json.dumps(identity, sort_keys=True)
        existing = self.db.execute('SELECT identity FROM meta WHERE id=1').fetchone()
        if existing is None:
            self.db.execute('INSERT INTO meta VALUES (1, ?, ?)', (encoded, 'OPEN'))
            self.db.commit()
        elif existing[0] != encoded:
            self.close()
            raise GateError('ledger identity drift or different invocation')
        try:
            self.audit()
        except Exception:
            self.close()
            raise

    def close(self):
        self.db.close()
        self.lock.close()

    def audit(self):
        rows = self.db.execute('SELECT slot,request_sha,reserve,state FROM attempts ORDER BY slot').fetchall()
        for index, row in enumerate(rows):
            if (index >= 36 or row[0] != index or row[1] != self.plan[index]['request_sha256']
                    or row[2] != self.plan[index]['reserve_usd']
                    or row[3] not in ('RESERVED', 'RECEIVED', 'UNCERTAIN', 'INVALID_USAGE')):
                raise GateError('ledger/request/reservation drift')
        for row in rows:
            if row[3] == 'RECEIVED':
                raw, detail = self.db.execute('SELECT raw,detail FROM attempts WHERE slot=?', (row[0],)).fetchone()
                try:
                    if validate_response(json.loads(raw), self.plan[row[0]]) != json.loads(detail):
                        raise GateError('persisted successful response drift')
                except (TypeError, ValueError) as exc:
                    raise GateError('persisted successful response drift') from exc
        if self.status() == 'COMPLETE' and (len(rows) != 36 or any(r[3] != 'RECEIVED' for r in rows)):
            raise GateError('incomplete ledger cannot claim completion')
        if sum(Decimal(r[2]) for r in rows) > CAP:
            raise GateError('ledger exceeds hard cap')
        return rows

    def status(self):
        return self.db.execute('SELECT status FROM meta WHERE id=1').fetchone()[0]

    def run(self, transport):
        rows = self.audit()
        if self.status() == 'COMPLETE':
            return self.receipt()
        if self.status() != 'OPEN' or any(r[3] != 'RECEIVED' for r in rows):
            with self.db:
                self.db.execute("UPDATE attempts SET state='UNCERTAIN' WHERE state='RESERVED'")
                self.db.execute("UPDATE meta SET status='STOPPED_OUTCOME_UNCERTAIN' WHERE id=1 AND status='OPEN'")
            raise GateError('unresolved outcome consumes its reservation; no retry or next call')
        for slot in self.plan[len(rows):]:
            # FULL synchronous commit must succeed before transport can start.
            with self.db:
                self.db.execute('INSERT INTO attempts(slot,request_sha,reserve,state) VALUES (?,?,?,?)',
                    (slot['index'], slot['request_sha256'], slot['reserve_usd'], 'RESERVED'))
            try:
                raw = transport(copy.deepcopy(slot['request']))
            except Exception as exc:
                # Exception text/body may contain credentials. Preserve only type.
                with self.db:
                    self.db.execute('UPDATE attempts SET state=?,detail=? WHERE slot=?',
                        ('UNCERTAIN', json.dumps({'failure_type': type(exc).__name__, 'usage': None}), slot['index']))
                    self.db.execute("UPDATE meta SET status='STOPPED_OUTCOME_UNCERTAIN' WHERE id=1")
                raise GateError('transport failed; outcome unknown, reservation retained, no retry') from None
            # Store raw before validating usage/format; a crash never permits replay.
            with self.db:
                self.db.execute('UPDATE attempts SET raw=? WHERE slot=?',
                    (json.dumps(raw, ensure_ascii=False, sort_keys=True), slot['index']))
            try:
                detail = validate_response(raw, slot)
            except GateError:
                with self.db:
                    self.db.execute("UPDATE attempts SET state='INVALID_USAGE' WHERE slot=?", (slot['index'],))
                    self.db.execute("UPDATE meta SET status='STOPPED_INVALID_USAGE' WHERE id=1")
                raise
            with self.db:
                self.db.execute('UPDATE attempts SET state=?,detail=? WHERE slot=?',
                    ('RECEIVED', json.dumps(detail, sort_keys=True), slot['index']))
        with self.db:
            self.db.execute("UPDATE meta SET status='COMPLETE' WHERE id=1")
        return self.receipt()

    def receipt(self):
        rows = self.db.execute('SELECT slot,request_sha,reserve,state,raw,detail FROM attempts ORDER BY slot').fetchall()
        attempts = [dict(slot=r[0], case_id=self.plan[r[0]]['case_id'], arm=self.plan[r[0]]['arm'],
            request_sha256=r[1], reserved_usd=r[2], state=r[3],
            response_raw=json.loads(r[4]) if r[4] is not None else None,
            detail=json.loads(r[5]) if r[5] is not None else None) for r in rows]
        simulation = self.identity['mode'] == 'SIMULATION'
        known = all(r['detail'] and 'rated_peak_usage_cost_usd' in r['detail'] for r in attempts)
        return dict(schema='hcl-sid001-run-receipt-v1', identity=self.identity, status=self.status(),
            attempts=attempts, attempted_slots=len(rows), provider_calls=0 if simulation else len(rows),
            simulated_calls=len(rows) if simulation else 0,
            provider_call_count_is_upper_bound=any(r[3] in ('RESERVED', 'UNCERTAIN') for r in rows),
            reserved_usd=str(sum(Decimal(r[2]) for r in rows)), hard_cap_usd='2.50',
            remaining_authority_usd='0' if simulation or self.status() != 'OPEN' else str(CAP - sum(Decimal(r[2]) for r in rows)),
            rated_peak_usage_cost_usd=str(sum(Decimal(r['detail']['rated_peak_usage_cost_usd']) for r in attempts)) if known else None,
            actual_invoice_cost_usd=None, retries=0, extraction_calls=0, paid_judge_calls=0,
            semantic_scores=None, evidence='TARGETED_SYNTHETIC_DIAGNOSTIC_NOT_NATIVE_UTILITY_OR_FINAL_EVIDENCE')


def mock_response(request):
    return dict(model=request['model'], usage=dict(prompt_tokens=1, completion_tokens=1),
        choices=[dict(finish_reason='stop', message=dict(content=json.dumps(dict(
            answer='SIMULATED TRANSPORT ONLY; NO SEMANTIC RESULT', source_citations=[],
            uncertainty='No model was called', assumptions='Fixture transport'))))])


def execute(output, *, simulation=False, grant=None, runs=None):
    runner = verify_manifest()
    plan = slots(json.loads(protocol.PACKAGE.read_text()))
    identity = dict(mode='SIMULATION' if simulation else 'PROVIDER',
        runner_sha256=protocol.digest(runner), protocol_sha256=PROTOCOL_SHA)
    if simulation:
        transport = mock_response
    else:
        require_grant(runner, grant)
        require_unique_run(os.environ, runs or {})
        if not LIVE.exists() or LIVE.read_bytes() != TEMPLATE.read_bytes():
            raise GateError('reviewed activation workflow differs')
        price = refresh_price()
        identity.update(run_id=os.environ['GITHUB_RUN_ID'], sha=os.environ['GITHUB_SHA'],
            approval_message=APPROVAL, credential_reference=CREDENTIAL_REF)
        # Only the existing Actions secret is read, after all authority gates.
        key = os.environ.get('DEEPSEEK_API_KEY')
        if not key:
            raise GateError('existing repository DeepSeek secret unavailable; no calls')
        from importlib.metadata import version
        if version('openai') != '2.14.0':
            raise GateError('reviewed provider SDK version required')
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url='https://api.deepseek.com', max_retries=0, timeout=600)
        def transport(req):
            result = client.chat.completions.create(**{k: v for k, v in req.items() if k != 'thinking'},
                extra_body={'thinking': req['thinking']}).model_dump(mode='json')
            # Headers/secrets never enter inputs; defensive exact-key redaction.
            return json.loads(json.dumps(result, ensure_ascii=False).replace(key, '<REDACTED_CREDENTIAL>'))
        write_json(Path(output) / 'execution-price.json', price)
    ledger = Ledger(Path(output) / 'ledger.sqlite3', identity, plan)
    try:
        return ledger.run(transport)
    finally:
        try:
            write_json(Path(output) / 'receipt.json', ledger.receipt())
        finally:
            ledger.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--preflight', action='store_true')
    modes.add_argument('--dry-run', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--output', default='sid001-results')
    parser.add_argument('--workflow-runs', type=Path)
    args = parser.parse_args()
    if args.preflight:
        verify_manifest()
        print('SID001_RUNNER_PREFLIGHT_PASS_PROVIDER_CALLS_0')
        return
    result = execute(args.output, simulation=args.dry_run,
        grant=json.loads(GRANT.read_text()) if args.execute and GRANT.exists() else None,
        runs=json.loads(args.workflow_runs.read_text()) if args.execute and args.workflow_runs else None)
    print(json.dumps({k: v for k, v in result.items() if k != 'attempts'}, sort_keys=True))


if __name__ == '__main__':
    main()
