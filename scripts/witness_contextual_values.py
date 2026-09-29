"""E04 context change and conditional partial order, ordinary source only."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.contextual_values import prepare_contextual_values

SOURCE='\n'.join((
    'Mira said, "As reviewer in team, I prefer safety over speed if urgent is false."',
    'Mira said, "As reviewer in team, I prefer speed over safety if urgent is true."',
    'Narrator: In team, Mira serves as reviewer.',
    'Narrator: In team, urgent is true.',
    'Narrator: In team, Mira chose speed as reviewer.',
    'Narrator: In team, urgent is now false instead of true.',
    'Narrator: In team, Mira chose safety as reviewer.'))
QUERY="Compare Mira's contextual preferences in team."


def witness():
    w=SemanticWorkspace();w.put_source('authored-e04',SOURCE)
    r=prepare_contextual_values(w,QUERY,source_id='authored-e04')
    assert r.payload['choice_comparisons'][0]['explanation']=='CONTEXT_CHANGE_SUPPORTED_WITHOUT_PREFERENCE_REVISION'
    assert [c['alignment'] for c in r.payload['choices']]==['SUPPORTED_BY_LOCAL_COMPARISON']*2
    messages=r.messages(w)
    return dict(schema='hcl-e04-positive-witness-v1',capability_delta='Explain different choices by changed applicability of unchanged contextual preferences, keeping conditional partial orders, role tension and explicit revision distinct.',
        actual_final_messages=messages,implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_E04_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
