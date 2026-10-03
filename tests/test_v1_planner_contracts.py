"""Self-authored interface contracts, distinct from model selection/efficacy tests."""
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.capability_catalog import CATALOG,validate_catalog
from hcl.cognition.universal_entry import PLANNER_POLICY
from tests.test_v1_universal_question import Stub,operation,plan,run

VALVE='\n'.join(['Kellan said, "I want to inspect the gauge."',
    'Kellan said, "I plan to open the valve in order to inspect the gauge."',
    'Kellan said, "At the time, I knew about the valve."',
    'Kellan said, "At the time, I could open the valve."',
    'Kellan said, "I opened the valve."'])
ARGUMENT='Narrator: In design, Ena could revise.\nEna: In design, I conclude the design is flexible because Ena could revise.'
RULE='For this analysis, responsibility requires causal contribution and control.'
EPISODE='Lumen: I opened the sluice.\nNarrator: The pipes broke.\nNarrator: Lumen opening the sluice caused the pipes to break.'


class PlannerContractTests(unittest.TestCase):
    def test_all_inventory_retained_and_current_adapters_have_contracts(self):
        self.assertTrue(validate_catalog());self.assertEqual(len(CATALOG),40)
        ready={cid for cid,c in CATALOG.items()if c.entry_contract is not None}
        self.assertEqual(ready,{'B01','B02','C01','C02','C03','C04','G01','G02','G03','G04','G05'})
        for cid,c in CATALOG.items():
            self.assertEqual(c.entry_readiness=='BOUNDED_ORDINARY_ADAPTER',c.entry_contract is not None)
            if c.entry_contract:
                self.assertLessEqual(c.entry_contract.minimum_sources,c.entry_contract.maximum_sources)
                self.assertLessEqual(c.entry_contract.maximum_sources,8)
        with self.assertRaises(Exception):CATALOG['G05'].entry_contract.question_origin='OPERATION_QUESTION'

    def test_exact_contracts_reach_actual_planner_messages_and_do_not_force_operations(self):
        session=UniversalHCL();stub=Stub(plan());r=run(session,'Explain coordination limits in an orchestra.',stub)
        payload=json.loads(stub.calls[0][1][-1]['content'])
        self.assertEqual(payload['capability_inventory'],json.loads(json.dumps([asdict(c)for c in CATALOG.values()])))
        self.assertEqual(r['operations'],[]);self.assertEqual(r['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertIn('empty operations array',PLANNER_POLICY)
        self.assertNotIn('Use C02 for supported',PLANNER_POLICY)
        self.assertIn('question_origin',PLANNER_POLICY)
        self.assertEqual(r['provider_calls'],0)

    def test_question_origin_contract_matches_dispatch(self):
        operation_question={'B01','B02','C01','C02','C03','C04'}
        for cid,c in CATALOG.items():
            if c.entry_contract:
                self.assertEqual(c.entry_contract.question_origin,
                    'OPERATION_QUESTION'if cid in operation_question else 'ORIGINAL_USER_REQUEST')

    def test_c02_documented_internal_form_performs_real_conditional_check(self):
        session=UniversalHCL();session.put_source('maintenance',VALVE)
        original='What can explain Kellan opening the valve, and what remains unresolved?'
        stub=Stub(plan(operation('C02','Why did Kellan open the valve?',['maintenance'])))
        r=run(session,original,stub);op=r['operations'][0]
        self.assertEqual(op['status'],'C02_EXECUTED');self.assertTrue(op['executed'])
        self.assertIn('CONDITIONALLY_SUPPORTED',{x['disposition']for x in op['result']['explanations']})
        self.assertEqual(op['result']['winning_motive'],'NOT_INFERRED')
        final=json.loads(stub.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'],original);self.assertEqual(final['sources'][0]['text'],VALVE)
        self.assertEqual(CATALOG['C02'].entry_contract.question_forms,('Why did <Actor> <verb and object>?',))

    def test_c02_freeform_stays_rejected_instead_of_relaxing_retained_parser(self):
        session=UniversalHCL();session.put_source('maintenance',VALVE)
        r=run(session,'What explanations are supported?',Stub(plan(operation('C02','List competing explanations for Kellan.',['maintenance']))))
        self.assertEqual(r['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        self.assertIn('freeform',CATALOG['C02'].entry_contract.question_contract)

    def test_g02_distinct_actor_single_source_and_duplicate_mentions(self):
        session=UniversalHCL();session.put_source('episode',EPISODE)
        binding=dict(role='actor',source_id='episode',start=0,quote='Lumen')
        good=run(session,RULE,Stub(plan(operation('G02','Apply the original rule.',['episode'],[binding]))))
        self.assertEqual(good['operations'][0]['status'],'G02_EXECUTED')
        self.assertEqual(good['operations'][0]['result']['individuals'][0]['status'],'SOURCE_FACTORS_CHECKED')
        repeated=dict(binding,start=EPISODE.index('Lumen',1))
        bad=run(session,RULE,Stub(plan(operation('G02','Apply the original rule.',['episode'],[binding,repeated]))))
        self.assertEqual(bad['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        self.assertIn('exactly once',CATALOG['G02'].entry_contract.binding_contract)

    def test_g02_distinct_actors_cannot_share_one_episode_source(self):
        source=EPISODE+'\nNeri: I stayed outside.';session=UniversalHCL();session.put_source('episode',source)
        bindings=[dict(role='actor',source_id='episode',start=source.index(a),quote=a)for a in ('Lumen','Neri')]
        r=run(session,RULE,Stub(plan(operation('G02','Apply original rule.',['episode'],bindings))))
        self.assertEqual(r['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        self.assertIn('distinct selected source ID',CATALOG['G02'].entry_contract.binding_contract)

    def test_g02_original_rule_missing_is_not_made_a_factor_check(self):
        session=UniversalHCL();session.put_source('episode',EPISODE)
        binding=dict(role='actor',source_id='episode',start=0,quote='Lumen')
        r=run(session,'What does this establish?',Stub(plan(operation('G02',RULE,['episode'],[binding]))))
        row=r['operations'][0]['result']['individuals'][0]
        self.assertEqual(row['status'],'NO_ADOPTED_INDIVIDUAL_RULE');self.assertIsNone(row['checked'])
        self.assertIn('checked=null',CATALOG['G02'].entry_contract.result_limits)

    def test_g01_original_caller_rule_and_source_rule_remain_distinct(self):
        a=UniversalHCL();r=run(a,RULE,Stub(plan(operation('G01','Prepare conditions.',[]))))
        self.assertGreater(r['operations'][0]['executable_premise_count'],0)
        b=UniversalHCL();b.put_source('policy','Institution archive policy: responsibility requires control.')
        r=run(b,'Which conditions are stated?',Stub(plan(operation('G01',RULE,['policy']))))
        self.assertEqual(r['operations'][0]['executable_premise_count'],0)
        self.assertEqual(CATALOG['G01'].entry_contract.minimum_sources,0)

    def test_g05_requires_the_original_single_factor_question_and_preserves_source(self):
        original='If Ena could revise were false, what changes?'
        session=UniversalHCL();session.put_source('design',ARGUMENT)
        stub=Stub(plan(operation('G05','A rewritten operation cannot supply the hypothesis.',['design'])))
        r=run(session,original,stub);row=r['operations'][0]
        self.assertEqual(row['status'],'G05_SENSITIVITY_PREPARED');self.assertEqual(row['variant_count'],1)
        self.assertEqual(row['result']['question'],original);self.assertFalse(row['result']['source_modified'])
        self.assertEqual(json.loads(stub.calls[-1][1][-1]['content'])['sources'][0]['text'],ARGUMENT)
        bad=run(session,'How might the design differ?',Stub(plan(operation('G05',original,['design']))))
        self.assertEqual(bad['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        self.assertEqual(len(CATALOG['G05'].entry_contract.question_forms),3)

    def test_single_source_contracts_do_not_merge_domains(self):
        for cid in ('B01','B02','C01','C02','C03','C04','G03','G04','G05'):
            self.assertEqual((CATALOG[cid].entry_contract.minimum_sources,CATALOG[cid].entry_contract.maximum_sources),(1,1))
            session=UniversalHCL();session.put_source('a',ARGUMENT);session.put_source('b',ARGUMENT)
            result=session._execute(operation(cid,'Why did Ena open the folder?',['a','b']),'If Ena could revise were false, what changes?')
            self.assertFalse(result['executed'])

    def test_unsupported_catalog_entries_remain_explicitly_unavailable(self):
        session=UniversalHCL();session.put_source('s',ARGUMENT)
        row=session._execute(operation('H01','Plan the question.',['s']),'What is established?')
        self.assertEqual(row['status'],'RETAINED_IMPLEMENTATION_REQUIRES_ENTRY_ADAPTER')
        self.assertIsNone(CATALOG['H01'].entry_contract)


if __name__=='__main__':unittest.main()
