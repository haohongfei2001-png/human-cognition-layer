"""G02: compose individual action-time checks without inventing group blame."""
from dataclasses import dataclass
import json
import re

from hcl.v1.cg03 import _ACTION_FORMS, check_responsibility, prepare_responsibility_narrative
from .normative_premises import NormativePremiseWorkspace, NormativePreparation
from .revision_time import _stamp

_POLICY=('Responsibility is conditional on an explicit caller rule. Separate '
    'causal contribution, action-time knowledge, foreseeability, control and '
    'stated intention for each actor. A harmful outcome does not establish '
    'malice, a unique responsible actor, or collective responsibility. A '
    'reported alternative is not verified feasible. A joint-action report '
    'does not create a group mind. Repeated outcome wording across actor '
    'sources is one comparison anchor, not independent corroboration. '
    'CG03 source-order timestamps are not real calendar time.')
_ALT=re.compile(r'(?P<actor>[A-Z][\w-]*): At the time I could have (?P<option>[^.]+?) instead of (?P<replaced>[^.]+)\.')
_JOINT=re.compile(r'Narrator: (?P<first>[A-Z][\w-]*) and (?P<second>[A-Z][\w-]*) jointly (?P<action>[^.]+)\.')
_GROUP_RULE='For this analysis, collective responsibility requires each participant to satisfy the individual rule.'


@dataclass(frozen=True)
class ResponsibilityComposition:
    observer:str|None
    known_at:str|None
    source_versions:tuple
    premise_preparation:NormativePreparation
    payload_json:str

    @property
    def payload(self):return json.loads(self.payload_json)

    def messages(self,workspace,*,max_chars=64000):
        if type(max_chars)is not int or not 1000<=max_chars<=128000:raise ValueError('bounded composition context required')
        self.premise_preparation.messages(workspace.premises,max_chars=128000)
        if self.source_versions!=workspace._selected_versions(self.observer,self.known_at):
            raise ValueError('responsibility source selection or access changed; prepare again')
        messages=[dict(role='system',content=_POLICY),dict(role='user',content=self.payload_json)]
        if len(json.dumps(messages,ensure_ascii=False))>max_chars:
            raise ValueError('responsibility composition context exceeds budget; narrow actors or sources')
        return messages


