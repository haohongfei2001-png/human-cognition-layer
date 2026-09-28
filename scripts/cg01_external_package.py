"""Provider-free preflight and opt-in CG-01 development runner.

Importing this module never reads credentials or calls a provider. A future
owner-authorized caller must inject an explicit provider adapter and key.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from hcl.v04.model import EventRecord
from hcl.v1 import (ConditionFact, ConditionKind, CognitionRequest,
                    ExplanationCandidate, FactAuthority, HCLCognitionLayer,
                    RequiredCondition, SemanticPreparation)


PACKAGE = Path(__file__).resolve().parents[1] / 'reports/HCL_CG01_EXTERNAL_PACKAGE.json'
FINAL_FORMAT = ('Return only JSON with keys assessment, reason, evidence_quote, '
    'unknown_motive. assessment must be INVALIDATED, CONSISTENT_CONDITIONAL, or '
    'UNRESOLVED. evidence_quote must be an exact short span from the supplied '
    'source. unknown_motive must be true. Do not infer a unique private motive.')
EXTRACTION_FORMAT = (
    'Extract only source-anchored conditions relevant to the candidate action. '
    'Return JSON with events (at most 8, at most 4000 quoted characters total), '
    'candidates (at most 3), facts (at most 12). '
    'Each event: event_id, quote (exact substring of source), actor_id, order_index '
    '(0..23, narrative order). Each candidate: candidate_id, target_actor, '
    'action_event_id, source_event_id, explanation, required list of kind/key. '
    'Each fact: fact_id, source_event_id, target_actor, kind, key, value boolean, '
    'authority, claim_time ACTION or SOURCE, first_learning_after_action boolean. '
    'Kinds are KNOWLEDGE, GOAL, OPPORTUNITY. Authorities are EXPLICIT_NARRATOR, '
    'DIRECT_SELF_REPORT, THIRD_PARTY_ATTRIBUTION, DIRECT_OBSERVATION. '
    'Do not fabricate a missing condition, an access route, or a first-learning '
    'statement. Output empty lists when source cannot support extraction.')


def load_package(path=PACKAGE):
    package = json.loads(Path(path).read_text())
    if package['schema'] != 'hcl-cg01-external-development-package-v1':
        raise ValueError('wrong CG-01 package schema')
    if package['arms'] != ['C', 'P', 'G', 'H', 'H-new'] or len(package['cases']) != 4:
        raise ValueError('arm or case identity drift')
    if len({case['id'] for case in package['cases']}) != 4:
        raise ValueError('duplicate case')
    for case in package['cases']:
        if hashlib.sha256(case['excerpt'].encode()).hexdigest() != case['excerpt_sha256']:
            raise ValueError('source excerpt digest drift')
        if case['expected_status'] not in package['output_contract']['assessment']:
            raise ValueError('invalid source-only adjudication')
    price = package['price_peak_usd_per_million']
    upper = package['provider_calls_max'] * (
        package['input_tokens_per_call_max'] * price['input_cache_miss'] +
        package['output_tokens_per_call_max'] * price['output']) / 1_000_000
    if upper > package['usd_hard_cap'] or package['provider_calls_max'] != 24:
        raise ValueError('cost or call ceiling exceeded')
    return package


def verify_source(source_bytes, package):
    if hashlib.sha256(source_bytes).hexdigest() != package['source']['sha256']:
        raise ValueError('external source digest drift')
    lines = source_bytes.decode('utf-8-sig').splitlines()
    for case in package['cases']:
        excerpt = '\n[noncontiguous source span]\n'.join(
            '\n'.join(lines[start-1:end]) for start, end in case['source_line_spans'])
        if excerpt != case['excerpt']:
            raise ValueError('source line/excerpt mismatch: ' + case['id'])


def task_query(case):
    return (f"Why did {case['target_actor']} {case['action_phrase']}? "
            f"Assess this candidate explanation: {case['candidate']} "
            f"{case['question']}")


def arm_messages(case, arm, prepared=None):
    if arm in ('H', 'H-new'):
        if prepared is None:
            raise ValueError('H arms require actual v1 preparation')
        if arm == 'H':
            return [{'role': 'system', 'content': FINAL_FORMAT}] + list(prepared.messages)
        context = deepcopy(prepared.context)
        for row in context.explanations:
            row['status'] = 'NOT_CHECKED'
            row['conditions'] = []
        payload = HCLCognitionLayer._payload(task_query(case), context)
        return [{'role': 'system', 'content': FINAL_FORMAT},
                prepared.messages[0], {'role': 'user', 'content': payload}]
    if arm not in ('C', 'P', 'G'):
        raise ValueError('unknown arm')
    prompts = {
        'C': 'Answer directly from the source; cite the evidence and uncertainty.',
        'P': ('Use a simple checklist: what the person knew, explicitly wanted, '
              'and could choose at the action time; do not guess absent facts.'),
        'G': ('Consider at least the supplied candidate and an open alternative. '
              'Organize source claims by actor, event order and access; distinguish '
              'support, challenge and missing information without asserting motive truth.'),
    }
    user = json.dumps({'source': case['excerpt'], 'candidate': case['candidate'],
                       'question': task_query(case)}, ensure_ascii=False)
    return [{'role': 'system', 'content': FINAL_FORMAT + ' ' + prompts[arm]},
            {'role': 'user', 'content': user}]


def semantic_messages(payload):
    return [{'role': 'system', 'content': EXTRACTION_FORMAT},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}]


def parse_semantic(raw, model_id, cost_usd, provider_calls=1):
    data = json.loads(raw)
    if (len(data['events']) > 8 or len(data['candidates']) > 3 or
        len(data['facts']) > 12 or
        sum(len(e['quote']) for e in data['events']) > 4000):
        raise ValueError('external semantic output bounds exceeded')
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for row in data['events']:
        order = row['order_index']
        if type(order) is not int or not 0 <= order < 24:
            raise ValueError('semantic event order invalid')
        stamp = (base + timedelta(seconds=order)).isoformat()
        events.append(EventRecord(row['event_id'], stamp, row['quote'],
            'cg01-external-source-span', stamp, row.get('actor_id'),
            metadata={'reader_only': True}))
    by_id = {e.event_id: e for e in events}
    candidates = []
    for row in data['candidates']:
        action = by_id[row['action_event_id']]
        required = tuple(RequiredCondition(ConditionKind(r['kind']), r['key'])
                         for r in row['required'])
        candidates.append(ExplanationCandidate(row['candidate_id'], row['target_actor'],
            action.event_id, action.valid_time, row['explanation'],
            row['source_event_id'], required))
    facts = []
    for row in data['facts']:
        source = by_id[row['source_event_id']]
        if row['claim_time'] not in ('ACTION', 'SOURCE'):
            raise ValueError('unbounded semantic claim time')
        action_time = candidates[0].action_time if candidates else source.valid_time
        first = source.valid_time if row['first_learning_after_action'] else None
        facts.append(ConditionFact(row['fact_id'], source.event_id,
            row['target_actor'], RequiredCondition(ConditionKind(row['kind']), row['key']),
            row['value'], action_time if row['claim_time'] == 'ACTION' else source.valid_time,
            FactAuthority(row['authority']), first))
    return SemanticPreparation(tuple(events), tuple(candidates), tuple(facts),
                               raw, model_id, provider_calls, cost_usd)


class DeepSeekProvider:
    """Explicitly constructed adapter; no environment or credential lookup."""
    def __init__(self, api_key, package=None):
        if not isinstance(api_key, str) or not api_key:
            raise ValueError('explicit API key required')
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url='https://api.deepseek.com',
                             max_retries=0, timeout=120)
        self.package = package or load_package()

    def __call__(self, messages, max_output_tokens, config):
        response = self.client.chat.completions.create(
            model=config['model'], messages=messages, max_tokens=max_output_tokens,
            response_format=config['response_format'],
            extra_body={'thinking': config['thinking']})
        choice = response.choices[0]
        usage = response.usage
        if usage is None or not isinstance(choice.message.content, str):
            raise ValueError('missing provider usage or output')
        peak = self.package['price_peak_usd_per_million']
        # Conservative all-cache-miss peak rating; actual bill may be lower.
        rated = (usage.prompt_tokens * peak['input_cache_miss'] +
                 usage.completion_tokens * peak['output']) / 1_000_000
        return {'model': response.model, 'raw': choice.message.content,
                'input_tokens': usage.prompt_tokens,
                'output_tokens': usage.completion_tokens,
                'cost_usd': rated, 'finish_reason': choice.finish_reason,
                'cost_basis': 'PEAK_ALL_INPUT_CACHE_MISS_UPPER_BOUND'}


class BudgetLedger:
    def __init__(self, package, on_update=None):
        self.package = package
        self.calls = 0
        self.cost_usd = 0.0
        self.attempts = []
        self.on_update = on_update

    def call(self, provider, messages):
        # UTF-8 bytes upper-bound token count for this English-only package.
        serialized = json.dumps(messages, ensure_ascii=False).encode()
        if len(serialized) > self.package['input_tokens_per_call_max']:
            raise ValueError('input cap exceeded before provider call')
        if self.calls >= self.package['provider_calls_max']:
            raise ValueError('call cap exceeded')
        peak = self.package['price_peak_usd_per_million']
        reserve = (self.package['input_tokens_per_call_max'] * peak['input_cache_miss'] +
                   self.package['output_tokens_per_call_max'] * peak['output']) / 1_000_000
        if self.cost_usd + reserve > self.package['usd_hard_cap']:
            raise ValueError('USD hard cap exceeded')
        self.calls += 1
        config = dict(self.package['provider_request'], model=self.package['model'])
        attempt = {'messages': messages, 'max_output_tokens': self.package['output_tokens_per_call_max'],
                   'provider_request': config, 'pending_reservation_usd': reserve}
        self.attempts.append(attempt)
        if self.on_update is not None:
            self.on_update(self)
        try:
            result = provider(messages, self.package['output_tokens_per_call_max'], config)
            if (result['model'] not in (self.package['model'], self.package['model_version']) or
                result['input_tokens'] > self.package['input_tokens_per_call_max'] or
                result['output_tokens'] > self.package['output_tokens_per_call_max'] or
                result['cost_usd'] < 0 or result['cost_usd'] > reserve or
                not isinstance(result['raw'], str)):
                raise ValueError('provider contract or cap violation')
        except Exception as exc:
            self.cost_usd += reserve  # failure consumes full reservation
            attempt.pop('pending_reservation_usd')
            attempt['failure_reservation_usd'] = reserve
            attempt['failure_type'] = type(exc).__name__
            if self.on_update is not None:
                self.on_update(self)
            raise
        attempt.pop('pending_reservation_usd')
        attempt['result'] = result
        self.cost_usd += result['cost_usd']
        if self.on_update is not None:
            self.on_update(self)
        return result


def score_output(raw, case):
    try:
        result = json.loads(raw)
        assessment = result['assessment']
        quote = result['evidence_quote']
        valid = assessment in ('INVALIDATED', 'CONSISTENT_CONDITIONAL', 'UNRESOLVED')
        grounded = isinstance(quote, str) and bool(quote) and quote in case['excerpt']
        return {'valid_output': valid and grounded and type(result['unknown_motive']) is bool,
                'assessment_match': assessment == case['expected_status'],
                'quote_anchored': grounded,
                'no_unique_motive_claim': result['unknown_motive'] is True,
                'source_first_human_audit_required': True}
    except (ValueError, KeyError, TypeError):
        return {'valid_output': False, 'assessment_match': False,
                'quote_anchored': False, 'no_unique_motive_claim': False,
                'source_first_human_audit_required': True}


def run_with_provider(provider, package=None, on_update=None):
    """Execute only when an owner-authorized caller injects a paid adapter."""
    package = package or load_package()
    rows = []
    def checkpoint(ledger):
        if on_update is not None:
            on_update({'rows': rows, 'calls': ledger.calls,
                       'cost_usd': ledger.cost_usd, 'attempts': ledger.attempts,
                       'scope': 'DEVELOPMENT_NOT_FRESH_HOLDOUT'})
    ledger = BudgetLedger(package, on_update=checkpoint)
    for case in package['cases']:
        query = task_query(case)
        def semantic_preparer(payload):
            response = ledger.call(provider, semantic_messages(payload))
            return parse_semantic(response['raw'], response['model'], response['cost_usd'])
        layer = HCLCognitionLayer(lambda _: '', semantic_preparer=semantic_preparer)
        prepared = layer.prepare(CognitionRequest(query, narrative=case['excerpt'],
            target_actor=case['target_actor'], allow_semantic_preparation=True))
        for arm in package['arms']:
            messages = arm_messages(case, arm, prepared if arm in ('H', 'H-new') else None)
            response = ledger.call(provider, messages)
            rows.append({'case_id': case['id'], 'arm': arm, 'raw': response['raw'],
                         'usage': {k: response[k] for k in ('model','input_tokens','output_tokens','cost_usd')},
                         'score': score_output(response['raw'], case),
                         'preparation_receipt': prepared.preparation_receipt if arm == 'H' else None,
                         'final_messages': messages})
            checkpoint(ledger)
    return {'rows': rows, 'calls': ledger.calls, 'cost_usd': ledger.cost_usd,
            'attempts': ledger.attempts, 'scope': 'DEVELOPMENT_NOT_FRESH_HOLDOUT'}
