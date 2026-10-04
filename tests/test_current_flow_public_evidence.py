"""Negative canaries verify allowlisted public evidence, with no provider calls."""
import copy
import json
import unittest
from unittest.mock import patch
from scripts import run_current_flow_diagnostic as runner
from scripts import current_flow_public_evidence as public
from tests.test_current_flow_diagnostic import execute,response,grant,VERIFIED
from tests.test_bounded_diagnostics import Client

class PublicEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.receipt=execute(Client(response))
        with patch.object(runner,'readiness',return_value=VERIFIED):self.package=runner.build_package()
        self.grant=grant(self.package)
        self.secret=dict(run_id='123',head_sha='a'*40,existing_provider_secret='PRESENT')
    def export(self):
        with patch.object(runner,'readiness',return_value=VERIFIED):
            return public.export(self.receipt,self.package,self.grant,'123','a'*40,self.secret)
    def test_final_fields_exact_with_complete_rated_cost(self):
        value=self.export()
        self.assertEqual(value['final_answer_fields'],json.loads(self.receipt['calls'][1]['response_content']))
        self.assertTrue(value['usage_complete']);self.assertEqual(value['provider_calls'],2)
        self.assertTrue(value['source_and_original_request_supported']);self.assertFalse(value['i02_certified'])
        self.assertEqual(value['semantic_review'],'PENDING_SOURCE_FIRST_REVIEW')
    def test_private_nested_canaries_never_serialize(self):
        for target in [self.receipt,*self.receipt['calls'],self.receipt['hcl'],self.receipt['hcl']['plan']]:
            target.update(reasoning_content='REASONING_CANARY',raw_error='ERROR_CANARY',debug='DEBUG_CANARY',env='SECRET_CANARY')
        self.receipt['calls'][0]['response_content']='PLANNING_CANARY'
        self.receipt['calls'][0]['request']='REQUEST_CANARY'
        self.receipt['calls'][1]['request']='ANSWER_REQUEST_CANARY'
        self.receipt['hcl']['answer_raw']='HISTORICAL_ANSWER_CANARY'
        encoded=json.dumps(self.export())
        self.assertNotIn('CANARY',encoded)
        self.assertNotIn('reasoning_content',encoded)
        self.assertNotIn('response_content',encoded)
    def test_nested_citation_extra_field_is_not_published(self):
        raw=json.loads(self.receipt['calls'][1]['response_content'])
        raw['source_citations'][0]['reasoning_content']='NESTED_CANARY'
        self.receipt['calls'][1]['response_content']=json.dumps(raw)
        value=self.export();self.assertIsNone(value['final_answer_fields']);self.assertNotIn('CANARY',json.dumps(value))
    def test_bad_citation_empty_answer_not_rewritten(self):
        raw=json.loads(self.receipt['calls'][1]['response_content']);raw['answer']='  ';raw['source_citations'][0]['end']=5
        self.receipt['calls'][1]['response_content']=json.dumps(raw)
        self.receipt['status']='HCL_FAILED_NO_RETRY';self.receipt.pop('hcl_citations_accepted')
        value=self.export();self.assertEqual(value['final_answer_fields'],raw);self.assertFalse(value['citations_accepted'])
        self.assertEqual(value['status'],'HCL_FAILED_NO_RETRY')
    def test_unknown_scalar_is_rejected_not_published(self):
        for field in ('status','reserved_usd','authorization_ref'):
            original=self.receipt[field];self.receipt[field]='SCALAR_CANARY'
            with self.assertRaises(Exception):self.export()
            self.receipt[field]=original
    def test_wrong_scope_or_identity_refused(self):
        for change in [dict(existing_provider_secret='ABSENT'),dict(run_id='124'),dict(head_sha='b'*40)]:
            self.secret=dict(run_id='123',head_sha='a'*40,existing_provider_secret='PRESENT',**{})
            self.secret.update(change)
            with self.assertRaises(ValueError):self.export()
    def test_missing_usage_holds_full_reservation(self):
        self.receipt['calls'][0].pop('usage');self.receipt['calls'][0].pop('actual_usd')
        value=self.export();self.assertFalse(value['usage_complete']);self.assertIsNone(value['usage_rated_usd'])
        self.assertEqual(value['reserved_usd'],self.receipt['reserved_usd'])
    def test_secret_workflow_uses_boolean_only_and_exact_artifact(self):
        workflow=runner.TEMPLATE.read_text()
        presence=workflow.split('- name: Existing provider secret presence')[1].split('- name: Single reviewed')[0]
        self.assertIn("${{ secrets.DEEPSEEK_API_KEY != '' }}",presence)
        self.assertNotIn('${{ secrets.DEEPSEEK_API_KEY }}',presence)
        self.assertIn('path: current-flow-public.json',workflow)
        self.assertNotIn('path: current-flow-private',workflow)
        self.assertNotIn('workflow_dispatch:',workflow)
        self.assertEqual(runner.WORKFLOW.read_bytes(),runner.TEMPLATE.read_bytes())

if __name__=='__main__':unittest.main()
