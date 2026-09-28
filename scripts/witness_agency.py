"""C01 positive agency join and dependent goal-abandonment revision."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.agency import prepare_agency


def witness():
    source = '\n'.join(('Mira said, "I want to reach shelter."',
        'Mira said, "To reach shelter, my subgoal is to find the path."',
        'Mira said, "I am considering a plan to cross the bridge in order to reach shelter."',
        'Mira said, "I plan to cross the bridge in order to reach shelter."',
        'Mira said, "I have an opportunity to cross the bridge."',
        'Mira said, "I completed my goal to find the path."'))
    workspace = CognitionWorkspace()
    workspace.put_source('authored-c01-scene', source)
    before = prepare_agency(workspace, "What are Mira's goals and plans?", source_id='authored-c01-scene')
    assert before.payload['plans'][0]['pursuit_check'] == 'SOURCE_SUPPORTED_PURSUIT_NOT_WORLD_FEASIBILITY'
    assert {g['goal']: g['status'] for g in before.payload['goals']} == {'find the path': 'COMPLETED', 'reach shelter': 'ACTIVE'}
    original_messages = before.messages(workspace)
    workspace.put_source('authored-c01-scene', source + '\nMira said, "I abandoned my goal to reach shelter."')
    after = prepare_agency(workspace, "What are Mira's goals and plans?", source_id='authored-c01-scene')
    assert after.payload['plans'][0]['pursuit_check'] == 'GOAL_NOT_REPORTED_ACTIVE'
    assert after.payload['plans'][0]['selection'] == 'REPORTED_SELECTED'
    return dict(schema='hcl-c01-positive-witness-v1',
        capability_delta='Explicit goal, plan selection and opportunity support a bounded pursuit join; a subgoal completion leaves the parent active, while later explicit parent abandonment changes the dependent plan check without inventing plan abandonment or intended causation.',
        original_source=source, before_actual_final_messages=original_messages, after_actual_final_messages=after.messages(workspace),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_C01_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
