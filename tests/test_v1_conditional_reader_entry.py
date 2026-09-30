"""Nonliteral prose stays unverified while existing conditional checks execute."""
import copy
import json
import unittest
from hcl.cognition import CognitionWorkspace, ClaimKind
from hcl.cognition.retained import prepare_retained, prepare_retained_reader, answer_retained_reader

QUOTES = ('Dana expressed a desire to protect the gate.',
    'Dana described a conditional plan to call Noor to protect the gate, provided the gate was clear.',
    'Dana reported having the opportunity to call Noor.',
    'Dana expressed confidence that the gate was clear.',
    'The story explicitly stipulated a fictional model in which the gate was not clear.')
LINES = ('Dana: I want to protect the gate.',
    'Dana: I plan to call Noor in order to protect the gate if the gate is clear.',
    'Dana: I have an opportunity to call Noor.',
    'Dana: I believe the gate is clear.',
    'Narrator: In the declared model, it is false that the gate is clear.')
QUERY = 'Which actions are supported and what limits remain?'
SOURCE = '\n'.join(QUOTES)
def proposals():
    return [dict(source_id='meeting', quote=q, kind='event', content=dict(canonical_statement=l))
        for q,l in zip(QUOTES,LINES)]
class Backend:
    def __init__(self, rows=None): self.rows = proposals() if rows is None else rows; self.calls = []
    def complete_json(self, messages, **kwargs):
        self.calls.append(dict(messages=messages,parameters=kwargs))
        return json.dumps(dict(candidates=self.rows))
def payload(r): return json.loads(r.messages[-1]['content'])

