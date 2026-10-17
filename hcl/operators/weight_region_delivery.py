"""Bounded deterministic explanation of existing weight-region certificates.

No new ranking, preference, norm, scenario or solver is introduced here. Every
sentence is reconstructed from the authoritative program and computed results.
"""
import json

from hcl.memory import codec
from hcl.semantics.joint_change_compiler import node_count

VERSION = 'weight-region-reasoned-delivery-1'
MAX_DELIVERY_BYTES = 65536


def display(value):
    # Persisted mappings may reopen in a different insertion order.
    return repr(json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False)))


def revision_summary(frame):
    revision = (frame or {}).get('revision_conditions', {})
    if not revision:
        return {}
    return dict(
        factual_guards={key: {k: v for k, v in fact.items() if k in ('kind', 'role', 'reference', 'possible_values', 'status', 'result_id', 'scope')}
                        for key, fact in revision['factual_guards'].items()},
        argument_disputes=[{k: v for k, v in query.items() if k in ('query_id', 'status', 'positive_accepted', 'opposed_accepted')}
                           for query in revision['argument_disputes']],
        unresolved_argument_facts=revision['unresolved_argument_facts'], change_scope=revision['change_scope'])


def explain_regions(program, actual, analyses, work):
    details, lines = [], []
    size = 0

    def emit(text):
        nonlocal size
        work.spend(1 + len(text.encode('utf-8')) // 64)
        size += len(text.encode('utf-8')) + 1
        if size > MAX_DELIVERY_BYTES:
            raise OverflowError('WEIGHT_DELIVERY_CAPACITY_FRONTIER')
        lines.append(text)

    try:
        emit('Conditional weight-domain reasons. These are declared analytical conditions, not an adoption operation or inferred personal preferences.')
        for analysis in analyses:
            domain = next(d for d in program['weight_domains'] if d['id'] == analysis['domain_id'])
            source, model_id, decision_id, frame_id = domain['binding']['target']
            model = next(m for m in program['base_program']['models'] if m['mental']['source_id'] == source and m['mental']['id'] == model_id)
            declaration = next(d for d in model['decisions'] if d['id'] == decision_id)
            framework = next(f for f in declaration['frameworks'] if f['id'] == frame_id)
            am = next((m for m in (actual or {}).get('models', []) if m['source_id'] == source and m['model_id'] == model_id), None)
            ad = next((d for d in (am or {}).get('decisions', []) if d['decision_id'] == decision_id), None)
            af = next((f for f in (ad or {}).get('frameworks', []) if f['framework_id'] == frame_id), None)
            detail = dict(domain_id=domain['id'], source_id=source, dimensions=[dict(id=d['id'], label=d['label']) for d in declaration['dimensions']],
                framework_origin=framework['origin'], domain_origin=domain['origin'],
                explicit_scenario_distribution=bool(declaration['scenarios']), scenario_scope=(ad or {}).get('scenario_scope', 'UNCOMPUTED'),
                revision_conditions=revision_summary(af))
            work.spend(node_count([detail, analysis]))
            details.append(detail)
            labels = {d['id']: d['label'] for d in detail['dimensions']}
            def dimension(key):
                return key + ' (' + labels[key] + ')'
            def alternative(key):
                policy = analysis.get('policy_catalog', {}).get(key)
                if policy is None:
                    return key
                return 'policy [root ' + policy['root_action_id'] + '; after observation ' + display(policy['continuations']) + ']'
            emit('Domain ' + domain['id'] + ' on source ' + source + ', framework ' + frame_id + ', decision rule ' + analysis['decision_rule'] + '.')
            for name, origin in (('Framework', detail['framework_origin']), ('Weight domain', detail['domain_origin'])):
                emit(name + ' provenance: ' + origin['kind'] + ', declared by ' + origin['declarer'] + ' at ' + str(origin['at']) + ' in ' + origin['frame_kind'] + '; source segments ' + display(origin['segment_ids']) + '. This analysis does not adopt it.')
            emit('Coordinates in order: ' + ', '.join(dimension(d) for d in domain['dimensions']) + '; all weights are nonnegative and sum to one. Domain constraints: ' + display(domain['constraints']) + '.')
            emit('The existing dominance comparisons and declared scalar rule determine these regions; no new whole-domain ranking is inferred.')
            if analysis['decision_rule'] == 'MINIMAX_REGRET':
                emit('MINIMAX_REGRET compares maximum same-scenario opportunity loss against permitted alternatives, without a scenario probability prior; all minimizing ties remain.')
            elif analysis['decision_rule'] == 'MAXIMIN':
                emit('MAXIMIN scalarizes within each shared scenario, then compares the worst scenario score; dimensions do not select separate scenarios or policies.')
            elif detail['explicit_scenario_distribution']:
                emit('EXPECTED uses the one explicitly declared scenario distribution; no probabilities or personal weights are invented.')
            else:
                emit('No scenario distribution was explicitly declared. EXPECTED can use a sole possible state without inventing probabilities; multiple retained states leave EXPECTED unresolved.')
            emit('Domain-wide robust recommendations: ' + display([alternative(a) for a in analysis['robust_recommended']]) + '; possible recommendations: ' + display([alternative(a) for a in analysis['possible_recommended']]) + '.')
            if not analysis['complete']:
                emit('This domain is incomplete: no complete robustness or possible-recommendation claim. Frontier: ' + display(analysis['frontier']) + '.')
            for branch in analysis['branches']:
                regions = branch['regions']
                emit('Joint branch ' + str(branch['branch_index']) + ': ' + regions['status'] + '; norm states ' + display(branch['norm_states']) + '.')
                for row in branch['hard_constraint_reasons']:
                    if row['status'] != 'PERMITTED_IN_DECLARED_FRAMEWORK':
                        emit(alternative(row['action_id']) + ' is ' + row['status'] + '; prohibiting norms ' + display(row['prohibiting_norms']) + '; unresolved norms ' + display(row['unresolved_norms']) + '. Utility cannot override infeasibility or a hard norm; unresolved applicability is not permission.')
                if regions['domain_status'] == 'EMPTY':
                    emit('The declared domain is empty; it confers no vacuous recommendation.')
                if regions['recommendation_partition']:
                    for region in regions['recommendation_partition']:
                        left, right = ('[' if region['lower_closed'] else '('), (']' if region['upper_closed'] else ')')
                        emit('Weight of ' + dimension(domain['dimensions'][0]) + ' ' + left + region['lower'] + ', ' + region['upper'] + right + ' recommends ' + '; '.join(alternative(a) for a in region['recommended']) + '. Boundary ties remain explicit.')
                else:
                    for cell in regions['cells']:
                        emit('Certified region ' + cell['cell_id'] + ' with coordinate constraints ' + display(cell['constraints']) + ' recommends ' + '; '.join(alternative(a) for a in cell['recommended']) + '.')
                # These are same-scenario dimensional differences, not a new
                # whole-domain ordering or independent dimension-wise policy.
                for row in branch['alternative_reasons']:
                    for scenario, differences in row['joint_value_differences'].items():
                        emit('Permitted comparison in scenario ' + scenario + ': ' + alternative(row['left']) + ' minus ' + alternative(row['right']) + ' has dimensional differences ' + ', '.join(dimension(d) + '=' + differences[d] for d in domain['dimensions']) + '. Negative values are costs of the left alternative; positive values are gains. This vector does not by itself rank alternatives across the whole domain.')
                if not branch['conditions_complete'] or not regions['complete']:
                    emit('Retained regions/comparisons are conditional partial evidence; unresolved branches or coverage frontiers prohibit a complete recommendation.')
            revision = detail['revision_conditions']
            emit('Recompute if factual guards change: ' + display(revision.get('factual_guards', {})) + '; or norm argument queries change: ' + display(revision.get('argument_disputes', [])) + '; unresolved argument facts: ' + display(revision.get('unresolved_argument_facts', [])) + '.')
            emit('Crossing the displayed weight boundaries may change the conditional recommendation. ' + revision.get('change_scope', 'Upstream revision conditions are uncomputed; no additional change condition is inferred.'))
        if len(analyses) != len(program['weight_domains']) or not all(a['complete'] for a in analyses):
            emit('Unresolved computation or coverage remains: this is not a complete recommendation across the declared domains.')
        text = ' '.join(lines)
        result = dict(version=VERSION, status='COMPLETE', domains=details, text=text, frontier=[])
        if len(codec.dumps(result)) > MAX_DELIVERY_BYTES:
            raise OverflowError('WEIGHT_DELIVERY_CAPACITY_FRONTIER')
        return result
    except OverflowError:
        # Never silently truncate a decisive objection or manufacture a full
        # recommendation after the explanation's own budget was exhausted.
        return dict(version=VERSION, status='PARTIAL', domains=[],
            text='Reasoned delivery is resource-limited. No complete recommendation is delivered; retained computation remains conditional evidence.',
            frontier=['WEIGHT_DELIVERY_WORK_OR_CAPACITY_FRONTIER'])
