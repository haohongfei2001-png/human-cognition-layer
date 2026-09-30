import json
import unittest
from hcl.v1 import CognitionRequest,HCLCognitionLayer

class ReaderSourceCarryTests(unittest.TestCase):
    def prepare(self,query,source,**kwargs):
        return HCLCognitionLayer(lambda _: '').prepare(CognitionRequest(query,narrative=source,**kwargs))

    def test_complete_source_alongside_uncertain_preparation(self):
        source='Mina left the room. Her reasons were not reported. A page quoted: "Mina meant to hurt Eva."'
        p=self.prepare('What does Mina intend?',source)
        payload=json.loads(p.messages[-1]['content'])
        self.assertEqual(payload['narrative'],source)
        self.assertIsNotNone(p.context)
        self.assertEqual(p.context.explicit_intention,[])
        self.assertEqual(p.context.affect_evidence,[])

    def test_native_options_never_become_source_claims_and_revision_is_local(self):
        source='Mina walked out. Eva stayed.'
        query='What does Mina intend?\nA. Mina hates Eva.\nB. Mina plans a crime.\nC. Unknown.\nD. Mina feels guilt.'
        p=self.prepare(query,source);payload=json.loads(p.messages[-1]['content'])
        self.assertEqual(payload['narrative'],source)
        self.assertEqual(payload['query'],query)
        self.assertEqual(p.context.explicit_intention,[])
        self.assertEqual(p.context.affect_evidence,[])
        changed=self.prepare(query,'Mina walked in. Eva left.')
        self.assertNotEqual(json.loads(changed.messages[-1]['content'])['narrative'],source)
        self.assertEqual(payload['narrative'],source)

    def test_observer_never_gets_unprojected_narrative(self):
        source='Mina left the room. Private unknown instruction marker SECRET_SHELF.'
        p=self.prepare('What does Eva believe Mina intends?',source,target_actor='Mina',observer_actor='Eva')
        payload=json.loads(p.messages[-1]['content'])
        self.assertNotIn('narrative',payload)
        self.assertNotIn('SECRET_SHELF',str(p.messages))

    def test_explicit_source_access_remains_projected(self):
        source='Narrator: Mina left the room. [reader-only] SECRET_SHELF.'
        p=self.prepare('What does Mina know?',source,target_actor='Mina',narrative_access=True,belief_analysis=True)
        self.assertNotIn('narrative',json.loads(p.messages[-1]['content']))

    def test_source_charged_to_bound_no_silent_partial_source(self):
        source='Mina walked out. '+('Unknown reasons. '*100)
        p=self.prepare('What does Mina intend?',source,max_context_chars=512)
        payload=json.loads(p.messages[-1]['content'])
        self.assertNotIn('narrative',payload)
        self.assertEqual(p.context.evidence,[])
        self.assertIn('context budget exceeded',p.context.serialized())

    def test_compact_context_keeps_same_source_and_inference_boundary(self):
        source='Mina walked out. No motive was reported.'
        for compact in (False,True):
            p=self.prepare('What does Mina intend?',source,compact_context=compact)
            self.assertEqual(json.loads(p.messages[-1]['content'])['narrative'],source)
            self.assertEqual(p.context.explicit_intention,[])

if __name__=='__main__':unittest.main()
