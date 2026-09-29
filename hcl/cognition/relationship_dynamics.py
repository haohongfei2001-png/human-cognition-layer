"""Source-bound failure explanations join role and relationship interpretations."""
from dataclasses import dataclass
import json
import re

from .agency_chain import SemanticWorkspace
from .core import ClaimKind
from .contextual_values import prepare_contextual_values
from .identity_roles import prepare_identity_roles
from .relational_conflict import prepare_relational_conflict

_NAME = r'[A-Z][\w-]*'
_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf"Explain how (?P<assessor>{_NAME})'s view of (?P<actor>{_NAME}) relates to the (?P<role>{_TERM}) role and preferences in (?P<context>{_TERM}) after the failure to (?P<action>[^.]+)\.")
_POLICY = ('The joined explanations are analyst interpretations, not a change in the '
    'characters. Source revision can change conditional failure/role explanations '
    'while reported regard, self-description and preferences stay unchanged. Link '
    'a failure to role behavior only through an explicit source episode binding. '
    'Neither poor performance nor stated intention proves global unreliability, '
    'identity, moral responsibility or value weights. Keep context-driven choice, '
    'explicit preference revision and unknown private change separate.')


@dataclass(frozen=True)
class RelationshipDynamicsResult:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=120000):
        if type(max_chars) is not int or not 1000<=max_chars<=160000:
            raise ValueError('bounded dynamics context required')
        if any(s not in workspace._documents or workspace._versions[s]!=v for s,v in self.source_versions):
            raise ValueError('dynamics source changed; recompute')
        statuses=workspace.core.support_statuses()
        if any(statuses.get(c)!='SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('dynamics support changed; recompute')
        messages=[dict(role='system',content=_POLICY),dict(role='user',content=self.payload_json)]
        if len(json.dumps(messages,ensure_ascii=False))>max_chars:
            raise ValueError('dynamics context budget exceeded')
        return messages


def prepare_relationship_dynamics(workspace,query,*,source_id,observer=None):
    m=_QUERY.fullmatch(query) if isinstance(query,str) and len(query)<=8000 else None
    if not m or m['actor']==m['assessor'] or len(m['action'])>200:
        raise ValueError('bounded person-role-failure query required')
    actor,assessor,role,context,action=(m[k] for k in ('actor','assessor','role','context','action'))
    failure=prepare_relational_conflict(workspace,f"Explain {assessor}'s response to {actor}'s failure to {action} in {context}.",source_id=source_id,observer=observer)
    identity=prepare_identity_roles(workspace,f"How does {actor}'s self-description relate to the {role} role in {context}?",source_id=source_id,observer=observer)
    values=prepare_contextual_values(workspace,f"Compare {actor}'s contextual preferences in {context}.",source_id=source_id,observer=observer)
    f,i,v=failure.payload,identity.payload,values.payload
    semantic=workspace.prepare_semantic(query,source_ids=(source_id,),observer=observer)
    core=workspace.core
    links=[]
    expected=f"In {context}, {actor}'s failure to {action} was the {role} episode."
    for key in semantic.candidate_ids:
        c=core.claims[key].content
        if c['kind']!='event' or c['validation']['semantic_support']!='BOUNDED_LITERAL_FORM':continue
        row,span=c['proposal'],core.spans[c['source_span_id']]
        if row['assertion_scope']=='SOURCE_REPORT' and row['speaker_surface']=='Narrator' and span.quote.startswith('Narrator:') and row['utterance']==expected:
            links.append(dict(source_claim_id=key,quote=span.quote))
    behaviors=[b for b in i['behavior_checks'] if b['action']==action and not b['positive']]
    linked=len(links)==1 and len(behaviors)==1 and f.get('status')=='CHECKED_CONDITIONAL_CONFLICT_AND_REPAIR'
    hypotheses=f.get('explanations',[])
    supported=[h['hypothesis'] for h in hypotheses if h['status']=='CONDITIONALLY_SUPPORTED']
    reason=f'{actor} failed to {action}'
    reports=f['relationship'].get('current_reports',[])
    cited=[r['source_claim_id'] for r in reports if r['reason']==reason]
    # Two different conditional interpretations depend on the same actual factors.
    # Their recipients' expressed attitudes and identity are separate source facts.
    relation_explanation=dict(status='SOURCE_CITED_FAILURE_CONDITIONALLY_EXPLAINED' if cited and supported else 'UNRESOLVED',
        cited_relationship_source_ids=cited,conditional_alternatives=supported if cited else [],
        reported_regard=f['relationship']['status'],attitude_rewritten=False,assessor_knows_factors='NOT_ESTABLISHED')
    role_evaluation=dict(status='BOUND_ROLE_FAILURE_CONDITIONALLY_EXPLAINED' if linked and supported else 'UNRESOLVED_EPISODE_OR_FACTORS',
        episode_bindings=links,behavior=behaviors[0] if linked else None,
        conditional_alternatives=supported if linked else [],
        role_requirement_status=behaviors[0]['status'] if linked else 'UNRESOLVED',
        reported_self_description=[r['label'] for r in i['current_self_descriptions']],identity_rewritten=False,moral_blame='NOT_INFERRED')
    value_paths=[c for c in v['choice_comparisons'] if c['explanation']!='CHANGE_EXPLANATION_UNRESOLVED']
    value_explanation=dict(source_choice_explanations=value_paths,failure_binding='NOT_ESTABLISHED',
        private_value_change='NOT_INFERRED',reported_preference_revisions=[r for view in v['role_preferences'].values()
            for r in view.get('native_check',{}).get('statements',[]) if r.get('supersedes_id')])
    payload=dict(query=query,actor=actor,assessor=assessor,role=role,context=context,
        failure=f,identity=i,values=v,relationship_interpretation=relation_explanation,
        role_evaluation=role_evaluation,value_change_explanation=value_explanation,policy=_POLICY,
        support_claim_ids=dict(failure=list(failure.claim_ids),identity=list(identity.claim_ids),
            values=list(values.claim_ids)))
    dependencies=tuple(dict.fromkeys((*failure.claim_ids,*identity.claim_ids,*values.claim_ids)))
    claims=list(dependencies)
    if dependencies:
        final=core.claim(semantic.scope,ClaimKind.CONDITIONAL_TOOL_RESULT,dict(operation='RELATIONSHIP_ROLE_VALUE_FAILURE_JOIN',**payload))
        core.support(final,*dependencies,*(r['source_claim_id'] for r in links))
        claims.append(final);payload['dependency_claim_id']=final
    return RelationshipDynamicsResult(identity.source_versions,json.dumps(payload,ensure_ascii=False,sort_keys=True),tuple(claims))


class RelationshipDynamicsWorkspace(SemanticWorkspace):
    """Cache and compare source revisions, with document and observer isolation."""
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.dynamics_cache={}
        self.dynamics_executions={}
        self.revision_kinds={}

    def revise_source(self,source_id,text,*,kind,permitted_observers=()):
        if kind not in ('ANALYST_SOURCE_CORRECTION','NEW_SOURCE_DISCLOSURE'):
            raise ValueError('explicit source revision kind required')
        if kind=='NEW_SOURCE_DISCLOSURE' and source_id in self._documents and not text.startswith(self._documents[source_id][0]+'\n'):
            raise ValueError('new disclosure must append to preserved source')
        prior_acl=self._documents.get(source_id,('',None))[1]
        invalidated=self.put_source(source_id,text,permitted_observers=permitted_observers)
        self.revision_kinds[source_id]=(self._versions[source_id],kind,prior_acl==permitted_observers)
        return invalidated

    def prepare_dynamics(self,query,*,source_id,observer=None):
        key=(source_id,query,observer)
        prior=self.dynamics_cache.get(key)
        if prior:
            try:prior.messages(self)
            except ValueError:pass
            else:return prior
        result=prepare_relationship_dynamics(self,query,source_id=source_id,observer=observer)
        self.dynamics_executions[key]=self.dynamics_executions.get(key,0)+1
        version,kind,stable_acl=self.revision_kinds.get(source_id,(None,'UNSPECIFIED_SOURCE_UPDATE',False))
        # A comparison must not resurrect formerly visible private material after
        # access revocation, or present an analyst correction as character change.
        if prior and stable_acl and version==self._versions[source_id] and result.source_versions:
            old,new=prior.payload,result.payload
            def selected(p):
                return dict(relationship_alternatives=p['relationship_interpretation']['conditional_alternatives'],
                    role_alternatives=p['role_evaluation']['conditional_alternatives'],
                    reported_regard=p['relationship_interpretation']['reported_regard'],
                    reported_self_description=p['role_evaluation']['reported_self_description'],
                    reported_preference_pairs={role:[(r['preferred'],r['over'],r['state']) for r in view.get('native_check',{}).get('statements',[])] for role,view in p['values']['role_preferences'].items()})
            before,after=selected(old),selected(new)
            new['source_revision_comparison']=dict(kind=kind,previous_source_versions=prior.source_versions,
                previous_analyst_snapshot=before,current_analyst_snapshot=after,
                changed_channels=[k for k in before if before[k]!=after[k]],character_change='NOT_INFERRED',
                historical_authority='PRIOR_ANALYST_SNAPSHOT_NOT_CURRENT_SOURCE_TRUTH')
            result=RelationshipDynamicsResult(result.source_versions,json.dumps(new,ensure_ascii=False,sort_keys=True),result.claim_ids)
        self.dynamics_cache[key]=result
        return result
