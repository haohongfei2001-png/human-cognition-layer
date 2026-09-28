"""B02 authored three-person access witness; provider-free."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CommunicationScene


def witness():
    source = '\n'.join(('Mira said, "I believe the gate is open."',
        "Narrator: Noor heard Mira's last statement.",
        "Narrator: Kai missed Mira's last statement.",
        "Narrator: Mira's last statement was publicly available.",
        'Noor said, "I do not believe the gate is open."',
        'Kai said, "I am unsure whether the road is safe."'))
    scene = CommunicationScene(source)
    rows = {}
    for actor in ('Mira', 'Noor', 'Kai'):
        view = scene.view(actor)
        workspace, bundle = view.epistemic('What was expressed?')
        rows[actor] = dict(visible_source=view.visible_text, authorizer_audit=list(view.access_audit),
            actual_final_messages=bundle.messages(workspace.core, 'What was expressed?'))
    assert 'the gate is open' not in rows['Kai']['visible_source']
    assert 'the gate is open' not in str(rows['Kai']['actual_final_messages'])
    assert rows['Mira']['visible_source'] != rows['Noor']['visible_source'] != rows['Kai']['visible_source']
    updated = CommunicationScene(source + "\nNarrator: Kai later heard Mira's last statement.")
    later = updated.view('Kai')
    assert 'the gate is open' in later.visible_text
    assert updated.view('Kai', through_line=6).visible_text == rows['Kai']['visible_source']
    workspace, bundle = later.epistemic('What was expressed?')
    return dict(schema='hcl-b02-positive-witness-v1',
        capability_delta='The same communication yields three distinct source-bounded inputs; later explicit receipt changes Kai only and preserves the earlier snapshot.',
        original_source=source, views=rows, later_kai_final_messages=bundle.messages(workspace.core, 'What was expressed?'),
        provider_calls=0, provider_spend_usd=0, implementation='CORRECTNESS_VERIFIED',
        ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_B02_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
