import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.episodic import EpisodicIndex
from hcl.cognition.identity_roles import prepare_identity_roles


class EpisodicTests(unittest.TestCase):
    def setup_index(self):
        w=SemanticWorkspace()
        w.put_source('chapter-one','Noor said, "I believe the bridge is open."\nMira said, "I believe the bridge is closed."',permitted_observers=('Mira',))
        w.put_source('chapter-two','Noor said, "I now believe the bridge is closed instead of open."',permitted_observers=('Mira',))
        return w,EpisodicIndex(w)

    def test_positive_retrieval_keeps_opposition_and_source_links(self):
        w,index=self.setup_index();result=index.retrieve('What evidence concerns the bridge?',observer='Mira')
        self.assertEqual(len(result.payload['events']),3)
        self.assertIn('closed',result.messages(index)[1]['content'])
        for row in result.payload['events']:
            self.assertEqual(w._documents[row['source_id']][0][row['start']:row['end']],row['excerpt'])
            self.assertEqual(row['summary'],row['excerpt'])
            self.assertEqual(index.fetch(row['event_id'],observer='Mira'),row)

    def test_person_proposition_transition_indexes(self):
        w,index=self.setup_index()
        result=index.retrieve('bridge',person='Mira',proposition='the bridge is closed')
        self.assertEqual(len(result.payload['events']),1)
        changed=index.retrieve('bridge',person='Noor',transition='instead of')
        self.assertEqual(changed.payload['events'][0]['source_id'],'chapter-two')

    def test_miss_is_not_ignorance_or_absence(self):
        w,index=self.setup_index();r=index.retrieve('weather forecast',observer='Mira')
        self.assertEqual(r.payload['status'],'RETRIEVAL_MISS')
        self.assertEqual(r.payload['missing_evidence'],'NOT_CHARACTER_IGNORANCE_OR_SOURCE_ABSENCE')

    def test_hidden_source_noninterference_and_fetch_refusal(self):
        w,index=self.setup_index();before=index.retrieve('bridge',observer='Mira').messages(index)
        w.put_source('private','Kai said, "The bridge is unsafe."',permitted_observers=('Kai',))
        self.assertEqual(index.retrieve('bridge',observer='Mira').messages(index),before)
        private=index.retrieve('unsafe',observer='Kai').payload['events'][0]
        with self.assertRaises(ValueError):index.fetch(private['event_id'],observer='Mira')
        self.assertEqual(index.retrieve('bridge',observer='Mira').messages(index),before)

    def test_changed_one_source_not_reindexed_other(self):
        w,index=self.setup_index();old=index.retrieve('bridge');old_id=old.payload['events'][0]['event_id']
        w.put_source('chapter-two','Noor said, "I now believe the bridge is repaired."',permitted_observers=('Mira',))
        with self.assertRaisesRegex(ValueError,'changed'):old.messages(index)
        new=index.retrieve('bridge');self.assertEqual(index.index_builds,{'chapter-one':1,'chapter-two':2})
        self.assertTrue(any('repaired' in r['excerpt'] for r in new.payload['events']))

    def test_removed_source_and_revoked_access_invalidate(self):
        w,index=self.setup_index();old=index.retrieve('bridge',observer='Mira')
        eid=next(r['event_id'] for r in old.payload['events'] if r['source_id']=='chapter-one')
        w.put_source('chapter-one',w._documents['chapter-one'][0],permitted_observers=())
        with self.assertRaises(ValueError):old.messages(index)
        with self.assertRaises(ValueError):index.fetch(eid,observer='Mira')
        w.remove_source('chapter-two')
        self.assertEqual(index.retrieve('bridge',observer='Mira').payload['events'],[])

    def test_source_order_not_real_event_time(self):
        w,index=self.setup_index();r=index.retrieve('bridge')
        self.assertTrue(all(x['event_time']=='NOT_INFERRED' for x in r.payload['events']))

    def test_conditional_prefix_and_pronoun_uncertainty_retained(self):
        w=SemanticWorkspace();w.put_source('s','Noor said, "Hello."\nIf she said, "The bridge is closed."')
        index=EpisodicIndex(w);row=index.retrieve('bridge').payload['events'][0]
        self.assertEqual(row['assertion_scope'],'CONDITIONAL_OR_EMBEDDED')
        self.assertEqual(row['speaker_resolution'],'UNRESOLVED_REFERENCE')
        self.assertTrue(row['source_line_context'].startswith('If she'))

    def test_duplicate_names_not_cross_document_identity(self):
        w,index=self.setup_index();rows=index.retrieve('bridge',person='Noor').payload['events']
        self.assertEqual(len({r['source_id'] for r in rows}),2)
        self.assertTrue(all(r['person_identity']=='SOURCE_LOCAL_ONLY' for r in rows))

    def test_native_operation_dependency_back_to_original_events(self):
        w=SemanticWorkspace();w.put_source('s','Noor said, "In team, I see myself as careful."\nNarrator: In team, Noor serves as reviewer.')
        operation=prepare_identity_roles(w,"How does Noor's self-description relate to the reviewer role in team?",source_id='s')
        index=EpisodicIndex(w)
        result=index.retrieve('Noor',dependency=operation.claim_ids[0])
        self.assertEqual(len(result.payload['events']),2)
        self.assertTrue(all(r['source_id']=='s' for r in result.payload['events']))

    def test_result_budget_is_explicit_partial_retrieval(self):
        w,index=self.setup_index();r=index.retrieve('bridge',max_events=1,max_chars=5000)
        self.assertEqual(len(r.payload['events']),1)
        self.assertTrue(r.payload['budget_truncated'])
        self.assertLessEqual(len(json.dumps(r.messages(index),ensure_ascii=False)),5000)
        with self.assertRaisesRegex(ValueError,'budget'):index.retrieve('bridge',max_chars=1000)

    def test_withdrawn_source_span_cannot_be_rendered(self):
        w,index=self.setup_index();r=index.retrieve('bridge');w.core.withdraw(r.payload['events'][0]['source_span_id'])
        with self.assertRaises(ValueError):r.messages(index)

    def test_no_provider_calls_during_indexing(self):
        class Backend:
            def complete_json(self,*args,**kwargs):raise AssertionError('unexpected provider')
        w=SemanticWorkspace(semantic_backend=Backend());w.put_source('s','Mira said, "The bridge is open."')
        index=EpisodicIndex(w);self.assertEqual(len(index.retrieve('bridge').payload['events']),1)
        self.assertEqual(w.backend_attempts,0)
