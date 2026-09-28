"""B04 ordinary report chains: copies are not independent support."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.report_provenance import prepare_reports


def witness():
    source = '\n'.join(('Noor said, "Mira believes the gate is open."',
        'Kai said, "Mira believes the gate is open."',
        "Narrator: Kai's last statement repeats Noor's last statement.",
        'Lena said, "Mira believes the gate is open."',
        "Narrator: Lena's last statement was copied from Kai's last statement.",
        'Mira said, "I do not believe the gate is open."'))
    workspace = CognitionWorkspace()
    workspace.put_source('authored-report-scene', source)
    report = prepare_reports(workspace, 'What does Mira believe?', source_id='authored-report-scene')
    payload = report.current(workspace.core)
    assert payload['report_occurrences'] == 4
    assert payload['current_provenance_family_count'] == 2
    assert payload['independent_support_count'] is None
    assert payload['assessment'][0]['status'] == 'REPORT_CONFLICT'
    final = report.messages(workspace.core)
    workspace.put_source('authored-report-scene', 'Mira said, "I am unsure whether the gate is open."')
    updated = prepare_reports(workspace, 'What does Mira believe?', source_id='authored-report-scene')
    assert updated.current(workspace.core)['assessment'][0]['status'] == 'CHARACTER_REPORTED_UNCERTAINTY'
    assert report.current(workspace.core)['report_occurrences'] == 0
    missing = prepare_reports(workspace, 'What does Kai believe?', source_id='authored-report-scene')
    assert missing.current(workspace.core)['missing_evidence'] == 'SYSTEM_INSUFFICIENT'
    return dict(schema='hcl-b04-positive-witness-v1',
        capability_delta='Three copied reports contract to one explicitly related provenance family; contrary self-report remains conflict, source correction invalidates old families, and character uncertainty stays distinct from system missing evidence.',
        source=source, actual_final_messages=final, corrected_final_messages=updated.messages(workspace.core),
        missing_evidence_final_messages=missing.messages(workspace.core),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_B04_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
