"""F03 full recorded evidence closure and unrelated-source non-interference."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.evidence_closure import EvidenceClosureIndex
from hcl.cognition.episodic import EpisodicIndex
from hcl.cognition.positions import assess_positions


def witness():
    w=SemanticWorkspace()
    w.put_source('meeting','Mira said, "I believe the gate is open."\nMira added, "I believe the gate is open."\nMira replied, "I do not believe the gate is open."')
    w.put_source('home','Noor said, "I believe the door is closed."')
    semantic=w.prepare_semantic('What did Mira express?',source_ids=('meeting',))
    positions=assess_positions(w.core,semantic)
    yes=next(r['interpretation_id'] for r in positions.current(w.core) if r['signal']=='AFFIRM')
    index=EvidenceClosureIndex(w,episodic=EpisodicIndex(w))
    before=index.select(yes,query='What did Mira express and what disputes it?')
    state=json.loads(before.messages[1]['content'])['cognition']
    target=next(r for r in state['claim_nodes'] if r['id']==yes)
    assert state['target_status']=='CHALLENGED' and len(target['support_groups'])==2
    assert len(state['source_spans'])==3 and all(r['episodic_event_refs'] for r in state['source_spans'])
    w.put_source('home','Noor said, "I believe the door is open."')
    assert index.select(yes,query='What did Mira express and what disputes it?') is before
    denial=next(k for k,s in w.core.spans.items() if s.quote.startswith('Mira replied'))
    w.core.withdraw(denial)
    after=index.select(yes,query='What did Mira express and what disputes it?')
    assert json.loads(after.messages[1]['content'])['cognition']['target_status']=='SUPPORT_AVAILABLE'
    assert any(not r['active'] for r in json.loads(after.messages[1]['content'])['cognition']['source_spans'])
    return dict(schema='hcl-f03-positive-witness-v1',
        capability_delta='Selected conclusion carries all source support alternatives and counterevidence; removing a challenge recomputes it while an unrelated source edit reuses the closure.',
        actual_final_messages=dict(challenged=before.messages,after_withdrawal=after.messages),
        recomputations={str(k):v for k,v in index.recomputations.items()},
        implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',
        activation='OPT_IN',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_F03_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
