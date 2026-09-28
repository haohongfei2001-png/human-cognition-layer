"""Goal-linked reported appraisal, expression and feeling without emotion guessing."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import re

from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind as Provenance
from hcl.v07 import IntentionEvidenceEvent, IntentionSignal
from hcl.v08.runtime import (HCLV08Runtime, AffectEvidenceEvent, AffectKind,
    AppraisalDimension, EvidenceStrength)
from .agency import _GOAL, _SUBGOAL, prepare_agency
from .core import ClaimKind, identity

_QUERY = re.compile(r'How does (?P<actor>[A-Z][\w-]*) appraise (?P<episode>[^?]+)\?')
_APPRAISAL = re.compile(r'(?P<episode>.+?) (?P<valence>helps|hinders) my goal to (?P<goal>.+)')
_REAPPRAISAL = re.compile(r'I now see (?P<episode>.+?) as (?P<valence>helpful|harmful) for my goal to (?P<goal>.+)')
_EMOTION = re.compile(r'I feel (?P<values>[a-z-]+(?: and [a-z-]+){0,2}) about (?P<episode>.+)')
_UNCERTAIN = re.compile(r'I am unsure how I feel about (?P<episode>.+)')
_ATTRIBUTION = re.compile(r'(?P<actor>[A-Z][\w-]*) seems (?P<value>[a-z-]+) about (?P<episode>.+)')
_EXPRESSION = re.compile(r'(?P<actor>[A-Z][\w-]*) (?P<value>smiled|cried|frowned) during (?P<episode>.+)')
_DIMENSION = re.compile(r'About (?P<episode>.+?), I (?P<value>feel in control|feel unable to control events|am certain about the outcome|am uncertain about the outcome)')
_POLICY = ('Keep reported emotions, observed expressions, third-party judgments and '
    'goal-linked appraisal distinct. Mixed goal congruence does not prove mixed felt '
    'emotion. Goal change can revise a conditional relevance check without erasing a '
    'reported feeling. Control and certainty are reported appraisals, not actual control '
    'or knowledge. Reappraisal requires explicit anchored revision, not analyst preference. '
    'Source order is not verified calendar chronology. No global value weights are used.')


@dataclass(frozen=True)
class AppraisalResult:
    scope: object
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded appraisal context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('appraisal source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(key) != 'SUPPORT_AVAILABLE' for key in self.claim_ids):
            raise ValueError('appraisal support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user',
            content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('appraisal context budget exceeded')
        return messages


def prepare_appraisal(workspace, query, *, source_id, observer=None):
    question = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not question or len(question['episode']) > 160:
        raise ValueError('bounded actor and episode appraisal question required')
    actor, episode = question['actor'], question['episode'].casefold()
    agency = prepare_agency(workspace, f"What are {actor}'s goals and plans?", source_id=source_id, observer=observer)
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, runtime = workspace.core, HCLV08Runtime()
    rows, diagnostics, claims, native_claims, current_appraisals, events = [], [], list(agency.claim_ids), {}, {}, []
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
    rows.sort(key=lambda row: row[0])
    if len(rows) > 20:
        raise ValueError('appraisal source statement budget exceeded')
    for index, (_, candidate, row, span, narrator) in enumerate(rows, 1):
        speaker, body = row['speaker_surface'], row['utterance'].rstrip('.!?')
        stamp = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat()
        event = EventRecord(identity('appraisal-source', candidate), stamp, span.quote, source_id, stamp,
            actor_id=None if narrator else speaker, metadata={'reader_only': narrator, 'time_semantics': 'SOURCE_ORDER_ONLY'})
        runtime.ingest_event(event)
        events.append(event)
        goal = _GOAL.fullmatch(body) or _SUBGOAL.fullmatch(body)
        if speaker == actor and goal and ' if ' not in goal['goal'] and ';' not in goal['goal']:
            verb = goal.groupdict().get('verb', 'want to')
            signal = {'want to': IntentionSignal.EXPLICIT_GOAL, 'aim to': IntentionSignal.EXPLICIT_GOAL,
                'completed my goal to': IntentionSignal.EXPLICIT_COMPLETION,
                'abandoned my goal to': IntentionSignal.EXPLICIT_ABANDONMENT,
                'am unsure whether to': IntentionSignal.CHARACTER_UNCERTAIN}[verb]
            native_goal = IntentionEvidenceEvent(identity('appraisal-goal', candidate), event.event_id, actor,
                goal['goal'], signal, Provenance.SELF_REPORT, stamp, stamp, span.quote)
            runtime.intentions.ingest_intention_evidence(native_goal)
            continue
        appraisal, revision = _APPRAISAL.fullmatch(body), _REAPPRAISAL.fullmatch(body)
        emotion, uncertain = _EMOTION.fullmatch(body), _UNCERTAIN.fullmatch(body)
        attribution, expression = _ATTRIBUTION.fullmatch(body), _EXPRESSION.fullmatch(body)
        dimension = _DIMENSION.fullmatch(body)
        candidate_match = appraisal or revision or emotion or uncertain or attribution or expression or dimension
        if not candidate_match or candidate_match['episode'].casefold() != episode:
            continue
        def add(kind, value, strength=EvidenceStrength.DIRECT, provenance=Provenance.SELF_REPORT,
                dimension=None, goal_key=None, supersedes=None):
            native = AffectEvidenceEvent(identity('appraisal-evidence', candidate, kind.value, value, goal_key),
                event.event_id, actor, episode, kind, strength, value, provenance, stamp, stamp,
                span.quote, dimension, goal_key, supersedes)
            runtime.ingest_affect_evidence(native)
            claim = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
                dict(operation='SOURCE_BOUND_AFFECT_OR_APPRAISAL', evidence=native.as_dict(), private_state='NOT_VERIFIED'))
            supports = [candidate]
            if supersedes:
                supports.append(native_claims[supersedes])
            if goal_key:
                supports.extend(g['claim_id'] for g in agency.payload['goals'] if g['goal'] == goal_key)
            core.support(claim, *supports)
            core.interpret(claim, unknown_conditions=('source_report_accuracy_not_established',))
            claims.append(claim)
            native_claims[native.evidence_id] = claim
            return native
        if speaker == actor and (appraisal or revision):
            matched = appraisal or revision
            target_goal = matched['goal']
            known = runtime.intentions.goal_estimates(actor)
            if not any(g.goal_key == target_goal and g.direct_evidence_ids for g in known):
                diagnostics.append(dict(candidate_id=candidate, reason='APPRAISAL_LACKS_PRIOR_SOURCE_GOAL'))
                continue
            prior = current_appraisals.get(target_goal, [])
            if revision and len(prior) != 1:
                diagnostics.append(dict(candidate_id=candidate, reason='REAPPRAISAL_ANCHOR_MISSING_OR_AMBIGUOUS'))
                continue
            value = 'helps' if matched['valence'] in ('helps', 'helpful') else 'hinders'
            evidence = add(AffectKind.APPRAISAL, value, dimension=AppraisalDimension.GOAL_CONGRUENCE,
                goal_key=target_goal, supersedes=prior[0] if revision else None)
            current_appraisals[target_goal] = [evidence.evidence_id] if revision else prior + [evidence.evidence_id]
        elif speaker == actor and emotion:
            values = emotion['values'].split(' and ')
            if any(v in ('not', 'never', 'maybe', 'probably') or len(v) > 24 for v in values):
                diagnostics.append(dict(candidate_id=candidate, reason='AMBIGUOUS_FEELING_FORM'))
                continue
            for value in dict.fromkeys(values):
                add(AffectKind.EMOTION, value)
        elif speaker == actor and uncertain:
            add(AffectKind.CHARACTER_UNCERTAIN, 'explicit_uncertainty_about_feeling')
        elif speaker == actor and dimension:
            value = dimension['value']
            which = AppraisalDimension.CONTROL if 'control' in value else AppraisalDimension.CERTAINTY
            add(AffectKind.APPRAISAL, value, dimension=which)
        elif not narrator and speaker != actor and attribution and attribution['actor'] == actor:
            add(AffectKind.EMOTION, attribution['value'], EvidenceStrength.ATTRIBUTED, Provenance.THIRD_PARTY_REPORT)
        elif narrator and expression and expression['actor'] == actor:
            add(AffectKind.EXPRESSION, expression['value'], EvidenceStrength.INFERRED, Provenance.NARRATOR_ASSERTION)
    native = runtime.answer_context(actor)
    goal_states = {g['goal']: g['status'] for g in agency.payload['goals']}
    applicable, suspended = [], []
    for evidence in native['current_evidence']:
        if evidence['kind'] == 'APPRAISAL' and evidence['dimension'] == 'GOAL_CONGRUENCE':
            state = goal_states.get(evidence['goal_key'], 'SYSTEM_INSUFFICIENT')
            entry = dict(evidence, current_goal_status=state, shared_claim_id=native_claims[evidence['evidence_id']])
            (applicable if state in ('ACTIVE', 'COMPLETED') else suspended).append(entry)
    by_goal = {}
    for row in applicable:
        by_goal.setdefault(row['goal_key'], set()).add(row['value'])
    values = {row['value'] for row in applicable}
    congruence = ('GOAL_APPRAISAL_CONFLICT' if any(len(v) > 1 for v in by_goal.values()) else
        'MIXED_GOAL_CONGRUENCE' if values == {'helps', 'hinders'} else
        'SUPPORTS_EVIDENCED_GOALS' if values == {'helps'} else
        'HINDERS_EVIDENCED_GOALS' if values == {'hinders'} else 'NO_CURRENT_GOAL_LINKED_APPRAISAL')
    reported = sorted({e['value'] for e in native['current_evidence'] if e['kind'] == 'EMOTION' and e['strength'] == 'DIRECT'})
    result = dict(episode=episode, goal_congruence=congruence, applicable_appraisals=applicable,
        suspended_goal_links=suspended, reported_emotions=reported,
        multiple_reported_feelings=len(set(reported)) > 1, inferred_actual_emotion='NOT_ESTABLISHED',
        actual_control='NOT_ESTABLISHED', actual_knowledge='NOT_ESTABLISHED',
        goal_projection='CURRENT_SOURCE_GOAL_RELEVANCE_NOT_AUTOMATIC_CHARACTER_REAPPRAISAL')
    final_claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
        dict(operation='GOAL_APPRAISAL_AFFECT_CHANNEL_JOIN', actor=actor, **result))
    if claims:
        core.support(final_claim, *claims)
        claims.append(final_claim)
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    payload = dict(query=query, actor=actor, original_sources=[dict(source_id=s, version=v, text=workspace._documents[s][0]) for s, v in versions],
        appraisal=result, retained_v08=native, goal_context=agency.payload, source_events=[asdict(e) for e in events],
        diagnostics=diagnostics, temporal_assumption='SOURCE_ORDER_NOT_VERIFIED_EVENT_CHRONOLOGY',
        provider_calls=0, policy=_POLICY)
    return AppraisalResult(semantic.scope, versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
