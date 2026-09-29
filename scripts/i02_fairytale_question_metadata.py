"""Audit pinned FairytaleQA question tags without returning question/answer text.

This is a task-fit screen, not a semantic judgment or confirmation release.
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

from scripts.i02_fairytale_metadata import PACKAGE, validate_metadata_only


QUESTION_SHA256 = '54a03fb11936d2363371ecbeb74f08695680fffd699507f9db0fcd7f5fb92f13'
QUESTION_GIT_BLOB = 'a8b6251f1826940eef45b4ba7abef8a05089778e'
EXPECTED_COLUMNS = (
    'question_id', 'local-or-sum', 'cor_section', 'attribute1', 'attribute2',
    'question', 'ex-or-im1', 'answer1', 'answer2', 'answer3', 'ex-or-im2',
    'answer4', 'answer5', 'answer6',
)
ALLOWED_CATEGORIES = frozenset({
    'action', 'causal relationship', 'character', 'feeling',
    'outcome resolution', 'prediction', 'setting',
})


def audit_question_tags(raw: bytes) -> dict:
    candidate = json.loads(PACKAGE.read_text())
    validate_metadata_only(candidate)
    if hashlib.sha256(raw).hexdigest() != QUESTION_SHA256:
        raise ValueError('pinned question bytes differ')
    blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if blob != QUESTION_GIT_BLOB or candidate['selected_questions_git_blob'] != blob:
        raise ValueError('publisher question Git blob differs')
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise ValueError('publisher question metadata columns differ')
        rows = list(reader)
    except UnicodeDecodeError as exc:
        raise ValueError('publisher question encoding differs') from exc
    if len(rows) != candidate['selected_question_count_metadata'] or any(
            row.get(None) is not None or any(row[key] is None for key in EXPECTED_COLUMNS)
            for row in rows):
        raise ValueError('publisher question row structure differs')
    if len({row['question_id'] for row in rows}) != len(rows):
        raise ValueError('duplicate publisher question identifier')
    if any(row['local-or-sum'] not in {'local', 'summary'} for row in rows):
        raise ValueError('unknown local/summary tag')
    if any(row['attribute1'] not in ALLOWED_CATEGORIES for row in rows):
        raise ValueError('unknown question category tag')

    # The publisher's categorical tags are inspected; the question and answer
    # fields are deliberately never read by this function or returned.
    level = dict(sorted(Counter(row['local-or-sum'] for row in rows).items()))
    category = dict(sorted(Counter(row['attribute1'] for row in rows).items()))
    summary = dict(sorted(Counter(row['attribute1'] for row in rows
                                  if row['local-or-sum'] == 'summary').items()))
    summary_character_or_feeling = sum(summary.get(tag, 0)
                                       for tag in ('character', 'feeling'))
    return {
        'schema': 'hcl-i02-fairytale-question-tag-audit-v1',
        'publisher_question_sha256': QUESTION_SHA256,
        'publisher_question_git_blob': blob,
        'question_count': len(rows),
        'local_or_summary_counts': level,
        'attribute1_counts': category,
        'summary_attribute1_counts': summary,
        'summary_character_or_feeling_tagged_count': summary_character_or_feeling,
        'task_family': 'LONG_CHARACTER_DEVELOPMENT',
        'task_family_fit': 'UNPROVEN_BY_METADATA',
        'question_file_processed_for_tags': True,
        'question_text_returned': False,
        'native_answer_text_returned': False,
        'source_text_returned': False,
        'item_semantic_audit': 'NOT_STARTED',
        'model_input_allowed': False,
        'confirmation_qualified': False,
        'provider_calls': 0,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('question_file')
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    result = audit_question_tags(Path(args.question_file).read_bytes())
    Path(args.receipt).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('QUESTION_TAG_AUDIT_PASS_UNQUALIFIED')
