"""E03 separate self-story, others' attribution, role rules and endorsement."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.identity_roles import prepare_identity_roles

SOURCE = '\n'.join(('Mira said, "In team, I see myself as careful."',
    'Noor said, "In team, I see Mira as careless."',
    'Narrator: In team, Mira serves as reviewer.',
    'Narrator: In team, a reviewer is required to check every patch.',
    'Narrator: In team, Mira did not check every patch.',
    'Mira said, "In team, I reject the requirement for a reviewer to check every patch."'))
QUERY = "How does Mira's self-description relate to the reviewer role in team?"


def witness():
    w = SemanticWorkspace()
    cases = dict(initial=SOURCE,
        occupancy_without_endorsement='\n'.join(SOURCE.splitlines()[:-1]),
        self_revision=SOURCE + '\nMira said, "In team, I now see myself as learning instead of careful."',
        role_exit=SOURCE + '\nNarrator: In team, Mira no longer serves as reviewer.')
    results = {}
    for name, text in cases.items():
        w.put_source('authored-e03-scene', text)
        results[name] = prepare_identity_roles(w, QUERY, source_id='authored-e03-scene').messages(w)
    states = {name: json.loads(messages[1]['content']) for name, messages in results.items()}
    assert states['initial']['local_tension']
    assert states['initial']['current_self_descriptions'][0]['label'] == 'careful'
    assert states['initial']['requirement_endorsements'][0]['endorsement'] == 'REJECTS'
    assert states['occupancy_without_endorsement']['requirement_endorsements'][0]['endorsement'] == 'NOT_REPORTED'
    assert states['self_revision']['current_self_descriptions'][0]['label'] == 'learning'
    assert states['role_exit']['role_status'] == 'REPORTED_NOT_OCCUPANT'
    return dict(schema='hcl-e03-positive-witness-v1',
        capability_delta='Keep self-description, others attribution, role occupancy, local requirement, behavior and personal endorsement separate; source-anchored self revision and role exit update different channels.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_E03_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
