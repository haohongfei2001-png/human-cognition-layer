"""F04: source-conditioned rival explanations of an apparent action change."""
from dataclasses import dataclass
import json
import re

from .core import ClaimKind, Scope
from .evidence_closure import EvidenceClosureIndex
from .workspace import CognitionWorkspace

_POLICY = ('Compare explicit source reports as rival conditional explanations. '
    'A reported action is not verified conduct; a reported knowledge change is '
    'not verified knowledge; a stated goal or value is not a private state. '
    'Role pressure and audience strategy are reports, not proved motives. '
    'An available analyst source is not character access. No candidate wins '
    'without further evidence. Do not infer growth, decline, moral character, '
    'deception or causal responsibility from this comparison.')
_OLD_KNOW = re.compile(r'I did not know that (?P<item>[^.]+)\.?$',re.I)
_NEW_KNOW = re.compile(r'I now know that (?P<item>[^.]+)\.?$',re.I)
_OLD_GOAL = re.compile(r'I want to (?P<item>[^.]+)\.?$',re.I)
_STABLE_GOAL = re.compile(r'I still want to (?P<item>[^.]+)\.?$',re.I)
_NEW_GOAL = re.compile(r'I now want to (?P<new>[^.]+?) instead of (?P<old>[^.]+)\.?$',re.I)
_OLD_VALUE = re.compile(r'As (?P<role>\w+) in (?P<context>\w+), I prefer (?P<item>[^.]+)\.?$',re.I)
_NEW_VALUE = re.compile(r'As (?P<role>\w+) in (?P<context>\w+), I now prefer (?P<new>[^.]+?) instead of (?P<old>[^.]+)\.?$',re.I)
_PRESSURE = re.compile(r'As (?P<role>\w+) in (?P<context>\w+), I faced pressure to (?P<action>[^.]+)\.?$',re.I)
_STRATEGY = re.compile(r'I told (?P<audience>[A-Z][\w-]*) I wanted to (?P<action>[^.]+?) so (?P=audience) would (?P<purpose>[^.]+)\.?$',re.I)


def _match(pattern, episode):
    return pattern.fullmatch(episode.reported_content) if episode.authority=='NARRATED_SPEECH_NOT_VERIFIED_WORLD_FACT' else None


def _norm(value):return value.strip().rstrip('.').casefold()


@dataclass(frozen=True)
class CharacterDevelopmentComparison:
    source_versions:tuple
    source_id:str
    observer:str|None
    payload_json:str

    @property
    def payload(self):return json.loads(self.payload_json)

    def messages(self,timeline,query,*,max_chars=64000):
        if not isinstance(query,str) or not query.strip() or len(query)>8000 or type(max_chars)is not int or not 1000<=max_chars<=128000:
            raise ValueError('bounded development question and context required')
        current=tuple(row for row in timeline._selected_versions(self.payload['known_at'],self.observer) if row[0]==self.source_id)
        if self.source_versions!=current:
            raise ValueError('source selection or access changed; compare again')
        messages=[dict(role='system',content=_POLICY),dict(role='user',content=json.dumps(dict(query=query,cognition=self.payload),ensure_ascii=False,sort_keys=True))]
        if len(json.dumps(messages,ensure_ascii=False))>max_chars:
            raise ValueError('complete competing explanation context exceeds budget')
        return messages


