"""Protected original-narrative source screen; never display text or run an arm.

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

PACKAGE = Path('reports/HCL_I02_GILMAN_PROTECTED_CANDIDATE.json')
PACKAGE_SHA256 = '049004386187f2256ed81f6197fb18d255be4ea4a36ee52cf484f215259e0863'
RAW_SHA256 = 'a40cdaa300cd6850f2c18c2c8fd027339e53c9ed5ac0c01fe9cfe3b57cbca898'
BODY_SHA256 = '00b4236dc9b2b4215ace0af20da168e77cba5e9ba826c079b4714fb13abe2d49'
QUESTION = "Across this story, how does the narrator's view of her husband change, and how much can we infer about his intentions from her account?"
QUESTION_SHA256 = 'ea91105e433f809327597b73b7ed6b342b588b52617e3fb2d35f4d124b312ffc'
RAW_URL = 'https://www.gutenberg.org/files/1952/1952-0.txt'
RDF_URL = 'https://www.gutenberg.org/ebooks/1952.rdf'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_body(raw):
    if sha(raw) != RAW_SHA256:
        raise ValueError('fixed publisher text edition drift')
    text = raw.decode('utf-8-sig')
    start = '*** START OF THE PROJECT GUTENBERG EBOOK 1952 ***'
    end = '*** END OF THE PROJECT GUTENBERG EBOOK 1952 ***'
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError('complete original body boundaries required')
    body = text.split(start, 1)[1].split(end, 1)[0].strip()
    if sha(body.encode()) != BODY_SHA256 or len(body) != 31497:
        raise ValueError('complete body drift; no excerpt or normalized rewrite')
    return body


def publisher_metadata(raw):
    root = ET.fromstring(raw)
    ns = {'d': 'http://purl.org/dc/terms/', 'pg': 'http://www.gutenberg.org/2009/pgterms/'}
    got = {k: [e.text for e in root.findall('.//' + tag, ns)] for k, tag in
           [('titles', 'd:title'), ('authors', 'pg:name'), ('deathdates', 'pg:deathdate'), ('rights', 'd:rights')]}
    expected = dict(titles=['The Yellow Wallpaper'], authors=['Gilman, Charlotte Perkins'],
                    deathdates=['1935'], rights=['Public domain in the USA.'])
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
            p['provider_input_allowed'] is not False or p['h_entry_executed'] is not False or
            p['native_question_or_answer_files_used'] is not False or
            p['provider_calls'] != 0 or p['provider_spend_usd'] != 0 or
            p['longmemeval'] != 'SEALED_NOT_ACCESSED'):
        raise ValueError('protected source boundary drift')
    return p


def screen(repository, raw, rdf):
    p = load_package()
    body = original_body(raw)
    meta = publisher_metadata(rdf)
    # No implementation/preparation repair uses this candidate. Source holder
    # applies only existing negative exposure screens and returns fingerprints.
    history = audit_history(repository, body)
    snapshot = audit_snapshot(repository, 'HEAD', body)
    clean = (history['status'] == 'REACHABLE_HISTORY_NO_TEXT_MATCH' and
             snapshot['status'] == 'TEXT_SNAPSHOT_NO_MATCH')
    return dict(schema='hcl-i02-gilman-protected-history-screen-v1',
        status='READY_FOR_SOURCE_FIRST_HOLDER_REVIEW' if clean else 'EXPOSURE_REVIEW_REQUIRED',
        package_sha256=sha(PACKAGE.read_bytes()), publisher_metadata=meta,
        publisher_metadata_sha256=sha(rdf), raw_sha256=sha(raw),
        source_sha256=sha(body.encode()), source_characters=len(body),
        question_sha256=sha(QUESTION.encode()),
        ordinary_input_sha256=sha(json.dumps(ordinary_input(body), sort_keys=True).encode()),
        complete_original_body=True, history=history, snapshot=snapshot,
        source_text_displayed=False, native_gold_used=False, h_entry_executed=False,
        source_used_for_runtime_repair=False, task_fit='PENDING_INDEPENDENT_SOURCE_FIRST_REVIEW',
        model_training_novelty='UNKNOWN_PUBLIC_CANONICAL_1892_WORK',
        rights_scope=p['rights_scope'], confirmation_qualified=False,
        provider_input_allowed=False, provider_calls=0, provider_spend_usd=0,
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
