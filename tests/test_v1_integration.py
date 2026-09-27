"""Independent synthetic integration behavior, never external benchmark scores."""
from dataclasses import replace
import ast
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind
from hcl.v07 import HCLV07Runtime, IntentionEvidenceEvent, IntentionSignal
from hcl.v08 import HCLV08Runtime, AffectEvidenceEvent, AffectKind, EvidenceStrength
from hcl.v09 import CausalModel, StructuralRule, SCOPE as CAUSAL_SCOPE
from hcl.v10 import ArgumentFramework, Argument, Attack, SCOPE as ARG_SCOPE
from hcl.v1 import CognitionRequest as Request, CognitionRouter, CostClass, HCLCognitionLayer, ToolRequest, EvidenceLevel


def event(eid='e1', text='Alice left the room.', actor='Alice', observers=(), metadata=None, minute=1):
    time = f'2026-01-01T00:{minute:02d}:00+00:00'
    return EventRecord(eid, time, text, 'synthetic-source', time, actor, tuple(observers), metadata=metadata or {})


class Backend:
    def complete_json(self, messages, **kwargs):
        return json.dumps({'belief_evidence': [{'subject_agent_id': 'Bob',
            'proposition_key': 'resign', 'signal': 'AFFIRM', 'evidence_kind': 'SELF_REPORT',
            'supersedes_proposition_key': None, 'evidence_text': 'I believe I will resign.'}], 'challenge_relations': []})


class RoutingTests(unittest.TestCase):
    def plan(self, text, **kw): return CognitionRouter().plan(Request(text, **kw))
    def test_plain_fact_direct(self):
        p = self.plan('What city is mentioned?')
        self.assertTrue(p.direct); self.assertEqual(p.cost_class, CostClass.ZERO)
        self.assertEqual(p.extraction_provider_calls, 0)
    def test_access_task(self):
        p = self.plan('Alice left before Bob revealed X. What does Alice know?')
        self.assertIn('belief', p.capabilities); self.assertIn('perspective', p.capabilities)
        self.assertNotIn('affect', p.capabilities)
    def test_statement_plan(self):
        p = self.plan('Alice says she plans to resign tomorrow.')
        self.assertIn('intention', p.optional_capabilities); self.assertIn('provenance', p.capabilities)
        self.assertNotIn('affect', p.capabilities)
    def test_action_emotion_requires_uncertainty(self):
        p = self.plan('Alice slammed the door. Is she angry?')
        self.assertIn('affect', p.optional_capabilities); self.assertIn('uncertainty', p.capabilities)
    def test_counterfactual_without_model_blocked(self):
        p = self.plan('If X had not happened, would Y still occur?')
        self.assertIn('causal', p.blocked_tools); self.assertNotIn('causal', p.tools)
    def test_incidental_evidence_does_not_activate(self):
        p = self.plan('What city is mentioned?', evidence=(event(text='Alice plans to travel to Paris and feels happy.'),))
        self.assertTrue(p.direct)
    def test_bilingual_access(self):
        self.assertIn('perspective', self.plan('A 没听到 B 的计划，后来 C 告诉 A 一部分。A 知道什么？').capabilities)
    def test_bilingual_fact(self): self.assertTrue(self.plan('提到了哪个城市？').direct)
    def test_unknown_tools_cannot_enter(self):
        with self.assertRaises(ValueError): self.plan('Run', tools=(ToolRequest('value_research', 'e1', {}),))
    def test_no_automatic_nl_argument_graph(self):
        p = self.plan('Which argument is convincing?')
        self.assertEqual(p.tools, ())
    def test_semantic_plan_does_not_change_with_history_labels(self):
        self.assertEqual(self.plan('What city is mentioned?').capabilities,
                         self.plan('What city is mentioned?', history=('some dataset label',)).capabilities)
    def test_explicit_scope_only_minimal(self):
        p=self.plan('What city is mentioned?', target_actor='Alice')
        self.assertIn('source_visibility',p.capabilities);self.assertNotIn('belief',p.capabilities)