def compare_character_development(timeline,source_id,actor,action,*,through_date,known_at,observer=None):
    """Compare one named person's same action across two source-declared dates.

    This bounded opt-in operation reads one authorized chapter. Its explicit
    factor grammar deliberately refuses generic motive/character inference.
    Every admitted rival retains its entire F03 recorded source closure.
    """
    from .narrative_time import _day, _stamp
    if not all(isinstance(x,str) and x and len(x)<=128 for x in (source_id,actor,action)) or actor.lower() in ('she','he','they','someone'):
        raise ValueError('one named actor, source and action required')
    cutoff=_day(through_date);stamp=_stamp(known_at)
    selected=timeline._select(stamp,observer)
    record=next((r for r in selected if r['source_id']==source_id),None)
    if record is None:raise ValueError('source unavailable or not authorized')
    episodes=[e for e in record['episodes'] if e.reference_status=='SOURCE_LOCAL_NAMES' and e.temporal_status=='DECLARED_DATES_ONLY' and e.disclosure_time<=cutoff]
    person=[e for e in episodes if e.actor_surface==actor]
    actions=[]
    for e in person:
        if e.authority!='NARRATED_ACTION_NOT_VERIFIED_WORLD_FACT':continue
        m=re.fullmatch(r'did(?P<negative> not)? (?P<action>.+)',e.reported_content)
        if m and _norm(m['action'])==_norm(action):actions.append((e,bool(m['negative'])))
    actions.sort(key=lambda item:(item[0].story_time,item[0].narrative_order))
    workspace=CognitionWorkspace()
    workspace._versions[source_id]=record['version']-1
    workspace.put_source(source_id,record['text'],permitted_observers=record['permitted_observers'])
    core=workspace.core
    scope=Scope(actor=actor,observer=observer,source_ids=(source_id,),assumptions=('source_local_name_only','reported_narrative_not_world_truth'))
    spans={}
    def anchor(e):
        if e.episode_id not in spans:
            key=core.add_span(record['text'],source_id=source_id,version=record['version'],start=e.start,end=e.end,
                order=e.narrative_order,permitted_observers=record['permitted_observers'])
            spans[e.episode_id]=key
        return spans[e.episode_id]
    def citation(e):
        return dict(episode_id=e.episode_id,source_id=e.source_id,source_version=e.source_version,
            source_span_id=anchor(e),quote=e.quote,story_time=e.story_time,
            disclosure_time=e.disclosure_time,system_record_time=e.system_record_time,
            authority=e.authority)
    status='COMPARABLE_ACTION_CHANGE'
    if len(actions)!=2 or actions[0][1]==actions[1][1] or actions[0][0].story_time>=actions[1][0].story_time:
        status='NO_UNAMBIGUOUS_COMPARABLE_ACTION_CHANGE'
    candidates=[];action_pair=[];recorded_closure=None;stable=[]
    if status=='COMPARABLE_ACTION_CHANGE':
        first,second=actions[0][0],actions[1][0]
        action_pair=[citation(first),citation(second)]
        before=[e for e in person if e.story_time<first.story_time]
        between=[e for e in person if first.story_time<e.story_time<second.story_time]
        # Same-day statement/action ordering is unresolved; it cannot supply a factor.
        def add(kind,roots,condition):
            ids={e.episode_id for e in roots}
            if len(ids)!=len(roots):return
            candidates.append(dict(kind=kind,factor_sources=[citation(e) for e in roots],
                conditional_explanation=condition,causal_status='NOT_ESTABLISHED',
                private_state='NOT_INFERRED'))
        for old in before:
            missing=_match(_OLD_KNOW,old)
            old_goal=_match(_OLD_GOAL,old)
            old_value=_match(_OLD_VALUE,old)
            for new in between:
                gained=_match(_NEW_KNOW,new)
                revision=_match(_NEW_GOAL,new)
                value_revision=_match(_NEW_VALUE,new)
                if missing and gained and _norm(missing['item'])==_norm(gained['item']):
                    add('NEW_REPORTED_INFORMATION',(old,new),'If both self reports are accurate, the reported information change may matter; actual access and use remain unknown.')
                if old_goal and revision and _norm(old_goal['item'])==_norm(revision['old']) and _norm(revision['new'])!=_norm(revision['old']):
                    add('EXPLICIT_REPORTED_GOAL_REVISION',(old,new),'The actor reports a different goal; actual preference and its role in the action remain unknown.')
                if old_value and value_revision and (old_value['role'],old_value['context'])==(value_revision['role'],value_revision['context']) and _norm(old_value['item'])==_norm(value_revision['old']) and _norm(value_revision['new'])!=_norm(value_revision['old']):
                    add('EXPLICIT_REPORTED_VALUE_REVISION',(old,new),'The actor reports a changed contextual preference; no global value change is inferred.')
        for appointment in between:
            if appointment.authority!='NARRATED_ROLE_CHANGE_NOT_INFERRED_IDENTITY':continue
            role=re.fullmatch(r'became (?P<role>\w+) in (?P<context>\w+)',appointment.reported_content)
            for pressure in between:
                report=_match(_PRESSURE,pressure)
                if role and report and appointment.story_time<pressure.story_time and (role['role'],role['context'])==(report['role'],report['context']) and _norm(report['action'])==_norm(action):
                    add('REPORTED_ROLE_PRESSURE',(appointment,pressure),'A source reports a role change and the actor reports pressure; compliance and motive are not established.')
        for strategy in between:
            report=_match(_STRATEGY,strategy)
            if report and _norm(report['action'])==_norm(action):
                add('EXPLICIT_REPORTED_AUDIENCE_STRATEGY',(strategy,),'The actor reports audience-directed words; sincerity, deception and action causation remain unknown.')
        if len(candidates)>16:
            raise ValueError('competing candidate budget exceeded; narrow the chapter or action')
        # An explicit continuing goal is separate source context, not an
        # obligation in or proof of any candidate's causal support path.
        stable=[citation(e) for e in between if _match(_STABLE_GOAL,e)]
        for candidate in candidates:
            roots=[first,second]+[next(e for e in episodes if e.episode_id==r['episode_id']) for r in candidate['factor_sources']]
            claim=core.claim(scope,ClaimKind.SYSTEM_INTERPRETATION,dict(operation='F04_COMPETING_DEVELOPMENT_EXPLANATION',
                kind=candidate['kind'],actor=actor,action=action,source_id=source_id,
                authority='SOURCE_CONDITIONED_ANALYST_HYPOTHESIS_NOT_PRIVATE_CAUSE'))
            core.support(claim,*(anchor(e) for e in roots))
            candidate['claim_id']=claim
        ids=[c['claim_id'] for c in candidates]
        for candidate in candidates:
            core.interpret(candidate['claim_id'],alternatives=tuple(k for k in ids if k!=candidate['claim_id']),
                unknown_conditions=('source_accuracy','actual_private_state','causal_link','unrecorded_alternatives'))
        if candidates:
            comparison=core.claim(scope,ClaimKind.SYSTEM_INTERPRETATION,dict(operation='F04_RIVAL_EXPLANATION_SET',
                actor=actor,action=action,source_id=source_id,selection='ALL_RECORDED_CANDIDATES_NO_WINNER'))
            for key in ids:core.support(comparison,key)
            core.interpret(comparison,unknown_conditions=('unrecorded_alternatives','candidate_truth_and_causation'))
            complete=EvidenceClosureIndex(workspace).select(comparison,observer=observer,
                query='Compare all recorded explanations without inferring character or motive.')
            recorded_closure=json.loads(complete.messages[1]['content'])['cognition']
    payload=dict(schema='hcl-f04-character-development-v1',source_id=source_id,source_version=record['version'],
        observer=observer,actor=actor,action=action,through_date=cutoff,known_at=stamp,status=status,
        action_pair=action_pair,candidates=candidates,continuing_goal_reports=stable,
        recorded_evidence_closure=recorded_closure,
        all_competing_candidates_retained=True,
        source_scope='ONE_AUTHORIZED_CHAPTER_AND_SOURCE_LOCAL_NAME',
        unsupported_inferences=('private_knowledge','actual_goal_or_value','actual_role_motive','deception','moral_character','growth_or_decline'),
        efficacy='UNTESTED',policy=_POLICY)
    return CharacterDevelopmentComparison(((source_id,record['version']),),source_id,observer,
        json.dumps(payload,ensure_ascii=False,sort_keys=True))
