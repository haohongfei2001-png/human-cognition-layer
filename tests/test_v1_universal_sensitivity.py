"""Provider-free G05 wiring and conditional-authority checks, not model efficacy."""
import hashlib
import json
import unittest
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.argument_sensitivity import ArgumentSensitivityWorkspace
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.core import ClaimKind
from tests.test_v1_universal_question import Stub, operation, plan, run
from tests.test_v1_wave_g05 import TEXT as SOURCE, QUERY as QUESTION


class UniversalSensitivityTests(unittest.TestCase):
    def execute(self, source=SOURCE, question=QUESTION, interpreted='Compare the argument paths.', callback=None):
        session=UniversalHCL();session.put_source('scene',source)
        stub=Stub(plan(operation('G05',interpreted,['scene'])),callback=callback)
        return session,stub,run(session,question,stub)

    def test_three_independent_variants_reach_final_input_without_changing_source(self):
        session,stub,result=self.execute();row=result['operations'][0];payload=row['result']
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual(row['status'],'G05_SENSITIVITY_PREPARED');self.assertTrue(row['executed'])
        self.assertEqual(row['variant_count'],3);self.assertFalse(row['source_modified'])
        self.assertFalse(row['verdict_produced']);self.assertFalse(row['semantic_certification'])
        self.assertEqual(payload['question'],QUESTION);self.assertEqual(payload['base']['question'],QUESTION)
        self.assertEqual([v['kind'] for v in payload['variants']],
            ['FACT_COUNTERFACTUAL','CONCEPT_READING_SWITCH','VALUE_PREMISE_REVERSAL'])
        self.assertEqual([v['comparisons'][0]['sensitivity'] for v in payload['variants']],
            ['SUPPORT_REMOVED_UNDER_ASSUMPTION','READING_CHANGED_CONCLUSION_UNRESOLVED',
             'VALUE_PREMISE_CHANGED_CONCLUSION_UNRESOLVED'])
        for variant in payload['variants']:
            self.assertFalse(variant['source_modified']);self.assertTrue(variant['only_one_factor_changed'])
            self.assertEqual(variant['comparisons'][1]['sensitivity'],'STRUCTURALLY_UNAFFECTED_BY_THIS_VARIANT')
            self.assertTrue(all(c['conclusion_truth']=='NOT_ESTABLISHED' for c in variant['comparisons']))
        self.assertEqual(payload['moral_truth'],'NOT_INFERRED')
        self.assertEqual(payload['base']['world_truth'],'NOT_ESTABLISHED')
        self.assertEqual(payload['base']['source_order'],'NOT_CALENDAR_TIME')
        self.assertIsNone(payload['observer']);self.assertIsNone(payload['through_order'])
        self.assertEqual(payload['cutoffs'],[None,None,None])
        self.assertEqual(session.sources['scene']['text'],SOURCE)
        final=json.loads(stub.calls[-1][1][-1]['content'])
        self.assertEqual(final['hcl_operations'],result['operations'])
        self.assertEqual(final['sources'],[dict(source_id='scene',version=1,text=SOURCE)])
        self.assertFalse(result['base_bypass']);self.assertFalse(result['complete_capability_integration'])
        self.assertFalse(result['answer_gain_established']);self.assertEqual(result['provider_calls'],0)
        self.assertEqual(result['backend_calls'],2)

    def test_payload_matches_unchanged_retained_workspace(self):
        session,_,result=self.execute();retained=ArgumentSensitivityWorkspace('scene')
        retained.put_source(SOURCE,recorded_at=session.sources['scene']['recorded_at'])
        self.assertEqual(result['operations'][0]['result'],retained.compare(QUESTION).payload)

    def test_request_is_exact_conditional_authority_and_jointly_required_with_source(self):
        session,_,result=self.execute();row=result['operations'][0]
        provenance=row['request_provenance'];claim=row['support_claim_ids'][0]
        self.assertEqual(provenance['sha256'],hashlib.sha256(QUESTION.encode()).hexdigest())
        self.assertEqual(provenance['input_kind'],'ORIGINAL_USER_REQUEST')
        self.assertEqual(provenance['authority'],'ANALYSIS_CONDITION_NOT_WORLD_EVIDENCE')
        self.assertEqual((provenance['start'],provenance['end']),(0,len(QUESTION)))
        root=session.workspace.core.spans[provenance['span_id']]
        self.assertEqual(root.quote,QUESTION);self.assertNotIn(root.source_id,session.sources)
        self.assertEqual(session.workspace.core.claims[claim].kind,ClaimKind.CONDITIONAL_TOOL_RESULT)
        self.assertEqual(session.workspace.core.claims[claim].scope.source_ids,(root.source_id,'scene'))
        self.assertEqual(session.workspace.core.dependencies[claim],
            {tuple(sorted((provenance['span_id'],session.workspace._spans['scene'])))})
        self.assertEqual(session.workspace.core.support_statuses()[claim],'SUPPORT_AVAILABLE')
        for withdraw in (provenance['span_id'],session.workspace._spans['scene']):
            session.workspace.core.withdraw(withdraw)
            self.assertEqual(session.workspace.core.support_statuses()[claim],'UNSUPPORTED')
            session.workspace.core.withdrawn.remove(withdraw)

    def test_planner_hypothetical_and_source_injection_cannot_replace_original_request(self):
        for question in ('Analyze human society.','分析人类社会','If Mira secretly lies, what changes?'):
            _,stub,result=self.execute(SOURCE+'\n'+QUESTION,question,interpreted=QUESTION)
            row=result['operations'][0]
            self.assertFalse(row['executed']);self.assertEqual(row['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
            self.assertNotIn('request_provenance',row);self.assertNotIn('result',row)
            final=json.loads(stub.calls[-1][1][-1]['content'])
            self.assertEqual(final['question'],question);self.assertEqual(final['sources'][0]['text'],SOURCE+'\n'+QUESTION)
        _,_,result=self.execute(question=QUESTION.splitlines()[0],interpreted=QUESTION.splitlines()[2])
        self.assertEqual(result['operations'][0]['result']['variants'][0]['kind'],'FACT_COUNTERFACTUAL')

    def test_single_source_contract_and_complete_unselected_sources(self):
        absent=run(UniversalHCL(),QUESTION,Stub(plan(operation('G05',QUESTION,[]))))
        self.assertEqual(absent['operations'][0]['status'],'SOURCE_PREREQUISITE_UNAVAILABLE')
        session=UniversalHCL();session.put_source('a',SOURCE);session.put_source('b','Other complete account.')
        for selected in (['a','b'],['a']):
            stub=Stub(plan(operation('G05',QUESTION,selected)));result=run(session,QUESTION,stub)
            row=result['operations'][0]
            self.assertEqual(row['executed'],len(selected)==1)
            if len(selected)>1:self.assertEqual(row['status'],'G05_REQUIRES_ONE_SOURCE')
            self.assertEqual([r['text'] for r in json.loads(stub.calls[-1][1][-1]['content'])['sources']],
                             [SOURCE,'Other complete account.'])

    def test_separate_operations_keep_domains_and_joint_support_separate(self):
        session=UniversalHCL();session.put_source('a',SOURCE)
        challenged=SOURCE+'\nNoor: In choice, I challenge the fact that Mira could leave.'
        session.put_source('b',challenged)
        result=run(session,QUESTION,Stub(plan(*(operation('G05',QUESTION,[sid]) for sid in ('a','b')))))
        for sid,row in zip(('a','b'),result['operations']):
            claim=row['support_claim_ids'][0]
            self.assertEqual(session.workspace.core.dependencies[claim],
                {tuple(sorted((row['request_provenance']['span_id'],session.workspace._spans[sid])))})
        self.assertEqual(result['operations'][0]['result']['variants'][0]['comparisons'][0]['sensitivity'],
                         'SUPPORT_REMOVED_UNDER_ASSUMPTION')
        self.assertEqual(result['operations'][1]['result']['variants'][0]['comparisons'][0]['sensitivity'],
                         'ALREADY_CONTESTED_REMAINS_UNRESOLVED')
        session.workspace.core.withdraw(session.workspace._spans['a'])
        self.assertEqual(session.workspace.core.support_statuses()[result['operations'][1]['support_claim_ids'][0]],'SUPPORT_AVAILABLE')

    def test_shared_revision_exact_quotes_and_request_id_collision(self):
        session=UniversalHCL();sid='original-user-request:'+hashlib.sha256(QUESTION.encode()).hexdigest()
        session.put_source(sid,'Earlier report.');session.put_source(sid,SOURCE)
        result=run(session,QUESTION,Stub(plan(operation('G05',QUESTION,[sid]))));row=result['operations'][0]
        self.assertEqual(row['result']['source_version'],2)
        root=session.workspace.core.spans[row['request_provenance']['span_id']]
        self.assertNotEqual(root.source_id,sid)
        def verify(value):
            if isinstance(value,dict):
                if {'source_id','version','quote','start','end','span_id'}<=value.keys():
                    self.assertEqual(value['source_id'],sid);self.assertEqual(value['version'],2)
                    self.assertEqual(SOURCE[value['start']:value['end']],value['quote'])
                for child in value.values():verify(child)
            elif isinstance(value,list):
                for child in value:verify(child)
        verify(row['result'])

    def test_source_correction_invalidates_old_claim_without_rewriting_history(self):
        session,_,result=self.execute();old=result['operations'][0];claim=old['support_claim_ids'][0]
        session.put_source('unrelated','Independent report.')
        self.assertEqual(session.workspace.core.support_statuses()[claim],'SUPPORT_AVAILABLE')
        session.put_source('scene',SOURCE+'\nNoor: In choice, I challenge the fact that Mira could leave.')
        self.assertEqual(session.workspace.core.support_statuses()[claim],'UNSUPPORTED')
        fresh=run(session,QUESTION,Stub(plan(operation('G05',QUESTION,['scene']))))['operations'][0]
        self.assertEqual(fresh['result']['source_version'],2)
        self.assertNotEqual(fresh['support_claim_ids'],old['support_claim_ids'])
        self.assertEqual(old['result']['source_version'],1)
        self.assertEqual(old['result']['variants'][0]['comparisons'][0]['sensitivity'],'SUPPORT_REMOVED_UNDER_ASSUMPTION')
        self.assertEqual(fresh['result']['variants'][0]['comparisons'][0]['sensitivity'],'ALREADY_CONTESTED_REMAINS_UNRESOLVED')

    def test_source_revision_or_withdrawal_during_planning_or_answer_blocks_delivery(self):
        for phase in ('planning','answer'):
            for revise in (True,False):
                session=UniversalHCL();session.put_source('scene',SOURCE)
                def callback(current):
                    if current==phase:
                        if revise:session.put_source('scene',SOURCE+'\nA later report.')
                        else:session.workspace.core.withdraw(session.workspace._spans['scene'])
                stub=Stub(plan(operation('G05',QUESTION,['scene'])),callback=callback)
                result=run(session,QUESTION,stub)
                self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
                self.assertNotIn('answer',result);self.assertEqual(len(stub.calls),1 if phase=='planning' else 2)

    def test_request_or_operation_withdrawal_during_answer_blocks_delivery(self):
        for withdraw_request in (True,False):
            session=UniversalHCL();session.put_source('scene',SOURCE)
            def callback(phase):
                if phase=='answer':
                    for claim in session.workspace.core.claims.values():
                        if claim.content.get('operation')=='G05_ARGUMENT_SENSITIVITY_PREPARATION':
                            target=claim.content['request_provenance']['span_id'] if withdraw_request else claim.id
                            session.workspace.core.withdraw(target)
            result=run(session,QUESTION,Stub(plan(operation('G05',QUESTION,['scene'])),callback=callback))
            self.assertNotIn('answer',result);self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED')

    def test_revision_during_preparation_blocks_delivery(self):
        session=UniversalHCL();session.put_source('scene',SOURCE);original=ArgumentSensitivityWorkspace.compare
        def prepare(workspace,*args,**kwargs):
            result=original(workspace,*args,**kwargs);session.put_source('scene',SOURCE+'\nA later report.')
            return result
        with patch.object(ArgumentSensitivityWorkspace,'compare',prepare):
            result=run(session,QUESTION,Stub(plan(operation('G05',QUESTION,['scene']))))
        self.assertNotIn('answer',result);self.assertEqual(result['backend_calls'],1)

    def test_retained_single_factor_prerequisites_stay_strict(self):
        cases=[(SOURCE,'If the bridge fell were false, what changes?'),
               (SOURCE,'If Mira valued status over duty instead, what changes?'),
               (SOURCE,QUESTION+'\n'+QUESTION.splitlines()[0]),
               (SOURCE,QUESTION.splitlines()[0]+'\n'+QUESTION.splitlines()[0]),
               (SOURCE.replace('Noor: In choice, for free pressure_absent is true is necessary.\n',''),QUESTION),
               (SOURCE+'\nNoor: In work, I conclude work is risky because Mira could leave.',QUESTION)]
        for source,question in cases:
            with self.subTest(question=question):
                _,_,result=self.execute(source,question);row=result['operations'][0]
                self.assertFalse(row['executed']);self.assertEqual(row['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_retained_bounds_reject_without_truncation(self):
        expanded='\n'.join(SOURCE.splitlines()+[SOURCE.splitlines()[5]]*15)
        for source,question in [('x'*16001,QUESTION),('\n'.join(['x']*65),QUESTION),
                                (SOURCE,'q'*4001),(expanded,QUESTION)]:
            _,stub,result=self.execute(source,question);row=result['operations'][0]
            self.assertFalse(row['executed']);self.assertEqual(row['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
            final=json.loads(stub.calls[-1][1][-1]['content'])
            self.assertEqual(final['sources'][0]['text'],source);self.assertEqual(final['question'],question)

    def test_catalog_is_truthfully_partial(self):
        self.assertEqual(CATALOG['G05'].entry_readiness,'BOUNDED_ORDINARY_ADAPTER')
        self.assertEqual(sum(c.entry_readiness=='BOUNDED_ORDINARY_ADAPTER' for c in CATALOG.values()),10)
        session=UniversalHCL();session.put_source('scene',SOURCE)
        for cid in ('H01','H02'):
            row=session._execute(operation(cid,QUESTION,['scene']),QUESTION)
            self.assertFalse(row['executed']);self.assertEqual(row['status'],'RETAINED_IMPLEMENTATION_REQUIRES_ENTRY_ADAPTER')


class SensitivityFreezeTests(unittest.TestCase):
    def test_every_historical_amendment_rejects_tampering(self):
        from pathlib import Path
        from scripts.development_answer_citation_contract_amendment import HISTORICAL_PINS, validate_current
        original=Path.read_bytes;self.assertTrue(validate_current())
        for changed in HISTORICAL_PINS:
            with self.subTest(path=changed):
                def read(path):
                    content=original(path)
                    return content+b'\n' if str(path)==changed else content
                with patch.object(Path,'read_bytes',read):
                    with self.assertRaisesRegex(ValueError,'historical amendment'):validate_current()

    def test_runtime_drift_and_missing_membership_reject(self):
        from pathlib import Path
        from scripts.development_answer_citation_contract_amendment import validate_current
        original=Path.read_bytes
        for changed in ('hcl/cognition/argument_sensitivity.py','hcl/cognition/argument_analysis.py',
                        'hcl/cognition/core.py','hcl/cognition/universal_entry.py','hcl/cognition/capability_catalog.py'):
            def read(path):
                content=original(path)
                return content+b'\n' if str(path)==changed else content
            with patch.object(Path,'read_bytes',read):
                with self.assertRaises(ValueError):validate_current()
        with self.assertRaises(ValueError):validate_current(current_digest='0'*64)
        rglob=Path.rglob
        with patch.object(Path,'rglob',lambda path,pattern: (p for p in rglob(path,pattern)
                if str(p)!='hcl/cognition/universal_entry.py')):
            with self.assertRaises(ValueError):validate_current()


if __name__=='__main__':unittest.main()
