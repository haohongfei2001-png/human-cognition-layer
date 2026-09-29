"""Pinned QuALITY metadata screen; never print article, question or answer text."""
import argparse
import hashlib
import json
from pathlib import Path


SOURCE_SHA256 = '227fe5cffbe127f29489e6ba46cc1d28aee5ea02c8af77eacc8f37673d9a9990'
SOURCE_BLOB = 'b212a78bdb23c0a6e0a0e3de7424a7057c8e5f1f'
PUBLISHER_COMMIT = 'f84977c40dbfef70c9cab48037b7becfc8e45f73'
ARTICLE_ID = '99919'
WRITER_ID = '1020'
ARTICLE_URL = 'https://thelongandshort.org/society/can-women-do-politics-differently'


def _majority(values, predicate):
    if not values:
        return False
    return sum(bool(predicate(value)) for value in values) > len(values) / 2


def build_report(raw, *, expected_sha256=SOURCE_SHA256):
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('pinned QuALITY development file hash mismatch')
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    article_rows = [row for row in rows if row.get('article_id') == ARTICLE_ID]
    selected = [row for row in article_rows if row.get('writer_id') == WRITER_ID]
    if (len(article_rows) != 2 or len(selected) != 1 or
            any(row.get('url') != ARTICLE_URL or row.get('source') != 'misc-longshort'
                for row in article_rows)):
        raise ValueError('preselected article metadata changed')
    row = selected[0]
    questions = row.get('questions')
    if not isinstance(questions, list) or not questions:
        raise ValueError('preselected writer questions missing')
    context_broad = 0
    answerable = 0
    for question in questions:
        validations = question.get('validation')
        if not isinstance(validations, list) or not validations:
            raise ValueError('human validation metadata missing')
        context = [int(v['untimed_eval2_context']) for v in validations]
        clarity = [int(v['untimed_eval1_answerability']) for v in validations]
        if any(v not in (1, 2, 3, 4) for v in context) or any(v not in (1, 2, 3) for v in clarity):
            raise ValueError('unexpected validation vocabulary')
        context_broad += _majority(context, lambda value: value >= 3)
        answerable += _majority(clarity, lambda value: value == 1)
    return {
        'schema': 'hcl-i02-quality-bounded-screen-v1',
        'publisher_commit': PUBLISHER_COMMIT,
        'publisher_file_blob': SOURCE_BLOB,
        'publisher_file_sha256': expected_sha256,
        'split': 'dev',
        'article_id': ARTICLE_ID,
        'selected_writer_id': WRITER_ID,
        'article_writer_set_count': len(article_rows),
        'selected_writer_question_count': len(questions),
        'human_majority_at_least_third_context_count': context_broad,
        'human_majority_answerable_count': answerable,
        'selected_article_sha256': hashlib.sha256(row['article'].encode()).hexdigest(),
        'selected_question_texts_sha256': hashlib.sha256(json.dumps(
            [q['question'] for q in questions], ensure_ascii=False,
            separators=(',', ':')).encode()).hexdigest(),
        'source_or_question_text_returned': False,
        'gold_or_options_returned': False,
        'implementer_article_body_opened_separately': True,
        'implementer_selected_question_texts_opened_separately': True,
        'native_gold_and_options_opened': False,
        'provider_calls': 0,
        'model_input_allowed': False,
        'confirmation_qualified': False,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pinned_dev_file', type=Path)
    args = parser.parse_args()
    print(json.dumps(build_report(args.pinned_dev_file.read_bytes()),
        ensure_ascii=False, indent=2, sort_keys=True))
