"""Verified delivery of exact conditional domains and their unresolved frontiers."""
from hcl.kernel.execution import PROTOCOL
from hcl.kernel.types import AnswerClaim, HCLFailure, ResultField, thaw
from hcl.operators.weight_region_model import verify_weight_regions, COVERAGE
from hcl.semantics.judgment_compiler import judgment_qualifications


def weight_region_claim(result):
    try:
        expected = verify_weight_regions(result.values).candidate_delta.new_inferences[0]
        local = result.values.get('local_model'); conditions = ()
        if local is not None:
            assumptions, residuals = judgment_qualifications(result.values['program'])
            qualification = dict(model_id='judgment-proposal:'+result.values['program']['candidate_identity'], version=PROTOCOL,
                dialect='judgment-model-5', domain_assumptions=list(assumptions), fit_residuals=[], unmodeled_observations=list(residuals))
            if thaw(local) != qualification: raise ValueError('weight qualifications changed')
            conditions = tuple('local-model:'+local['model_id']+':assumption:'+str(i) for i in range(len(local['domain_assumptions'])))
        elif result.result_id != expected.result_id: raise ValueError('pure weight identity changed')
        if (result.kind != expected.kind or result.assumption_environments != (*expected.assumption_environments, *conditions)
                or result.premise_ids != expected.premise_ids or result.counterevidence_ids != expected.counterevidence_ids
                or result.rule_version != expected.rule_version or result.coverage != expected.coverage or result.diagnostics):
            raise ValueError('weight metadata changed')
    except (ValueError, KeyError, TypeError, IndexError, StopIteration, RecursionError, OverflowError, HCLFailure):
        raise HCLFailure('FAILED', 'answer', 'WEIGHT_REGION_RESULT_MISMATCH', 'values',
            'The weight analysis differs from its source-bound exact domain, joint branches or coverage proof.') from None
    value = result.values
    if 'reasoned_delivery' in value:
        delivery = value['reasoned_delivery']
        text = delivery['text']
        if value['issues']: text += ' Unresolved: ' + ', '.join(value['issues']) + '.'
        fields = ('reasoned_delivery', 'analyses', 'complete', 'source_versions', 'issues', 'local_evaluations', 'semantic_certified', 'scope')
        return AnswerClaim(text, 'claim:' + result.result_id, tuple(ResultField(result.result_id, name, value[name]) for name in fields),
                           result.assumption_environments, result.counterevidence_ids, COVERAGE)
    lines = ['Conditional exact normalized rational weight-domain analysis. Facts, feasibility, hard norms and real joint argument branches remain fixed.']
    for analysis in value['analyses']:
        lines.append('Domain '+analysis['domain_id']+': robust recommendations '+repr(tuple(analysis['robust_recommended']))+
                     '; possible recommendations '+repr(tuple(analysis['possible_recommended']))+'.')
        if analysis.get('policy_horizon') == 2:
            lines.append('Each alternative is one complete two-step observation-conditioned policy, shared across every dimension and scenario; fixed action-time hard norms constrain every reachable step. All scalar optima remain tied.')
            mentioned = set(analysis['robust_recommended']) | set(analysis['possible_recommended'])
            mentioned.update(a for b in analysis['branches'] for c in b['regions']['cells'] for a in c['recommended'])
            for identity in sorted(mentioned):
                policy = analysis['policy_catalog'][identity]
                lines.append('Policy '+identity+': root '+policy['root_action_id']+'; after observation '+repr(thaw(policy['continuations']))+'.')
        if analysis['decision_rule'] == 'MINIMAX_REGRET':
            lines.append('Declared MINIMAX_REGRET minimizes the largest same-scenario opportunity loss against permitted alternatives, retains all minimizer ties, and assumes no probabilities across scenarios.')
        for branch in analysis['branches']:
            regions = branch['regions']
            lines.append('Joint branch '+str(branch['branch_index'])+' '+regions['status']+'.')
            if regions['domain_status'] == 'EMPTY': lines.append('The declared domain is empty; no action is robust by vacuous intersection.')
            if not regions['recommendation_partition'] and regions['cells']:
                lines.append('Coordinates are the first dimensions in declared order; the final weight is one minus their sum.')
                for cell in regions['cells']:
                    lines.append('Region '+cell['cell_id']+' linear conditions '+repr(thaw(cell['constraints']))+' recommends '+repr(tuple(cell['recommended']))+'.')
            for region in regions['recommendation_partition']:
                left, right = ('[' if region['lower_closed'] else '('), (']' if region['upper_closed'] else ')')
                lines.append('First-dimension weight '+left+region['lower']+', '+region['upper']+right+' recommends '+repr(tuple(region['recommended']))+'.')
        if not analysis['complete']: lines.append('Unresolved branches or resource frontiers prevent a complete robustness claim.')
    lines.append('Declared weights are conditional analysis, never inferred personal preferences or adoption. Hard obligations cannot be compensated by utility. Exact branch cells retain boundary ties, worst-scenario switches, dominance exclusions and alternative value losses.')
    if any(a.get('policy_horizon') == 2 for a in value['analyses']):
        lines[-1] = lines[-1].replace('dominance exclusions', 'dominance comparisons')
    if value['issues']: lines.append('Unresolved: '+', '.join(value['issues'])+'.')
    fields = ('analyses', 'complete', 'source_versions', 'issues', 'local_evaluations', 'semantic_certified', 'scope')
    return AnswerClaim(' '.join(lines), 'claim:'+result.result_id, tuple(ResultField(result.result_id, name, value[name]) for name in fields),
                       result.assumption_environments, result.counterevidence_ids, COVERAGE)
