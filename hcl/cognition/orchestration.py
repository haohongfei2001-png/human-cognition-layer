"""First universal-entry slice: actual adapter outcomes, complete inventory, explicit gaps.

This is not a claim that every registered capability has an ordinary-input adapter.
The shared source reader executes before composition; unsupported input never becomes Base.
"""
import hashlib
from hcl.v1.capabilities import CAPABILITIES, CapabilityType, resolve_dependencies

_ADAPTERS = {
    'information_state': ('EXISTING_NAMED_OBSERVATION_CHECKER', 'information_treatment', 'checked_operations'),
    'belief': ('B01_EXISTING_MODAL_SCOPE_CHECKER', 'epistemic_treatment', 'checked_mental_expressions'),
    'intention': ('C01_EXISTING_GOAL_PLAN_OPPORTUNITY_CHECKER', 'agency_treatment', 'checked_operations'),
    'perspective': ('B02_EXISTING_REPORTED_ACCESS_CHECKER', 'communication_treatment', 'checked_operations'),
    'causal': ('C03_EXISTING_BELIEF_PLAN_MODEL_JOIN', 'plan_feasibility_treatment', 'checked_plans'),
}
_FOUNDATION = frozenset(('evidence', 'provenance', 'temporal', 'actor_source', 'source_visibility', 'uncertainty'))


def compose_plan(query, source, source_id, version, preparation):
    """Use executed typed adapter receipts, never source labels or benchmark IDs.

    Task interpretation is explicitly bounded: ordinary reader analysis of the
    supplied question, with typed semantic candidate admission. An unimplemented
    task/capability mapping is recorded as such, not guessed from keywords.
    """
    inventory=[];operations=[];gaps=[]
    for cid, capability in CAPABILITIES.items():
        entry=dict(capability_id=cid,kind=capability.kind.value,
                   implementation=capability.implementation,dependencies=list(capability.dependencies))
        if capability.kind == CapabilityType.INACTIVE:
            entry.update(status='INACTIVE_NOT_EXECUTED', reason=capability.activation_policy)
        elif cid in _FOUNDATION:
            entry.update(status='SOURCE_SCOPE_FOUNDATION', reason='BOUND_TO_SHARED_SOURCE_ROOT; NO_PRIVATE_OR_CALENDAR_TRUTH')
        elif cid in _ADAPTERS:
            mechanism,key,count_key=_ADAPTERS[cid]
            observed=preparation.get(key,{})
            count=observed.get(count_key,0)
            if type(count)is not int or count<0:raise ValueError('invalid adapter execution count')
            enabled=bool(observed.get('enabled',True))
            row=dict(capability_id=cid, mechanism=mechanism, checked_operations=count,
                     status='CHECKED_RESULT' if count else 'NO_CHECKED_RESULT',
                     reason=(None if count else observed.get('coverage_failure') or 'NO_ADMITTED_TYPED_PREMISES'),
                     adapter_enabled=enabled, evidence_source=key)
            operations.append(row)
            entry.update(status=row['status'],reason=row['reason'],adapter=mechanism,
                         coverage='BOUNDED_ADAPTER_ONLY; NOT_ALL_REGISTERED_FAMILY_BEHAVIOR')
        elif cid in ('goal','motivation_evidence'):
            entry.update(status='PARTIAL_VIA_INTENTION_ADAPTER',reason='ONLY_EXPLICIT_REPORTED_AGENCY; NO_INVENTED_MOTIVE')
        else:
            entry.update(status='ORDINARY_ENTRY_INTEGRATION_GAP',reason='IMPLEMENTED_MODULE_NOT_YET_CALLABLE_FROM_THIS_ORDINARY_ENTRY')
            gaps.append(cid)
        inventory.append(entry)
    actual=sum(op['checked_operations'] for op in operations)
    return dict(schema='hcl-universal-entry-first-slice-v1',entry='HCL_ORDINARY_ORCHESTRATION',
        task=dict(question=query,interpretation='BOUNDED_ORDINARY_READER_ANALYSIS',
                  understanding_limit='TYPED_SOURCE_CANDIDATE_ADMISSION; GENERAL_TASK_PLANNER_NOT_COMPLETE'),
        source_binding=dict(source_id=source_id,version=version,
                            sha256=hashlib.sha256(source.encode()).hexdigest(),complete_source_retained=True),
        inventory=inventory,operations=operations,integration_gaps=gaps,
        selected_dependency_closure=list(resolve_dependencies([op['capability_id'] for op in operations if op['checked_operations']])),
        partial_family_integrations=[cid for cid in _ADAPTERS if cid!='information_state'],
        checked_operations=actual,checked_treatment_present=bool(actual),base_bypass=False,
        complete_capability_integration=False,
        composition_status='CHECKED_RESULTS_WITH_LIMITS' if actual else 'HCL_EXPLICIT_CAPABILITY_INSUFFICIENCY',
        source_review='EXACT_SOURCE_ANCHORS_ONLY; SEMANTIC_SUPPORT_UNASSESSED',
        provider_calls=0)


def wire_plan(plan):
    """The final input receives genuine outcomes and limits, not a fake success trace."""
    return {key:plan[key] for key in ('schema','entry','operations','integration_gaps',
        'selected_dependency_closure','partial_family_integrations','checked_operations','checked_treatment_present','base_bypass','complete_capability_integration',
        'composition_status','source_review')}


def prepare_information_operation(workspace, query, source_id):
    """One genuine additional registry path, selected internally from the question."""
    from hcl.v1.information_state import information_query, check_information_state
    from .core import Scope, ClaimKind
    selected = information_query(query)
    if selected is None:
        return None, dict(enabled=False, checked_operations=0, coverage_failure='NO_BOUND_ACTOR_OBJECT_QUERY'), []
    source=workspace._documents[source_id][0]
    if len(source)>16000:
        return None, dict(enabled=False,checked_operations=0,coverage_failure='NAMED_OBSERVATION_SOURCE_BUDGET_EXCEEDED'), []
    result=check_information_state(source,*selected)
    claim=workspace.core.claim(Scope(source_ids=(source_id,)),ClaimKind.CONDITIONAL_TOOL_RESULT,
        dict(operation='EXISTING_NAMED_OBSERVATION_CHECKER',source_id=source_id,
             source_version=workspace._versions[source_id],result=result))
    workspace.core.support(claim,workspace._spans[source_id])
    count=result['checked_observation_count']
    return dict(result,source_id=source_id,source_version=workspace._versions[source_id],claim_id=claim), dict(
        enabled=True,checked_operations=count,coverage_failure=None if count else result['status']), [claim]