class ResponsibilityCompositionWorkspace:
    """One bounded source transcript per person, plus optional joint report."""
    def __init__(self):
        self.premises=NormativePremiseWorkspace(max_sources=4)
        self.episodes={}
        self.joint=None

    def put_episode(self,actor,source_id,text,*,recorded_at,permitted_observers=()):
        if not isinstance(actor,str) or not actor or len(actor)>64 or not isinstance(source_id,str) or not source_id or len(source_id)>128 or not isinstance(text,str) or not text or len(text)>16000 or not isinstance(permitted_observers,tuple) or any(not isinstance(a,str) or not a for a in permitted_observers):
            raise ValueError('bounded named actor and authorized source required')
        if actor not in self.episodes and len(self.episodes)>=4:raise ValueError('at most four actor episodes')
        if any(a!=actor and row['source_id']==source_id for a,row in self.episodes.items()) or (self.joint and self.joint['source_id']==source_id):
            raise ValueError('distinct actor and joint source identities required')
        old=self.episodes.get(actor);stamp=_stamp(recorded_at)
        if old and (old['source_id']!=source_id or stamp<=old['recorded_at']):
            raise ValueError('episode correction requires same source and later record time')
        version=old['version']+1 if old else 1
        self.episodes[actor]=dict(actor=actor,source_id=source_id,text=text,version=version,
            recorded_at=stamp,permitted_observers=permitted_observers)
        return version

    def put_joint_report(self,source_id,text,*,recorded_at,permitted_observers=()):
        if not isinstance(source_id,str) or not source_id or len(source_id)>128 or not isinstance(text,str) or not text or len(text)>2000 or not isinstance(permitted_observers,tuple) or any(not isinstance(a,str) or not a for a in permitted_observers):
            raise ValueError('bounded authorized joint source required')
        old=self.joint;stamp=_stamp(recorded_at)
        if any(row['source_id']==source_id for row in self.episodes.values()):
            raise ValueError('distinct actor and joint source identities required')
        if old and (old['source_id']!=source_id or stamp<=old['recorded_at']):
            raise ValueError('joint report correction requires same source and later record time')
        self.joint=dict(source_id=source_id,text=text,version=old['version']+1 if old else 1,
            recorded_at=stamp,permitted_observers=permitted_observers)
        return self.joint['version']

    def _visible(self,row,observer,known_at):
        return row is not None and (observer is None or observer in row['permitted_observers']) and (known_at is None or row['recorded_at']<=known_at)

    def _selected_versions(self,observer,known_at):
        rows=[r for r in self.episodes.values() if self._visible(r,observer,known_at)]
        if self._visible(self.joint,observer,known_at):rows.append(self.joint)
        return tuple(sorted((r['source_id'],r['version']) for r in rows))

    def prepare(self,question,*,actors,observer=None,known_at=None,adopted_framework_text=None):
        if not isinstance(actors,tuple) or not 1<=len(actors)<=4 or len(set(actors))!=len(actors) or any(a not in self.episodes for a in actors):
            raise ValueError('one to four distinct registered actors required')
        if observer is not None and (not isinstance(observer,str) or not observer):raise ValueError('named observer or reader analysis required')
        stamp=_stamp(known_at) if known_at is not None else None
        premise=self.premises.prepare(question,observer=observer,known_at=stamp,
            adopted_framework_text=adopted_framework_text)
        typed=premise.typed_premises
        rows=[];outcomes=[]
        for actor in actors:
            source=self.episodes[actor]
            if not self._visible(source,observer,stamp):
                rows.append(dict(actor=actor,status='SOURCE_VIEW_INSUFFICIENT',source=None,
                    checked=None,alternatives=[],diagnostics=[]))
                continue
            lines=[];alternatives=[];diagnostics=[];offset=0
            for raw in source['text'].splitlines(keepends=True):
                line=raw.rstrip('\r\n');m=_ALT.fullmatch(line)
                if m:
                    if m['actor']==actor:
                        alternatives.append(dict(source_id=source['source_id'],source_version=source['version'],
                            start=offset,end=offset+len(line),quote=line,option=m['option'],replaced=m['replaced'],
                            status='UNRESOLVED_FOCAL_ACTION_LINK'))
                    else:diagnostics.append(dict(start=offset,status='OTHER_ACTOR_ALTERNATIVE_NOT_ATTRIBUTED'))
                else:lines.append(line)
                offset+=len(raw)
            if not typed:
                rows.append(dict(actor=actor,status='NO_ADOPTED_INDIVIDUAL_RULE',source=dict(source_id=source['source_id'],version=source['version']),
                    checked=None,alternatives=alternatives,diagnostics=diagnostics))
                continue
            narrative='\n'.join(lines)
            parsed=prepare_responsibility_narrative(narrative,actor,typed,premise_scope='FOCAL_EPISODE')
            diagnostics.extend(parsed.source_span_diagnostics)
            if parsed.failure:
                rows.append(dict(actor=actor,status='SOURCE_EPISODE_UNRESOLVED',source=dict(source_id=source['source_id'],version=source['version']),
                    failure=parsed.failure,checked=None,alternatives=alternatives,diagnostics=diagnostics))
                continue
            action=next(e for e in parsed.events if e.event_id==parsed.case.action_event_id)
            outcome=next(e for e in parsed.events if e.event_id==parsed.case.outcome_event_id)
            focal=re.fullmatch(rf'{re.escape(actor)}: I (?P<verb>[a-z]+) (?P<object>[^.]+)\.',action.raw_text)
            for alternative in alternatives:
                replaced=re.fullmatch(r'(?P<verb>[a-z]+) (?P<object>.+)',alternative['replaced'])
                if (focal and replaced and replaced['verb'] in _ACTION_FORMS.get(focal['verb'],())
                        and replaced['object'].casefold()==focal['object'].casefold()):
                    alternative['status']='SOURCE_REPORTED_OPTION_NOT_VERIFIED_FEASIBILITY'
            outcomes.append(outcome.raw_text)
            checked=check_responsibility(parsed.case,parsed.events,target_actor=actor)
            rows.append(dict(actor=actor,status='SOURCE_FACTORS_CHECKED',source=dict(source_id=source['source_id'],version=source['version']),
                action_quote=action.raw_text,outcome_quote=outcome.raw_text,checked=checked,
                alternatives=alternatives,diagnostics=diagnostics,
                independent_world_truth='NOT_ESTABLISHED'))
        # Repeating the same outcome line in separate local transcripts allows
        # conditional comparison. It is not independent corroboration.
        comparable=len(outcomes)==len(actors) and len(set(outcomes))==1
        collective_rule=bool(re.search(r'(?:^|[.!?]\s+)'+re.escape(_GROUP_RULE)+r'(?=$|\s)',question))
        joint=self.joint if self._visible(self.joint,observer,stamp) else None
        match=_JOINT.fullmatch(joint['text']) if joint else None
        joint_named=bool(match and set(actors)=={match['first'],match['second']})
        joint_actions_match=bool(joint_named and len(rows)==2 and
            all(r.get('action_quote','').endswith('I '+match['action']+'.') for r in rows))
        assessments=[r['checked']['premise_assessments'] for r in rows if r['checked']]
        if not collective_rule:group_status='NO_ADOPTED_COLLECTIVE_RULE'
        elif len(typed)!=1:group_status='COLLECTIVE_RULE_REQUIRES_ONE_SELECTED_INDIVIDUAL_RULE'
        elif not joint_named:group_status='JOINT_PARTICIPATION_NOT_ESTABLISHED'
        elif not assessments or len(assessments)!=len(actors):group_status='INDIVIDUAL_FACTOR_VIEW_INSUFFICIENT'
        elif not joint_actions_match:group_status='JOINT_ACTION_DOES_NOT_MATCH_INDIVIDUAL_ACTIONS'
        elif not comparable:group_status='COMMON_OUTCOME_NOT_ESTABLISHED'
        elif any(any(a['result']=='CONDITIONALLY_NOT_SUPPORTED' for a in group) for group in assessments):
            group_status='CONDITIONALLY_NOT_SUPPORTED_BY_INDIVIDUAL_CLAIMS'
        elif all(any(a['result']=='CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS' for a in group) for group in assessments):
            group_status='CONDITIONALLY_SUPPORTED_ON_REPORTED_JOINT_ACTION_AND_INDIVIDUAL_CLAIMS'
        else:group_status='UNRESOLVED_INDIVIDUAL_FACTORS'
        payload=dict(schema='hcl-g02-responsibility-composition-v1',question=question,actors=list(actors),observer=observer,
            known_at=stamp,premise_candidates=premise.payload['candidates'],individuals=rows,
            shared_outcome_quote=outcomes[0] if comparable else None,
            outcome_alignment='SAME_SOURCE_WORDING_NOT_INDEPENDENT_CORROBORATION' if comparable else 'NOT_ESTABLISHED',
            collective=dict(status=group_status,caller_rule=_GROUP_RULE if collective_rule else None,
                joint_report=dict(source_id=joint['source_id'],source_version=joint['version'],quote=joint['text']) if joint else None,
                reported_participation='SOURCE_REPORTED_NOT_WORLD_VERIFIED' if joint_named else 'NOT_ESTABLISHED',
                group_mind='NOT_INFERRED'),
            temporal_semantics='CG03_SOURCE_ORDER_AND_EXPLICIT_ACTION_TIME_WORDING_NOT_CALENDAR_PROOF',
            verdict='NO_MORAL_OR_LEGAL_TRUTH',efficacy='UNTESTED',policy=_POLICY)
        return ResponsibilityComposition(observer,stamp,self._selected_versions(observer,stamp),premise,
            json.dumps(payload,ensure_ascii=False,sort_keys=True))
