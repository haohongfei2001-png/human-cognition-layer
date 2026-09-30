"""Reconstruct one fixed author-original source unit and native issue, not a solver.

No sampling by H results; no source rewriting. Only PDF layout and the inherited
bibliographic footnote for the preceding Russell quotation are removed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PDF_SHA256 = 'be913546c61c6627bfb861e3039b0147af7fb3717f9b1bee8fd6c3b33d980d52'
SOURCE_SHA256 = '268665309d08875af75ca4eceebdd9f367b474e0f86fdec27325af6476a4975e'
QUESTION = 'What would the error-theorist say about the morality of stealing?'
QUESTION_SHA256 = '11207a82743bc39bd399f6dae90f0003c751f8ec9ebd733fd4045bb2e8e15ab1'


def reconstruct(pages):
    text = '\n'.join(pages[i] for i in (205, 206))
    if text.count('7. Metaethics and Stealing\n') != 1:
        raise ValueError('fixed author section boundary missing')
    unit = text.split('7. Metaethics and Stealing\n', 1)[1]
    unit = re.sub(r'5  B\. Russell, History of Western Philosophy.*?5502mbp#page/n3/mode/2up\n', '', unit, flags=re.S)
    unit = re.sub(r'(?m)^(?:APPLIED ETHICS|Stealing|19[34])(?:\n|$)', '', unit)
    unit = ' '.join(unit.split())
    issues = ' '.join(pages[208].split())
    if ('10. ' + QUESTION + ' KEY TERMINOLOGY' not in issues or
            hashlib.sha256(unit.encode()).hexdigest() != SOURCE_SHA256 or
            not unit.endswith('most people would wish to.')):
        raise ValueError('source unit or native question extraction drift')
    return {'source_text': unit, 'ordinary_question': QUESTION}


def audit_pdf(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PDF_SHA256:
        raise ValueError('fixed publisher archive PDF mismatch')
    from pypdf import PdfReader
    reader = PdfReader(path)
    if len(reader.pages) != 264:
        raise ValueError('PDF edition mismatch')
    task = reconstruct({i: reader.pages[i].extract_text() for i in (205, 206, 208)})
    item = json.loads(Path('reports/HCL_I02_OBP_METAETHICS_DEVELOPMENT_SOURCE.json').read_text())
    if any(item[k] != v for k, v in task.items()):
        raise ValueError('saved source differs from pinned author source unit')
    return dict(pdf_sha256=PDF_SHA256, source_sha256=SOURCE_SHA256,
                question_sha256=QUESTION_SHA256, author_unit_reconstruction='EXACT_NORMALIZED_MATCH',
                source_characters=len(task['source_text']), provider_calls=0,
                provider_spend_usd=0, confirmation_qualified=False,
                longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(audit_pdf(args.pdf), indent=2) + '\n')
    print('AUTHOR_UNIT_RECONSTRUCTION_PASS_NO_PROVIDER_CALL')
