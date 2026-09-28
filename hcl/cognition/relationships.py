"""Directional domain/aspect-specific reported regard with explicit source basis."""
from dataclasses import dataclass
import json
import re

from .core import ClaimKind

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf"How does (?P<assessor>{_NAME}) regard (?P<target>{_NAME})'s (?P<aspect>{_TERM}) in (?P<domain>{_TERM})\?")
_REGARD = re.compile(rf"In (?P<domain>{_TERM}), I (?P<now>now )?(?P<verb>trust|distrust|am unsure about) (?P<target>{_NAME})'s (?P<aspect>{_TERM})(?: instead of (?P<old>trusting|distrusting) it)? because (?P<reason>.+)")
_ATTRIBUTED = re.compile(rf"In (?P<domain>{_TERM}), (?P<assessor>{_NAME}) (?P<verb>trusts|distrusts|is unsure about) (?P<target>{_NAME})'s (?P<aspect>{_TERM}) because (?P<reason>.+)")
_POLICY = ('Regard is a source-reported view from one named person toward another '
    'within an exact domain and aspect. Competence regard is not moral regard or a '
    'global trust score. Direction is not reciprocal. A cited reason and its current '
    'source support are separate from the reported judgment; counterevidence does not '
    'silently change the person\'s attitude. Only explicit anchored revision replaces '
    'a prior reported stance. Third-party attribution is not a direct self-report. '
    'Source order and sincerity remain assumptions; no actual character trait is proved.')


@dataclass(frozen=True)
class RelationshipResult:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded relationship context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('relationship source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('relationship support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('relationship context budget exceeded')
        return messages


def prepare_relationship(workspace, query, *, source_id, observer=None):
    question = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not question or question['assessor'] == question['target']:
        raise ValueError('bounded directional relationship question required')
    assessor, target, aspect, domain = (question[k] for k in ('assessor', 'target', 'aspect', 'domain'))
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        content = core.claims[candidate].content
        if content['kind'] != 'event' or content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row, span = content['proposal'], core.spans[content['source_span_id']]
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and row['speaker_candidates'] != [row['speaker_surface']]):
            continue
        rows.append(dict(candidate=candidate, speaker=row['speaker_surface'], body=row['utterance'].rstrip('.!?'),
            start=span.start, quote=span.quote, narrator=narrator))
    rows.sort(key=lambda r: r['start'])
    if len(rows) > 20:
        raise ValueError('relationship source budget exceeded')
    current, historical, attributed, diagnostics, claims = [], [], [], [], []
    def basis(reason, through=None):
        supported = [r['candidate'] for r in rows if r['narrator'] and r['body'] == f'In {domain}, {reason}' and (through is None or r['start'] < through)]
        counter = [r['candidate'] for r in rows if r['narrator'] and r['body'] == f'In {domain}, it is false that {reason}' and (through is None or r['start'] < through)]
        state = 'CONTESTED_SOURCE_BASIS' if supported and counter else 'SOURCE_COUNTEREVIDENCE' if counter else 'SOURCE_SUPPORTED_BASIS' if supported else 'SELF_REPORTED_REASON_ONLY'
        return dict(status=state, supporting_source_ids=supported, counterevidence_source_ids=counter, world_truth='NOT_ESTABLISHED', assessor_access='NOT_ESTABLISHED', time_semantics='SOURCE_ORDER_ONLY')
    for row in rows:
        direct, reported = _REGARD.fullmatch(row['body']), _ATTRIBUTED.fullmatch(row['body'])
        matching = direct if direct and row['speaker'] == assessor else reported if reported and reported['assessor'] == assessor and row['speaker'] != assessor else None
        if not matching or (matching['target'], matching['aspect'], matching['domain']) != (target, aspect, domain):
            continue
        values = matching.groupdict()
        stance = 'TRUST' if values['verb'] in ('trust', 'trusts') else 'DISTRUST' if values['verb'] in ('distrust', 'distrusts') else 'CHARACTER_UNCERTAIN'
        report = dict(assessor=assessor, target=target, aspect=aspect, domain=domain, stance=stance,
            reason=values['reason'], quote=row['quote'], source_claim_id=row['candidate'],
            basis_at_report=basis(values['reason'], row['start']), basis_current=basis(values['reason']),
            authority='DIRECT_SELF_REPORT' if matching is direct else 'THIRD_PARTY_ATTRIBUTION', private_regard='NOT_ESTABLISHED')
        claim = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
            dict(operation='REPORTED_DOMAIN_REGARD', **report))
        core.support(claim, row['candidate'])
        core.interpret(claim, unknown_conditions=('reported_attitude_not_verified',))
        claims.append(claim)
        report['claim_id'] = claim
        if matching is reported:
            attributed.append(report)
            continue
        if values.get('now') or values.get('old'):
            old_stance = {'trusting': 'TRUST', 'distrusting': 'DISTRUST'}.get(values.get('old'))
            prior = [r for r in current if r['stance'] == old_stance]
            if not values.get('now') or len(prior) != 1:
                diagnostics.append(dict(report=report, status='EXPLICIT_REVISION_ANCHOR_MISSING_OR_AMBIGUOUS'))
                continue
            historical.append(prior[0])
            current.remove(prior[0])
            report['revises_source_claim_id'] = prior[0]['source_claim_id']
        current.append(report)
    stances = {r['stance'] for r in current}
    status = ('CONFLICTING_REPORTED_REGARD' if len(stances) > 1 else next(iter(stances)) if stances else
        'ATTRIBUTED_ONLY' if attributed else 'SYSTEM_INSUFFICIENT')
    payload = dict(query=query, original_source=original, status=status, assessor=assessor, target=target,
        aspect=aspect, domain=domain, current_reports=current, historical_reports=historical,
        attributed_reports=attributed, diagnostics=diagnostics, reciprocal_view='NOT_INFERRED',
        other_domain_or_aspect='NOT_GENERALIZED', global_trust_score='NOT_CREATED', actual_trait='NOT_ESTABLISHED', policy=_POLICY)
    if rows:
        final = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='DIRECTIONAL_RELATIONSHIP_BASIS_CHECK', assessor=assessor, target=target,
                domain=domain, aspect=aspect, status=status, current_reports=current))
        core.support(final, *(r['candidate'] for r in rows), *claims)
        claims.append(final)
    return RelationshipResult(versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
