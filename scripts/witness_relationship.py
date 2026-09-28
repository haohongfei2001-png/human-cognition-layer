"""E01 directional regard, counterevidence and explicit local revision."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.relationships import prepare_relationship

SOURCE = '\n'.join(('Narrator: In coding, Noor found the bug.',
    'Mira said, "In coding, I trust Noor\'s competence because Noor found the bug."',
    'Mira said, "In coding, I am unsure about Noor\'s honesty because the accounts differ."'))
QUERY = "How does Mira regard Noor's competence in coding?"


def witness():
    w = CognitionWorkspace()
    revised = SOURCE + '\nNarrator: In coding, Noor missed the bug.\nMira said, "In coding, I now distrust Noor\'s competence instead of trusting it because Noor missed the bug."'
    cases = dict(initial=(SOURCE, QUERY), honesty=(SOURCE, QUERY.replace('competence', 'honesty')),
        reverse=(SOURCE, "How does Noor regard Mira's competence in coding?"),
        counterevidence=(SOURCE + '\nNarrator: In coding, it is false that Noor found the bug.', QUERY), revised=(revised, QUERY))
    results = {}
    for name, (text, query) in cases.items():
        w.put_source('authored-e01-scene', text)
        results[name] = prepare_relationship(w, query, source_id='authored-e01-scene').messages(w)
    states = {name: json.loads(messages[1]['content']) for name, messages in results.items()}
    assert states['initial']['status'] == 'TRUST'
    assert states['honesty']['status'] == 'CHARACTER_UNCERTAIN'
    assert states['reverse']['status'] == 'SYSTEM_INSUFFICIENT'
    assert states['counterevidence']['status'] == 'TRUST'
    assert states['counterevidence']['current_reports'][0]['basis_current']['status'] == 'CONTESTED_SOURCE_BASIS'
    assert states['revised']['status'] == 'DISTRUST'
    return dict(schema='hcl-e01-positive-witness-v1',
        capability_delta='Keep regard directional and domain/aspect-specific; counterevidence changes its source basis without rewriting a reported attitude, while explicit anchored revision changes only that local report.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_E01_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
