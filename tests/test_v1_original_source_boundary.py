"""Generic original/derived input boundary and raw-preserving citation delivery."""
import json
import unittest
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from hcl.cognition.retained import audit_original_citations
from tests.test_v1_conditional_reader_entry import Backend, proposals, SOURCE, QUOTES, LINES, QUERY

ROOT=Path(__file__).resolve().parents[1]
def final(citations):
    return json.dumps(dict(answer='The source reports a conditional plan.',source_citations=citations,
        uncertainty='Translations remain unverified.',assumptions='No private/world truth.'))

class OriginalBoundaryTests(unittest.TestCase):
    def workspace(self,text=SOURCE):
        w=CognitionWorkspace();w.put_source('meeting',text);return w
    def prepare(self,w=None,b=None):
        w=w or self.workspace();return w,w.prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=b or Backend())

    def test_primary_originals_and_conditional_real_state_are_structurally_separate(self):
        w,r=self.prepare();p=json.loads(r.messages[-1]['content'])
        self.assertEqual(p['sources'],[dict(source_id='meeting',version=1,text=SOURCE)])
        c=p['conditional_cognition'];self.assertIn('NOT_QUOTABLE_SOURCE',c['authority'])
        self.assertIn('NOT_ORIGINAL_SEMANTIC_CERTIFICATE',c['validation_scope'])
        self.assertNotIn('sources',c['state']);self.assertIn('derived_sources',c['state'])
        self.assertEqual(c['state']['checked_plan_feasibility'][0]['plans'][0]['model_condition_check'],'MODEL_CONDITION_CONTRADICTED')
        self.assertEqual(w.core.claims[r.operation_ids[0]].content['retained_state']['checked_plan_feasibility'],c['state']['checked_plan_feasibility'])
        self.assertEqual(len(r.scope.assumptions),5);self.assertFalse(r.receipt['semantic_certification'])

    def test_true_original_citations_pass_location_only_and_raw_answer_unchanged(self):
        w=self.workspace();raw=final([QUOTES[0],QUOTES[1]]);calls=[]
        a=w.answer_reader_semantic(QUERY,lambda m:calls.append(m) or raw,source_ids=('meeting',),backend=Backend())
        self.assertEqual(a['answer'],raw);self.assertEqual(a['answer_raw'],raw)
        self.assertTrue(a['source_citation_audit']['deliverable'])
        self.assertEqual(a['source_citation_audit']['semantic_adequacy'],'UNASSESSED')
        self.assertFalse(a['source_citation_audit']['semantic_certification'])
        self.assertEqual(calls,[a['actual_final_messages']]);self.assertEqual(a['answer_adapter_calls'],1)

    def test_derived_quotes_and_partial_bad_list_fail_closed_without_replacement(self):
        for citations in (list(LINES),[QUOTES[0],LINES[1]]):
            raw=final(citations);calls=[]
            a=self.workspace().answer_reader_semantic(QUERY,lambda m:calls.append(m) or raw,source_ids=('meeting',),backend=Backend())
            self.assertEqual(a['answer_raw'],raw);self.assertNotEqual(a['answer'],raw)
            self.assertEqual(json.loads(a['answer'])['source_citations'],[])
            self.assertFalse(a['source_citation_audit']['deliverable']);self.assertEqual(len(calls),1)
            self.assertFalse(a['source_citation_audit']['raw_output_rewritten'])

    def test_consumed_real_failure_is_offline_regression_not_rescore_or_rerun(self):
        receipt=json.loads((ROOT/'reports/HCL_DRE001_RAW_RECEIPT.json').read_text())
        raw=receipt['attempts'][-1]['response_raw']['choices'][0]['message']['content']
        _,r=self.prepare();a=audit_original_citations(r,raw)
        self.assertFalse(a['deliverable']);self.assertTrue(receipt['final_format_valid'])
        self.assertEqual(receipt['provider_calls'],2);self.assertFalse(a['semantic_certification'])

    def test_whitespace_layout_anchor_retains_original_substring_no_lexical_repair(self):
        _,r=self.prepare();q=QUOTES[0].replace('expressed a','expressed\n  a')
        a=audit_original_citations(r,final([q]));self.assertTrue(a['deliverable'])
        self.assertEqual(a['anchors'][0]['original_quote'],QUOTES[0]);self.assertEqual(a['anchors'][0]['submitted_quote'],q)
        self.assertEqual(a['anchors'][0]['location_rule'],'UNIQUE_WHITESPACE_LAYOUT_ONLY')
        self.assertFalse(audit_original_citations(r,final([QUOTES[0].replace('desire','fear')]))['deliverable'])

    def test_source_identity_version_and_derived_alias_cannot_be_substituted(self):
        _,r=self.prepare()
        for c in (dict(source_id='ordinary-source',quote=QUOTES[0]),dict(source_id='meeting',version=2,quote=QUOTES[0]),dict(source_id='Noor',quote=QUOTES[0])):
            self.assertFalse(audit_original_citations(r,final([c]))['deliverable'])
        self.assertTrue(audit_original_citations(r,final([dict(source_id='meeting',version=1,start=0,quote=QUOTES[0])]))['deliverable'])

    def test_duplicate_quote_requires_explicit_valid_original_offset(self):
        w=self.workspace(SOURCE+'\n'+QUOTES[0]);rows=proposals();rows[0]['start']=0
        _,r=self.prepare(w,Backend(rows))
        self.assertFalse(audit_original_citations(r,final([QUOTES[0]]))['deliverable'])
        self.assertTrue(audit_original_citations(r,final([dict(source_id='meeting',start=0,quote=QUOTES[0])]))['deliverable'])

    def test_missing_citations_have_no_source_or_semantic_certificate(self):
        _,r=self.prepare();a=audit_original_citations(r,final([]))
        self.assertTrue(a['deliverable']);self.assertEqual(a['status'],'NO_CITATIONS_SEMANTICS_UNASSESSED')
        self.assertFalse(a['semantic_certification'])
        self.assertFalse(audit_original_citations(r,'not JSON')['deliverable'])
        self.assertFalse(audit_original_citations(r,final(['x']*33))['deliverable'])

    def test_revision_during_final_answer_blocks_delivery_preserving_raw_once(self):
        w=self.workspace();raw=final([QUOTES[0]]);calls=[]
        def backend(m):calls.append(m);w.put_source('meeting','Dana withdrew the report.');return raw
        a=w.answer_reader_semantic(QUERY,backend,source_ids=('meeting',),backend=Backend())
        self.assertEqual(a['answer_raw'],raw);self.assertEqual(len(calls),1)
        self.assertEqual(a['source_citation_audit']['status'],'STALE_OR_CHALLENGED_SUPPORT')
        self.assertFalse(a['source_citation_audit']['deliverable'])

    def test_revision_during_extraction_cannot_relabel_old_candidates_or_pay_final(self):
        w=self.workspace();calls=[]
        class Revising(Backend):
            def complete_json(self,m,**kwargs):
                value=super().complete_json(m,**kwargs);w.put_source('meeting','Dana withdrew the report.');return value
        b=Revising()
        with self.assertRaisesRegex(ValueError,'source changed'):
            w.answer_reader_semantic(QUERY,lambda m:calls.append(m),source_ids=('meeting',),backend=b)
        self.assertEqual(len(b.calls),1);self.assertFalse(calls)
        self.assertFalse(any(w.core.claims[k].content.get('source_span_id') in w.core.grounded() for k in w.core.claims))

    def test_local_revision_recomputes_conditional_plan_without_original_quote_upgrade(self):
        w,before=self.prepare();correction='Dana explicitly corrected the report: the gate was not clear rather than clear.'
        w.put_source('meeting',SOURCE+'\n'+correction);rows=proposals()+[dict(source_id='meeting',quote=correction,kind='event',content=dict(canonical_statement='Dana: I now believe it is false that the gate is clear instead of the gate is clear.'))]
        after=w.prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=Backend(rows))
        with self.assertRaises(ValueError):before.current_messages(w)
        state=json.loads(after.messages[-1]['content'])['conditional_cognition']['state']
        self.assertEqual(state['checked_plan_feasibility'][0]['plans'][0]['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertFalse(audit_original_citations(after,final([LINES[3]]))['deliverable'])

if __name__=='__main__':unittest.main()
