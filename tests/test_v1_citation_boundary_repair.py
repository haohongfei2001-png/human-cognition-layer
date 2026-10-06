"""Three deterministic boundary defects; no provider calls or historical rescoring."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from hcl.cognition import CognitionWorkspace,UniversalHCL
from hcl.cognition import retained
from hcl.cognition.reader_entry import answer_reader_entry
from hcl.cognition.universal_entry import HCLBoundaryError
from scripts.development_explicit_citation_amendment import validate_current
from tests.test_v1_universal_question import Stub,operation,plan,run


def response(answer='A source report.',citations=()):
    return dict(answer=answer,source_citations=list(citations),uncertainty='',assumptions='')


def audit(source,quote,**fields):
    messages=[dict(role='user',content=json.dumps(dict(sources=[dict(source_id='s',version=1,text=source)])))]
    raw=json.dumps(response(citations=[dict(source_id='s',quote=quote,**fields)]))
    return retained.audit_supplied_source_citations(messages,raw)


class AnswerPort(Stub):
    def __init__(self,raw,source_id='s'):
        super().__init__(plan(operation('B01','What is reported?',[source_id])));self.raw=raw
    def complete(self,phase,messages):
        result=super().complete(phase,messages)
        if phase=='answer':result['text']=self.raw
        return result


class CitationBoundaryRepairTests(unittest.TestCase):
    def test_overlapping_exact_quotations_are_not_unique(self):
        for text,quote in [('ha ha ha','ha ha'),('🙂🙂🙂','🙂🙂'),('ababa','aba')]:
            for fields in ({},dict(start=999)):
                with self.subTest(text=text,fields=fields):
                    result=audit(text,quote,**fields)
                    self.assertFalse(result['deliverable']);self.assertEqual(result['status'],'INVALID_ORIGINAL_CITATIONS')
                    self.assertFalse(result['raw_output_rewritten'])

    def test_correct_explicit_overlapping_offsets_disambiguate(self):
        for text,quote,starts in [('ha ha ha','ha ha',(0,3)),('🙂🙂🙂','🙂🙂',(0,1))]:
            for start in starts:
                result=audit(text,quote,start=start)
                self.assertTrue(result['deliverable']);anchor=result['anchors'][0]
                self.assertEqual((anchor['start'],anchor['end']),(start,start+len(quote)))
                self.assertEqual(anchor['original_quote'],quote)
        self.assertFalse(audit('ha ha ha','ha ha',start=1)['deliverable'])

    def test_overlapping_whitespace_alternatives_remain_ambiguous(self):
        for fields in ({},dict(start=0),dict(start=3)):
            self.assertFalse(audit('ha ha ha','ha  ha',**fields)['deliverable'])
        result=audit('blue\n door.','blue door.',start=999)
        self.assertTrue(result['deliverable'])
        self.assertEqual(result['anchors'][0]['location_rule'],'UNIQUE_WHITESPACE_LAYOUT_ONLY')
        self.assertEqual(result['anchors'][0]['original_quote'],'blue\n door.')

    def test_exact_offset_and_unique_relocation_still_precede_layout_alternatives(self):
        result=audit('Prefix. blue door.','blue door.',start=999)
        self.assertTrue(result['deliverable']);self.assertEqual(result['anchors'][0]['start'],8)
        result=audit('blue door. blue\n door.','blue door.',start=11)
        self.assertTrue(result['deliverable']);self.assertEqual(result['anchors'][0]['start'],0)
        self.assertEqual(result['anchors'][0]['location_rule'],'EXACT_ORIGINAL_QUOTE')

    def test_ambiguity_scan_stops_after_second_location(self):
        original=retained.re.finditer;seen=[]
        def counted(pattern,text):
            for match in original(pattern,text):
                seen.append(match.span());yield match
        with patch.object(retained.re,'finditer',counted):
            result=audit('ha '*10000,'ha ha')
        self.assertFalse(result['deliverable']);self.assertEqual(len(seen),2)

    def test_universal_overlap_rejection_preserves_raw_answer_and_stops_after_two_stub_phases(self):
        session=UniversalHCL();session.put_source('s','ha ha ha')
        raw=json.dumps(response(citations=[dict(source_id='s',quote='ha ha')]))
        port=AnswerPort(raw);result=run(session,'What is quoted?',port)
        self.assertEqual(result['status'],'ANSWER_SOURCE_REVIEW_FAILED')
        self.assertNotIn('answer',result);self.assertEqual(result['answer_raw'],raw)
        self.assertEqual([p for p,_ in port.calls],['planning','answer']);self.assertEqual(result['provider_calls'],0)

    def test_legacy_reader_rejects_all_nonstring_answers_without_hidden_repair(self):
        for value in (None,False,3,3.5,[],{},['claim']):
            w=CognitionWorkspace();w.put_source('s','A source report.');calls=[]
            raw=json.dumps(response(answer=value))
            def backend(frame):calls.append(frame);return raw
            result=answer_reader_entry(w,'What is reported?',backend,source_ids=('s',))
            self.assertFalse(result['source_citation_audit']['deliverable'])
            self.assertEqual(result['answer_raw'],raw);self.assertNotEqual(result['answer'],raw)
            self.assertFalse(result['source_citation_audit']['raw_output_rewritten']);self.assertEqual(len(calls),1)
            self.assertEqual(json.loads(result['answer'])['answer'],'I cannot support this answer from the supplied text.')

    def test_string_answers_and_other_strict_boundaries_are_preserved(self):
        for value in ('','A bounded report.'):
            w=CognitionWorkspace();w.put_source('s','A source report.');raw=json.dumps(response(answer=value))
            result=answer_reader_entry(w,'What is reported?',lambda _:raw,source_ids=('s',))
            self.assertTrue(result['source_citation_audit']['deliverable']);self.assertEqual(result['answer'],raw)
        for fields in (dict(end=5),dict(version=2),dict(start=True),dict(extra='value')):
            self.assertFalse(audit('A source report.','A source report.',**fields)['deliverable'])
        self.assertFalse(audit('A source report.','A fabricated report.')['deliverable'])
        self.assertFalse(audit('A source report.','A report.')['deliverable'])

    def test_source_id_129_rejects_before_mutation_or_any_backend_call(self):
        for sid in ('a'*129,'灯'*129,'🙂'*129):
            session=UniversalHCL();session.put_source('existing','Preserved.');port=Stub()
            before=copy.deepcopy(session.sources);version=dict(session.workspace._versions)
            with self.assertRaises(HCLBoundaryError):
                session.put_source(sid,'New source.');run(session,'Question.',port)
            self.assertEqual(port.calls,[]);self.assertEqual(session.sources,before)
            self.assertEqual(session.workspace._versions,version)

    def test_exact_128_character_source_ids_and_revisions_remain_identity_preserving(self):
        for sid in ('a'*128,'灯'*128,'🙂'*128):
            session=UniversalHCL();session.put_source(sid,'First source.');session.put_source(sid,'Current source.')
            self.assertEqual(list(session.sources),[sid]);self.assertEqual(session.sources[sid]['version'],2)
            raw=json.dumps(response(citations=[dict(source_id=sid,quote='Current source.',version=2)]))
            port=AnswerPort(raw,sid);result=run(session,'What is reported?',port)
            self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
            final=json.loads(port.calls[-1][1][-1]['content'])
            self.assertEqual(final['sources'],[dict(source_id=sid,version=2,text='Current source.')])
            self.assertEqual(result['source_review']['actual_primary_source_ids'],[sid])
            self.assertEqual(result['provider_calls'],0)

    def test_historical_pins_and_changes_outside_two_functions_reject(self):
        self.assertTrue(validate_current())
        with self.assertRaises(ValueError):validate_current(current_digest='0'*64)
        original=Path.read_bytes
        for target in ('hcl/cognition/retained.py','hcl/cognition/universal_entry.py','hcl/cognition/reader_entry.py','reports/HCL_PLANNER_CONTRACT_SMOKE_CLOSURE.json'):
            def read(path):
                data=original(path);return data+b'\nUNRELATED = True\n' if str(path)==target else data
            with patch.object(Path,'read_bytes',read),self.assertRaises(ValueError):validate_current()


if __name__=='__main__':unittest.main()
