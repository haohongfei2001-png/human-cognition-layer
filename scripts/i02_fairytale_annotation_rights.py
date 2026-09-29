"""Pin author-team annotation provenance without releasing a held-out case."""

import hashlib
import json
from pathlib import Path

from scripts.i02_fairytale_metadata import LICENSE, PACKAGE, validate_metadata_only


README_SHA256 = '6787b4cdb8d70a2fc21c9daaf2ef5813037891d5ae3cf982de5aa5195b4dfd3e'
README_BLOB = '09fcb6ce539b670414fffc7a9fb1413102ba9a83'
LICENSE_BLOB = 'b6076b10d587404f9f73a523876eecc1deaa47e0'
AUTHORSHIP_PHRASES = (
    'questions and answers developed by educational experts',
    'education experts labeled qa-pairs',
)


def _blob(raw):
    return hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()


def audit_annotation_rights(readme_raw: bytes, license_raw: bytes) -> dict:
    candidate = json.loads(PACKAGE.read_text())
    validate_metadata_only(candidate)
    if (hashlib.sha256(readme_raw).hexdigest() != README_SHA256 or
            _blob(readme_raw) != README_BLOB):
        raise ValueError('pinned author-team README differs')
    if (hashlib.sha256(license_raw).hexdigest() !=
            candidate['author_team_license_sha256'] or
            _blob(license_raw) != LICENSE_BLOB or
            license_raw != LICENSE.read_bytes()):
        raise ValueError('pinned author-team LICENSE differs')
    try:
        readme = readme_raw.decode('utf-8').casefold()
        license_text = license_raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('author-team evidence encoding differs') from exc
    if any(phrase not in readme for phrase in AUTHORSHIP_PHRASES):
        raise ValueError('annotation authorship statement missing')
    if ('Apache License' not in license_text or
            'Version 2.0, January 2004' not in license_text):
        raise ValueError('repository license text differs')
    return {
        'schema': 'hcl-i02-fairytale-annotation-rights-v1',
        'author_team_commit': candidate['author_team_commit'],
        'publisher_readme_sha256': README_SHA256,
        'publisher_readme_git_blob': README_BLOB,
        'publisher_license_sha256': candidate['author_team_license_sha256'],
        'publisher_license_git_blob': LICENSE_BLOB,
        'expert_authored_questions_reported_by_publisher': True,
        'root_apache_2_license_pinned': True,
        'annotation_license_scope': 'ROOT_LICENSE_AND_AUTHORSHIP_EVIDENCE_PROVIDER_USE_REVIEW_PENDING',
        'underlying_story_rights': 'SEPARATE_SCOPED_EDITION_MATCH_USA_CHINA_ONLY',
        'provider_processing_geography': 'UNVERIFIED',
        'question_semantics': 'NOT_AUDITED',
        'task_family_fit': 'UNPROVEN',
        'model_input_allowed': False,
        'confirmation_qualified': False,
        'story_question_or_answer_text_returned': False,
        'provider_calls': 0,
        'longmemeval': 'SEALED_NOT_ACCESSED',
    }
