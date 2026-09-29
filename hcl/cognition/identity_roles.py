"""Self-description, identity attribution, role rule, behavior and endorsement."""
from dataclasses import dataclass
import json
import re

from .core import ClaimKind

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf"How does (?P<actor>{_NAME})'s self-description relate to the (?P<role>{_TERM}) role in (?P<context>{_TERM})\?")
_SELF = re.compile(rf'In (?P<context>{_TERM}), I see myself as (?P<label>.+)')
_REVISION = re.compile(rf'In (?P<context>{_TERM}), I now see myself as (?P<label>.+?) instead of (?P<old>.+)')
_OTHER = re.compile(rf'In (?P<context>{_TERM}), I see (?P<actor>{_NAME}) as (?P<label>.+)')
_OCCUPANCY = re.compile(rf'In (?P<context>{_TERM}), (?P<actor>{_NAME}) (?P<verb>serves as|does not serve as|no longer serves as) (?P<role>{_TERM})')
_REQUIREMENT = re.compile(rf'In (?P<context>{_TERM}), a (?P<role>{_TERM}) is required to (?P<action>.+)')
_PERFORMANCE = re.compile(rf'In (?P<context>{_TERM}), (?P<actor>{_NAME}) (?P<verb>did not|did) (?P<action>.+)')
_ENDORSE = re.compile(rf'In (?P<context>{_TERM}), I (?P<verb>endorse|reject|am unsure about) the requirement for a (?P<role>{_TERM}) to (?P<action>.+)')
_POLICY = ('Separate self-narrative, another person\'s identity attribution, sourced role '
    'occupancy, local requirements, reported behavior and personal endorsement. Role '
    'occupancy or compliance does not imply endorsement. A local rule/behavior tension '
    'does not prove a global identity, moral truth, hypocrisy or personality trait. '
    'Explicit self-description revision is source-local; an isolated behavior or a '
    'third-party label cannot rewrite it. Current endorsement does not backfill a prior '
    'behavior-time attitude. Source order is not verified chronology.')


