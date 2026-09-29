"""Provider-free default-entry coverage on an already exposed dev distribution.

No answers or gold are accessed, scored, logged, or sent to a model.
"""
import argparse
import hashlib
import json
from pathlib import Path

from hcl.v1 import HCLCognitionLayer, prepare_person_context
from scripts.serious_eval_contract import runtime_digest


DATASET_SHA256 = 'e9cbb1daff74b70a6cd15641ba2f602a925761759200a17c9225aca90018a42b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def audit(path):
    raw = Path(path).read_bytes()
    if sha(raw) != DATASET_SHA256:
        raise ValueError('development dataset bytes changed')
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        item = json.loads(line)
        text = item['document']
        question = item['questions'][0]['question_text']
        prepared = prepare_person_context(HCLCognitionLayer(lambda _: ''),
                                          question, text)
        payload = json.loads(prepared.messages[-1]['content'])
        if (payload['query'] != question or len(payload['sources']) != 1 or
                payload['sources'][0]['text'] != text or
                prepared.preparation_receipt['specialized_cognition_treatment'] is not False or
                prepared.preparation_receipt['extraction_provider_calls'] != 0):
            raise ValueError('default ordinary long-source coverage failed')
        rows.append(dict(passage_id=item['metadata']['passage_id'],
                         source_sha256=sha(text.encode()), source_chars=len(text),
                         question_sha256=sha(question.encode()),
                         candidate_count=prepared.preparation_receipt['candidate_count'],
                         final_input_chars=len(prepared.messages[-1]['content']),
                         full_source_present=True))
    if len(rows) != 25 or len({r['passage_id'] for r in rows}) != 25:
        raise ValueError('complete 25-story development set required')
    return dict(schema='hcl-i02-long-source-default-coverage-v1',
                dataset_sha256=DATASET_SHA256, runtime_sha256=runtime_digest(),
                ordinary_entry='prepare_person_context(DEFAULT_CONTEXT)',
                rows=rows, complete_source_count=len(rows),
                specialized_cognition_treatment=False,
                confirmation_qualified=False, provider_calls=0,
                provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        raise ValueError('do not overwrite coverage receipt')
    target.write_text(json.dumps(audit(args.dataset), indent=2, sort_keys=True) + '\n')
    print('I02_DEFAULT_LONG_SOURCE_COVERAGE_PASS')
