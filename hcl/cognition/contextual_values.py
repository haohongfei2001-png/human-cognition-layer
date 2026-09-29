"""Context changes, role-scoped preferences and conditional partial orders."""
from dataclasses import dataclass
import itertools
import json
import re

from hcl.v1.cg04 import prepare_preference_narrative, check_preferences
from .core import ClaimKind
from .identity_roles import prepare_identity_roles

_TERM = r'[A-Za-z][A-Za-z0-9_-]{0,31}'
_QUERY = re.compile(rf"Compare (?P<actor>{_TERM})'s contextual preferences in (?P<context>{_TERM})\.")
_ROLE = re.compile(rf'As (?P<role>{_TERM}) in (?P<context>{_TERM}), I (?:now )?prefer ')
_CONDITION = re.compile(rf'In (?P<context>{_TERM}), (?P<key>{_TERM}) is (?P<value>true|false)\.')
_CHANGE = re.compile(rf'In (?P<context>{_TERM}), (?P<key>{_TERM}) is now (?P<value>true|false) instead of (?P<old>true|false)\.')
_CHOICE = re.compile(rf'In (?P<context>{_TERM}), (?P<actor>{_TERM}) chose (?P<value>{_TERM}) as (?P<role>{_TERM})\.')
_POLICY = ('Separate source-reported contextual preference, role, condition and choice. '
    'A choice consistent with a preference does not prove motivation or endorsement. '
    'Transitive paths are conditional on the analyst transitivity assumption, never '
    'new self-reports; incomparable values remain unordered. Conflicts prevent a '
    'forced total order. Context change may explain a different choice without value '
    'revision. Source order is not character knowledge or verified event chronology. '
    'No global weights, actual value change or moral winner is inferred.')


@dataclass(frozen=True)
class ContextualValues:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=96000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded values context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s,v in self.source_versions):
            raise ValueError('values source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('values support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=self.payload_json)]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('values context budget exceeded')
        return messages


def _order(checked):
    # Do not promote narrator/third-party preference attribution to self expression.
    active = [r for r in checked['statements'] if r['state'] == 'APPLICABLE_SOURCE_CLAIM' and r['authority'] == 'DIRECT_SELF_REPORT']
    values = sorted({x for r in checked['statements'] if r['state'] != 'OTHER_SCOPE' and r['authority'] == 'DIRECT_SELF_REPORT' for x in (r['preferred'],r['over'])})
    edges = {}
    for r in active:
        edges.setdefault(r['preferred'], []).append((r['over'], r['statement_id']))
    paths = {}
    def visit(origin, node, seen, ids):
        for other, statement in edges.get(node, []):
            candidate = ids + [statement]
            paths.setdefault((origin,other), candidate)
            if other not in seen:
                visit(origin, other, seen | {other}, candidate)
    for value in values:
        visit(value, value, {value}, [])
    conflicts = [dict(values=[a,b], forward=paths[a,b], reverse=paths[b,a])
        for a,b in itertools.combinations(values, 2) if (a,b) in paths and (b,a) in paths]
    return dict(assumption='LOCAL_TRANSITIVITY_FOR_ANALYST_COMPARISON_NOT_REPORTED_PRIVATE_ORDER',
        status='CONFLICTING_DIRECTED_RELATION' if conflicts else 'CONDITIONAL_PARTIAL_ORDER',
        strict_comparisons=[dict(preferred=a, over=b, statement_path=ids,
            authority='EXPLICIT_PAIR' if len(ids)==1 else 'CONDITIONAL_TRANSITIVE_PATH')
            for (a,b),ids in sorted(paths.items()) if a!=b and (b,a) not in paths],
        conflicts=conflicts, incomparable_pairs=[[a,b] for a,b in itertools.combinations(values,2)
            if (a,b) not in paths and (b,a) not in paths], global_weights='NOT_INFERRED')


