"""A03 ordinary-input challenge/withdrawal witness; no provider work."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import EvidenceCore, AuthorizedText, prepare_semantics, assess_positions


def witness():
    core = EvidenceCore()
    text = ('Mira said, "I believe the gate is open." '
            'Mira added, "I do not believe the gate is open." '
            'Noor said, "I believe the door is shut."')
    result = prepare_semantics('Compare their expressed positions.', (AuthorizedText('dialogue', text),), core=core)
    assessment = assess_positions(core, result)
    before = assessment.current(core)
    before_messages = assessment.messages(core, 'Compare their expressed positions.')
    root = next(k for k, span in core.spans.items() if 'do not believe' in span.quote)
    invalidated = core.withdraw(root)
    after = assessment.current(core)
    assert [r['support_status'] for r in before if r['actor'] == 'Mira'] == ['CHALLENGED', 'CHALLENGED']
    assert [r['support_status'] for r in after if r['actor'] == 'Mira'] == ['SUPPORT_AVAILABLE', 'UNSUPPORTED']
    assert [r for r in before if r['actor'] == 'Noor'] == [r for r in after if r['actor'] == 'Noor']
    return dict(schema='hcl-a03-positive-witness-v1',
        capability_delta='An explicit counterstatement contests only Mira; withdrawing its support restores the surviving expression without rewriting Noor or source history.',
        before=before, after=after, invalidated=sorted(invalidated),
        before_actual_final_messages=before_messages,
        after_actual_final_messages=assessment.messages(core, 'Compare their expressed positions.'),
        provider_calls=0, provider_spend_usd=0, implementation='CORRECTNESS_VERIFIED',
        ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_A03_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
