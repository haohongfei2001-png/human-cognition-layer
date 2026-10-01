"""Authored ordinary-source entry witness; not benchmark efficacy evidence."""
import argparse,json
from pathlib import Path
from hcl.cognition import CognitionWorkspace

SOURCE='Mira said, “I want to help the team.”\nMira added, “I plan to call Rowan in order to help the team if the room is open.”\nMira said, “I have an opportunity to call Rowan.”\nMira said, “I believe the room is open.”'
QUERY='What does the text support about this plan, and what remains unknown?'

class NoExtraction:
 def complete_json(self,*args,**kwargs):raise AssertionError('local supported input must not spend extraction')

def witness():
 w=CognitionWorkspace();w.put_source('meeting-record',SOURCE)
 output=json.dumps(dict(answer='Mira reports a conditional plan.',source_citations=[dict(source_id='meeting-record',quote='I plan to call Rowan in order to help the team if the room is open.',version=1)],uncertainty='Private intention and world feasibility unknown.',assumptions='Only source-reported statements.'))
 calls=[]
 result=w.answer_reader_entry(QUERY,lambda m:calls.append(m) or output,source_ids=('meeting-record',),backend=NoExtraction())
 entry=result['prepared'];payload=json.loads(result['actual_final_messages'][-2]['content'])
 plan=payload['checked_plan_feasibility'][0]['plans'][0]
 assert result['answer']==output and result['answer_raw']==output and len(calls)==1
 assert entry.receipt['checked_treatment_present'] and entry.receipt['extraction_calls']==0
 assert plan['world_feasibility']=='NOT_ESTABLISHED' and plan['deliberate_impossibility']=='NOT_INFERRED'
 w.put_source('meeting-record',SOURCE+'\nMira said, “I now believe the room is closed instead of the room is open.”')
 try:entry.current_messages(w)
 except ValueError:revision=True
 else:raise AssertionError('old support survived source revision')
 return dict(schema='hcl-adaptive-reader-v19-witness',status='PASS_PROVIDER_FREE',
  capability_delta='ordinary source entry selects actual B01/C01/C03 state before spending optional extraction; caller source ID/revision preserved',
  source=SOURCE,query=QUERY,actual_final_messages=result['actual_final_messages'],
  entry_receipt=entry.receipt,raw_answer=output,source_citation_audit=result['source_citation_audit'],
  revision_invalidates=revision,provider_calls=0,provider_spend_usd=0,
  answer_backend='STUB_NOT_PROVIDER',semantic_certification=False,answer_gain=False,
  evidence='AUTHORED_CORRECTNESS_NOT_BENCHMARK_OR_INDEPENDENT_EFFICACY',longmemeval='SEALED_NOT_ACCESSED')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
 Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('ADAPTIVE_READER_V19_PASS_PROVIDER_FREE')
