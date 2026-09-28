"""D05 individual views, scoped authority and selective coordination update."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.joint_plan import prepare_joint_plan

SOURCE = '\n'.join(('Mira said, "I want to publish the report."',
    'Mira said, "I plan to draft the report in order to publish the report."',
    'Mira said, "I have an opportunity to draft the report."',
    'Noor said, "I want to publish the report."',
    'Noor said, "I plan to publish the report in order to publish the report."',
    'Noor said, "I have an opportunity to publish the report."',
    'Kai said, "I want to publish the report."',
    'Kai said, "I plan to review the report in order to publish the report."',
    'Kai said, "I have an opportunity to review the report."',
    'Mira said, "In team, I propose the joint plan to publish the report."',
    "Narrator: Noor and Kai heard Mira's last statement.",
    'Noor said, "I accept Mira\'s joint plan in team to publish the report."',
    "Narrator: Mira and Kai heard Noor's last statement.",
    'Kai said, "I accept Mira\'s joint plan in team to publish the report."',
    "Narrator: Mira and Noor heard Kai's last statement.",
    'Narrator: In team, only editor may authorize the plan to publish the report.',
    'Narrator: In team, Mira is editor.',
    'Mira said, "In team, I authorize Noor to publish the report."',
    "Narrator: Noor heard Mira's last statement."))
QUERY = 'Can Mira, Noor and Kai carry out the joint plan to publish the report in team?'


def witness():
    w = SemanticWorkspace()
    incomplete = SOURCE.replace("Narrator: Mira and Noor heard Kai's last statement.", "Narrator: Mira heard Kai's last statement.")
    cases = dict(no_authority='\n'.join(SOURCE.splitlines()[:15]), authorized=SOURCE,
        revoked=SOURCE + '\nMira said, "I revoke my authorization for Noor to publish the report in team."',
        missing_peer_receipt=incomplete, later_peer_receipt=incomplete + "\nNarrator: Noor later heard Kai's last statement.")
    results = {}
    for name, text in cases.items():
        w.put_source('authored-d05-scene', text)
        results[name] = prepare_joint_plan(w, QUERY, source_id='authored-d05-scene').messages(w)
    states = {name: json.loads(messages[1]['content']) for name, messages in results.items()}
    assert states['no_authority']['status'] == 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED'
    assert states['authorized']['status'] == 'COORDINATION_PREMISES_SUPPORTED'
    assert states['revoked']['status'] == 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED'
    assert states['missing_peer_receipt']['status'] == 'PEER_COORDINATION_RECEIPTS_INCOMPLETE'
    assert states['later_peer_receipt']['status'] == 'COORDINATION_PREMISES_SUPPORTED'
    for name in ('Mira', 'Kai'):
        before = next(p for p in states['missing_peer_receipt']['participants'] if p['actor'] == name)
        after = next(p for p in states['later_peer_receipt']['participants'] if p['actor'] == name)
        assert before['peer_endorsement_receipts'] == after['peer_endorsement_receipts']
    return dict(schema='hcl-d05-positive-witness-v1',
        capability_delta='Three distinct participants coordinate only under their own grounded plans, endorsements and receipt paths; scoped permission and revocation update final-action eligibility without transferring authority or creating a group mind.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_D05_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
