"""Pin a possible independent long-narrative source without opening content."""

import csv
import hashlib
import io
import json
from pathlib import Path


PACKAGE = Path('reports/HCL_I02_FAIRYTALE_METADATA_CANDIDATE.json')
METADATA = Path('reports/HCL_I02_FAIRYTALE_METADATA.csv')
LICENSE = Path('reports/HCL_I02_FAIRYTALE_APACHE_LICENSE.txt')


def validate_metadata_only(package=None, raw=None):
    package = package or json.loads(PACKAGE.read_text())
    raw = METADATA.read_bytes() if raw is None else raw
    if (package.get('schema') != 'hcl-i02-fairytale-metadata-candidate-v1' or
            package.get('status') != 'PRESELECTED_METADATA_ONLY_NOT_MODEL_INPUT_QUALIFIED' or
            package.get('selection_rule') !=
                'LONGEST_JAPANESE_FAIRYBOOK_STORY_EXCLUDING_KNOWN_PUBLIC_SNIPPET_GROUP'):
        raise ValueError('unrecognized metadata-only source freeze')
    if hashlib.sha256(raw).hexdigest() != package.get('metadata_sha256'):
        raise ValueError('publisher metadata bytes differ from freeze')
    if hashlib.sha256(LICENSE.read_bytes()).hexdigest() != package.get('author_team_license_sha256'):
        raise ValueError('publisher license copy differs from freeze')
    if any(package.get(key) is not False for key in (
            'source_text_opened', 'questions_opened', 'native_answers_opened',
            'model_input_allowed', 'confirmation_qualified')):
        raise ValueError('metadata receipt cannot promote unseen content')
    if (package.get('item_semantic_audit') != 'NOT_STARTED' or
            package.get('provider_calls') != 0 or package.get('provider_spend_usd') != 0 or
            package.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('metadata stage cannot claim item/provider outcome')
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if len(rows) != 278 or set(rows[0]) != {
            'filename', 'origin', 'split', 'sections', 'words', 'questions'}:
        raise ValueError('publisher metadata shape drift')
    if len({row['filename'] for row in rows}) != len(rows):
        raise ValueError('duplicate story metadata')
    for row in rows:
        if any(not row[key] for key in ('filename', 'origin', 'split')):
            raise ValueError('incomplete story metadata')
        if any(not row[key].isdigit() for key in ('sections', 'words', 'questions')):
            raise ValueError('invalid metadata counts')
    choices = [row for row in rows if row['origin'] == 'japanese-fairybook' and
        row['filename'] != package['excluded_search_snippet_group']]
    if not choices:
        raise ValueError('no unexposed metadata candidate')
    selected = sorted(choices, key=lambda row: (-int(row['words']), row['filename']))[0]
    expected = {'filename': package['selected_story_filename'],
        'origin': package['selected_origin'], 'split': package['selected_native_split'],
        'sections': str(package['selected_sections_metadata']),
        'words': str(package['selected_words_metadata']),
        'questions': str(package['selected_question_count_metadata'])}
    if selected != expected:
        raise ValueError('predeclared candidate is not metadata selection')
    if not all(isinstance(package.get(key), str) and len(package[key]) == 40 for key in (
            'author_team_commit', 'selected_story_git_blob', 'selected_questions_git_blob')):
        raise ValueError('exact publisher commit/blob IDs required')
    if not package.get('rights_status', '').startswith('PROVISIONAL_'):
        raise ValueError('content/edition rights not yet qualified')
    return {'selected': selected, 'qualified': False,
        'source_text_opened': False, 'questions_opened': False,
        'native_answers_opened': False, 'provider_calls': 0}


if __name__ == '__main__':
    print(json.dumps(validate_metadata_only(), sort_keys=True))
