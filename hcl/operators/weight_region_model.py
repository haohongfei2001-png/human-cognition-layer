"""One source-authorized upstream computation, then exact conditional domains."""
from dataclasses import replace
from types import SimpleNamespace

from hcl.kernel.execution import ExecutionBudget
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, Issue, OpResult, Principal, thaw
from hcl.memory import codec
from hcl.operators.judgment import JudgmentWork
from hcl.operators.weight_regions import solve_regions
from hcl.semantics.concept_version_compiler import digest
from hcl.semantics.joint_change_compiler import node_count
from hcl.semantics.weight_region_compiler import verify_weight_program

KIND = 'CONDITIONAL_WEIGHT_REGION_JUDGMENT'
VERSION = 's4-exact-weight-region-judgment-5'
COVERAGE = 'EXACT_FINITE_WEIGHT_DOMAIN_NOT_PREFERENCE_INFERENCE_OR_ADOPTION'
MAX_CERTIFICATE_BYTES = 4 * 1024 * 1024


class WeightRegionOperator:
    def run(self, snapshot, issue, allowance, program):
        try: return self._run(snapshot, issue, allowance, thaw(program))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, StopIteration, ZeroDivisionError):
            raise HCLFailure('INVALID_REQUEST', 'weight_regions', 'INVALID_WEIGHT_REGION', 'weight_domains',
                             'The weight domain violates its exact bounded source and scope contract.') from None

    def _run(self, snapshot, issue, allowance, program):
        from hcl.operators.judgment_model import JudgmentModelOperator
        work = JudgmentWork(allowance.max_local_evaluations)
        # Reserve bounded validation before replaying any compiler or solver.
        # A budget too small to bind the input cannot authorize an unchecked
        # partial certificate. No full verifier runs on this exhausted path.
        validation = node_count(program)
        if validation > work.limit:
            raise HCLFailure('BUDGET_EXHAUSTED', 'weight_regions', 'WEIGHT_VALIDATION_FRONTIER', 'proof',
                             'The remaining allowance cannot verify this source-bound weight program.')
        work.spend(validation)
        verify_weight_program(program, snapshot, allowance)
        analyses, issues, environments, counters = [], [], set(), set()
        actual = None
        try:
            # Reuse the same authoritative runner once. No alternative fact,
            # feasibility, commitment or independently invented norm branches.
            operation = JudgmentModelOperator()._run(snapshot, issue,
                replace(allowance, max_local_evaluations=work.limit-work.used), program['base_program'])
            work.spend(operation.resource_usage['local_evaluations'])
            inference = operation.candidate_delta.new_inferences[0]
            actual = thaw(inference.values)
            environments.update(inference.assumption_environments); counters.update(inference.counterevidence_ids)
            issues.extend(operation.issues)
            for domain in program['weight_domains']:
                work.spend()
                analysis = dict(domain_id=domain['id'], domain_identity=domain['domain_identity'], target=domain['binding']['target'],
                    decision_rule=domain['decision_rule'], origin=domain['origin'], branches=[], complete=False,
                    robust_recommended=[], unique_robust_recommended=[], possible_recommended=[], frontier=[],
                    fixed_upstream_result_id=inference.result_id, adoption_authorized=False)
                analyses.append(analysis)
                model = next((m for m in actual['models'] if [m['source_id'], m['model_id']] == domain['binding']['target'][:2]), None)
                decision = None if model is None else next((d for d in model['decisions'] if d['decision_id'] == domain['decision_id']), None)
                frame = None if decision is None else next((f for f in decision['frameworks'] if f['framework_id'] == domain['framework_id']), None)
                if frame is None or frame['status'] != 'COMPUTED' or model['actual_argument'] is None:
                    analysis['frontier'].append('FIXED_UPSTREAM_UNCOMPUTED'); continue
                theory = model['actual_argument']['values']['models'][0]
                upstream_complete = not (model['frontier'] or decision['frontier'] or theory['frontier'] or theory['strict_conflicts'] or theory['inactive_assumptions'])
                outcomes = {row['action_id']: row for row in decision['outcomes']}
                for index, branch in enumerate(frame['branches']):
                    work.spend(1+len(outcomes))
                    permitted = {e['action_id'] for e in branch['result']['eligibility'] if e['status'] == 'PERMITTED_IN_DECLARED_FRAMEWORK'}
                    vectors = {a: {s['scenario_id']: s['vector'] for s in outcomes[a]['scenarios']} for a in sorted(permitted)}
                    if domain['decision_rule'] == 'EXPECTED' and any(len(row['scenarios']) != 1 for row in decision['outcomes'] if row['feasible']):
                        analysis['frontier'].append('EXPECTED_PROBABILITIES_UNSPECIFIED'); break
                    regions = solve_regions(domain, vectors, domain['dimensions'], domain['decision_rule'], work)
                    conditions_complete = upstream_complete and 'UNRESOLVED' not in branch['states'].values() and branch['basis'] != 'CONSERVATIVE_UNRESOLVED'
                    reasons = []
                    for left, right in combinations_for_reasons(vectors, domain['dimensions'], work): reasons.append(dict(left=left[0], right=right[0], joint_value_differences=left[1], scope='LOSSES_AND_GAINS_REMAIN_CONDITIONAL_ON_DECLARED_WEIGHTS'))
                    output = dict(branch_index=index, basis=branch['basis'], extension=branch['extension'], norm_states=branch['states'],
                        eligibility=branch['result']['eligibility'], regions=regions, conditions_complete=conditions_complete,
                        complete=conditions_complete and regions['complete'], alternative_reasons=reasons,
                        hard_constraint_reasons=branch['result']['eligibility'])
                    # Bound proof growth before retaining another branch.
                    if len(codec.dumps([program, actual, analyses, output])) > MAX_CERTIFICATE_BYTES-262144:
                        analysis['frontier'].append('WEIGHT_AUDIT_CAPACITY_FRONTIER'); raise OverflowError('WEIGHT_AUDIT_CAPACITY_FRONTIER')
                    analysis['branches'].append(output)
                    analysis['frontier'].extend(regions['frontier'])
                    if not conditions_complete: analysis['frontier'].append('FIXED_JOINT_BRANCH_UNRESOLVED')
                branches = analysis['branches']
                complete = (bool(branches) and len(branches) == len(frame['branches']) and all(b['complete'] for b in branches))
                work.spend(1+node_count([b['regions']['robust_recommended'] for b in branches]))
                analysis['complete'] = complete
                if complete and all(b['regions']['domain_status'] == 'NONEMPTY' for b in branches):
                    analysis['robust_recommended'] = sorted(set.intersection(*(set(b['regions']['robust_recommended']) for b in branches)))
                    analysis['unique_robust_recommended'] = sorted(set.intersection(*(set(b['regions']['unique_robust_recommended']) for b in branches)))
                    analysis['possible_recommended'] = sorted({a for b in branches for a in b['regions']['possible_recommended']})
                issues.extend(analysis['frontier'])
        except OverflowError:
            issues.append('WEIGHT_WORK_OR_PROOF_FRONTIER')
        complete = len(analyses) == len(program['weight_domains']) and all(a['complete'] for a in analyses)
        if not complete: issues.append('WEIGHT_REGIONS_CONDITIONAL_FRONTIER')
        values = dict(operator_version=VERSION, issue_id=issue.issue_id, rule_version=snapshot.rule_version,
            source_versions=dict(snapshot.source_versions), program=program, actual_judgment=actual,
            analyses=analyses, complete=complete, execution_allowance=work.limit, local_evaluations=work.used,
            issues=sorted(set(issues)), semantic_certified=False, scope=COVERAGE)
        result = InferenceResult('weight-region:'+digest([issue.issue_id, values]), KIND, values,
            tuple(sorted(environments)), tuple(sorted(snapshot.source_versions)), tuple(sorted(counters)), snapshot.rule_version, COVERAGE)
        if len(codec.dumps(result)) > MAX_CERTIFICATE_BYTES:
            raise HCLFailure('BUDGET_EXHAUSTED', 'weight_regions', 'WEIGHT_AUDIT_CAPACITY', 'proof', 'The exact weight proof exceeds the unchanged audit capacity.')
        return OpResult('judgment.weight_regions', VERSION, snapshot.source_versions, ('append_inference',),
            (result.result_id,), tuple(sorted(set(issues))), dict(local_evaluations=work.used), (),
            Delta(snapshot.session_id, snapshot.principal, snapshot.revision, snapshot.access_epoch, snapshot.rule_version, snapshot.source_versions, (result,)))


