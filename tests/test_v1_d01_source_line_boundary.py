"""Prevent a source-line mismatch from turning unrelated own speech into receipt."""
import json
import unittest
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.communication import CommunicationScene
from tests.test_v1_universal_question import Stub, operation, plan, run

PREFIX='Noor said, "Okay."'
PROMISE='Mira said, "I promise Noor to deliver the report if the permit arrives."'
CUE="Narrator: Noor heard Mira's last statement."
QUERY="What is the status of Mira's promise to Noor to deliver the report?"
QUESTION='Describe the source-reported promise and receipt without assuming private understanding.'
UNSUPPORTED=('\r','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029')


def answer(source):
    session=UniversalHCL();session.put_source('scene',source)
    port=Stub(plan(operation('D01',QUERY,['scene'])))
    return port,run(session,QUESTION,port)


class CommitmentSourceLineBoundaryTests(unittest.TestCase):
    def test_each_unsupported_separator_refuses_before_native_and_keeps_original_bytes(self):
        for separator in UNSUPPORTED:
            source=PREFIX+separator+PROMISE
            with self.subTest(separator=repr(separator)),patch('hcl.cognition.commitments.prepare_commitment')as native:
                port,result=answer(source)
                native.assert_not_called()
                row=result['operations'][0]
                self.assertEqual(row['status'],'D01_REQUIRES_LF_OR_CRLF_SOURCE')
                self.assertFalse(row['executed'])
                final=json.loads(port.calls[-1][1][-1]['content'])
                self.assertEqual(final['question'],QUESTION)
                self.assertEqual(final['sources'][0]['text'],source)
                self.assertEqual(final['sources'][0]['text'].encode(),source.encode())

    def test_lf_crlf_keep_no_receipt_distinct_from_actual_receipt(self):
        for separator in ('\n','\r\n'):
            for delivered in (False,True):
                source=PREFIX+separator+PROMISE+(separator+CUE if delivered else '')
                with self.subTest(separator=repr(separator),delivered=delivered):
                    port,result=answer(source);row=result['operations'][0]
                    self.assertEqual(row['status'],'D01_EXECUTED')
                    self.assertEqual(row['result']['commitment']['receipt'],'REPORTED_EXPOSURE' if delivered else 'EXPOSURE_UNKNOWN')
                    self.assertEqual(row['result']['commitment']['conditions_received'],delivered)
                    self.assertEqual(row['result']['original_source'],source)

    def test_native_b02_still_accepts_its_wider_line_representation(self):
        for separator in UNSUPPORTED:
            view=CommunicationScene(PREFIX+separator+PROMISE).view('Noor')
            self.assertEqual(view.visible_text,PREFIX)
            self.assertEqual(view.access_audit[1]['status'],'EXPOSURE_UNKNOWN')
            self.assertFalse(view.access_audit[1]['content_transmitted'])

    def test_guard_only_applies_to_selected_d01_source(self):
        session=UniversalHCL();session.put_source('scene',PREFIX+'\n'+PROMISE)
        other=PREFIX+'\r'+PROMISE;session.put_source('other',other)
        port=Stub(plan(operation('D01',QUERY,['scene'])))
        result=run(session,QUESTION,port)
        self.assertEqual(result['operations'][0]['status'],'D01_EXECUTED')
        self.assertFalse(result['operations'][0]['result']['commitment']['conditions_received'])
        sources=json.loads(port.calls[-1][1][-1]['content'])['sources']
        self.assertEqual(next(s['text']for s in sources if s['source_id']=='other'),other)


if __name__=='__main__':unittest.main()
