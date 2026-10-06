"""Authored engineering contracts, not replayed model answers or efficacy tests."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from hcl.cognition import CognitionWorkspace, UniversalHCL
from hcl.cognition.reader_entry import _FINAL_ANSWER_POLICY, _EXPLICIT_CITATION_FINAL_ANSWER_POLICY, answer_reader_entry
from hcl.cognition.retained import audit_supplied_source_citations
from scripts.development_explicit_citation_amendment import validate_current
from tests.test_v1_universal_question import Stub, operation, plan, run

SOURCE = 'Lin wrote the note.\nThe blue box stayed closed.'
SOURCES = [dict(source_id='record-a', version=3, text=SOURCE)]


def answer(citations):
    return dict(answer='A source-local report.', source_citations=citations,
                uncertainty='No private state or world truth established.', assumptions='None.')


def messages(sources=SOURCES):
    return [dict(role='user', content=json.dumps(dict(sources=sources)))]


def audit(citations, sources=SOURCES):
    return audit_supplied_source_citations(messages(sources), answer(citations))


class AnswerPort(Stub):
    def __init__(self, citations, selected=None):
        super().__init__(selected); self.citations=citations
    def complete(self, phase, frame):
        result=super().complete(phase, frame)
        if phase=='answer':result['text']=json.dumps(answer(self.citations))
        return result


class AnswerCitationContractTests(unittest.TestCase):
    def test_policy_discloses_exact_fields_and_internal_anchor_distinction(self):
        for text in ('required source_id and quote', 'optional fields are version and start',
                     'Do not include end or any other field', 'Internal prepared-state anchors',
                     'zero-based Unicode character offset', 'at most 32 entries',
                     'at most 4000 characters', 'not a boolean', 'source_citations must be empty'):
            self.assertIn(text, _FINAL_ANSWER_POLICY)

    def test_exact_objects_and_legacy_single_source_strings_remain_valid(self):
        for citations in ([dict(source_id='record-a',quote=SOURCE,version=3,start=0)], [SOURCE], []):
            result=audit(citations)
            self.assertTrue(result['deliverable']);self.assertFalse(result['semantic_certification'])
            self.assertFalse(result['raw_output_rewritten'])

    def test_extra_end_and_other_internal_anchor_fields_still_reject_without_mutation(self):
        for field,value in [('end',len(SOURCE)),('span_id','internal-span'),('order',1),('confidence',1)]:
            citation=dict(source_id='record-a',quote=SOURCE,version=3,start=0,**{field:value})
            original=copy.deepcopy(citation);result=audit([citation])
            self.assertEqual(result['status'],'INVALID_ORIGINAL_CITATIONS')
            self.assertFalse(result['deliverable']);self.assertEqual(citation,original)
            self.assertFalse(result['raw_output_rewritten'])

    def test_wrong_source_and_stale_boolean_or_noninteger_versions_reject(self):
        for source_id,version in [('absent',3),('record-a',2),('record-a',True),('record-a','3'),('record-a',3.0)]:
            self.assertFalse(audit([dict(source_id=source_id,quote=SOURCE,version=version)])['deliverable'])

        version_one=[dict(SOURCES[0],version=1)]
        self.assertFalse(audit([dict(source_id='record-a',quote=SOURCE,version=True)],version_one)['deliverable'])
        self.assertTrue(audit([dict(source_id='record-a',quote=SOURCE,version=1)],version_one)['deliverable'])

    def test_invalid_offset_types_reject_and_null_is_accepted(self):
        for start in (True,False,-1,'0',0.0):
            self.assertFalse(audit([dict(source_id='record-a',quote=SOURCE,start=start)])['deliverable'])
        self.assertTrue(audit([dict(source_id='record-a',quote=SOURCE,start=None)])['deliverable'])

    def test_unique_exact_quote_relocation_preserves_submitted_offset(self):
        quote='The blue box stayed closed.';result=audit([dict(source_id='record-a',quote=quote,start=999)])
        self.assertTrue(result['deliverable']);anchor=result['anchors'][0]
        self.assertEqual(anchor['submitted_start'],999)
        self.assertEqual(anchor['start'],SOURCE.index(quote))
        self.assertEqual(anchor['location_rule'],'EXACT_ORIGINAL_QUOTE')

    def test_repeated_quotes_require_correct_exact_offset(self):
        source=[dict(source_id='repeat',version=1,text='Signal. Pause. Signal.')]
        for extra in ({},dict(start=1)):
            self.assertFalse(audit([dict(source_id='repeat',quote='Signal.',**extra)],source)['deliverable'])
        start=source[0]['text'].rindex('Signal.')
        result=audit([dict(source_id='repeat',quote='Signal.',start=start)],source)
        self.assertTrue(result['deliverable']);self.assertEqual(result['anchors'][0]['start'],start)

    def test_whitespace_only_relocation_remains_explicit_without_lexical_repair(self):
        source=[dict(source_id='layout',version=1,text='A blue\n  door.')]
        result=audit([dict(source_id='layout',quote='blue door.')],source)
        self.assertTrue(result['deliverable']);anchor=result['anchors'][0]
        self.assertEqual(anchor['location_rule'],'UNIQUE_WHITESPACE_LAYOUT_ONLY')
        self.assertEqual(anchor['original_quote'],'blue\n  door.')
        self.assertEqual(anchor['submitted_quote'],'blue door.')
        repeated=[dict(source_id='layout',version=1,text='blue\n door. blue\t door.')]
        self.assertFalse(audit([dict(source_id='layout',quote='blue door.',start=0)],repeated)['deliverable'])

    def test_exact_quote_precedes_whitespace_normalized_alternative(self):
        text='blue door. blue\n door.';source=[dict(source_id='layout',version=1,text=text)]
        result=audit([dict(source_id='layout',quote='blue door.',start=11)],source)
        self.assertTrue(result['deliverable']);self.assertEqual(result['anchors'][0]['start'],0)
        self.assertEqual(result['anchors'][0]['location_rule'],'EXACT_ORIGINAL_QUOTE')

    def test_fabricated_noncontiguous_and_empty_quotes_reject(self):
        for quote in ('Lin erased the note.','Lin wrote stayed closed.','', '  ', 'x'*4001):
            self.assertFalse(audit([dict(source_id='record-a',quote=quote)])['deliverable'])
        self.assertTrue(audit([SOURCE]*32)['deliverable'])
        self.assertFalse(audit([SOURCE]*33)['deliverable'])
        for length,expected in ((4000,True),(4001,False)):
            text='x'*length;source=[dict(source_id='long-quote',version=1,text=text)]
            self.assertEqual(audit([dict(source_id='long-quote',quote=text)],source)['deliverable'],expected)

    def test_unicode_offsets_are_character_positions_and_multisource_requires_identity(self):
        text='灯🙂 Echo. Echo.';source=[dict(source_id='unicode',version=1,text=text)]
        result=audit([dict(source_id='unicode',quote='Echo.',start=9)],source)
        self.assertTrue(result['deliverable']);self.assertEqual(result['anchors'][0]['start'],9)
        self.assertFalse(audit([dict(source_id='unicode',quote='Echo.',start=len(text[:9].encode()))],source)['deliverable'])
        utf16_offset=len(text[:9].encode('utf-16-le'))//2
        self.assertFalse(audit([dict(source_id='unicode',quote='Echo.',start=utf16_offset)],source)['deliverable'])
        multiple=SOURCES+source
        self.assertFalse(audit([SOURCE],multiple)['deliverable'])
        self.assertTrue(audit([dict(source_id='record-a',quote=SOURCE),dict(source_id='unicode',quote='Echo.',start=9)],multiple)['deliverable'])

    def test_expanded_policy_reaches_universal_answer_without_changing_source_or_raw_result(self):
        session=UniversalHCL();session.put_source('record-a',SOURCE)
        citation=dict(source_id='record-a',quote=SOURCE,end=len(SOURCE))
        port=AnswerPort([citation],plan(operation('B01','What is directly reported?',['record-a'])));result=run(session,'What is directly reported?',port)
        self.assertEqual([phase for phase,_ in port.calls],['planning','answer'])
        self.assertIn(_EXPLICIT_CITATION_FINAL_ANSWER_POLICY,port.calls[-1][1][0]['content'])
        self.assertEqual(json.loads(port.calls[-1][1][-1]['content'])['sources'][0]['text'],SOURCE)
        self.assertEqual(result['status'],'ANSWER_SOURCE_REVIEW_FAILED')
        self.assertFalse(result['source_review']['deliverable'])
        self.assertEqual(json.loads(result['answer_raw']),answer([citation]))
        self.assertEqual(result['provider_calls'],0)

    def test_no_source_citations_empty_and_explicit_unsourced_path_remains(self):
        for citations,expected in (([],'ANSWERED_WITH_EXPLICIT_LIMITS'),([dict(source_id='invented',quote='fact')],'ANSWER_SOURCE_REVIEW_FAILED')):
            port=AnswerPort(citations,plan(operation('G01','Prepare the caller condition.',[])))
            result=run(UniversalHCL(),'For this analysis, responsibility requires control.',port)
            self.assertEqual(result['status'],expected)
            self.assertIn('source_citations must be empty',port.calls[-1][1][0]['content'])

    def test_shared_reader_policy_is_fully_budgeted_and_no_final_call_on_overflow(self):
        source='Lin believes the corridor is clear. Lin said, "I do not believe the corridor is clear."'
        def workspace():
            w=CognitionWorkspace();w.put_source('record-a',source);return w
        raw=json.dumps(answer([dict(source_id='record-a',quote=source)]));calls=[]
        def backend(frame):calls.append(frame);return raw
        large=answer_reader_entry(workspace(),'What is reported?',backend,source_ids=('record-a',))
        self.assertEqual(large['actual_final_messages'][-1]['content'],_FINAL_ANSWER_POLICY)
        exact=len(json.dumps(large['actual_final_messages'],ensure_ascii=False));calls.clear()
        result=answer_reader_entry(workspace(),'What is reported?',backend,source_ids=('record-a',),max_chars=exact)
        self.assertEqual(result['actual_final_messages'],large['actual_final_messages'])
        self.assertTrue(result['source_citation_audit']['deliverable']);self.assertEqual(len(calls),1)
        with self.assertRaises(ValueError):
            answer_reader_entry(workspace(),'What is reported?',backend,source_ids=('record-a',),max_chars=exact-1)
        self.assertEqual(len(calls),1)

    def test_current_amendment_preserves_runtime_membership_validator_and_failed_receipt(self):
        self.assertTrue(validate_current())
        with self.assertRaises(ValueError):validate_current(current_digest='0'*64)
        original=Path.read_bytes
        for target in ('hcl/cognition/retained.py','reports/HCL_PLANNER_CONTRACT_SMOKE_CLOSURE.json'):
            def read(path):
                data=original(path)
                return data+b' ' if str(path)==target else data
            with patch.object(Path,'read_bytes',read),self.assertRaises(ValueError):validate_current()
        def changed_reader(path):
            data=original(path)
            return data+b'\nUNRELATED_RUNTIME_CHANGE = True\n' if str(path)=='hcl/cognition/reader_entry.py' else data
        with patch.object(Path,'read_bytes',changed_reader),self.assertRaises(ValueError):validate_current()
        report=json.loads(Path('reports/HCL_PLANNER_CONTRACT_SMOKE_CLOSURE.json').read_text())
        self.assertFalse(report['deliverable']);self.assertEqual(report['aggregate_calls'],11)
        self.assertEqual(report['receipt_sha256'],'88bb45c146ebe0f5f6f1bf745d8a0c786fb250c901558ceddf8c225f931f3de9')


if __name__=='__main__':unittest.main()
