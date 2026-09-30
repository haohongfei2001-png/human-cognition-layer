"""Development-exposed original narrative: metadata screening only, no arm run.

A history-negative result cannot qualify task semantics, source rights, reviewer
independence or model-training novelty. No NarrativeQA question/gold is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
from scripts.i02_exposure_history import audit_history
from scripts.i02_exposure_snapshot import audit_snapshot

PACKAGE = Path('reports/HCL_I02_GASKELL_DEVELOPMENT_CANDIDATE.json')
PACKAGE_SHA256 = '3e198a2357124497333309bc7df22b43f57c833492f8718170d21d2afc3d9e7c'
RAW_SHA256 = '8fdafc01407ce9a54fa5b68135009d41f1eac1cdf71819b7bae03184d46a11eb'
BODY_SHA256 = '3a51cd3465537a94ab034d292435b23cfeaf822b9c2aa6addf66f33590a4ad91'
QUESTION = "Across the complete narrative, how do the central person's views of other people and possible life choices develop? Distinguish source-supported developments from later narration, uncertain motives and counterfactual claims."
QUESTION_SHA256 = 'cdb79b4bc48d01d24824d0d898d4f176c8dd2ed6dc35b6ca987ca0c4402511b9'
RAW_URL = 'https://www.gutenberg.org/files/4268/4268-0.txt'
RDF_URL = 'https://www.gutenberg.org/ebooks/4268.rdf'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_body(raw):
    if sha(raw) != RAW_SHA256:
        raise ValueError('fixed publisher text edition drift')
    text = raw.decode('utf-8-sig')
    start = '*** START OF THE PROJECT GUTENBERG EBOOK COUSIN PHILLIS ***'
    end = '*** END OF THE PROJECT GUTENBERG EBOOK COUSIN PHILLIS ***'
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('complete original body boundaries required')
    container = text.split(start, 1)[1].split(end, 1)[0].strip()
    title = 'PART I\r\n\r\n\r\n'
    if container.count(title) != 1 or container.index(title) != 200:
        raise ValueError('non-author front matter boundary drift')
    body = container[200:].strip()
    if sha(body.encode()) != BODY_SHA256 or len(body) != 217526:
        raise ValueError('complete body drift; no excerpt or normalized rewrite')
    return body


def publisher_metadata(raw):
    root = ET.fromstring(raw)
    ns = {'d': 'http://purl.org/dc/terms/', 'pg': 'http://www.gutenberg.org/2009/pgterms/'}
    got = {k: [e.text for e in root.findall('.//' + tag, ns)] for k, tag in
           [('titles', 'd:title'), ('authors', 'pg:name'), ('deathdates', 'pg:deathdate'), ('rights', 'd:rights')]}
    expected = dict(titles=['Cousin Phillis'], authors=['Gaskell, Elizabeth Cleghorn'],
                    deathdates=['1865'], rights=['Public domain in the USA.'])
    if got != expected:
        raise ValueError('publisher attribution, title, death date or rights metadata drift')
    return got


def ordinary_input(body):
    # No dataset gold, diagnosis, hidden actor state, manual route or H-only labels.
    return dict(question=QUESTION, source_text=body)


def load_package():
    raw = PACKAGE.read_bytes()
    if sha(raw) != PACKAGE_SHA256:
        raise ValueError('fixed protected metadata package drift')
    p = json.loads(raw)
    if (p['raw_url'] != RAW_URL or p['raw_sha256'] != RAW_SHA256 or
            p['source_sha256'] != BODY_SHA256 or p['ordinary_question'] != QUESTION or
            p['question_sha256'] != QUESTION_SHA256 or p['confirmation_qualified'] is not False or
            p['source_used_for_runtime_repair'] is not False or p['native_qa_or_gold_used'] is not False or
            p['provider_calls'] != 0 or p['provider_spend_usd'] != 0 or
            p['longmemeval'] != 'SEALED_NOT_ACCESSED'):
        raise ValueError('fixed development source boundary drift')
    return p


def ordinary_entry_probe(body):
    from hcl.v1 import HCLCognitionLayer, prepare_person_context
    from scripts.serious_eval_contract import runtime_digest
    calls=[]
    def prohibited_answer(_):
        calls.append(1)
        raise AssertionError('source qualification cannot invoke an H answer')
    try:
        prepared=prepare_person_context(HCLCognitionLayer(prohibited_answer),QUESTION,body)
        result=dict(status='PREPARED_NOT_EXECUTED',final_messages_sha256=sha(json.dumps(prepared.messages,sort_keys=True,ensure_ascii=False).encode()),
            specialized_cognition_treatment=prepared.preparation_receipt.get('specialized_cognition_treatment'),
            candidate_count=prepared.preparation_receipt.get('candidate_count'))
    except ValueError:
        result=dict(status='REFUSED_COMPLETE_LONG_SOURCE',refusal_type='ValueError',final_messages_sha256=None)
    if calls:raise ValueError('unexpected H call')
    return dict(result,runtime_sha256=runtime_digest(),source_characters=len(body),complete_source_not_truncated=True,
                source_text_displayed=False,h_provider_calls=0)


def screen(repository, raw, rdf):
    p = load_package()
    body = original_body(raw)
    if sha(rdf) != p['publisher_metadata_sha256']:
        raise ValueError('fixed rights metadata drift')
    meta = publisher_metadata(rdf)
    # No implementation/preparation repair uses this development candidate. Source holder
    # applies only existing negative exposure screens and returns fingerprints.
    history = audit_history(repository, body)
    snapshot = audit_snapshot(repository, 'HEAD', body)
    clean = (history['status'] == 'REACHABLE_HISTORY_NO_TEXT_MATCH' and
             snapshot['status'] == 'TEXT_SNAPSHOT_NO_MATCH')
    return dict(schema='hcl-i02-gaskell-development-history-screen-v1',
        status='READY_FOR_DEVELOPMENT_SOURCE_HOLDER_REVIEW' if clean else 'EXPOSURE_REVIEW_REQUIRED',
        package_sha256=sha(PACKAGE.read_bytes()), publisher_metadata=meta,
        publisher_metadata_sha256=sha(rdf), raw_sha256=sha(raw),
        source_sha256=sha(body.encode()), source_characters=len(body),
        question_sha256=sha(QUESTION.encode()),
        ordinary_input_sha256=sha(json.dumps(ordinary_input(body), sort_keys=True).encode()),
        complete_original_body=True, history=history, snapshot=snapshot,
        h_ordinary_entry_probe=ordinary_entry_probe(body),
        source_text_displayed=True, native_gold_used=False, h_entry_executed=False,
        source_used_for_runtime_repair=False, task_fit='PENDING_SOURCE_FIRST_REVIEW',
        model_training_novelty='UNKNOWN_PUBLIC_CANONICAL_ORIGINAL_WORK',
        rights_scope=p['rights_scope'], confirmation_qualified=False,
        permission_scope=p['permission_scope'], provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


def download(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    receipt = screen(args.repository, download(RAW_URL), download(RDF_URL))
    receipt['github_run_id'] = __import__('os').environ.get('GITHUB_RUN_ID')
    receipt['github_sha'] = __import__('os').environ.get('GITHUB_SHA')
    Path(args.output).write_text(json.dumps(receipt, indent=2) + '\n')
    print('PROTECTED_HISTORY_METADATA_WRITTEN_NO_SOURCE_GOLD_ARM_OR_PROVIDER_OUTPUT')
