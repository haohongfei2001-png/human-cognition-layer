"""Individual plans, explicit joint endorsement and source-local authority."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re

from hcl.v04.model import EventRecord
from hcl.v1.cg02 import SocialAct, SocialActKind, check_social_exchange
from .agency import prepare_agency
from .communication import CommunicationScene
from .core import ClaimKind, identity

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf'Can (?P<a>{_NAME}), (?P<b>{_NAME}) and (?P<c>{_NAME}) carry out the joint plan to (?P<goal>.+?) in (?P<context>{_TERM})\?')
_PROPOSE = re.compile(rf'In (?P<context>{_TERM}), I propose the joint plan to (?P<goal>.+)')
_ACCEPT = re.compile(rf"I accept (?P<proposer>{_NAME})'s joint plan in (?P<context>{_TERM}) to (?P<goal>.+)")
_RULE = re.compile(rf'In (?P<context>{_TERM}), only (?P<role>{_TERM}) may authorize the plan to (?P<goal>.+)')
_ROLE = re.compile(rf'In (?P<context>{_TERM}), (?P<actor>{_NAME}) is (?P<negative>not )?(?P<role>{_TERM})')
_GRANT = re.compile(rf'In (?P<context>{_TERM}), I authorize (?P<recipient>{_NAME}) to (?P<goal>.+)')
_REVOKE = re.compile(rf'I revoke my authorization for (?P<recipient>{_NAME}) to (?P<goal>.+?) in (?P<context>{_TERM})')
_POLICY = ('A joint plan is not an omniscient group mind. Keep each participant\'s '
    'reported goal, selected plan, opportunity, endorsement and received messages '
    'separate. Only explicit source-local rules and role claims support conditional '
    'authority. Authority is not transferable by a third-party report or an unauthorized '
    'delegate. Later role/receipt evidence does not backfill an earlier grant/acceptance. '
    'Reported permission and coordination do not establish legal authority, actual '
    'consent, common knowledge, private motive or world feasibility.')


@dataclass(frozen=True)
class JointPlanResult:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded joint-plan context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('joint-plan source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('joint-plan support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('joint-plan context budget exceeded')
        return messages


def prepare_joint_plan(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or len({match['a'], match['b'], match['c']}) != 3 or len(match['goal']) > 200:
        raise ValueError('bounded three distinct participants and local goal required')
    actors, goal, context = (match['a'], match['b'], match['c']), match['goal'], match['context']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        content = core.claims[candidate].content
        if content['kind'] != 'event' or content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        proposal, span = content['proposal'], core.spans[content['source_span_id']]
        narrator = proposal['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:')
        if proposal['assertion_scope'] != 'SOURCE_REPORT' or (not narrator and proposal['speaker_candidates'] != [proposal['speaker_surface']]):
            continue
        rows.append(dict(candidate=candidate, speaker=proposal['speaker_surface'], body=proposal['utterance'].rstrip('.!?'),
            quote=span.quote, line=original[:span.start].count('\n') + 1, narrator=narrator))
    rows.sort(key=lambda r: r['line'])
    if len(rows) > 24:
        raise ValueError('joint-plan source budget exceeded')
    proposals = [r for r in rows if r['speaker'] in actors and (p := _PROPOSE.fullmatch(r['body'])) and p['context'] == context and p['goal'] == goal]
    if len(proposals) > 1:
        raise ValueError('multiple joint proposal episodes; narrow source')
    if not proposals:
        return JointPlanResult(versions, json.dumps(dict(query=query, status='SYSTEM_INSUFFICIENT', original_source=original,
            reason='no_unambiguous_visible_joint_proposal', participants=[], policy=_POLICY), sort_keys=True), ())
    proposal = proposals[0]
    proposer = proposal['speaker']
    scene = CommunicationScene(original, source_id=source_id)
    def receipt(actor, line, cutoff):
        audit = next(a for a in scene.view(actor, through_line=cutoff).access_audit if a['statement_line'] == line)
        return dict(status=audit['status'], received=audit['content_transmitted'])
    events = []
    for index, row in enumerate(rows, 1):
        stamp = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat()
        events.append(EventRecord(identity('joint-source', row['candidate']), stamp, row['quote'], source_id, stamp,
            actor_id=None if row['narrator'] else row['speaker'], metadata={'reader_only': row['narrator']}))
    event_by_candidate = {r['candidate']: e for r, e in zip(rows, events)}
    event = event_by_candidate[proposal['candidate']]
    act = SocialAct(identity('joint-proposal', proposal['candidate']), SocialActKind.PROPOSAL, proposer, None,
        goal, proposal['quote'], event.event_id, event.valid_time)
    acts, endorsements = [act], {proposer: proposal}
    endorsement_history = []
    for row in rows:
        accepted = _ACCEPT.fullmatch(row['body'])
        if (accepted and row['speaker'] in actors and row['speaker'] != proposer and row['line'] > proposal['line']
                and accepted['proposer'] == proposer and accepted['context'] == context and accepted['goal'] == goal):
            endorsements[row['speaker']] = row
            endorsement_history.append(row)
            event = event_by_candidate[row['candidate']]
            acts.append(SocialAct(identity('joint-acceptance', row['candidate']), SocialActKind.ACCEPTANCE, row['speaker'], proposer,
                goal, row['quote'], event.event_id, event.valid_time, refers_to=act.act_id))
    native = check_social_exchange(tuple(acts), (), (), tuple(events))
    claims, participants = [], []
    for actor in actors:
        agency = prepare_agency(workspace, f"What are {actor}'s goals and plans?", source_id=source_id, observer=observer)
        claims.extend(agency.claim_ids)
        plans = [p for p in agency.payload['plans'] if p['goal'] == goal]
        selected = [p for p in plans if p['selection'] == 'REPORTED_SELECTED' and p['goal_status'] == 'ACTIVE']
        endorsement = endorsements.get(actor)
        original_receipt = receipt(actor, proposal['line'], endorsement['line']) if endorsement else dict(status='NO_EXPLICIT_ENDORSEMENT', received=False)
        peer_receipts = {other: receipt(actor, endorsements[other]['line'], len(scene.lines)) if other in endorsements else dict(status='NO_EXPLICIT_ENDORSEMENT', received=False) for other in actors if other != actor}
        ready_plans = [p for p in selected if p['pursuit_check'] == 'SOURCE_SUPPORTED_PURSUIT_NOT_WORLD_FEASIBILITY']
        participants.append(dict(actor=actor, plans=plans, selected_action_claims=[p['claim_id'] for p in selected],
            endorsement=endorsement, proposal_receipt_at_endorsement=original_receipt, peer_endorsement_receipts=peer_receipts,
            individually_supported=bool(selected and len(ready_plans) == len(selected) and endorsement and original_receipt['received']),
            received_peer_endorsements=all(r['received'] for r in peer_receipts.values()), private_consent='NOT_ESTABLISHED'))
    grants = []
    for row in rows:
        grant = _GRANT.fullmatch(row['body'])
        if not grant or row['speaker'] not in actors or grant['recipient'] not in actors or grant['goal'] != goal or grant['context'] != context:
            continue
        rule_rows = [r for r in rows if r['line'] < row['line'] and r['narrator'] and (rule := _RULE.fullmatch(r['body'])) and rule['context'] == context and rule['goal'] == goal]
        roles = {_RULE.fullmatch(r['body'])['role'] for r in rule_rows}
        role = next(iter(roles)) if len(roles) == 1 else None
        role_rows = [r for r in rows if r['line'] < row['line'] and r['narrator'] and (assignment := _ROLE.fullmatch(r['body'])) and assignment['context'] == context and assignment['actor'] == row['speaker'] and assignment['role'] == role]
        role_values = {not bool(_ROLE.fullmatch(r['body'])['negative']) for r in role_rows}
        revoked = [r for r in rows if r['line'] > row['line'] and r['speaker'] == row['speaker'] and (rev := _REVOKE.fullmatch(r['body'])) and rev['recipient'] == grant['recipient'] and rev['goal'] == goal and rev['context'] == context]
        state = ('REPORTED_REVOKED' if revoked else 'RULE_UNRESOLVED' if len(roles) != 1 else
            'ROLE_CONFLICT' if len(role_values) > 1 else 'ROLE_NOT_AUTHORIZED_BY_SOURCE' if role_values == {False} else
            'AUTHORIZED_UNDER_SOURCE_RULE' if role_values == {True} else 'ROLE_UNRESOLVED')
        grants.append(dict(issuer=row['speaker'], recipient=grant['recipient'], action=goal, quote=row['quote'], status=state,
            source_claim_id=row['candidate'], rule_source_ids=[r['candidate'] for r in rule_rows], role_source_ids=[r['candidate'] for r in role_rows],
            revocation_source_ids=[r['candidate'] for r in revoked], receipt=receipt(grant['recipient'], row['line'], len(scene.lines)),
            legal_authority='NOT_ESTABLISHED', delegated_authority='NOT_INFERRED'))
    executors = [p['actor'] for p in participants if any(plan['action'] == goal and plan['selection'] == 'REPORTED_SELECTED' and plan['goal_status'] == 'ACTIVE' for plan in p['plans'])]
    authorized = [a for a in executors if any(g['recipient'] == a and g['status'] == 'AUTHORIZED_UNDER_SOURCE_RULE' and g['receipt']['received'] for g in grants)]
    status = ('PARTICIPANT_PLAN_OR_ENDORSEMENT_UNRESOLVED' if not all(p['individually_supported'] for p in participants) else
        'PEER_COORDINATION_RECEIPTS_INCOMPLETE' if not all(p['received_peer_endorsements'] for p in participants) else
        'NO_REPORTED_FINAL_ACTION_PLAN' if not executors else 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED' if set(authorized) != set(executors) else 'COORDINATION_PREMISES_SUPPORTED')
    result = dict(status=status, context=context, goal=goal, participants=participants, grants=grants,
        final_action_executors=executors, source_authorized_and_informed_executors=authorized,
        group_private_state='NOT_CREATED', world_feasibility='NOT_ESTABLISHED', common_knowledge='NOT_INFERRED')
    final = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT, dict(operation='MULTIPARTY_PLAN_AUTHORITY_JOIN', **result))
    core.support(final, *(r['candidate'] for r in rows), *claims)
    claims.append(final)
    payload = dict(query=query, original_source=original, **result, cg02_source_check=native,
        endorsement_history=endorsement_history, dependency_claim_id=final, policy=_POLICY)
    return JointPlanResult(versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
