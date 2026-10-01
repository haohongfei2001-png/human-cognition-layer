"""Observe authored source-scope contrasts without constructing a provider."""
import argparse
import hashlib
import json
from pathlib import Path

from hcl.cognition import CognitionWorkspace
from scripts.serious_eval_contract import runtime_digest


SPEECH = 'Eva said, “I believe the gate is clear.”'
CASES = {
    'ordinary_statement': SPEECH,
    'inline_hypothetical': 'In a hypothetical scenario, ' + SPEECH,
    'inline_counterfactual': 'In a counterfactual scenario, ' + SPEECH,
    'imagined_preamble': 'The following conversation was imagined. ' + SPEECH,
    'actual_discussion': 'After reading a hypothetical example, ' + SPEECH,
    'actual_resumption': 'The following conversation was imagined. ' + SPEECH +
        ' In reality, Noor said, “I believe the gate is blocked.”',
}


def witness():
    rows = []
    for label, source in CASES.items():
        workspace = CognitionWorkspace()
        workspace.put_source('scene', source)
        entry = workspace.prepare_reader_entry('Which views does this account report?',
            source_ids=('scene',))
        payload = json.loads(entry.messages[-1]['content'])
        rows.append(dict(case=label, source=source,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            source_complete=payload['sources'][0]['text'] == source,
            checked_treatment_present=entry.receipt['checked_treatment_present'],
            checked_speakers=[r['speaker'] for r in
                payload.get('checked_epistemic', {}).get('epistemic_objects', [])],
            extraction_calls=entry.receipt['extraction_calls']))
    return dict(schema='hcl-qualified-speech-scope-witness-v1',
        runtime_sha256=runtime_digest(), cases=rows,
        origin='NEW_AUTHORED_PROVIDER_FREE_CORRECTNESS_CONTRASTS',
        provider_calls=0, answer_calls=0, provider_spend_usd=0,
        semantic_answer_improvement_established=False, native_task_utility_established=False,
        scope='BOUNDED_SOURCE_QUALIFICATION_NOT_GENERAL_DISCOURSE_UNDERSTANDING')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
