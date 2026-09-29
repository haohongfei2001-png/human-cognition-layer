"""One bounded ordinary-entry functional run using the existing DeepSeek client."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.identity_roles import prepare_identity_roles
from hcl.cognition.semantic import AuthorizedText, _local_candidates
from scripts.run_cg02_external_once import DeepSeekProvider
from scripts.witness_identity_roles import SOURCE, QUERY

PACKAGE = Path('reports/HCL_ORDINARY_ENTRY_FUNCTIONAL_PACKAGE.json')
WORKFLOW = Path('.github/workflows/hcl-cognition-functional-once.yml')
FIELDS = ('self_description', 'others_attribution', 'role_occupancy', 'role_requirement',
    'reported_behavior', 'personal_endorsement', 'unresolved')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def build_package():
    files = sorted([*Path('hcl').rglob('*.py'), *Path('scripts').rglob('*.py'), WORKFLOW])
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return dict(schema='hcl-ordinary-entry-functional-v1',
        purpose='ONE_AUTHORED_OPERATIONAL_SMOKE_NOT_EFFICACY_OR_EXTERNAL_EVIDENCE',
        authorization='LATEST_OWNER_DEFAULT_APPROVAL_FOR_BOUNDED_EXISTING_PROVIDER_DEVELOPMENT',
        historical_budget_transfer=False, provider='deepseek', provider_endpoint='https://api.deepseek.com',
        model='deepseek-flash', expected_model_family='DeepSeek-V4.1-Flash',
        provider_request=dict(thinking=dict(type='disabled'), response_format=dict(type='json_object'), temperature=0, max_retries=0),
        service_tier='provider_default_no_tier_parameter', maximum_provider_calls=2,
        maximum_output_tokens=dict(extraction=2048, final=768), budget_cap_usd=0.30,
        guard_rates_usd_per_million=dict(input=1.32, output=3.96),
        rated_peak_rates_usd_per_million=dict(input=0.30, cache_hit=0.006, output=1.20),
        price_source='https://api-docs.deepseek.com/quick_start/pricing/', price_verified_date='2026-09-29',
        price_note='Current Flash peak rates; cap additionally reserves at higher existing Pro peak rates. Invoice cost not independently available.',
        source=SOURCE, query=QUERY, source_id='authored-ordinary-entry-functional',
        final_fields=list(FIELDS), runtime_files=hashes, runtime_sha256=digest(hashes),
        source_class='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT', longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    package = json.loads(PACKAGE.read_text())
    if package != build_package():
        raise ValueError('frozen functional source/runtime/package drift')
    return package


class ReplayExtraction:
    def complete_json(self, messages, **kwargs):
        sources = json.loads(messages[1]['content'])['sources']
        candidates = []
        for item in sources:
            for row in _local_candidates(AuthorizedText(**item)):
                if row['kind'] == 'event':
                    candidates.append(dict(source_id=row['source_id'], quote=row['quote'], kind='event',
                        content={key: row['content'][key] for key in ('speaker_surface', 'utterance')}))
        return json.dumps(dict(candidates=candidates))


def prepare(package, backend):
    workspace = SemanticWorkspace(semantic_backend=backend, max_backend_calls=1)
    workspace.put_source(package['source_id'], package['source'])
    result = prepare_identity_roles(workspace, package['query'], source_id=package['source_id'])
    state = result.payload
    if not (state['role_status'] == 'REPORTED_OCCUPANT' and state['local_tension'] and
        [r['label'] for r in state['current_self_descriptions']] == ['careful'] and
        [r['label'] for r in state['other_identity_attributions']] == ['careless'] and
        [r['endorsement'] for r in state['requirement_endorsements']] == ['REJECTS']):
        raise ValueError('required grounded channels absent; final call refused')
    messages = result.messages(workspace, max_chars=48000)
    messages.append(dict(role='user', content='Answer the question using a JSON object with exactly these fields: ' +
        ', '.join(package['final_fields']) + '. Use concise strings or lists. Keep reported source channels separate; explain uncertainty without inferring a global identity, moral truth or endorsement from role occupancy.'))
    semantic = next(iter(workspace.semantic_cache.values()))
    return dict(actual_final_messages=messages, cognition_state=state,
        extraction_backend_calls=semantic.backend_calls, extraction_status=semantic.backend_status,
        semantic_diagnostics=semantic.diagnostics, source_derived_candidate_ids=list(semantic.candidate_ids))


class BoundedCalls:
    def __init__(self, package, transport, output):
        self.package, self.transport, self.output = package, transport, Path(output)
        if self.output.exists():
            raise ValueError('existing receipt refuses a repeated run')
        self.receipt = dict(schema='hcl-functional-run-receipt-v1', package_sha256=digest(package),
            runtime_sha256=package['runtime_sha256'], status='STARTED', attempts=[],
            conservative_guard_spend_usd=0.0, rated_peak_spend_usd=0.0, estimated_provider_spend_usd=0.0,
            actual_invoice_cost_usd=None, budget_cap_usd=package['budget_cap_usd'], retries=0,
            run_id=os.environ.get('GITHUB_RUN_ID'), run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),
            sha=os.environ.get('GITHUB_SHA'), evidence='FUNCTIONAL_DEVELOPMENT_ONLY', longmemeval='SEALED_NOT_ACCESSED')
        self.save()

    def save(self):
        write_json(self.output, self.receipt)

    def call(self, phase, messages):
        if self.receipt['status'] != 'STARTED':
            raise ValueError('failed or closed run cannot continue')
        if len(self.receipt['attempts']) >= self.package['maximum_provider_calls'] or phase != ('extraction' if not self.receipt['attempts'] else 'final'):
            raise ValueError('one extraction and one final call; no retry')
        request = dict(model=self.package['model'], messages=messages,
            max_tokens=self.package['maximum_output_tokens'][phase], temperature=0,
            response_format=dict(type='json_object'), thinking=dict(type='disabled'))
        input_bound = len(json.dumps(request, ensure_ascii=False).encode()) * 2 + 4096
        guard = self.package['guard_rates_usd_per_million']
        reserve = (input_bound * guard['input'] + request['max_tokens'] * guard['output']) / 1_000_000
        if self.receipt['conservative_guard_spend_usd'] + reserve > self.package['budget_cap_usd']:
            raise ValueError('hard cap refuses next call before transport')
        attempt = dict(phase=phase, request_raw=request, input_token_bound=input_bound, reserved_usd=reserve)
        self.receipt['attempts'].append(attempt)
        self.save()
        try:
            raw = self.transport(request)
            attempt['response_raw'] = raw
            self.save()
            usage = raw.get('usage') or {}
            choices = raw.get('choices') or []
            choice = choices[0] if choices else {}
            content = (choice.get('message') or {}).get('content')
            actual_model = raw.get('model')
            allowed = isinstance(actual_model, str) and (actual_model.lower() in ('deepseek-flash', 'deepseek-v4-flash') or actual_model.lower().startswith('deepseek-v4.1-flash'))
            inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
            if not (allowed and type(inp) is int and type(out) is int and 0 <= inp <= input_bound and
                    0 <= out <= request['max_tokens'] and isinstance(content, str) and choice.get('finish_reason') == 'stop'):
                raise ValueError('response identity/usage/finish contract failed')
            rated = self.package['rated_peak_rates_usd_per_million']
            cost = (inp * rated['input'] + out * rated['output']) / 1_000_000
            guarded = (inp * guard['input'] + out * guard['output']) / 1_000_000
            estimated = None
            hit, miss, created = usage.get('prompt_cache_hit_tokens'), usage.get('prompt_cache_miss_tokens'), raw.get('created')
            if type(hit) is int and type(miss) is int and min(hit, miss) >= 0 and hit + miss == inp and type(created) is int:
                time = datetime.fromtimestamp(created, timezone.utc)
                peak = time.weekday() < 5 and (1 <= time.hour < 4 or 6 <= time.hour < 10)
                estimated = (hit * rated['cache_hit'] + miss * rated['input'] + out * rated['output']) / 1_000_000 * (1 if peak else 0.5)
            attempt.update(actual_model_id=actual_model, usage=usage, rated_peak_cost_usd=cost,
                estimated_provider_cost_usd=estimated, conservative_guard_cost_usd=guarded)
            self.receipt['conservative_guard_spend_usd'] += guarded
            self.receipt['rated_peak_spend_usd'] += cost
            if estimated is None or self.receipt['estimated_provider_spend_usd'] is None:
                self.receipt['estimated_provider_spend_usd'] = None
            else:
                self.receipt['estimated_provider_spend_usd'] += estimated
            self.save()
            return content
        except Exception as exc:
            attempt['failure_type'] = type(exc).__name__
            attempt['failure_reservation_usd'] = reserve
            if 'conservative_guard_cost_usd' not in attempt:
                self.receipt['conservative_guard_spend_usd'] += reserve
            self.receipt['estimated_provider_spend_usd'] = None
            self.receipt['status'] = 'FAILED_NO_RETRY'
            self.save()
            raise

    def complete_json(self, messages, **kwargs):
        return self.call('extraction', messages)


def execute(package, transport, output):
    ledger = BoundedCalls(package, transport, output)
    try:
        prepared = prepare(package, ledger)
        ledger.receipt['preparation'] = prepared
        ledger.save()
        final = ledger.call('final', prepared['actual_final_messages'])
        parsed = json.loads(final)
        if not isinstance(parsed, dict) or set(parsed) != set(package['final_fields']):
            raise ValueError('final answer field contract failed')
        ledger.receipt.update(status='PIPELINE_COMPLETED_REQUIRES_SOURCE_FIRST_REVIEW', final_answer=parsed)
    except Exception as exc:
        ledger.receipt.update(status='FAILED_NO_RETRY', failure_type=type(exc).__name__)
        raise
    finally:
        ledger.receipt.update(provider_calls=len(ledger.receipt['attempts']), authorization_remaining_usd=0,
            budget_state='CLOSED_NO_TRANSFER_NO_RERUN')
        ledger.save()
    return ledger.receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', default='functional-preflight.json')
    args = parser.parse_args()
    if sum((args.freeze, args.preflight, args.execute)) != 1:
        parser.error('exactly one mode required')
    if args.freeze:
        write_json(PACKAGE, build_package())
        return
    package = load_package()
    preflight = prepare(package, ReplayExtraction())
    if args.preflight:
        write_json(args.output, dict(status='PASS_PROVIDER_FREE', package_sha256=digest(package),
            runtime_sha256=package['runtime_sha256'], provider_calls=0, preparation=preflight))
        return
    if os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or os.environ.get('HCL_FUNCTIONAL_AUTHORIZED') != 'ONE_NORMAL_DEVELOPMENT_RUN':
        raise ValueError('workflow attempt-one authorization required')
    provider = DeepSeekProvider(os.environ.get('DEEPSEEK_API_KEY'), package)
    def transport(request):
        response = provider.client.chat.completions.create(**{k:v for k,v in request.items() if k != 'thinking'},
            extra_body=dict(thinking=request['thinking']))
        return response.model_dump(mode='json')
    execute(package, transport, args.output)


if __name__ == '__main__':
    main()
