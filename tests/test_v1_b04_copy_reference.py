"""Literal copy reference regressions; broader unclassified cue scopes stay deferred."""
import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
from hcl.cognition import CognitionWorkspace
from hcl.cognition.report_provenance import prepare_reports
from tests.test_v1_report_provenance import N,K,L,COPY_K,COPY_L,M

FIXTURE=Path('eval/b04_copy_reference_counterexamples_v1.json')
QUERY='What does Mira believe?'


def prepare(text):
    w=CognitionWorkspace();w.put_source('scene',text)
    return w,prepare_reports(w,QUERY,source_id='scene')


class CopyReferenceTests(unittest.TestCase):
    def test_frozen_counterexamples_and_positive_controls(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),'60167873ae475a197058b470a35ee813fc882db1475d7e8d58ed3d6189b3b021')
        for case in json.loads(FIXTURE.read_text())['cases']:
            with self.subTest(case=case['case_id']):
                if case['expected_contract']=='REJECT_UNRESOLVED_LAST_STATEMENT':
                    with self.assertRaisesRegex(ValueError,'copy cue requires'):prepare(case['source'])
                else:
                    w,r=prepare(case['source']);self.assertEqual(r.current(w.core)['current_provenance_family_count'],1)

    def test_unsupported_latest_copier_modal_does_not_fall_back(self):
        deep='Kai said, "I believe Mira believes Noor believes Lena believes Sana believes the gate is open."'
        with self.assertRaisesRegex(ValueError,'copy cue requires'):prepare('\n'.join((N,K,deep,COPY_K)))

    def test_inline_conditional_speech_does_not_replace_actual_latest_utterance(self):
        for who in ('Noor','Kai'):
            w,r=prepare('\n'.join((N,K,f'If {who} said, "I prefer tea."',COPY_K)))
            p=r.current(w.core);self.assertEqual(p['current_provenance_family_count'],1)
            self.assertIsNone(p['independent_support_count'])

    def test_quoted_inner_actor_is_not_an_independent_speaker(self):
        for who in ('Noor','Kai'):
            quote=f'Lena said, "For example, {who} said \'I prefer tea.\'"'
            w,r=prepare('\n'.join((N,K,quote,COPY_K)))
            self.assertEqual(r.current(w.core)['current_provenance_family_count'],1)
        # The actual outer speaker did utter this nonmental example, so their
        # own latest statement cannot silently refer to an older belief.
        outer='Noor said, "For example, Lena said \'I prefer tea.\'"'
        with self.assertRaisesRegex(ValueError,'copy cue requires'):prepare('\n'.join((N,K,outer,COPY_K)))

    def test_narrator_attribution_is_not_a_subject_statement(self):
        text='Narrator: Noor believes Mira believes the gate is open.\n'+K+'\n'+COPY_K
        with self.assertRaisesRegex(ValueError,'copy cue requires'):prepare(text)

    def test_same_single_semantic_preparation_and_no_provider_subcall(self):
        w=CognitionWorkspace();w.put_source('scene','\n'.join((N,K,COPY_K)))
        with patch.object(w,'prepare_semantic',wraps=w.prepare_semantic)as call:
            r=prepare_reports(w,QUERY,source_id='scene')
        self.assertEqual(call.call_count,1);self.assertNotIn('backend',call.call_args.kwargs)
        self.assertEqual(r.current(w.core)['provider_calls'],0)

    def test_copy_conflict_and_direct_contrary_report_keep_existing_boundaries(self):
        w,r=prepare('\n'.join((N,K,COPY_K,L,COPY_L,M)));p=r.current(w.core)
        self.assertEqual(p['report_occurrences'],4);self.assertEqual(p['current_provenance_family_count'],2)
        self.assertEqual(p['assessment'][0]['status'],'REPORT_CONFLICT')
        self.assertIsNone(p['independent_support_count']);self.assertEqual(p['independence'],'NOT_ESTABLISHED')
        family=next(f for f in p['provenance_families']if f['relation_claim_ids'])
        w.core.withdraw(family['relation_claim_ids'][0]);later=r.current(w.core)
        self.assertEqual(next(f for f in later['provenance_families']if f['claim_id']==family['claim_id'])['support_status'],'UNSUPPORTED')
        self.assertIsNone(later['independent_support_count'])

    def test_hidden_source_never_participates_in_reference_resolution(self):
        w=CognitionWorkspace();w.put_source('scene','SECRET\n'+COPY_K,permitted_observers=('Noor',))
        r=prepare_reports(w,QUERY,source_id='scene',observer='Kai')
        self.assertEqual(r.current(w.core)['missing_evidence'],'SYSTEM_INSUFFICIENT')
        self.assertNotIn('SECRET',str(r.messages(w.core)))

    def test_source_revision_invalidates_previous_family(self):
        text='\n'.join((N,K,COPY_K));w,old=prepare(text)
        w.put_source('scene','\n'.join((N,K,'Noor said, "I prefer tea."',COPY_K)))
        self.assertEqual(old.current(w.core)['current_provenance_family_count'],0)
        with self.assertRaisesRegex(ValueError,'copy cue requires'):prepare_reports(w,QUERY,source_id='scene')
        self.assertEqual(w._versions['scene'],2)


if __name__=='__main__':unittest.main()
