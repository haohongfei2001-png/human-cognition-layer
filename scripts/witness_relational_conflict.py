"""E02 failure alternatives and explicit repair reports."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.relational_conflict import prepare_relational_conflict

SOURCE = '\n'.join(('Noor said, "I failed to deliver the report in coding."',
    'Noor said, "For the attempt to deliver the report in coding, at the time I did not know the requirements."',
    'Noor said, "For the attempt to deliver the report in coding, at the time I could not prevent the failure."',
    'Mira said, "In coding, I distrust Noor\'s reliability because Noor failed to deliver the report."'))
QUERY = "Explain Mira's response to Noor's failure to deliver the report in coding."
APOLOGY = '\nNoor said, "I apologize to Mira for failing to deliver the report in coding."'
RECEIPT = "\nNarrator: Mira heard Noor's last statement."
FORGIVE = '\nMira said, "In coding, I forgive Noor for failing to deliver the report."'


def witness():
    w = SemanticWorkspace()
    changed = SOURCE.replace('did not know', 'knew').replace('could not prevent', 'could prevent')
    changed += '\nNoor said, "For the attempt to deliver the report in coding, at the time I intended to fail to deliver the report."'
    cases = dict(information_and_control=SOURCE, stated_choice=changed,
        apology_received=SOURCE + APOLOGY + RECEIPT, forgiveness_reported=SOURCE + APOLOGY + RECEIPT + FORGIVE)
    results = {}
    for name, text in cases.items():
        w.put_source('authored-e02-scene', text)
        results[name] = prepare_relational_conflict(w, QUERY, source_id='authored-e02-scene').messages(w)
    states = {name: json.loads(messages[1]['content']) for name, messages in results.items()}
    assert states['information_and_control']['explanations'][0]['status'] == 'CONDITIONALLY_SUPPORTED'
    assert states['stated_choice']['explanations'][2]['status'] == 'CONDITIONALLY_SUPPORTED'
    assert states['apology_received']['repair_status'] == 'APOLOGY_RECEIVED_FORGIVENESS_UNKNOWN'
    assert states['forgiveness_reported']['repair_status'] == 'REPORTED_FORGIVENESS'
    assert all(state['relationship']['status'] == 'DISTRUST' for state in states.values())
    return dict(schema='hcl-e02-positive-witness-v1',
        capability_delta='Differentiate information/control constraints from informed controllable stated choice; receiving an apology is distinct from reported forgiveness and does not overwrite scoped relationship judgments.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_E02_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