def prepare_contextual_values(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query,str) and len(query)<=8000 else None
    if not match or match['actor'] == 'Narrator':
        raise ValueError('bounded actor/context query required')
    actor, context = match['actor'], match['context']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, rows = workspace.core, []
    versions = tuple((s,workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    for candidate in semantic.candidate_ids:
        c = core.claims[candidate].content
        if c['kind']!='event' or c['validation']['semantic_support']!='BOUNDED_LITERAL_FORM':
            continue
        row, span = c['proposal'], core.spans[c['source_span_id']]
        narrator = row['speaker_surface']=='Narrator' and span.quote.startswith('Narrator:')
        if row['assertion_scope']!='SOURCE_REPORT' or (not narrator and row['speaker_candidates']!=[row['speaker_surface']]):
            continue
        rows.append(dict(candidate_id=candidate, quote=span.quote, order=span.start,
            speaker=row['speaker_surface'], body=row['utterance'], narrator=narrator))
    rows.sort(key=lambda r:r['order'])
    if len(rows)>20:
        raise ValueError('values source budget exceeded')
    # The same derived line is checked by the historical native preference runtime.
    conditions, preferences, choices, changes, diagnostics, role_names = [], [], [], [], [], set()
    invalid_condition_keys = set()
    def snapshot(role):
        if invalid_condition_keys:
            return dict(status='UNRESOLVED_CONDITION_REVISION', order=None, source_bindings=[])
        selected = sorted([*preferences,*conditions], key=lambda r:r['order'])
        derived = '\n'.join(r['derived_line'] for r in selected)
        if not derived:
            return dict(status='NO_EXPLICIT_PREFERENCE', order=None, source_bindings=[])
        prep = prepare_preference_narrative(derived,actor,role,context)
        bindings = [dict(source_claim_id=r['candidate_id'], original_quote=r['quote'], derived_line=r['derived_line']) for r in selected]
        if prep.case is None:
            return dict(status='UNRESOLVED_NATIVE_PREPARATION', failure=prep.failure, order=None, source_bindings=bindings)
        checked = check_preferences(prep.case,prep.events)
        return dict(status='CHECKED', native_check=checked, order=_order(checked), source_bindings=bindings)
    for row in rows:
        body = row['body']
        pref = _ROLE.match(body)
        if row['speaker']==actor and pref and pref['context']==context:
            role_names.add(pref['role'])
            preferences.append(dict(row,derived_line=f'{actor}: {body}'))
        # Keep third-party claims in the original source, without turning them into
        # self expressions or rejecting a valid direct report from a different role.
        cond, change = _CONDITION.fullmatch(body), _CHANGE.fullmatch(body)
        if row['narrator'] and cond and cond['context']==context:
            conditions.append(dict(row,key=cond['key'],value=cond['value'],derived_line='Narrator: '+body))
        if row['narrator'] and change and change['context']==context:
            prior = [c for c in conditions if c['key']==change['key']]
            if len(prior)!=1 or prior[0]['value']!=change['old'] or change['value']==change['old']:
                diagnostics.append(dict(source_claim_id=row['candidate_id'],status='CONDITION_REVISION_ANCHOR_UNRESOLVED'))
                # An unresolved update is evidence of uncertainty; do not retain a
                # false appearance of a settled current condition.
                invalid_condition_keys.add(change['key'])
            else:
                old = prior[0]
                conditions.remove(old)
                conditions.append(dict(row,key=change['key'],value=change['value'],derived_line=f"Narrator: In {context}, {change['key']} is {change['value']}."))
                changes.append(dict(source_claim_id=row['candidate_id'],prior_source_claim_id=old['candidate_id'],key=change['key'],old=change['old'],new=change['value'],order=row['order']))
        choice = _CHOICE.fullmatch(body)
        if row['narrator'] and choice and (choice['actor'],choice['context'])==(actor,context):
            role_names.add(choice['role'])
            state = snapshot(choice['role'])
            order = state.get('order') or {}
            comparisons = order.get('strict_comparisons',[])
            supported = any(r['preferred']==choice['value'] for r in comparisons)
            opposed = any(r['over']==choice['value'] for r in comparisons)
            choices.append(dict(row,role=choice['role'],value=choice['value'],preference_snapshot=state,
                alignment='CONFLICT_UNRESOLVED' if order.get('conflicts') else 'SUPPORTED_BY_LOCAL_COMPARISON' if supported and not opposed else
                'OPPOSED_BY_LOCAL_COMPARISON' if opposed and not supported else 'PARTIAL_OR_UNKNOWN',
                actual_motive='NOT_ESTABLISHED'))
    if len(role_names)>2:
        raise ValueError('at most two contextual preference roles')
    views = {role:snapshot(role) for role in sorted(role_names)}
    role_views = {role:prepare_identity_roles(workspace, f"How does {actor}'s self-description relate to the {role} role in {context}?",source_id=source_id,observer=observer).payload for role in sorted(role_names)}
    comparisons = []
    for first,second in zip(choices, choices[1:]):
        intervening = [c for c in changes if first['order']<c['order']<second['order']]
        revisions = [r for r in preferences if first['order']<r['order']<second['order'] and 'I now prefer ' in r['body']]
        def pref_signature(choice):
            return [(r['quote'],r['state']) for r in choice['preference_snapshot'].get('native_check',{}).get('statements',[])]
        old_sig,new_sig = pref_signature(first),pref_signature(second)
        conditional = (first['value']!=second['value'] and first['role']==second['role'] and intervening and not revisions and
            first['alignment']==second['alignment']=='SUPPORTED_BY_LOCAL_COMPARISON' and
            [q for q,s in old_sig]==[q for q,s in new_sig] and old_sig!=new_sig)
        comparisons.append(dict(first_choice_source_id=first['candidate_id'],second_choice_source_id=second['candidate_id'],
            explanation='CONTEXT_CHANGE_SUPPORTED_WITHOUT_PREFERENCE_REVISION' if conditional else
                'ROLE_SCOPE_CHANGED_NOT_GLOBAL_VALUE_REVISION' if first['role']!=second['role'] else
                'EXPLICIT_PREFERENCE_REVISION_REQUIRES_NATIVE_CHECK' if revisions else 'CHANGE_EXPLANATION_UNRESOLVED',
            condition_changes=intervening,actual_value_change='NOT_INFERRED'))
    role_conflicts = []
    for left,right in itertools.combinations(sorted(views),2):
        a = (views[left].get('order') or {}).get('strict_comparisons',[])
        b = (views[right].get('order') or {}).get('strict_comparisons',[])
        for x in a:
            for y in b:
                if (x['preferred'],x['over'])==(y['over'],y['preferred']):
                    role_conflicts.append(dict(roles=[left,right],values=[x['preferred'],x['over']],status='ROLE_SCOPED_TENSION_NOT_GLOBAL_INCOHERENCE'))
    payload = dict(query=query,actor=actor,context=context,original_source=original,role_preferences=views,
        current_role_identity_views=role_views,choices=choices,choice_comparisons=comparisons,
        explicit_condition_changes=changes,cross_role_tensions=role_conflicts,diagnostics=diagnostics,
        private_values='NOT_ESTABLISHED',global_weights='NOT_INFERRED',policy=_POLICY)
    claims=[]
    if rows:
        final=core.claim(semantic.scope,ClaimKind.CONDITIONAL_TOOL_RESULT,dict(operation='CONTEXTUAL_CHOICE_PARTIAL_ORDER',**payload))
        core.support(final,*(r['candidate_id'] for r in rows))
        claims.append(final)
        payload['dependency_claim_id']=final
    return ContextualValues(versions,json.dumps(payload,ensure_ascii=False,sort_keys=True),tuple(claims))
