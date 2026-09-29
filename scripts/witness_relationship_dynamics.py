"""E05 source correction propagates without changing reported identity or regard."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hcl.cognition.relationship_dynamics import RelationshipDynamicsWorkspace

SOURCE='\n'.join((
    'Noor said, "I failed to deliver the report in team."',
    'Noor said, "For the attempt to deliver the report in team, at the time I did not know the requirements."',
    'Noor said, "For the attempt to deliver the report in team, at the time I could not prevent the failure."',
    'Noor said, "For the attempt to deliver the report in team, at the time I did not intend to fail to deliver the report."',
    'Mira said, "In team, I distrust Noor\'s reliability because Noor failed to deliver the report."',
    'Noor said, "In team, I see myself as careful."',
    'Narrator: In team, Noor serves as reviewer.',
    'Narrator: In team, a reviewer is required to deliver the report.',
    'Narrator: In team, Noor did not deliver the report.',
    "Narrator: In team, Noor's failure to deliver the report was the reviewer episode.",
    'Noor said, "As reviewer in team, I prefer safety over speed."'))
QUERY="Explain how Mira's view of Noor relates to the reviewer role and preferences in team after the failure to deliver the report."


def witness():
    w=RelationshipDynamicsWorkspace();w.put_source('team',SOURCE)
    before=w.prepare_dynamics(QUERY,source_id='team');before_messages=before.messages(w)
    w.put_source('club',SOURCE.replace('team','club'))
    other=w.prepare_dynamics(QUERY.replace('team','club'),source_id='club')
    old_other_messages=other.messages(w)
    changed=SOURCE.replace('did not know','knew').replace('could not prevent','could prevent').replace('did not intend','intended')
    w.revise_source('team',changed,kind='ANALYST_SOURCE_CORRECTION')
    after=w.prepare_dynamics(QUERY,source_id='team')
    assert after.payload['role_evaluation']['conditional_alternatives']==['INFORMED_CONTROLLABLE_STATED_CHOICE']
    assert set(after.payload['source_revision_comparison']['changed_channels'])=={'relationship_alternatives','role_alternatives'}
    assert w.prepare_dynamics(QUERY.replace('team','club'),source_id='club') is other
    assert old_other_messages==other.messages(w)
    return dict(schema='hcl-e05-positive-witness-v1',capability_delta='Source-corrected failure factors update coupled relationship and role explanations while preserving expressed identity, regard, preference and another domain.',
        actual_final_messages=dict(before=before_messages,after=after.messages(w)),unrelated_domain_unchanged=True,
        operation_counts={str(k):v for k,v in w.dynamics_executions.items()},implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_E05_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