def combinations_for_reasons(vectors, ids, work):
    from fractions import Fraction
    from itertools import combinations
    from hcl.operators.agency import encoded
    for left, right in combinations(vectors, 2):
        differences = {}
        for scenario in vectors[left]:
            work.spend(1+len(ids))
            differences[scenario] = {d: encoded(Fraction(vectors[left][scenario][d])-Fraction(vectors[right][scenario][d])) for d in ids}
        yield (left, differences), (right, None)


def verify_weight_regions(values):
    data = thaw(values); data.pop('local_model', None)
    if type(data['execution_allowance']) is not int or not 0 <= data['execution_allowance'] <= 10000000: raise ValueError('bounded weight certificate required')
    host = data['program']['host_context']
    snapshot = SimpleNamespace(session_id=host['session_id'], principal=Principal(**host['principal']), revision=0,
        access_epoch=0, rule_version=data['rule_version'], source_versions=data['source_versions'])
    expected = WeightRegionOperator()._run(snapshot, Issue(data['issue_id'], 'judgment.evaluate'),
        replace(ExecutionBudget(), max_local_evaluations=data['execution_allowance']), data['program'])
    if codec.canonical(thaw(expected.candidate_delta.new_inferences[0].values)) != codec.canonical(data):
        raise ValueError('weight domain, exact coverage or boundary certificate changed')
    return expected