class ConditionalReaderTests(unittest.TestCase):
    def workspace(self, source=SOURCE, observers=()):
        w = CognitionWorkspace(); w.put_source('meeting', source, permitted_observers=observers); return w

    def test_real_conditional_mechanisms_and_complete_original_final_inputs(self):
        w = self.workspace(); b = Backend()
        r = prepare_retained_reader(w, QUERY, source_ids=('meeting',), backend=b)
        p = payload(r); plan = p['checked_plan_feasibility'][0]['plans'][0]
        self.assertEqual(plan['subjective_feasibility'],'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(plan['model_condition_check'],'MODEL_CONDITION_CONTRADICTED')
        self.assertEqual(plan['deliberate_impossibility'],'NOT_INFERRED')
        self.assertEqual(p['shared_semantic_binding']['original_sources'][0]['text'],SOURCE)
        self.assertEqual(len(r.scope.assumptions),5)
        self.assertTrue(r.receipt['checked_treatment_present'])
        self.assertFalse(r.receipt['semantic_certification'])
        self.assertFalse(r.receipt['private_state_established'])
        self.assertFalse(r.receipt['world_truth_established'])
        self.assertTrue(all(w.core.claims[k].kind==ClaimKind.CONDITIONAL_TOOL_RESULT for k in r.operation_ids))
        self.assertEqual(w.core.claims[r.operation_ids[0]].content['retained_state']['checked_plan_feasibility'],p['checked_plan_feasibility'])

    def test_actual_translation_contract_and_raw_response_saved(self):
        w = self.workspace(); b = Backend(); r=prepare_retained_reader(w,QUERY,source_ids=('meeting',),backend=b)
        self.assertEqual(len(b.calls),1)
        self.assertEqual(r.receipt['actual_translation_requests'],b.calls)
        self.assertIn('UNVERIFIED TRANSLATION HYPOTHESIS',b.calls[0]['messages'][-1]['content'])
        self.assertIn('canonical_statement',b.calls[0]['messages'][-1]['content'])
        self.assertEqual(json.loads(r.receipt['raw_translation_response'])['candidates'],proposals())
        self.assertEqual(r.receipt['actual_final_messages'],r.messages)
        self.assertEqual(r.receipt['semantic_translation_status'],'CONDITIONAL_ON_UNVERIFIED_TRANSLATION')

    def test_source_revision_propagates_and_old_unverified_branch_cannot_answer(self):
        w=self.workspace(); before=prepare_retained_reader(w,QUERY,source_ids=('meeting',),backend=Backend())
        revised='Dana explicitly corrected the report: the gate was not clear rather than clear.'
        text=SOURCE+'\n'+revised; rows=proposals()+[dict(source_id='meeting',quote=revised,kind='event',content=dict(canonical_statement='Dana: I now believe it is false that the gate is clear instead of the gate is clear.'))]
        invalidated=w.put_source('meeting',text);self.assertTrue(set(before.operation_ids)<=invalidated)
        with self.assertRaises(ValueError):before.current_messages(w)
        after=prepare_retained_reader(w,QUERY,source_ids=('meeting',),backend=Backend(rows))
        self.assertEqual(payload(after)['checked_plan_feasibility'][0]['plans'][0]['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(payload(before)['checked_plan_feasibility'][0]['plans'][0]['subjective_feasibility'],'SUPPORTED_UNDER_REPORTED_BELIEFS')

    def test_semantic_challenge_stops_dependent_checked_result(self):
        w=self.workspace();r=prepare_retained_reader(w,QUERY,source_ids=('meeting',),backend=Backend())
        original=w.core.projections[r.translation_ids[0]];claim=w.core.claims[original]
        c=w.core.claim(claim.scope,ClaimKind.SYSTEM_INTERPRETATION,{'disputed':True})
        w.core.support(c,claim.content['source_span_id']);w.core.challenge(original,c)
        with self.assertRaises(ValueError):r.current_messages(w)
        w.core.withdraw(c);self.assertEqual(r.current_messages(w),r.messages)

    def test_source_access_filtered_before_any_translation_call(self):
        w=self.workspace(observers=('Analyst',));b=Backend()
        with self.assertRaises(ValueError):prepare_retained_reader(w,QUERY,source_ids=('meeting',),observer='Noor',backend=b)
        self.assertFalse(b.calls)

    def test_actor_cannot_be_renamed_or_pronoun_alternatives_silently_selected(self):
        text='Dana expressed confidence that the gate was clear.'
        for rows in ([dict(source_id='meeting',quote=text,kind='event',content=dict(canonical_statement='Mira: I believe the gate is clear.'))],
                     [dict(source_id='meeting',quote=text,kind='event',content=dict(canonical_statement=line)) for line in ('Dana: I believe the gate is clear.','Dana: I believe it is false that the gate is clear.')]):
            with self.assertRaises(ValueError):prepare_retained_reader(self.workspace(text),QUERY,source_ids=('meeting',),backend=Backend(rows))

    def test_later_knowledge_cross_source_and_bad_quotes_do_not_enter_checks(self):
        for query,sources in (('At statement 1, '+QUERY,('meeting',)),(QUERY,('meeting','other'))):
            w=self.workspace();w.put_source('other','Later Dana received an update.');b=Backend()
            with self.assertRaises(ValueError):prepare_retained_reader(w,query,source_ids=sources,backend=b)
            self.assertFalse(b.calls)
        rows=proposals();rows[0]['quote']='Dana never said this.'
        with self.assertRaises(ValueError):prepare_retained_reader(self.workspace(),QUERY,source_ids=('meeting',),backend=Backend(rows))

    def test_exactly_one_translation_and_one_final_call_from_ordinary_input(self):
        b=Backend();calls=[]
        r=self.workspace().answer_reader_semantic(QUERY,lambda m:calls.append(m) or 'correctness stub',source_ids=('meeting',),backend=b)
        self.assertEqual(len(b.calls),1);self.assertEqual(calls,[r['prepared'].messages])
        self.assertEqual(r['preparation_backend_calls'],1);self.assertEqual(r['answer_adapter_calls'],1)
        self.assertEqual(r['actual_final_messages'],calls[0])

    def test_backend_failure_and_context_failure_never_retry_or_call_final(self):
        class Failed(Backend):
            def complete_json(self,m,**kw):self.calls.append(m);raise RuntimeError('failed')
        b=Failed();calls=[]
        with self.assertRaises(RuntimeError):answer_retained_reader(self.workspace(),QUERY,lambda m:calls.append(m),source_ids=('meeting',),backend=b)
        self.assertEqual(len(b.calls),1);self.assertFalse(calls)
        with self.assertRaises(ValueError):answer_retained_reader(self.workspace(),QUERY,lambda m:calls.append(m),source_ids=('meeting',),backend=Backend(),max_chars=512)
        self.assertFalse(calls)

    def test_no_caller_moral_premise_or_legacy_unsupported_query_activation(self):
        b=Backend()
        with self.assertRaises(TypeError):prepare_retained_reader(self.workspace(),QUERY,source_ids=('meeting',),backend=b,responsibility_premises=('moral rule',))
        with self.assertRaises(ValueError):prepare_retained(self.workspace(),'Infer her secret motives.',source_ids=('meeting',),backend=b)
        self.assertFalse(b.calls)

if __name__=='__main__':unittest.main()
