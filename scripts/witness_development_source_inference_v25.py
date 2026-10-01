"""Compare authored wires to certified v24; no provider or consumed-answer run."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from hcl.cognition import CognitionWorkspace
from hcl.cognition.reader_entry import _SOURCE_INFERENCE_POLICY
from scripts.development_drc008_replay import ARCHIVE, validate_archive
from scripts.development_runtime_amendment_v25 import validate_current

QUERY = 'Explain source-supported action and mental reports while preserving uncertainty.'
SOURCES = (
    'Lena moved a crate. The lamp broke.',
    'Lena said, "I intended to break the lamp." Lena moved a crate. The lamp broke.',
    'Omar said, "Lena intended to break the lamp." Lena moved a crate. The lamp broke.',
    'Lena denied intending to break the lamp. Later, Omar learned that the lamp broke.',
    'Lena said, "I believe the corridor is clear." Omar heard Lena\'s last statement.',
    'Lena believes the corridor is clear. Lena said, "I do not believe the corridor is clear." '
    'Lena said, "I plan to carry the crate in order to clear the room if the corridor is clear."',
)


def witness():
    validate_current()
    cert = validate_archive()
    env = dict(os.environ)
    # Witnesses have no transport; also withhold ambient provider access from
    # historical subprocesses rather than relying on the absence of invocation.
    for key in list(env):
        if key.endswith(('_API_KEY', '_AUTHORIZED')) or key == 'PYTHONPATH':
            env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix='hcl-v25-certified-before-') as tmp:
        with zipfile.ZipFile(ARCHIVE) as archive:
            for name in cert['files']:
                if name.startswith('hcl/') and name.endswith('.py'):
                    path = Path(tmp) / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(name))
        code = ('import json,sys;sys.path.insert(0,sys.argv[1]);'
                'from hcl.cognition import CognitionWorkspace;'
                'data=json.load(sys.stdin);results=[];'
                '\nfor source in data["sources"]:\n'
                ' w=CognitionWorkspace();w.put_source("scene",source);'
                'p=w.prepare_reader_entry(data["query"],source_ids=("scene",));'
                'results.append(dict(messages=p.messages,receipt=p.receipt))\n'
                'print(json.dumps(results))')
        before = json.loads(subprocess.run([sys.executable, '-c', code, tmp],
            input=json.dumps(dict(sources=SOURCES, query=QUERY)), text=True,
            capture_output=True, check=True, env=env).stdout)
        # Keep v24's unchanged historical witness executable against its exact
        # consumed runtime, instead of weakening its byte-equality/cost claims.
        historical = ('import json,sys;sys.path.insert(0,sys.argv[1]);'
                      'from scripts.witness_development_empty_state_v24 import witness as v24;'
                      'from scripts.witness_development_paragraph_access_v21 import witness as v21;'
                      'print(json.dumps(dict(v21=v21(),v24=v24())))')
        old_witness = json.loads(subprocess.run([sys.executable, '-c', historical, tmp],
            text=True, capture_output=True, check=True, env=env).stdout)
    rows = []
    for source, old in zip(SOURCES, before):
        w = CognitionWorkspace()
        w.put_source('scene', source)
        entry = w.prepare_reader_entry(QUERY, source_ids=('scene',))
        assert entry.messages[1:] == old['messages'][1:]
        assert entry.messages[0]['content'] == old['messages'][0]['content'] + ' ' + _SOURCE_INFERENCE_POLICY
        assert entry.receipt['checked_treatment_present'] == old['receipt']['checked_treatment_present']
        assert entry.current_messages(w) == entry.messages
        rows.append(dict(source=source, before_messages=old['messages'],
            actual_final_prepared_messages=entry.messages,
            checked_treatment_present=entry.receipt['checked_treatment_present'],
            boundary=entry.receipt['answer_inference_boundary'],
            source_and_checked_wire_identical=True, extraction_calls=entry.receipt['extraction_calls']))
    assert rows[-1]['checked_treatment_present']
    assert 'checked_reported_communication' in json.loads(rows[-2]['actual_final_prepared_messages'][-1]['content'])
    return dict(schema='hcl-source-inference-v25-witness', status='PASS_PROVIDER_FREE',
        before_main_sha=cert['run_sha'], before_runtime_sha256=cert['runtime_sha256'],
        capability_delta='Uniform source-bounded explanation instructions in the actual ordinary-reader final wire, without new semantic treatment or changed source/checker states.',
        authored_contrasts=rows, historical_witnesses_on_certified_v24=old_witness,
        evidence='IMPLEMENTED_UNVALIDATED_DELIVERY_POLICY',
        provider_calls=0, provider_spend_usd=0, answer_gain_claimed=False,
        semantic_certification=False, cost_saving_claimed=False,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print('SOURCE_INFERENCE_V25_PASS_PROVIDER_FREE')