class LayerTests(unittest.TestCase):
    def prepare(self, query, **kw):
        return HCLCognitionLayer(lambda messages: 'answer').prepare(Request(query, **kw))
    def test_direct_constructs_no_runtime_one_answer(self):
        model=Mock(return_value='Paris')
        with patch('hcl.v07.HCLV07Runtime', side_effect=AssertionError('unexpected runtime')):
            self.assertEqual(HCLCognitionLayer(model).answer('What city is mentioned?'), 'Paris')
        model.assert_called_once()
    def test_base_model_object_adapter_and_debug_receipt(self):
        class Model:
            complete = Mock(return_value='Insufficient evidence.')
        model=Model()
        receipt=HCLCognitionLayer(model).answer('What does Alice know?',target_actor='Alice',debug=True)
        self.assertEqual(receipt.answer,'Insufficient evidence.');model.complete.assert_called_once()
    def test_narrator_does_not_leak_and_metadata_is_not_prompt(self):
        secret=event('secret','Hidden code is 9182.', None, metadata={'reader_only':True})
        public=event('public','The city is Paris.', 'Bob', ('Alice',), {'gold':'private answer'})
        p=self.prepare('What does Alice know?',evidence=(secret,public),target_actor='Alice')
        self.assertEqual([e['event_id'] for e in p.context.evidence],['public'])
        self.assertNotIn('9182',str(p.messages));self.assertNotIn('private answer',str(p.messages))
    def test_second_order_boundary_and_history_not_forwarded(self):
        private=event('private','Bob plans to leave.', 'Bob')
        joint=event('joint','Bob said hello.', 'Bob', ('Alice',))
        p=self.prepare('What does Alice believe Bob knows?',evidence=(private,joint),target_actor='Bob',observer_actor='Alice',history=('Secret is 9182.',))
        self.assertEqual([e['event_id'] for e in p.context.evidence],['joint'])
        self.assertNotIn('9182',str(p.messages));self.assertEqual(p.context.perspective['order'],2)
    def test_bitemporal_scope(self):
        old=event('old',minute=1);future=event('future',minute=5)
        late=replace(event('late',minute=1),recorded_at='2026-01-01T00:08:00+00:00')
        p=self.prepare('What does Alice know?',target_actor='Alice',evidence=(old,future,late),event_time='2026-01-01T00:02:00+00:00',knowledge_cutoff='2026-01-01T00:03:00+00:00')
        self.assertEqual([e['event_id'] for e in p.context.evidence],['old'])
    def test_missing_actor_fails_closed(self):
        p=self.prepare('Who knows the secret?',evidence=(event(text='Private secret is 9182.'),))
        self.assertEqual(p.context.evidence,[]);self.assertNotIn('9182',str(p.messages))
    def test_system_unknown_not_character_uncertain(self):
        p=self.prepare('Is Alice angry?',evidence=(event(text='Alice slammed the door.'),),target_actor='Alice')
        self.assertEqual(p.context.affect_evidence,[])
        self.assertTrue(any(x['status']=='SYSTEM_INSUFFICIENT' for x in p.context.uncertainty))
        self.assertNotIn('CHARACTER_UNCERTAIN',p.context.serialized())
    def test_action_not_motive(self):
        p=self.prepare('Why did Alice go away?',evidence=(event(),),target_actor='Alice')
        self.assertEqual(p.context.explicit_intention,[]);self.assertEqual(p.context.affect_evidence,[])
    def test_third_party_not_private_truth(self):
        runtime=HCLV07Runtime();source=event(text='Alice probably wants a promotion.',actor='Bob',observers=('Alice',))
        runtime.ingest_event(source)
        runtime.ingest_intention_evidence(IntentionEvidenceEvent('i1',source.event_id,'Alice','promotion',IntentionSignal.THIRD_PARTY_ATTRIBUTION,BeliefEvidenceKind.THIRD_PARTY_REPORT,source.valid_time,source.recorded_at,source.raw_text))
        p=HCLCognitionLayer(lambda m:'answer',intentions=runtime).prepare(Request('What does Alice want?',target_actor='Alice'))
        self.assertEqual(p.context.explicit_intention[0]['evidence_level'],EvidenceLevel.THIRD_PARTY_REPORT.value)
        self.assertNotIn('DIRECT_SELF_REPORT',p.context.serialized())
    def test_combined_perspective_belief_intention_with_partial_report(self):
        runtime=HCLV07Runtime()
        private=event('p','I believe I will resign. I plan to resign tomorrow.', 'Bob')
        partial=event('s','Bob mentioned making a change.', 'C', ('Alice',),minute=2)
        runtime.perspectives.ingest_event(private,Backend());runtime.ingest_event(partial)
        runtime.ingest_intention_evidence(IntentionEvidenceEvent('i1','p','Bob','resign',IntentionSignal.EXPLICIT_INTENTION,BeliefEvidenceKind.SELF_REPORT,private.valid_time,private.recorded_at,'I plan to resign tomorrow.'))
        layer=HCLCognitionLayer(lambda m:'answer',intentions=runtime)
        hidden=layer.prepare(Request('What does Alice believe Bob intends, and why?',target_actor='Bob',observer_actor='Alice'))
        self.assertEqual(hidden.context.belief,[]);self.assertEqual(hidden.context.explicit_intention,[])
        own=layer.prepare(Request('What does Bob believe and plan?',target_actor='Bob'))
        self.assertEqual(own.context.belief[0]['status'],'AFFIRMED')
        self.assertEqual(own.context.explicit_intention[0]['goal_key'],'resign')
        self.assertEqual(own.context.affect_evidence,[])
        self.assertNotIn('promotion',str(hidden.messages))
    def test_shared_affect_runtime_direct_report_only_when_selected(self):
        runtime=HCLV08Runtime();source=event(text='I feel relieved.')
        runtime.ingest_event(source)
        runtime.ingest_affect_evidence(AffectEvidenceEvent('a1','e1','Alice','trip',AffectKind.EMOTION,EvidenceStrength.DIRECT,'relief',BeliefEvidenceKind.SELF_REPORT,source.valid_time,source.recorded_at,source.raw_text))
        layer=HCLCognitionLayer(lambda m:'answer',affects=runtime)
        p=layer.prepare(Request('How does Alice feel?',target_actor='Alice'))
        self.assertEqual(p.context.affect_evidence[0]['value'],'relief')
        p=layer.prepare(Request('What does Alice know?',target_actor='Alice'))
        self.assertEqual(p.context.affect_evidence,[])
    def test_budget_failure_preserves_uncertainty_without_truncating(self):
        p=self.prepare('What does Alice know?',target_actor='Alice',evidence=(event(text='A'*3000),),max_context_chars=512)
        self.assertEqual(p.context.evidence,[]);self.assertIn('context budget exceeded',p.context.serialized())
    def test_input_conflict_rejected_before_persistent_mutation(self):
        runtime=HCLV07Runtime();runtime.ingest_event(event())
        with self.assertRaises(ValueError):
            HCLCognitionLayer(lambda m:'',intentions=runtime).prepare(Request('What does Alice know?',target_actor='Alice',evidence=(event('new'),event(text='changed'))))
        self.assertEqual(len(runtime.perspectives.events),1)
    def test_transient_requests_do_not_share_events(self):
        layer=HCLCognitionLayer(lambda m:'')
        layer.prepare(Request('What does Alice know?',target_actor='Alice',evidence=(event(),)))
        p=layer.prepare(Request('What does Alice know?',target_actor='Alice'))
        self.assertEqual(p.context.evidence,[])


