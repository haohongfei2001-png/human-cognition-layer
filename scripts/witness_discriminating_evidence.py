"""H02 finite source-discriminating retrieval and ordinary rival update."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition.discriminating_evidence import DiscriminatingEvidenceWorkspace

ARGUMENTS = '''Mira: In choice, I conclude choice is free because Mira could leave.
Noor: In choice, I conclude choice is not free because Mira was pressured.'''
EVIDENCE = '''Narrator: In choice, Mira could leave.
Narrator: In choice, Mira was not pressured.'''
QUESTION = 'Why do Mira and Noor disagree about freedom?'


def witness():
    w = DiscriminatingEvidenceWorkspace('argument-source')
    w.put_source(ARGUMENTS, recorded_at='2026-04-01T00:00:00Z',
                 permitted_observers=('Analyst',))
    before = w.prepare_evidence(QUESTION, observer='Analyst')
    assert before.payload['stop_reason'] == 'NO_INFORMATION_GAIN_STOP'
    w.put_evidence_source('chapter-evidence', EVIDENCE,
        recorded_at='2026-04-02T00:00:00Z', permitted_observers=('Analyst',))
    after = w.prepare_evidence(QUESTION, observer='Analyst')
    assert [r['conditional_status'] for r in after.payload['rivals']] == [
        'ALL_PREMISES_SOURCE_SUPPORTED', 'WEAKENED_BY_COUNTEREVIDENCE']
    assert [step['gain'][0]['gain'] for step in after.payload['retrieval_steps']] == [
        'SOURCE_REPORTED_SUPPORT', 'SOURCE_REPORTED_COUNTEREVIDENCE']
    return dict(schema='hcl-h02-positive-witness-v1',
        capability_delta='Two source-reported rival arguments begin unresolved; finite F01 retrieval of separately authorized evidence adds direct support to one premise and counterevidence to the other, then stops without selecting a world-true winner.',
        ordinary_argument_source=ARGUMENTS, ordinary_evidence_source=EVIDENCE,
        ordinary_question=QUESTION, before=before.payload, after=after.payload,
        actual_final_model_messages=after.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_H02_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, separators=(',', ':')) + '\n')
