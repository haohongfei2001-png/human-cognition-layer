"""Authored direction/example scene-cue regressions, without provider transport."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch

from hcl.cognition import CognitionWorkspace, semantic
from scripts.development_embedded_scene_amendment import PREVIOUS_SEMANTIC_SHA
from scripts.development_executable_entry_amendment import validate_current
from scripts.serious_eval_contract import runtime_digest

BASELINE = 'e4230dd46a47ecdc0940f168bbae36b3149968c6'
PREFIX = 'The following conversation was imagined.\n\n'
SPEECH = 'Noor said, “I believe the gate is clear.”'
CASES = {
    'ordinary': SPEECH,
    'imagined': PREFIX + SPEECH,
    'bracketed_actual': PREFIX + '[Direction. In reality, a bell rang.]\n\n' + SPEECH,
    'fenced_actual': PREFIX + '```\nIn reality, a bell rang.\n```\n\n' + SPEECH,
    'real_actual': PREFIX + 'In reality, a bell rang.\n\n' + SPEECH,
    'bracketed_hypothetical': '[Example. This scene is hypothetical.]\n\n' + SPEECH,
    'fenced_hypothetical': '```\nThis scene is hypothetical.\n```\n\n' + SPEECH,
}


def observe():
    rows = []
    for label, source in CASES.items():
        workspace = CognitionWorkspace()
        workspace.put_source('scene', source)
        entry = workspace.prepare_reader_entry('Which views does this account report?', source_ids=('scene',))
        payload = json.loads(entry.messages[-1]['content'])
        rows.append(dict(case=label, source=source,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            source_complete=payload['sources'][0]['text'] == source,
            checked_treatment_present=entry.receipt['checked_treatment_present'],
            extraction_calls=entry.receipt['extraction_calls']))
    return rows


def witness():
    validate_current()
    code = subprocess.check_output(['git', 'show', BASELINE + ':hcl/cognition/semantic.py'])
    if hashlib.sha256(code).hexdigest() != PREVIOUS_SEMANTIC_SHA:
        raise ValueError('baseline semantic source hash mismatch')
    name = 'hcl.cognition._embedded_scene_baseline'
    old = types.ModuleType(name)
    old.__package__ = 'hcl.cognition'
    sys.modules[name] = old
    try:
        exec(compile(code, BASELINE + ':semantic.py', 'exec'), old.__dict__)
        with patch.object(semantic, '_local_candidates', old._local_candidates):
            before = observe()
    finally:
        sys.modules.pop(name, None)
    after = observe()
    assert [r['checked_treatment_present'] for r in before] == [True, False, True, True, True, False, False]
    assert [r['checked_treatment_present'] for r in after] == [True, False, False, False, True, True, True]
    assert all(r['source_complete'] and r['extraction_calls'] == 0 for r in before + after)
    return dict(schema='hcl-embedded-scene-cues-witness-v1', baseline_commit=BASELINE,
        current_runtime_sha256=runtime_digest(), before=before, after=after,
        origin='NEW_AUTHORED_PROVIDER_FREE_CORRECTNESS_CONTRASTS', provider_calls=0,
        provider_spend_usd=0, answer_gain_claimed=False, native_task_utility_established=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
