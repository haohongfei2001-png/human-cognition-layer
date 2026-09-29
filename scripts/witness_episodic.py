"""F01 authorized retrieval preserves contradiction and exact source anchors."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.episodic import EpisodicIndex


def witness():
    w=SemanticWorkspace()
    w.put_source('chapter-one','Noor said, "I believe the bridge is open."\nMira said, "I believe the bridge is closed."',permitted_observers=('Mira',))
    w.put_source('chapter-two','Noor said, "I now believe the bridge is closed instead of open."',permitted_observers=('Mira',))
    index=EpisodicIndex(w)
    before=index.retrieve('What evidence concerns the bridge?',observer='Mira');messages=before.messages(index)
    assert len(before.payload['events'])==3
    w.put_source('private','Kai said, "The bridge is unsafe."',permitted_observers=('Kai',))
    assert index.retrieve('What evidence concerns the bridge?',observer='Mira').messages(index)==messages
    w.put_source('chapter-two','Noor said, "I now believe the bridge is repaired."',permitted_observers=('Mira',))
    after=index.retrieve('What evidence concerns the bridge?',observer='Mira')
    assert index.index_builds=={'chapter-one':1,'chapter-two':2}
    for row in after.payload['events']:
        assert w._documents[row['source_id']][0][row['start']:row['end']]==row['summary']
    return dict(schema='hcl-f01-positive-witness-v1',capability_delta='Retrieve source-local episodes, opposing propositions and transitions with exact originals, permission isolation and changed-chapter reindexing.',
        actual_final_messages=dict(before=messages,after=after.messages(index)),hidden_source_noninterference=True,
        index_builds=index.index_builds,implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_F01_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
