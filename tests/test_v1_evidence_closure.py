import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.core import ClaimKind, Scope
from hcl.cognition.epistemic import prepare_epistemic
from hcl.cognition.evidence_closure import EvidenceClosureIndex
from hcl.cognition.episodic import EpisodicIndex
from hcl.cognition.positions import assess_positions


class EvidenceClosureTests(unittest.TestCase):
    def setUp(self):
        self.w=SemanticWorkspace()
        self.w.put_source('meeting','Mira said, "I believe the gate is open."\nMira added, "I believe the gate is open."\nMira replied, "I do not believe the gate is open."')
        semantic=self.w.prepare_semantic('What did Mira express?',source_ids=('meeting',))
        position=assess_positions(self.w.core,semantic)
        rows=position.current(self.w.core)
        self.yes=next(r['interpretation_id'] for r in rows if r['signal']=='AFFIRM')
        self.no=next(r['interpretation_id'] for r in rows if r['signal']=='DENY')
        self.index=EvidenceClosureIndex(self.w,episodic=EpisodicIndex(self.w))

    def select(self,target=None):
        return self.index.select(target or self.yes,query='What did Mira express and what disputes it?')

    def test_ordinary_input_selects_all_supports_and_challenge(self):
        result=self.select();payload=json.loads(result.messages[1]['content'])['cognition']
        target=next(r for r in payload['claim_nodes'] if r['id']==self.yes)
        self.assertEqual(len(target['support_groups']),2)
        self.assertEqual(target['support_group_semantics'],'ALTERNATIVES_OR')
        self.assertEqual(target['status'],'CHALLENGED')
        self.assertEqual(target['alternatives'],[self.no])
        self.assertEqual(len(target['challenges']),1)
        self.assertEqual(len(payload['source_spans']),3)
        self.assertTrue(all(row['episodic_event_refs'] for row in payload['source_spans']))
        self.assertIn('do not believe',result.messages[1]['content'])

    def test_challenge_withdrawal_recomputes_target_only(self):
        old=self.select();negative=self.select(self.no)
        source=next(k for k,s in self.w.core.spans.items() if s.quote.startswith('Mira replied') and '\n' not in s.quote)
        self.w.core.withdraw(source)
        with self.assertRaisesRegex(ValueError,'changed'):old.current_messages(self.index)
        current=self.select()
        self.assertEqual(json.loads(current.messages[1]['content'])['cognition']['target_status'],'SUPPORT_AVAILABLE')
        self.assertTrue(any(not r['active'] for r in json.loads(current.messages[1]['content'])['cognition']['source_spans']))
        self.assertIsNot(current,old)
        self.assertIsNot(negative,self.select(self.no))

    def test_unrelated_document_update_reuses_selected_closure(self):
        old=self.select();self.w.put_source('home','Noor said, "I believe the door is closed."')
        self.assertIs(old,self.select())
        self.w.put_source('home','Noor said, "I believe the door is open."')
        self.assertIs(old,self.select())
        self.assertEqual(self.index.recomputations[(self.yes,None)],1)

    def test_one_alternative_support_removed_without_erasing_other(self):
        old=self.select()
        first=next(k for k,s in self.w.core.spans.items() if s.quote.startswith('Mira said') and '\n' not in s.quote)
        self.w.core.withdraw(first)
        current=self.select();p=json.loads(current.messages[1]['content'])['cognition']
        yes=next(r for r in p['claim_nodes'] if r['id']==self.yes)
        self.assertEqual(sorted(g['grounded'] for g in yes['support_groups']),[False,True])
        self.assertEqual(p['target_status'],'CHALLENGED')
        self.assertIsNot(old,current)

    def test_and_support_obligations_never_reduced_to_one(self):
        scope=self.w.core.claims[self.yes].scope
        pair=self.w.core.claim(scope,ClaimKind.CONDITIONAL_TOOL_RESULT,dict(label='both'))
        spans=[k for k,s in self.w.core.spans.items() if s.quote.startswith(('Mira said','Mira added')) and '\n' not in s.quote]
        self.w.core.support(pair,*spans)
        result=self.index.select(pair,query='Are both reports supported?')
        item=next(r for r in json.loads(result.messages[1]['content'])['cognition']['claim_nodes'] if r['id']==pair)
        self.assertEqual(len(item['support_groups']),1)
        self.assertEqual(len(item['support_groups'][0]['members']),2)
        self.w.core.withdraw(spans[0])
        changed=self.index.select(pair,query='Are both reports supported?')
        self.assertEqual(json.loads(changed.messages[1]['content'])['cognition']['target_status'],'UNSUPPORTED')

    def test_revision_keeps_old_new_and_explicit_reason(self):
        scope=self.w.core.claims[self.yes].scope
        root=next(iter(self.w.core.spans))
        replacement=self.w.core.claim(scope,ClaimKind.SYSTEM_INTERPRETATION,dict(label='new analyst reading'))
        reason=self.w.core.claim(scope,ClaimKind.SOURCE_REPORT,dict(label='correction basis'))
        self.w.core.support(replacement,root);self.w.core.support(reason,root)
        self.w.core.replace_interpretation(self.yes,replacement,reasons=(reason,))
        p=json.loads(self.index.select(replacement,query='Why was the reading revised?').messages[1]['content'])['cognition']
        self.assertEqual(len(p['revisions']),1)
        self.assertEqual(p['revisions'][0]['kind'],'ANALYST_INTERPRETATION_REVISION_NOT_CHARACTER_CHANGE')
        self.assertEqual(p['target_status'],'SUPPORT_AVAILABLE')
        self.assertIn(self.yes,{r['id'] for r in p['claim_nodes']})
        self.assertIn(reason,{r['id'] for r in p['claim_nodes']})

    def test_rootless_cycle_cannot_appear_as_support(self):
        scope=self.w.core.claims[self.yes].scope
        a=self.w.core.claim(scope,ClaimKind.SYSTEM_INTERPRETATION,dict(label='cycle-a'))
        b=self.w.core.claim(scope,ClaimKind.SYSTEM_INTERPRETATION,dict(label='cycle-b'))
        self.w.core.support(a,b);self.w.core.support(b,a)
        p=json.loads(self.index.select(a,query='Is this reading supported?').messages[1]['content'])['cognition']
        self.assertEqual(p['target_status'],'UNSUPPORTED')
        self.assertEqual({r['id'] for r in p['claim_nodes']},{a,b})
        self.assertEqual(p['source_spans'],[])

    def test_full_closure_budget_refuses_without_dropping_counterevidence(self):
        with self.assertRaisesRegex(ValueError,'budget'):
            self.index.select(self.yes,query='Explain.',max_chars=1000)
        with self.assertRaisesRegex(ValueError,'node budget'):
            EvidenceClosureIndex(self.w,max_nodes=2).select(self.yes,query='Explain.')

    def test_access_revocation_cannot_expose_old_quotes(self):
        w=SemanticWorkspace()
        source='Mira said, "I believe the gate is open."'
        w.put_source('meeting',source,permitted_observers=('Mira',))
        semantic=w.prepare_semantic('What did Mira express?',source_ids=('meeting',),observer='Mira')
        target=assess_positions(w.core,semantic).interpretation_ids[0]
        index=EvidenceClosureIndex(w)
        old=index.select(target,observer='Mira',query='What did Mira express?')
        w.put_source('meeting',source,permitted_observers=())
        with self.assertRaisesRegex(ValueError,'access changed'):
            old.current_messages(index)
        with self.assertRaisesRegex(ValueError,'access changed'):
            index.select(target,observer='Mira',query='What did Mira express?')

    def test_observer_scope_and_hidden_source_are_not_crossed(self):
        self.w.put_source('private','Kai said, "Noor promised me a secret."',permitted_observers=('Kai',))
        self.assertNotIn('secret',self.select().messages[1]['content'])
        with self.assertRaisesRegex(ValueError,'observer scope'):
            self.index.select(self.yes,observer='Kai',query='What did Mira express?')
