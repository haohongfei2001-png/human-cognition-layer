"""Compare original authored narrator-scope contrasts at the exact prior runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch

from hcl.cognition import CognitionWorkspace
from hcl.cognition import semantic
from scripts.development_narrator_actual_amendment import PREVIOUS_SEMANTIC_SHA
from scripts.development_c02_planned_input_amendment import validate_current
from scripts.serious_eval_contract import runtime_digest

BASELINE = '97b9bf187360860327ab573bae2217401b779ff0'
PREFIX = 'The following conversation was imagined.\n\n'
REPORT = 'Noor believes the gate is clear.'
CASES = {
    'ordinary_report': REPORT,
    'imagined_report': PREFIX + REPORT,
    'actual_resumption': PREFIX + 'In reality, a bell rang.\n\n' + REPORT,
    'spoken_transition': PREFIX + 'Eva said, “In reality, a bell rang.”\n\n' + REPORT,
    'stage_transition': PREFIX + '[Direction. In reality, a bell rang.]\n\n' + REPORT,
    'later_qualification': PREFIX + 'In reality, a bell rang.\n\nThis scene is hypothetical.\n\n' + REPORT,
}


def observe():
    rows = []
    for label, source in CASES.items():
        workspace = CognitionWorkspace()
        workspace.put_source('scene', source)
        entry = workspace.prepare_reader_entry('Which views does this account report?', source_ids=('scene',))
        payload = json.loads(entry.messages[-1]['content'])
        objects = payload.get('checked_epistemic', {}).get('epistemic_objects', [])
        rows.append(dict(case=label, source=source,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            source_complete=payload['sources'][0]['text'] == source,
            narrator_reports=sum(r['public_expression']['channel'] == 'SOURCE_NARRATOR_ATTRIBUTION' for r in objects),
            private_interpretations=sum(r['private_interpretation'] is not None for r in objects),
            extraction_calls=entry.receipt['extraction_calls']))
    return rows


def witness():
    validate_current()
    code = subprocess.check_output(['git', 'show', BASELINE + ':hcl/cognition/semantic.py'])
    if hashlib.sha256(code).hexdigest() != PREVIOUS_SEMANTIC_SHA:
        raise ValueError('baseline semantic source hash mismatch')
    name = 'hcl.cognition._narrator_scope_baseline'
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
    assert [r['narrator_reports'] for r in before] == [1, 0, 0, 0, 0, 0]
    assert [r['narrator_reports'] for r in after] == [1, 0, 1, 0, 0, 0]
    assert all(r['source_complete'] and r['extraction_calls'] == 0 and r['private_interpretations'] == 0
               for r in before + after)
    return dict(schema='hcl-narrator-actual-scope-witness-v1', baseline_commit=BASELINE,
        current_runtime_sha256=runtime_digest(), before=before, after=after,
        origin='NEW_AUTHORED_PROVIDER_FREE_CORRECTNESS_CONTRASTS', provider_calls=0,
        provider_spend_usd=0, answer_gain_claimed=False, native_task_utility_established=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
