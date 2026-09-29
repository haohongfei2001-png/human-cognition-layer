"""Verify a pinned held-out story's upstream edition without printing its text.

Inputs are local raw files acquired separately. The function emits only
hashes, counts and exact normalized containment; it never reads questions or
answers. This does not judge task fit or semantic answer validity.
"""

import argparse
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from scripts.i02_fairytale_metadata import validate_metadata_only


STORY_SHA256 = 'd4c92d2c038bae6ff535e051cad53d9ee4092bb49e3ecdd2a13ef6c5bb961891'
STORY_GIT_BLOB = 'ad5754d177a8e85ff9800896d8c7f592d32fe883'
BOOK_SHA256 = 'a17eec00fcaaba3d8e3496945486a3be8a984cbb694d4f6db0f4616e782af115'
BOOK_URL = 'https://www.gutenberg.org/cache/epub/4018/pg4018.txt'
STORY_SECTIONS = 43
STORY_WORDS = 5800
BOOK_WORDS = 74685


def _words(text):
    return re.findall(r'[a-z0-9]+', text.casefold())


def blind_match(story_raw, book_raw):
    validate_metadata_only()
    if hashlib.sha256(story_raw).hexdigest() != STORY_SHA256:
        raise ValueError('pinned story bytes differ')
    blob = hashlib.sha1(f'blob {len(story_raw)}\0'.encode() + story_raw).hexdigest()
    if blob != STORY_GIT_BLOB:
        raise ValueError('publisher story Git blob differs')
    if hashlib.sha256(book_raw).hexdigest() != BOOK_SHA256:
        raise ValueError('pinned Gutenberg edition bytes differ')
    try:
        rows = list(csv.DictReader(io.StringIO(story_raw.decode('utf-8-sig'))))
        book_text = book_raw.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('source encoding differs') from exc
    if len(rows) != STORY_SECTIONS or set(rows[0]) != {'section', 'text'} or any(
            not row['text'] for row in rows):
        raise ValueError('story section structure differs')
    story_words = _words(' '.join(row['text'] for row in rows))
    book_words = _words(book_text)
    if len(story_words) != STORY_WORDS or len(book_words) != BOOK_WORDS:
        raise ValueError('pinned normalized token counts differ')
    # Exact continuous normalized membership is stronger than sampled n-grams.
    # It reveals no source words or matching offset to the caller.
    found = (' '.join(story_words) in ' '.join(book_words))
    if not found:
        raise ValueError('dataset story is not a contiguous normalized edition excerpt')
    return {
        'schema': 'hcl-i02-fairytale-blind-edition-match-v1',
        'publisher_story_sha256': STORY_SHA256,
        'publisher_story_git_blob': blob,
        'gutenberg_edition_url': BOOK_URL,
        'gutenberg_edition_sha256': BOOK_SHA256,
        'story_sections': len(rows),
        'story_normalized_words': len(story_words),
        'book_normalized_words': len(book_words),
        'exact_normalized_contiguous_match': True,
        'story_text_returned': False,
        'questions_or_answers_read': False,
        'provider_calls': 0,
        'confirmation_qualified': False,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('story_file')
    parser.add_argument('book_file')
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    result = blind_match(Path(args.story_file).read_bytes(),
        Path(args.book_file).read_bytes())
    Path(args.receipt).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('BLIND_EDITION_MATCH_PASS')
