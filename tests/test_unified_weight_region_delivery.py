"""User-visible reasons are exact result consumption, not a new preference rule."""
from dataclasses import replace
from unittest.mock import patch
import unittest

from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.operators.weight_region_model import WeightRegionOperator, verify_weight_regions, DELIVERY_VERSION
from hcl.runtime.answer import AnswerAssembler
from scripts.witness_unified_policy_weight_regions import propose as policy_propose
from tests import test_unified_weight_regions as base


class ReasonedDeliveryTests(unittest.TestCase):
    setUp = base.WeightRegionRuntimeTests.setUp
    candidate = base.WeightRegionRuntimeTests.candidate
    pure = base.WeightRegionRuntimeTests.pure
    run_candidate = base.WeightRegionRuntimeTests.run_candidate

    def policy(self, rule='EXPECTED', **kwargs):
        return policy_propose(self.f.store.snapshot('s',self.f.owner,self.f.request.source_handles), self.f.request.question, rule, **kwargs)

    def legacy(self, candidate=None, limit=100000):
        proof=self.pure(candidate,limit=limit)
        snapshot=self.f.store.snapshot('s',self.f.owner,self.f.request.source_handles)
        return WeightRegionOperator()._run(snapshot,Issue('domain','judgment.evaluate'),
            replace(self.f.request.budget,max_local_evaluations=limit),thaw(proof.values['program']),reasoned_delivery=False).candidate_delta.new_inferences[0]

    def test_real_answer_names_dimensions_provenance_and_exact_costs(self):
        candidate=self.candidate(); candidate['models'][0]['decisions'][0]['dimensions'][0]['label']='关怀'
        value,result,port,proof=self.run_candidate(candidate,stream=True)
        self.assertEqual(port.attempts,1); self.assertTrue(value['complete'])
        self.assertEqual(value['operator_version'],DELIVERY_VERSION)
        for fragment in ('Weight of x (关怀)', 'ANALYST_CONDITIONAL', 'declared by analyst', 'This analysis does not adopt it',
                         'X minus Y', 'x (关怀)=4', 'y (y)=-6', 'Negative values are costs', '[2/5, 2/5]', 'no new whole-domain ranking'):
            self.assertIn(fragment,result.answer)
        self.assertTrue(any(f.field=='reasoned_delivery' for c in result.claim_records for f in c.used_result_fields))
        self.assertTrue(AnswerAssembler().compact_claim(proof).text.startswith(AnswerAssembler()._claim(proof).text))

    def test_two_step_rejected_alternative_and_guard_query_are_readable(self):
        value,result,_,_=self.run_candidate(self.policy())
        for fragment in ("'r': 'ignore'", 'is PROHIBITED', 'protect-known-risk', 'care (care)=7', 'convenience (convenience)=-3',
                         'factual guards change', 'knows-risk', 'norm argument queries change', 'duty', '3/10'):
            self.assertIn(fragment,result.answer)
        self.assertTrue(value['complete'])
        detail=value['reasoned_delivery']['domains'][0]
        self.assertEqual(detail['revision_conditions']['factual_guards']['knowledge']['reference']['query_id'],'knows-risk')
        self.assertEqual(detail['revision_conditions']['argument_disputes'][0]['query_id'],'duty')

    def test_existing_rules_outcomes_and_regions_do_not_change(self):
        for rule in ('EXPECTED','MAXIMIN','MINIMAX_REGRET'):
            for policy in (False,True):
                candidate=self.policy(rule) if policy else self.candidate()
                candidate['weight_domains'][0]['decision_rule']=rule
                new=self.pure(candidate);old=self.legacy(candidate)
                self.assertEqual(new.values['actual_judgment'],old.values['actual_judgment'])
                self.assertEqual(new.values['analyses'],old.values['analyses'])
                self.assertEqual(new.values['program'],old.values['program'])
                self.assertGreater(new.values['local_evaluations'],old.values['local_evaluations'])
                text=AnswerAssembler()._claim(new).text
                self.assertIn(rule,text)
                verify_weight_regions(old.values)

    def test_expected_distinguishes_declared_distribution_from_single_possible_state(self):
        for candidate in (self.candidate(),self.policy()):
            self.assertFalse(candidate['models'][0]['decisions'][0]['scenarios'])
            value=thaw(self.pure(candidate).values)
            self.assertTrue(value['complete'])
            self.assertFalse(value['reasoned_delivery']['domains'][0]['explicit_scenario_distribution'])
            self.assertIn('No scenario distribution was explicitly declared',value['reasoned_delivery']['text'])
            self.assertNotIn('uses the one explicitly declared scenario distribution',value['reasoned_delivery']['text'])
        value=thaw(self.pure(self.policy(uncertain=True)).values)
        self.assertTrue(value['reasoned_delivery']['domains'][0]['explicit_scenario_distribution'])
        self.assertIn('uses the one explicitly declared scenario distribution',value['reasoned_delivery']['text'])

    def test_legacy_renderers_and_roundtrip_payloads_remain_unchanged(self):
        for candidate in (self.candidate(),self.policy(),self.policy('MINIMAX_REGRET')):
            old=self.legacy(candidate)
            self.assertNotIn('reasoned_delivery',old.values)
            claim=AnswerAssembler().compact_claim(old)
            self.assertIn('First-dimension weight',claim.text)
            self.assertNotIn('Conditional weight-domain reasons',claim.text)
            reopened=codec.loads(codec.dumps(old))
            self.assertEqual(codec.dumps(claim),codec.dumps(AnswerAssembler().compact_claim(reopened)))
            self.assertEqual(codec.dumps(old),codec.dumps(verify_weight_regions(old.values).candidate_delta.new_inferences[0]))

    def test_text_metadata_and_revision_forgery_are_rejected(self):
        proof=self.pure(self.policy())
        for mutate in (
            lambda v:v['reasoned_delivery'].update(text='Adopt forbidden action'),
            lambda v:v['reasoned_delivery']['domains'][0]['dimensions'][0].update(label='fake'),
            lambda v:v['reasoned_delivery']['domains'][0]['framework_origin'].update(declarer='user'),
            lambda v:v['reasoned_delivery']['domains'][0]['revision_conditions'].update(argument_disputes=[]),
            lambda v:v.update(operator_version='s4-two-step-policy-weight-regions-1'),
            lambda v:v['reasoned_delivery'].update(status='PARTIAL'),
        ):
            value=thaw(proof.values);mutate(value)
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=value))

    def test_explanation_budget_and_size_frontiers_withhold_recommendations(self):
        old=self.legacy()
        value=thaw(self.pure(limit=old.values['local_evaluations']+1).values)
        self.assertFalse(value['complete']);self.assertEqual(value['reasoned_delivery']['status'],'PARTIAL')
        self.assertIn('WEIGHT_DELIVERY_WORK_OR_CAPACITY_FRONTIER',value['issues'])
        self.assertTrue(all(not a['possible_recommended'] and not a['robust_recommended'] for a in value['analyses']))
        with patch('hcl.operators.weight_region_delivery.MAX_DELIVERY_BYTES',128):
            value,result,_,_=self.run_candidate()
            self.assertFalse(value['complete']);self.assertIn('resource-limited',result.answer)
            self.assertNotIn(' recommends ',result.answer)

    def test_unknown_and_partial_coverage_keep_their_qualification(self):
        candidate=self.policy();model=candidate['models'][0]
        model['mental']['variables'][1]['initial']=None
        model['decisions'][0]['frameworks'][0]['norms'][0].update(guard_fact_ids=['promise'],argument_query_id=None)
        value,result,_,_=self.run_candidate(candidate)
        self.assertFalse(value['complete']);self.assertIn('UNRESOLVED',result.answer)
        self.assertIn('conditional partial evidence',result.answer)
        self.assertNotIn('is PERMITTED_IN_DECLARED_FRAMEWORK',result.answer)
        self.assertFalse(value['analyses'][0]['possible_recommended'])

    def test_domain_changes_change_explanation_without_fact_changes(self):
        before=self.pure();candidate=self.candidate();d=candidate['weight_domains'][0]
        d['constraints']=base.interval_constraints(d['segment_ids'])
        after=self.pure(candidate)
        self.assertNotEqual(before.values['reasoned_delivery']['text'],after.values['reasoned_delivery']['text'])
        b=before.values['actual_judgment']['models'][0];a=after.values['actual_judgment']['models'][0]
        self.assertEqual(b['decisions'][0]['outcomes'],a['decisions'][0]['outcomes'])
        self.assertEqual(b['actual_interaction']['values']['models'][0]['commitments'],a['actual_interaction']['values']['models'][0]['commitments'])

    def test_new_reopen_recovery_unknown_and_source_acl_contracts(self):
        base.WeightRegionRuntimeTests.test_returned_computed_committed_recovery_never_resends(self)
        base.WeightRegionRuntimeTests.test_secondary_acl_revocation_and_unknown_send_hold(self)


if __name__=='__main__':unittest.main()
