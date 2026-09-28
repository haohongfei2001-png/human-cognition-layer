"""Source-bound conditional commitment lifecycle; no automatic blame or trust."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
import json
import re

from hcl.v04.model import EventRecord
from hcl.v1.cg02 import (SocialAct, SocialActKind, SocialCondition,
    ParticipantInterpretation, check_social_exchange)
from .communication import CommunicationScene
from .core import ClaimKind, identity

_NAME = r'[A-Z][\w-]*'
_QUERY = re.compile(rf"What is the status of (?P<speaker>{_NAME})'s promise to (?P<recipient>{_NAME}) to (?P<action>[^?]+)\?")
_PROMISE = re.compile(rf'I promise (?P<recipient>{_NAME}) to (?P<action>.+?) if (?P<condition>.+)')
_RESPONSE = re.compile(rf"I (?P<kind>accept|refuse) (?P<speaker>{_NAME})'s promise to (?P<action>.+)")
_END = re.compile(rf'I (?P<kind>withdraw|fulfilled) my promise to (?P<recipient>{_NAME}) to (?P<action>.+)')
_EXPECT = re.compile(rf'I expect (?P<speaker>{_NAME}) to (?P<action>.+?)(?: if (?P<condition>.+))?')
_FACT = re.compile(r'It is (?P<value>true|false) that (?P<condition>.+)')
_POLICY = ('Original conditional commitment, delivery, acceptance, expectation, withdrawal '
    'and reported fulfillment are separate. Hearing does not prove comprehension, '
    'acceptance or mutual knowledge. Missing condition evidence is not false. Withdrawal '
    'does not erase an earlier commitment or expectation. Fulfillment reports are not '
    'verified outcomes. No moral obligation, promise-breaking, motive or global trust '
    'is inferred. Source order is conditional, not verified calendar chronology.')


@dataclass(frozen=True)
class CommitmentResult:
    scope: object
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded social context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('social source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('social support changed; recompute')
        result = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(result, ensure_ascii=False)) > max_chars:
            raise ValueError('social context budget exceeded')
        return result


def prepare_commitment(workspace, query, *, source_id, observer=None):
    question = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not question or len(question['action']) > 200 or question['speaker'] == question['recipient']:
        raise ValueError('bounded distinct speaker/recipient promise question required')
    speaker, recipient, action = question['speaker'], question['recipient'], question['action']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows, claims = workspace.core, [], []
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        content = core.claims[candidate].content
        if content['kind'] != 'event' or content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row = content['proposal']
        span = core.spans[content['source_span_id']]
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and row['speaker_candidates'] != [row['speaker_surface']]):
            continue
        rows.append((span.start, candidate, row, span, narrator))
    rows.sort(key=lambda r: r[0])
    if len(rows) > 24:
        raise ValueError('commitment source budget exceeded')
    matches = [(i, _PROMISE.fullmatch(r[2]['utterance'].rstrip('.!?'))) for i, r in enumerate(rows) if r[2]['speaker_surface'] == speaker]
    matches = [(i, m) for i, m in matches if m and m['recipient'] == recipient and m['action'] == action]
    if len(matches) > 1:
        raise ValueError('multiple matching promises; narrow the source episode')
    if not matches:
        payload = dict(query=query, status='SYSTEM_INSUFFICIENT', reason='no_unambiguous_visible_conditional_promise', original_source=original, policy=_POLICY)
        return CommitmentResult(semantic.scope, versions, json.dumps(payload, sort_keys=True), ())
    index, promise = matches[0]
    condition = promise['condition']
    promise_row = rows[index]
    # B02 owns delivery semantics; addressing is deliberately not receipt.
    view = CommunicationScene(original, source_id=source_id).view(recipient)
    source_line = original[:promise_row[0]].count('\n') + 1
    audit = next(a for a in view.access_audit if a['statement_line'] == source_line)
    delivery = audit['status']
    received = audit['content_transmitted']
    events, ids = [], {}
    for n, (_, candidate, row, span, narrator) in enumerate(rows, 1):
        stamp = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=n)).isoformat()
        event = EventRecord(identity('social-source', candidate), stamp, span.quote, source_id, stamp,
            actor_id=None if narrator else row['speaker_surface'],
            recipient_ids=(recipient,) if n - 1 == index and received else (),
            metadata={'reader_only': narrator})
        events.append(event)
        ids[candidate] = event.event_id
    event = events[index]
    act = SocialAct(identity('conditional-promise', promise_row[1]), SocialActKind.CONDITIONAL_COMMITMENT,
        speaker, recipient, action, promise_row[3].quote, event.event_id, event.valid_time,
        (SocialCondition(condition, condition, event.event_id),))
    acts, interpretations, history, facts, diagnostics = [act], [], [], [], []
    expectation_receipts = {}
    for n, (_, candidate, row, span, narrator) in enumerate(rows):
        body, who = row['utterance'].rstrip('.!?'), row['speaker_surface']
        fact = _FACT.fullmatch(body)
        if narrator and fact and fact['condition'] == condition:
            facts.append(dict(value=fact['value'] == 'true', quote=span.quote, source_claim_id=candidate))
        response, end, expected = _RESPONSE.fullmatch(body), _END.fullmatch(body), _EXPECT.fullmatch(body)
        response_ok = response and who == recipient and response['speaker'] == speaker and response['action'] == action
        end_ok = end and who == speaker and end['recipient'] == recipient and end['action'] == action
        expected_ok = expected and who == recipient and expected['speaker'] == speaker and expected['action'] == action
        if not (response_ok or end_ok or expected_ok):
            continue
        if n <= index:
            diagnostics.append(dict(source_claim_id=candidate, status='NO_PRIOR_PROMISE_REFERENCE'))
            continue
        kind = response['kind'].upper() if response_ok else end['kind'].upper() if end_ok else 'EXPECTATION'
        history.append(dict(kind=kind, quote=span.quote, source_claim_id=candidate,
            source_order=n + 1, verified_private_state=False))
        if kind in ('ACCEPT', 'REFUSE', 'WITHDRAW'):
            native_kind = {'ACCEPT': SocialActKind.ACCEPTANCE, 'REFUSE': SocialActKind.REFUSAL, 'WITHDRAW': SocialActKind.WITHDRAWAL}[kind]
            target = speaker if response_ok else recipient
            # A withdrawal's addressee is named by its original quoted text.
            acts.append(SocialAct(identity('social-response', candidate), native_kind, who, target,
                action, span.quote, events[n].event_id, events[n].valid_time, refers_to=act.act_id))
        elif kind == 'EXPECTATION':
            formed_line = original[:span.start].count('\n') + 1
            at_formation = CommunicationScene(original, source_id=source_id).view(recipient, through_line=formed_line)
            receipt = next(a for a in at_formation.access_audit if a['statement_line'] == source_line)
            expectation_receipts[identity('social-expectation', candidate)] = receipt
            history[-1]['condition_receipt_at_formation'] = receipt['status']
            interpretations.append(ParticipantInterpretation(identity('social-expectation', candidate), who,
                act.act_id, action, (expected['condition'],) if expected['condition'] else (),
                span.quote, events[n].event_id, events[n].valid_time))
    checked = check_social_exchange(tuple(acts), tuple(interpretations), (), tuple(events))
    # Current delivery must not be backfilled into an earlier reported expectation.
    comparisons = []
    for interpretation in interpretations:
        receipt = expectation_receipts[interpretation.interpretation_id]
        historical_events = tuple(replace(e, recipient_ids=(recipient,) if receipt['content_transmitted'] else ())
            if e.event_id == act.source_event_id else e for e in events)
        historical = check_social_exchange(tuple(acts), (interpretation,), (), historical_events)
        for comparison in historical['expectation_comparisons']:
            comparison['condition_receipt_at_expectation'] = receipt['status']
            comparisons.append(comparison)
    checked['expectation_comparisons'] = comparisons
    fact_values = {f['value'] for f in facts}
    condition_status = 'CONFLICTING_SOURCE_CLAIMS' if len(fact_values) > 1 else 'SOURCE_REPORTED_TRUE' if fact_values == {True} else 'SOURCE_REPORTED_FALSE' if fact_values == {False} else 'UNKNOWN'
    responses = {h['kind'] for h in history if h['kind'] in ('ACCEPT', 'REFUSE')}
    acceptance = 'CONFLICTING_RESPONSE_REPORTS' if len(responses) > 1 else 'REPORTED_ACCEPTANCE' if responses == {'ACCEPT'} else 'REPORTED_REFUSAL' if responses else 'NO_EXPLICIT_RESPONSE'
    withdrawals = [h for h in history if h['kind'] == 'WITHDRAW']
    fulfilled = [h for h in history if h['kind'] == 'FULFILLED']
    lifecycle = ('REPORTED_WITHDRAWAL_AND_FULFILLMENT' if withdrawals and fulfilled else
        'REPORTED_WITHDRAWN' if withdrawals else 'REPORTED_FULFILLED' if fulfilled else
        'CONDITION_NOT_MET_IN_SOURCE' if fact_values == {False} else
        'CONDITIONALLY_TRIGGERED_IN_SOURCE' if fact_values == {True} else 'CONDITION_UNRESOLVED')
    result = dict(original_promise=asdict(act), condition_status=condition_status,
        condition_evidence=facts, receipt=delivery, conditions_received=received,
        acceptance=acceptance, lifecycle=lifecycle, history=history,
        fulfillment='SOURCE_REPORT_NOT_VERIFIED_OUTCOME' if fulfilled else 'NOT_ESTABLISHED',
        obligation='NOT_ESTABLISHED', blame='NOT_INFERRED', trust_change='NOT_INFERRED',
        private_understanding='NOT_ESTABLISHED', temporal_assumption='SOURCE_ORDER_NOT_VERIFIED_CHRONOLOGY')
    final = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
        dict(operation='SOCIAL_COMMITMENT_LIFECYCLE', **result))
    # All source candidates are read dependencies, including delivery reports and
    # negative/conflicting facts. Source-version guards also cover absent facts.
    core.support(final, *(r[1] for r in rows))
    claims.append(final)
    payload = dict(query=query, original_source=original, status='CHECKED_CONDITIONAL_LIFECYCLE',
        commitment=result, cg02_source_check=checked, diagnostics=diagnostics,
        dependency_claim_id=final, policy=_POLICY)
    return CommitmentResult(semantic.scope, versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
