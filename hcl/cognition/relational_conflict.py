"""Failure attribution and reported repair without automatic blame or forgiveness."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re

from hcl.v04.model import EventRecord
from hcl.v1.cg03 import (ResponsibilityFactor, FactorClaim, ClaimAuthority,
    _asserted_factor_polarity, _factor_row)
from .communication import CommunicationScene
from .core import ClaimKind, identity
from .relationships import prepare_relationship

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf"Explain (?P<assessor>{_NAME})'s response to (?P<target>{_NAME})'s failure to (?P<action>.+?) in (?P<domain>{_TERM})\.")
_POLICY = ('A reported failure does not establish bad intention, lack of effort, blame '
    'or a global character defect. Keep action-bound knowledge, control and stated '
    'intention separate. Competing explanations are conditional and nonexclusive. '
    'Receiving or accepting an apology is not forgiveness. Explicit forgiveness is '
    'a reported expression, not verified private feeling. Factor evidence does not '
    'automatically overwrite a separately reported relationship judgment. No normative '
    'premise or moral responsibility is manufactured.')


@dataclass(frozen=True)
class RelationalConflict:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded conflict context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('conflict source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('conflict support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('conflict context budget exceeded')
        return messages


def prepare_relational_conflict(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or match['assessor'] == match['target'] or len(match['action']) > 200:
        raise ValueError('bounded directional failure response question required')
    assessor, target, action, domain = (match[k] for k in ('assessor', 'target', 'action', 'domain'))
    relationship = prepare_relationship(workspace, f"How does {assessor} regard {target}'s reliability in {domain}?", source_id=source_id, observer=observer)
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    original = relationship.payload['original_source']
    for candidate in semantic.candidate_ids:
        c = core.claims[candidate].content
        if c['kind'] != 'event' or c['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row, span = c['proposal'], core.spans[c['source_span_id']]
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and row['speaker_candidates'] != [row['speaker_surface']]):
            continue
        rows.append(dict(candidate=candidate, speaker=row['speaker_surface'], body=row['utterance'].rstrip('.!?'),
            quote=span.quote, line=original[:span.start].count('\n') + 1, narrator=narrator))
    rows.sort(key=lambda r: r['line'])
    failures = [r for r in rows if (r['speaker'] == target and r['body'] == f'I failed to {action} in {domain}') or
        (r['narrator'] and r['body'] == f'In {domain}, {target} failed to {action}')]
    if len(failures) > 1:
        raise ValueError('multiple failure episodes; narrow source')
    if not failures:
        return RelationalConflict(relationship.source_versions, json.dumps(dict(query=query, original_source=original,
            status='SYSTEM_INSUFFICIENT', reason='no_unambiguous_visible_failure', relationship=relationship.payload, policy=_POLICY), sort_keys=True), relationship.claim_ids)
    failure = failures[0]
    stamp = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=failure['line'])).isoformat()
    action_id = identity('reported-failure', failure['candidate'])
    prefix = f'For the attempt to {action} in {domain}, '
    predicates = {
        'at the time I knew the requirements': (ResponsibilityFactor.KNOWLEDGE, True),
        'at the time I did not know the requirements': (ResponsibilityFactor.KNOWLEDGE, False),
        'at the time I could prevent the failure': (ResponsibilityFactor.CONTROL, True),
        'at the time I could not prevent the failure': (ResponsibilityFactor.CONTROL, False),
        f'at the time I intended to fail to {action}': (ResponsibilityFactor.STATED_INTENTION, True),
        f'at the time I did not intend to fail to {action}': (ResponsibilityFactor.STATED_INTENTION, False),
    }
    factors, bindings = [], []
    for row in rows:
        if row['speaker'] != target or not row['body'].startswith(prefix):
            continue
        body = row['body'][len(prefix):]
        if body not in predicates:
            continue
        kind, value = predicates[body]
        derived = f'{target}: {body}.'
        source_time = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=row['line'])).isoformat()
        event = EventRecord(identity('failure-factor-source', row['candidate']), source_time, derived, source_id, source_time, actor_id=target)
        factor = FactorClaim(identity('failure-factor', row['candidate']), kind, target, action_id,
            event.event_id, derived, stamp, value, ClaimAuthority.DIRECT_SELF_REPORT)
        # Reuse CG03's complete asserted-subject/polarity check. This is a factor
        # comparison, not a responsibility case with invented normative premises.
        if _asserted_factor_polarity(factor, event) != value:
            raise ValueError('factor source polarity mismatch')
        factors.append(factor)
        bindings.append(dict(claim_id=factor.claim_id, source_claim_id=row['candidate'], original_quote=row['quote'],
            derived_factor_quote=derived, action_binding=action_id, time='EXPLICIT_ATTEMPT_TIME_CLAIM_NOT_LATER_KNOWLEDGE'))
    checked = {kind.value: _factor_row(kind, [f for f in factors if f.factor == kind]) for kind in
        (ResponsibilityFactor.KNOWLEDGE, ResponsibilityFactor.CONTROL, ResponsibilityFactor.STATED_INTENTION)}
    def check(kind, expected):
        state = checked[kind]['state']
        return 'CONFLICT' if state == 'CONTESTED' else 'UNKNOWN' if state not in ('SUPPORTED_CLAIM', 'CONTRADICTED_CLAIM') else 'SUPPORTED' if (state == 'SUPPORTED_CLAIM') == expected else 'CONTRADICTED'
    definitions = dict(INFORMATION_GAP=(('KNOWLEDGE', False),), CONTROL_CONSTRAINT=(('CONTROL', False),),
        INFORMED_CONTROLLABLE_STATED_CHOICE=(('KNOWLEDGE', True), ('CONTROL', True), ('STATED_INTENTION', True)))
    candidates = []
    for hypothesis, required in definitions.items():
        conditions = {kind: check(kind, value) for kind, value in required}
        values = set(conditions.values())
        status = 'CONFLICTING_PREMISES' if 'CONFLICT' in values else 'WEAKENED_BY_COUNTEREVIDENCE' if 'CONTRADICTED' in values else 'CONDITIONALLY_SUPPORTED' if values == {'SUPPORTED'} else 'UNRESOLVED'
        candidates.append(dict(hypothesis=hypothesis, conditions=conditions, status=status, actual_cause='NOT_ESTABLISHED'))
    scene = CommunicationScene(original, source_id=source_id)
    apologies = [r for r in rows if r['speaker'] == target and r['line'] > failure['line'] and r['body'] == f'I apologize to {assessor} for failing to {action} in {domain}']
    apology_receipts = []
    for row in apologies:
        audit = next(a for a in scene.view(assessor).access_audit if a['statement_line'] == row['line'])
        apology_receipts.append(dict(row, receipt=audit['status'], received=audit['content_transmitted'], sincerity='NOT_ESTABLISHED'))
    forgiveness = [dict(r, value=r['body'] == f'In {domain}, I forgive {target} for failing to {action}') for r in rows if r['speaker'] == assessor and r['line'] > failure['line'] and r['body'] in
        (f'In {domain}, I forgive {target} for failing to {action}', f'In {domain}, I do not forgive {target} for failing to {action}')]
    expressed = {r['value'] for r in forgiveness}
    repair = ('CONFLICTING_FORGIVENESS_REPORTS' if len(expressed) > 1 else 'REPORTED_FORGIVENESS' if expressed == {True} else
        'REPORTED_NON_FORGIVENESS' if expressed == {False} else 'APOLOGY_RECEIVED_FORGIVENESS_UNKNOWN' if any(a['received'] for a in apology_receipts) else
        'APOLOGY_RECEIPT_UNKNOWN' if apologies else 'NO_EXPLICIT_REPAIR_REPORT')
    result = dict(failure=failure, factor_checks=checked, factor_source_bindings=bindings, explanations=candidates,
        repair_status=repair, apologies=apology_receipts, forgiveness_reports=forgiveness,
        relationship=relationship.payload, actual_forgiveness='NOT_ESTABLISHED', moral_blame='NOT_INFERRED',
        automatic_relationship_change=False, general_character='NOT_INFERRED')
    final = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT, dict(operation='RELATIONAL_FAILURE_REPAIR_JOIN', **result))
    core.support(final, *(r['candidate'] for r in rows), *relationship.claim_ids)
    payload = dict(query=query, original_source=original, status='CHECKED_CONDITIONAL_CONFLICT_AND_REPAIR', **result, dependency_claim_id=final, policy=_POLICY)
    return RelationalConflict(relationship.source_versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), relationship.claim_ids + (final,))
