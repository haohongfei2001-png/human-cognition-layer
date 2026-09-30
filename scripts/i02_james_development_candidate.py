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

PACKAGE = Path('reports/HCL_I02_JAMES_DEVELOPMENT_CANDIDATE.json')
PACKAGE_SHA256 = '506cb48194acdb68e294adc008d93829a9b22cde339bdec201125005565561ea'
RAW_SHA256 = 'c97205a1c4b5fe962e410ab09fcbb8faf3f663af15e63b59deaa5c7cbdf891d8'
BODY_SHA256 = '2090d6458cd1f81d669a71a137f40a03996e99fff016c1a0c95cee77e278fe4a'
QUESTION = "Across the complete story, how do the central person's views of self, other people and possible life choices change? Distinguish source-supported changes from uncertain motives or counterfactual claims."
QUESTION_SHA256 = '483634f5740d8d3b387b36c15defa6d57390dc8febcdc3f9ba399591f2114377'
RAW_URL = 'https://www.gutenberg.org/files/1190/1190.txt'
RDF_URL = 'https://www.gutenberg.org/ebooks/1190.rdf'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_body(raw):
    if sha(raw) != RAW_SHA256:
        raise ValueError('fixed publisher text edition drift')
    text = raw.decode('utf-8-sig')
    start = '***START OF THE PROJECT GUTENBERG EBOOK THE JOLLY CORNER***'
    end = '***END OF THE PROJECT GUTENBERG EBOOK THE JOLLY CORNER***'
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('complete original body boundaries required')
    container = text.split(start, 1)[1].split(end, 1)[0].strip()
    title = 'THE JOLLY CORNER\r\nby Henry James'
    if container.count(title) != 1 or container.index(title) != 104:
        raise ValueError('non-author front matter boundary drift')
    body = container[104:].strip()
    if sha(body.encode()) != BODY_SHA256 or len(body) != 80958:
        raise ValueError('complete body drift; no excerpt or normalized rewrite')
    return body


def publisher_metadata(raw):
    root = ET.fromstring(raw)
    ns = {'d': 'http://purl.org/dc/terms/', 'pg': 'http://www.gutenberg.org/2009/pgterms/'}
    got = {k: [e.text for e in root.findall('.//' + tag, ns)] for k, tag in
           [('titles', 'd:title'), ('authors', 'pg:name'), ('deathdates', 'pg:deathdate'), ('rights', 'd:rights')]}
    expected = dict(titles=['The Jolly Corner'], authors=['James, Henry'],
                    deathdates=['1916'], rights=['Public domain in the USA.'])
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
    return dict(schema='hcl-i02-james-development-history-screen-v1',
        status='READY_FOR_DEVELOPMENT_SOURCE_HOLDER_REVIEW' if clean else 'EXPOSURE_REVIEW_REQUIRED',
        package_sha256=sha(PACKAGE.read_bytes()), publisher_metadata=meta,
        publisher_metadata_sha256=sha(rdf), raw_sha256=sha(raw),
        source_sha256=sha(body.encode()), source_characters=len(body),
        question_sha256=sha(QUESTION.encode()),
        ordinary_input_sha256=sha(json.dumps(ordinary_input(body), sort_keys=True).encode()),
        complete_original_body=True, history=history, snapshot=snapshot,
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