class ToolTests(unittest.TestCase):
    def prepare(self, source, tool, **kw):
        return HCLCognitionLayer(lambda m:'answer').prepare(Request('Compute the supplied operation.',evidence=(source,),tools=(tool,),**kw)).context
    def test_causal_conditional_and_no_evidence_mutation(self):
        source=event(text='X = U; Y = X',metadata={'causal_model_scope':CAUSAL_SCOPE})
        model=CausalModel('m','e1',('U','X','Y'),('U',),(StructuralRule('X','U','X = U'),StructuralRule('Y','X','Y = X')))
        c=self.prepare(source,ToolRequest('causal','e1',{'model':model,'target':'Y','observations':{'U':1},'interventions':{'X':0}}))
        self.assertEqual(c.tool_results[0].result['value'],0)
        self.assertEqual(len(c.evidence),1);self.assertEqual(c.belief,[])
        self.assertEqual(c.tool_results[0].evidence_level,'TOOL_CONDITIONAL_RESULT')
    def test_inaccessible_tool_no_execution(self):
        source=event(text='Hidden model.',actor='Bob')
        with patch('hcl.v1.tools.execute_tool',side_effect=AssertionError('private tool executed')):
            c=self.prepare(source,ToolRequest('causal','e1',{}),target_actor='Alice')
        self.assertEqual(c.tool_results,[]);self.assertEqual(c.evidence,[])
    def test_future_tool_no_execution(self):
        with patch('hcl.v1.tools.execute_tool',side_effect=AssertionError('future tool executed')):
            c=self.prepare(event(minute=5),ToolRequest('argumentation','e1',{}),event_time='2026-01-01T00:02:00+00:00')
        self.assertEqual(c.tool_results,[])
    def test_invalid_model_fails_closed(self):
        c=self.prepare(event(),ToolRequest('causal','e1',{'model':'guess','target':'X'}))
        self.assertEqual(c.tool_results,[]);self.assertEqual(c.uncertainty[0]['status'],'INVALID_TOOL_INPUT')
    def test_argument_extensions_not_world_truth(self):
        source=event(text='a; b; a attacks b; b attacks a',metadata={'argumentation_scope':ARG_SCOPE})
        graph=ArgumentFramework('f','e1',(Argument('a','a'),Argument('b','b')),(Attack('a','b','a attacks b'),Attack('b','a','b attacks a')))
        c=self.prepare(source,ToolRequest('argumentation','e1',{'framework':graph,'semantics':'preferred','target':'a'}))
        result=c.tool_results[0].result
        self.assertEqual(len(result['labellings']),2);self.assertFalse(result['skeptical'])
        self.assertEqual(c.belief,[]);self.assertTrue(result['not_world_truth'])
    def test_alternative_readings_no_winner(self):
        source=event(text='(Aa∧Ba); (Aa∨Ba); Aa',metadata={'formal_scope':'EXPLICIT_FORMAL_INPUT'})
        digest=hashlib.sha256(source.raw_text.encode()).hexdigest()
        rows=[{'id':'conjunction','source_sha256':digest,'premises':['(Aa∧Ba)'],'conclusion':'Aa'},
              {'id':'disjunction','source_sha256':digest,'premises':['(Aa∨Ba)'],'conclusion':'Aa'}]
        c=self.prepare(source,ToolRequest('formal_reading','e1',{'readings':rows}))
        self.assertEqual(c.tool_results[0].status,'READING_DEPENDENT');self.assertIsNone(c.tool_results[0].result['label'])
    def test_formal_equivalence(self):
        c=self.prepare(event(text='¬¬Aa; Aa',metadata={'formal_scope':'EXPLICIT_FORMAL_INPUT'}),ToolRequest('formal_verifier','e1',{'left':'¬¬Aa','right':'Aa'}))
        self.assertEqual(c.tool_results[0].status,'EQUIVALENT')
    def test_countermodel_witness_and_domain_limit(self):
        c=self.prepare(event(text='Aa; Ba',metadata={'formal_scope':'EXPLICIT_FORMAL_INPUT'}),ToolRequest('countermodel','e1',{'premises':['Aa'],'conclusion':'Ba','domain_size':1}))
        self.assertEqual(c.tool_results[0].status,'VERIFIED_FINITE_COUNTERMODEL')
    def test_formal_anchors_and_digest_required(self):
        source=event(text='Aa',metadata={'formal_scope':'EXPLICIT_FORMAL_INPUT'})
        c=self.prepare(source,ToolRequest('formal_verifier','e1',{'left':'Aa','right':'Ba'}))
        self.assertEqual(c.tool_results,[])
    def test_missing_tool_no_fabricated_graph(self):
        p=HCLCognitionLayer(lambda m:'answer').prepare(Request('Find the grounded extension of the attack graph.'))
        self.assertEqual(p.context.tool_results,[]);self.assertIn('argumentation',p.plan.blocked_tools)


class BoundaryTests(unittest.TestCase):
    def test_no_harness_or_provider_imports(self):
        for path in Path('hcl/v1').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                names=[]
                if isinstance(node,ast.Import): names=[x.name for x in node.names]
                elif isinstance(node,ast.ImportFrom): names=[node.module or '']
                for name in names:
                    self.assertFalse(name.split('.')[0] in {'eval','scripts','reports','openai','pandas'},(path,name))
    def test_invalid_scope_and_duplicate_sources(self):
        with self.assertRaises(ValueError): Request('query',event_time='2026-01-01')
        with self.assertRaises(ValueError): Request('query',observer_actor='Alice')
        with self.assertRaises(ValueError): Request('query',evidence=(event(),event(text='changed')))
    def test_internal_runtime_not_invoked_for_optional_unselected(self):
        runtime=HCLV07Runtime()
        with patch.object(runtime,'answer_context',side_effect=AssertionError('unselected intention')):
            HCLCognitionLayer(lambda m:'answer',intentions=runtime).prepare(Request('What does Alice know?',target_actor='Alice'))

if __name__=='__main__': unittest.main()