@dataclass(frozen=True)
class IdentityRoleResult:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded identity context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('identity source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('identity support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('identity context budget exceeded')
        return messages


def prepare_identity_roles(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or match['actor'] == 'Narrator':
        raise ValueError('bounded named actor, role and context required')
    actor, role, context = match['actor'], match['role'], match['context']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        c = core.claims[candidate].content
        if c['kind'] != 'event' or c['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row, span = c['proposal'], core.spans[c['source_span_id']]
        narrator = row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and row['speaker_candidates'] != [row['speaker_surface']]):
            continue
        rows.append(dict(source_claim_id=candidate, speaker=row['speaker_surface'], body=row['utterance'].rstrip('.!?'), quote=span.quote,
            order=span.start, narrator=narrator))
    rows.sort(key=lambda r: r['order'])
    if len(rows) > 20:
        raise ValueError('identity source budget exceeded')
    self_reports, historical, attributions, occupancy, rules, behavior, endorsements, diagnostics = [], [], [], [], [], [], [], []
    for row in rows:
        body, who = row['body'], row['speaker']
        description, revision, other = _SELF.fullmatch(body), _REVISION.fullmatch(body), _OTHER.fullmatch(body)
        occupied, required, performed, endorsed = _OCCUPANCY.fullmatch(body), _REQUIREMENT.fullmatch(body), _PERFORMANCE.fullmatch(body), _ENDORSE.fullmatch(body)
        if who == actor and description and description['context'] == context:
            self_reports.append(dict(row, label=description['label'], authority='SELF_NARRATIVE_NOT_ACTUAL_TRAIT'))
        elif who == actor and revision and revision['context'] == context:
            prior = [r for r in self_reports if r['label'] == revision['old']]
            if len(prior) != 1:
                diagnostics.append(dict(source_claim_id=row['source_claim_id'], status='SELF_REVISION_ANCHOR_UNRESOLVED'))
            else:
                historical.append(prior[0])
                self_reports.remove(prior[0])
                self_reports.append(dict(row, label=revision['label'], revises_source_claim_id=prior[0]['source_claim_id'], authority='EXPLICIT_REPORTED_SELF_REVISION'))
        elif who != actor and other and other['actor'] == actor and other['context'] == context:
            attributions.append(dict(row, label=other['label'], authority='THIRD_PARTY_IDENTITY_ATTRIBUTION'))
        if row['narrator'] and occupied and (occupied['actor'], occupied['role'], occupied['context']) == (actor, role, context):
            if occupied['verb'] == 'no longer serves as':
                positive = [r for r in occupancy if r['value']]
                if not positive:
                    diagnostics.append(dict(source_claim_id=row['source_claim_id'], status='ROLE_EXIT_WITHOUT_PRIOR_OCCUPANCY'))
                    continue
                occupancy = [dict(row, value=False, retired_role_source_ids=[r['source_claim_id'] for r in occupancy])]
            else:
                occupancy.append(dict(row, value=occupied['verb'] == 'serves as'))
        if row['narrator'] and required and (required['role'], required['context']) == (role, context):
            rules.append(dict(row, action=required['action'], authority='SOURCE_LOCAL_REQUIREMENT_NOT_MORAL_TRUTH'))
        if row['narrator'] and performed and (performed['actor'], performed['context']) == (actor, context):
            prior_rules = [r for r in rules if r['action'] == performed['action']]
            role_values = {r['value'] for r in occupancy}
            checked = ('ROLE_OR_REQUIREMENT_UNRESOLVED_AT_BEHAVIOR' if not prior_rules or role_values != {True} else
                'MEETS_DECLARED_REQUIREMENT' if performed['verb'] == 'did' else 'DOES_NOT_MEET_DECLARED_REQUIREMENT')
            behavior.append(dict(row, action=performed['action'], positive=performed['verb'] == 'did', status=checked,
                rule_source_ids=[r['source_claim_id'] for r in prior_rules], role_source_ids=[r['source_claim_id'] for r in occupancy],
                personal_endorsement='NOT_INFERRED', moral_verdict='NOT_INFERRED'))
        if who == actor and endorsed and (endorsed['role'], endorsed['context']) == (role, context):
            endorsements.append(dict(row, action=endorsed['action'], stance={'endorse': 'ENDORSES', 'reject': 'REJECTS', 'am unsure about': 'CHARACTER_UNCERTAIN'}[endorsed['verb']], authority='PERSONAL_REPORTED_POSITION'))
    values = {r['value'] for r in occupancy}
    role_status = 'CONFLICTING_OCCUPANCY_REPORTS' if len(values) > 1 else 'REPORTED_OCCUPANT' if values == {True} else 'REPORTED_NOT_OCCUPANT' if values == {False} else 'UNKNOWN'
    requirement_views = []
    for action in sorted({r['action'] for r in rules}):
        reports = [r for r in endorsements if r['action'] == action]
        positions = {r['stance'] for r in reports}
        requirement_views.append(dict(action=action, endorsement='CONFLICTING_REPORTED_POSITIONS' if len(positions) > 1 else next(iter(positions)) if positions else 'NOT_REPORTED', reports=reports))
    payload = dict(query=query, original_source=original, actor=actor, context=context, role=role,
        current_self_descriptions=self_reports, historical_self_descriptions=historical, other_identity_attributions=attributions,
        role_status=role_status, role_source_reports=occupancy, source_requirements=rules,
        requirement_endorsements=requirement_views, unlinked_endorsement_reports=[e for e in endorsements if not any(r['action'] == e['action'] for r in rules)],
        behavior_checks=behavior, diagnostics=diagnostics, actual_identity='NOT_ESTABLISHED',
        local_tension=any(b['status'] == 'DOES_NOT_MEET_DECLARED_REQUIREMENT' for b in behavior),
        identity_rewritten_from_behavior=False, global_personality='NOT_CREATED', policy=_POLICY)
    claims = []
    if rows:
        final = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT, dict(operation='SELF_ROLE_BEHAVIOR_ENDORSEMENT_JOIN', **payload))
        core.support(final, *(r['source_claim_id'] for r in rows))
        claims.append(final)
        payload['dependency_claim_id'] = final
    return IdentityRoleResult(versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
