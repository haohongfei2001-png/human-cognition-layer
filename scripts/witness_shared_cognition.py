"""Development witness only; no external corpus, provider, gold or secret access."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace


def witness():
    w = CognitionWorkspace()
    definition = 'Alice: In team, by fair I mean consent is true.'
    condition = 'Narrator: In team, proposal has consent false.'
    belief = 'Alice: In team, I believe proposal is fair.'
    query = "Compare Alice's belief and meaning of fair for proposal in team."
    w.put_source('meeting', '\n'.join((definition, condition, belief)))
    w.put_source('home', 'Bob: In home, I believe dinner is good.')
    before = w.prepare(query, source_ids=('meeting',))
    before_receipt = w.receipt(before)
    bob = w.prepare('What does Bob believe?', source_ids=('home',))
    invalidated = w.put_source('meeting', '\n'.join((definition, condition.replace('false', 'true'), belief)))
    after = w.prepare(query, source_ids=('meeting',))
    assert w.prepare('What does Bob believe?', source_ids=('home',)) is bob
    relation = lambda p: json.loads(p.messages[-1]['content'])['composed_cognition']['belief_concept_comparison']['rows'][0]['relation']
    assert relation(before) == 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA'
    assert relation(after) == 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA'
    assert set(before.claim_ids) <= invalidated
    assert not set(bob.claim_ids) & invalidated
    digest = hashlib.sha256()
    for path in sorted(Path('hcl').rglob('*.py')):
        digest.update(str(path).encode() + b'\0' + path.read_bytes())
    return dict(schema='hcl-a01-positive-witness-v1', runtime_sha256=digest.hexdigest(),
        capability_delta='Source correction revises the dependent belief/concept comparison; unrelated Bob state stays identical without reexecution.',
        before=before_receipt, after=w.receipt(after),
        before_relation=relation(before), after_relation=relation(after),
        invalidated_claim_ids=sorted(set(before.claim_ids) & invalidated),
        unrelated_preserved=True, actual_preparation_executions=w.executions,
        provider_calls=0, provider_spend_usd=0, efficacy='UNTESTED',
        ordinary_input='REPLAY_VERIFIED_BOUNDED_LEGACY_GRAMMAR',
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_A01_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
