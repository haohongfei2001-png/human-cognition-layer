"""Check whether publisher summary tags span this preselected long story."""

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

from scripts.i02_fairytale_metadata import PACKAGE
from scripts.i02_fairytale_question_metadata import audit_question_tags


def audit_section_span(raw: bytes) -> dict:
    tag_receipt = audit_question_tags(raw)
    package = json.loads(PACKAGE.read_text())
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    spans = []
    summary_categories = Counter()
    for row in rows:
        if row['local-or-sum'] != 'summary':
            continue
        if not re.fullmatch(r'\d+,\d+', row['cor_section']):
            raise ValueError('summary section reference structure differs')
        first, second = map(int, row['cor_section'].split(','))
        if not 1 <= first < second <= package['selected_sections_metadata']:
            raise ValueError('summary references invalid source sections')
        spans.append(second - first)
        summary_categories[row['attribute1']] += 1
    if len(spans) != tag_receipt['local_or_summary_counts']['summary']:
        raise ValueError('summary count differs from pinned tag audit')
    return {
        'schema': 'hcl-i02-fairytale-section-span-audit-v1',
        'publisher_question_sha256': tag_receipt['publisher_question_sha256'],
        'publisher_question_git_blob': tag_receipt['publisher_question_git_blob'],
        'source_section_count': package['selected_sections_metadata'],
        'summary_item_count': len(spans),
        'summary_section_span_counts': dict(sorted(Counter(spans).items())),
        'maximum_summary_section_span': max(spans),
        'summary_character_or_feeling_tagged_count':
            sum(summary_categories[tag] for tag in ('character', 'feeling')),
        'task_family': 'LONG_CHARACTER_DEVELOPMENT',
        'task_family_fit': 'NOT_SUPPORTED_BY_PUBLISHER_TAG_AND_SECTION_METADATA',
        'question_or_answer_text_returned': False,
        'story_text_returned': False,
        'model_input_allowed': False,
        'confirmation_qualified': False,
        'provider_calls': 0,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('question_file')
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    result = audit_section_span(Path(args.question_file).read_bytes())
    Path(args.receipt).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('SECTION_SPAN_AUDIT_PASS_FAMILY_UNQUALIFIED')
